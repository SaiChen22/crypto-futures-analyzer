"""
Main entry point for Crypto Futures Analyzer.
Runs analysis and sends notifications via Telegram.
"""

import asyncio
import logging
import sys
from typing import List, Dict, Tuple
from datetime import datetime

from .config import load_config, validate_config, Config
from .exchanges.binance import BinanceFuturesClient
from .analysis.technical import analyze_technicals, TechnicalSignal
from .analysis.funding import analyze_funding_rate, FundingSignal
from .analysis.liquidation import (
    analyze_liquidations, 
    estimate_liquidations_from_trades,
    LiquidationSignal
)
from .analysis.signals import (
    aggregate_signals,
    filter_signals,
    rank_signals,
    AggregatedSignal,
    SignalType
)
from .notifications.telegram import (
    TelegramNotifier,
    format_detailed_signal,
    format_signals_summary
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)


async def analyze_symbol(
    client: BinanceFuturesClient,
    symbol: str,
    config: Config
) -> Dict[str, AggregatedSignal]:
    """
    Perform full analysis on a single symbol across all timeframes.
    
    Args:
        client: Binance API client
        symbol: Trading pair symbol
        config: Application config
        
    Returns:
        Dict mapping timeframe to AggregatedSignal
    """
    results = {}
    
    for timeframe in config.timeframes:
        try:
            # Fetch OHLCV data
            df = client.get_klines(symbol, timeframe, limit=100)
            
            # Technical analysis
            technical = analyze_technicals(
                df=df,
                symbol=symbol,
                timeframe=timeframe,
                rsi_oversold=config.rsi_oversold,
                rsi_overbought=config.rsi_overbought,
                ema_short_period=config.ema_short_period,
                ema_long_period=config.ema_long_period,
                volume_spike_threshold=config.volume_spike_threshold
            )
            
            # Funding rate analysis
            funding_data = client.get_funding_rate(symbol)
            funding = analyze_funding_rate(
                symbol=symbol,
                funding_rate=funding_data['funding_rate'],
                next_funding_time=funding_data.get('funding_time'),
                extreme_positive_threshold=config.funding_rate_extreme_positive,
                extreme_negative_threshold=config.funding_rate_extreme_negative
            )
            
            # Liquidation analysis (estimate from recent trades)
            trades = client.get_recent_trades(symbol, limit=500)
            long_liqs, short_liqs = estimate_liquidations_from_trades(trades)
            liquidation = analyze_liquidations(
                symbol=symbol,
                long_liquidations_usd=long_liqs,
                short_liquidations_usd=short_liqs,
                threshold_usd=config.liquidation_threshold_usd
            )
            
            # Aggregate all signals
            aggregated = aggregate_signals(
                symbol=symbol,
                timeframe=timeframe,
                technical=technical,
                funding=funding,
                liquidation=liquidation
            )
            
            results[timeframe] = aggregated
            
        except Exception as e:
            logger.error(f"Error analyzing {symbol} on {timeframe}: {e}")
            continue
    
    return results


async def run_analysis(config: Config) -> Tuple[List[AggregatedSignal], List[AggregatedSignal]]:
    """
    Run full analysis on all tracked symbols.
    
    Args:
        config: Application config
        
    Returns:
        Tuple of (long_signals, short_signals)
    """
    logger.info("Starting analysis...")
    
    # Initialize Binance client
    client = BinanceFuturesClient(
        api_key=config.binance_api_key,
        api_secret=config.binance_api_secret
    )
    
    # Get top symbols by volume
    logger.info(f"Fetching top {config.top_coins_count} futures symbols...")
    symbols = client.get_top_futures_symbols(limit=config.top_coins_count)
    logger.info(f"Analyzing symbols: {', '.join(symbols[:5])}... ({len(symbols)} total)")
    
    all_signals: List[AggregatedSignal] = []
    
    # Analyze each symbol
    for symbol in symbols:
        try:
            symbol_results = await analyze_symbol(client, symbol, config)
            
            # Add all timeframe results
            for timeframe, signal in symbol_results.items():
                if signal.signal_type != SignalType.NEUTRAL:
                    all_signals.append(signal)
                    
        except Exception as e:
            logger.error(f"Failed to analyze {symbol}: {e}")
            continue
    
    logger.info(f"Analysis complete. Found {len(all_signals)} potential signals.")
    
    # Filter by minimum score
    filtered = filter_signals(all_signals, min_score=config.min_signal_score)
    logger.info(f"After filtering (min score {config.min_signal_score}): {len(filtered)} signals")
    
    # Rank and separate long/short
    ranked = rank_signals(filtered, top_n=5)
    
    return ranked['long'], ranked['short']


async def send_notifications(
    config: Config,
    long_signals: List[AggregatedSignal],
    short_signals: List[AggregatedSignal]
) -> None:
    """
    Send analysis results via Telegram.
    
    Args:
        config: Application config
        long_signals: List of long signals
        short_signals: List of short signals
    """
    notifier = TelegramNotifier(
        bot_token=config.telegram_bot_token,
        chat_id=config.telegram_chat_id
    )
    
    if not long_signals and not short_signals:
        logger.info("No strong signals found, sending notification...")
        await notifier.send_no_signals_message()
        return
    
    # Send summary
    logger.info("Sending signals summary...")
    await notifier.send_signals_summary(long_signals, short_signals)
    
    # Send detailed alerts for very strong signals (score >= 8.5)
    very_strong = [
        s for s in (long_signals + short_signals) 
        if s.total_score >= 8.5
    ]
    
    for signal in very_strong[:3]:  # Limit to top 3 detailed alerts
        message = format_detailed_signal(signal)
        await notifier.send_message(message)
        await asyncio.sleep(1)  # Rate limiting
    
    logger.info(f"Sent {len(very_strong)} detailed alerts")


async def main() -> int:
    """Main entry point."""
    logger.info("=" * 50)
    logger.info("Crypto Futures Analyzer")
    logger.info(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 50)
    
    # Load configuration
    config = load_config()
    
    # Validate configuration
    errors = validate_config(config)
    if errors:
        for error in errors:
            logger.error(f"Config error: {error}")
        return 1
    
    try:
        # Run analysis
        long_signals, short_signals = await run_analysis(config)
        
        logger.info(f"Found {len(long_signals)} long signals, {len(short_signals)} short signals")
        
        # Log top signals
        if long_signals:
            logger.info("Top LONG signals:")
            for s in long_signals[:3]:
                logger.info(f"  - {s.symbol} ({s.timeframe}): {s.total_score}/10")
        
        if short_signals:
            logger.info("Top SHORT signals:")
            for s in short_signals[:3]:
                logger.info(f"  - {s.symbol} ({s.timeframe}): {s.total_score}/10")
        
        # Send notifications
        await send_notifications(config, long_signals, short_signals)
        
        logger.info("Analysis complete!")
        return 0
        
    except Exception as e:
        logger.error(f"Analysis failed: {e}", exc_info=True)
        return 1


def run():
    """Synchronous entry point for running from command line."""
    exit_code = asyncio.run(main())
    sys.exit(exit_code)


if __name__ == "__main__":
    run()
