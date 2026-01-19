"""
Liquidation analysis module.
Large liquidations can indicate potential reversals or momentum continuation.
"""

import logging
from dataclasses import dataclass
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


@dataclass
class LiquidationSignal:
    """Liquidation analysis result."""
    symbol: str
    
    # Recent liquidation data
    total_long_liquidations_usd: float
    total_short_liquidations_usd: float
    net_liquidations_usd: float  # Positive = more longs liquidated
    
    # Analysis
    signal: str  # 'long', 'short', 'neutral'
    description: str
    
    # Score contribution
    score: float  # 0-10 scale


def analyze_liquidations(
    symbol: str,
    long_liquidations_usd: float,
    short_liquidations_usd: float,
    threshold_usd: float = 1_000_000  # $1M threshold for significance
) -> LiquidationSignal:
    """
    Analyze liquidation data for trading signals.
    
    Liquidation logic:
    - Large long liquidations -> Price dropped -> Potential bottom -> Long opportunity
    - Large short liquidations -> Price spiked -> Potential top -> Short opportunity
    - The net difference indicates which side was hurt more
    
    Args:
        symbol: Trading pair symbol
        long_liquidations_usd: Total long liquidations in USD
        short_liquidations_usd: Total short liquidations in USD
        threshold_usd: Minimum USD value for significant liquidations
        
    Returns:
        LiquidationSignal with analysis results
    """
    net_liquidations = long_liquidations_usd - short_liquidations_usd
    total_liquidations = long_liquidations_usd + short_liquidations_usd
    
    signal = 'neutral'
    score = 0.0
    description = ""
    
    # Check if liquidations are significant
    if total_liquidations < threshold_usd / 2:
        signal = 'neutral'
        score = 0
        description = (
            f"Low liquidation activity. "
            f"Longs: ${long_liquidations_usd:,.0f}, Shorts: ${short_liquidations_usd:,.0f}"
        )
        
    # Large long liquidations -> Potential long opportunity (contrarian)
    elif long_liquidations_usd >= threshold_usd and long_liquidations_usd > short_liquidations_usd * 1.5:
        signal = 'long'
        # Score based on magnitude of liquidations
        magnitude_score = min(long_liquidations_usd / threshold_usd, 5)
        imbalance_score = min((long_liquidations_usd / max(short_liquidations_usd, 1) - 1), 5)
        score = min(magnitude_score + imbalance_score, 10)
        description = (
            f"Large long liquidations detected (${long_liquidations_usd:,.0f}). "
            f"Potential capitulation - consider long positions."
        )
        
    # Large short liquidations -> Potential short opportunity (contrarian)
    elif short_liquidations_usd >= threshold_usd and short_liquidations_usd > long_liquidations_usd * 1.5:
        signal = 'short'
        magnitude_score = min(short_liquidations_usd / threshold_usd, 5)
        imbalance_score = min((short_liquidations_usd / max(long_liquidations_usd, 1) - 1), 5)
        score = min(magnitude_score + imbalance_score, 10)
        description = (
            f"Large short liquidations detected (${short_liquidations_usd:,.0f}). "
            f"Potential short squeeze exhaustion - consider short positions."
        )
        
    # Balanced but significant liquidations
    elif total_liquidations >= threshold_usd:
        signal = 'neutral'
        score = 0
        description = (
            f"Balanced liquidations. "
            f"Longs: ${long_liquidations_usd:,.0f}, Shorts: ${short_liquidations_usd:,.0f}"
        )
    
    else:
        signal = 'neutral'
        score = 0
        description = "No significant liquidation activity detected."
    
    return LiquidationSignal(
        symbol=symbol,
        total_long_liquidations_usd=long_liquidations_usd,
        total_short_liquidations_usd=short_liquidations_usd,
        net_liquidations_usd=net_liquidations,
        signal=signal,
        description=description,
        score=round(score, 1)
    )


def estimate_liquidations_from_trades(
    trades: List[Dict[str, Any]],
    price_threshold_percent: float = 0.5
) -> tuple[float, float]:
    """
    Estimate liquidation volumes from trade data.
    
    This is an approximation since Binance doesn't provide direct liquidation data
    via REST API. Large trades at sharp price movements are likely liquidations.
    
    Args:
        trades: List of recent trades
        price_threshold_percent: Price movement threshold to consider as liquidation
        
    Returns:
        Tuple of (estimated_long_liquidations, estimated_short_liquidations)
    """
    if not trades:
        return 0.0, 0.0
    
    long_liqs = 0.0
    short_liqs = 0.0
    
    # Sort trades by time
    sorted_trades = sorted(trades, key=lambda x: x['time'])
    
    for i, trade in enumerate(sorted_trades[1:], 1):
        prev_trade = sorted_trades[i - 1]
        
        # Calculate price change
        if prev_trade['price'] > 0:
            price_change = (trade['price'] - prev_trade['price']) / prev_trade['price'] * 100
        else:
            continue
        
        # Large sell during price drop -> likely long liquidation
        if price_change < -price_threshold_percent and trade['is_buyer_maker']:
            long_liqs += trade['quote_qty']
        
        # Large buy during price spike -> likely short liquidation
        elif price_change > price_threshold_percent and not trade['is_buyer_maker']:
            short_liqs += trade['quote_qty']
    
    return long_liqs, short_liqs


def analyze_liquidations_batch(
    symbols: List[str],
    liquidation_data: Dict[str, tuple[float, float]],
    threshold_usd: float = 1_000_000
) -> Dict[str, LiquidationSignal]:
    """
    Analyze liquidations for multiple symbols.
    
    Args:
        symbols: List of symbols to analyze
        liquidation_data: Dict mapping symbol to (long_liqs, short_liqs)
        threshold_usd: USD threshold for significance
        
    Returns:
        Dict mapping symbol to LiquidationSignal
    """
    results = {}
    
    for symbol in symbols:
        long_liqs, short_liqs = liquidation_data.get(symbol, (0.0, 0.0))
        results[symbol] = analyze_liquidations(
            symbol=symbol,
            long_liquidations_usd=long_liqs,
            short_liquidations_usd=short_liqs,
            threshold_usd=threshold_usd
        )
    
    return results
