"""
Configuration management for Crypto Futures Analyzer.
Loads settings from environment variables.
"""

import os
from dataclasses import dataclass
from typing import List


@dataclass
class Config:
    """Application configuration loaded from environment variables."""
    
    # Binance API credentials (optional - will use fallback if unavailable)
    binance_api_key: str
    binance_api_secret: str
    
    # Telegram settings
    telegram_bot_token: str
    telegram_chat_id: str
    
    # Exchange settings
    preferred_exchange: str  # 'auto', 'binance', 'bybit', 'okx'
    
    # Analysis settings
    timeframes: List[str]
    top_coins_count: int
    min_signal_score: float
    
    # Funding rate thresholds (extreme values indicating potential reversal)
    funding_rate_extreme_positive: float  # Above this = potential short
    funding_rate_extreme_negative: float  # Below this = potential long
    
    # Technical indicator settings
    rsi_oversold: float
    rsi_overbought: float
    ema_short_period: int
    ema_long_period: int
    
    # Volume spike threshold (multiplier of average volume)
    volume_spike_threshold: float
    
    # Liquidation threshold (USD) - only consider significant liquidations
    liquidation_threshold_usd: float


def load_config() -> Config:
    """Load configuration from environment variables with defaults."""
    
    return Config(
        # API credentials (optional - fallback exchanges don't need keys)
        binance_api_key=os.environ.get("BINANCE_API_KEY", ""),
        binance_api_secret=os.environ.get("BINANCE_API_SECRET", ""),
        telegram_bot_token=os.environ.get("TELEGRAM_BOT_TOKEN", ""),
        telegram_chat_id=os.environ.get("TELEGRAM_CHAT_ID", ""),
        
        # Exchange preference: auto will try Binance first, then fallback
        preferred_exchange=os.environ.get("PREFERRED_EXCHANGE", "auto"),
        
        # Analysis settings
        timeframes=os.environ.get("TIMEFRAMES", "1h,4h").split(","),
        top_coins_count=int(os.environ.get("TOP_COINS_COUNT", "20")),
        min_signal_score=float(os.environ.get("MIN_SIGNAL_SCORE", "7.0")),
        
        # Funding rate thresholds
        funding_rate_extreme_positive=float(os.environ.get("FUNDING_EXTREME_POSITIVE", "0.1")),  # 0.1%
        funding_rate_extreme_negative=float(os.environ.get("FUNDING_EXTREME_NEGATIVE", "-0.1")),  # -0.1%
        
        # Technical indicators
        rsi_oversold=float(os.environ.get("RSI_OVERSOLD", "30")),
        rsi_overbought=float(os.environ.get("RSI_OVERBOUGHT", "70")),
        ema_short_period=int(os.environ.get("EMA_SHORT_PERIOD", "12")),
        ema_long_period=int(os.environ.get("EMA_LONG_PERIOD", "26")),
        
        # Volume
        volume_spike_threshold=float(os.environ.get("VOLUME_SPIKE_THRESHOLD", "2.0")),
        
        # Liquidations
        liquidation_threshold_usd=float(os.environ.get("LIQUIDATION_THRESHOLD_USD", "1000000")),  # $1M
    )


def validate_config(config: Config) -> List[str]:
    """Validate configuration and return list of errors."""
    errors = []
    
    # Telegram is required
    if not config.telegram_bot_token:
        errors.append("TELEGRAM_BOT_TOKEN is not set")
    if not config.telegram_chat_id:
        errors.append("TELEGRAM_CHAT_ID is not set")
    
    # Binance keys are optional (will fallback to Bybit/OKX)
    if not config.binance_api_key or not config.binance_api_secret:
        # Not an error, just a warning - will use fallback exchanges
        pass
    
    if config.min_signal_score < 0 or config.min_signal_score > 10:
        errors.append("MIN_SIGNAL_SCORE must be between 0 and 10")
    
    if config.rsi_oversold >= config.rsi_overbought:
        errors.append("RSI_OVERSOLD must be less than RSI_OVERBOUGHT")
    
    valid_exchanges = ['auto', 'binance', 'bybit', 'okx']
    if config.preferred_exchange.lower() not in valid_exchanges:
        errors.append(f"PREFERRED_EXCHANGE must be one of: {', '.join(valid_exchanges)}")
    
    return errors
