"""
Technical analysis module for calculating trading indicators.
"""

import logging
from dataclasses import dataclass
from typing import Dict, Any, Optional, Tuple

import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class TechnicalSignal:
    """Result of technical analysis for a symbol."""
    symbol: str
    timeframe: str
    
    # RSI
    rsi: float
    rsi_signal: str  # 'oversold', 'overbought', 'neutral'
    
    # MACD
    macd: float
    macd_signal: float
    macd_histogram: float
    macd_crossover: str  # 'bullish', 'bearish', 'none'
    
    # EMA
    ema_short: float
    ema_long: float
    ema_crossover: str  # 'bullish', 'bearish', 'none'
    price_vs_ema: float  # Percentage above/below EMA
    
    # Volume
    volume_ratio: float  # Current volume vs average
    volume_spike: bool
    
    # Price action
    current_price: float
    price_change_percent: float
    
    # Overall bias
    bias: str  # 'long', 'short', 'neutral'
    strength: float  # 0-10 scale


def calculate_rsi(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """
    Calculate Relative Strength Index.
    
    Args:
        df: DataFrame with 'close' column
        period: RSI period (default 14)
        
    Returns:
        Series with RSI values
    """
    delta = df['close'].diff()
    
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    
    return rsi


def calculate_macd(
    df: pd.DataFrame, 
    fast: int = 12, 
    slow: int = 26, 
    signal: int = 9
) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """
    Calculate MACD indicator.
    
    Args:
        df: DataFrame with 'close' column
        fast: Fast EMA period
        slow: Slow EMA period
        signal: Signal line period
        
    Returns:
        Tuple of (MACD line, Signal line, Histogram)
    """
    ema_fast = df['close'].ewm(span=fast, adjust=False).mean()
    ema_slow = df['close'].ewm(span=slow, adjust=False).mean()
    
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - signal_line
    
    return macd_line, signal_line, histogram


def calculate_ema(df: pd.DataFrame, period: int) -> pd.Series:
    """
    Calculate Exponential Moving Average.
    
    Args:
        df: DataFrame with 'close' column
        period: EMA period
        
    Returns:
        Series with EMA values
    """
    return df['close'].ewm(span=period, adjust=False).mean()


def calculate_sma(df: pd.DataFrame, period: int) -> pd.Series:
    """
    Calculate Simple Moving Average.
    
    Args:
        df: DataFrame with 'close' column
        period: SMA period
        
    Returns:
        Series with SMA values
    """
    return df['close'].rolling(window=period).mean()


def calculate_volume_ratio(df: pd.DataFrame, period: int = 20) -> float:
    """
    Calculate current volume relative to average.
    
    Args:
        df: DataFrame with 'volume' column
        period: Lookback period for average
        
    Returns:
        Ratio of current volume to average
    """
    avg_volume = df['volume'].tail(period).mean()
    current_volume = df['volume'].iloc[-1]
    
    if avg_volume > 0:
        return current_volume / avg_volume
    return 1.0


def detect_macd_crossover(macd: pd.Series, signal: pd.Series) -> str:
    """
    Detect MACD crossover signal.
    
    Args:
        macd: MACD line series
        signal: Signal line series
        
    Returns:
        'bullish', 'bearish', or 'none'
    """
    if len(macd) < 2 or len(signal) < 2:
        return 'none'
    
    # Check for crossover in last 2 candles
    prev_diff = macd.iloc[-2] - signal.iloc[-2]
    curr_diff = macd.iloc[-1] - signal.iloc[-1]
    
    if prev_diff < 0 and curr_diff > 0:
        return 'bullish'
    elif prev_diff > 0 and curr_diff < 0:
        return 'bearish'
    
    return 'none'


def detect_ema_crossover(ema_short: pd.Series, ema_long: pd.Series) -> str:
    """
    Detect EMA crossover signal.
    
    Args:
        ema_short: Short-term EMA series
        ema_long: Long-term EMA series
        
    Returns:
        'bullish', 'bearish', or 'none'
    """
    if len(ema_short) < 2 or len(ema_long) < 2:
        return 'none'
    
    prev_diff = ema_short.iloc[-2] - ema_long.iloc[-2]
    curr_diff = ema_short.iloc[-1] - ema_long.iloc[-1]
    
    if prev_diff < 0 and curr_diff > 0:
        return 'bullish'
    elif prev_diff > 0 and curr_diff < 0:
        return 'bearish'
    
    return 'none'


def analyze_technicals(
    df: pd.DataFrame,
    symbol: str,
    timeframe: str,
    rsi_oversold: float = 30,
    rsi_overbought: float = 70,
    ema_short_period: int = 12,
    ema_long_period: int = 26,
    volume_spike_threshold: float = 2.0
) -> Optional[TechnicalSignal]:
    """
    Perform full technical analysis on price data.
    
    Args:
        df: DataFrame with OHLCV data
        symbol: Trading pair symbol
        timeframe: Analysis timeframe
        rsi_oversold: RSI oversold threshold
        rsi_overbought: RSI overbought threshold
        ema_short_period: Short EMA period
        ema_long_period: Long EMA period
        volume_spike_threshold: Volume spike multiplier
        
    Returns:
        TechnicalSignal object with analysis results
    """
    try:
        if len(df) < max(ema_long_period, 26) + 10:
            logger.warning(f"Insufficient data for {symbol} analysis")
            return None
        
        # Calculate indicators
        rsi = calculate_rsi(df)
        macd_line, signal_line, histogram = calculate_macd(df)
        ema_short = calculate_ema(df, ema_short_period)
        ema_long = calculate_ema(df, ema_long_period)
        volume_ratio = calculate_volume_ratio(df)
        
        # Get current values
        current_rsi = rsi.iloc[-1]
        current_macd = macd_line.iloc[-1]
        current_signal = signal_line.iloc[-1]
        current_histogram = histogram.iloc[-1]
        current_ema_short = ema_short.iloc[-1]
        current_ema_long = ema_long.iloc[-1]
        current_price = df['close'].iloc[-1]
        
        # Calculate price change
        if len(df) >= 2:
            price_change = ((current_price - df['close'].iloc[-2]) / df['close'].iloc[-2]) * 100
        else:
            price_change = 0.0
        
        # RSI signal
        if current_rsi <= rsi_oversold:
            rsi_signal = 'oversold'
        elif current_rsi >= rsi_overbought:
            rsi_signal = 'overbought'
        else:
            rsi_signal = 'neutral'
        
        # Crossover detection
        macd_crossover = detect_macd_crossover(macd_line, signal_line)
        ema_crossover = detect_ema_crossover(ema_short, ema_long)
        
        # Price vs EMA
        price_vs_ema = ((current_price - current_ema_long) / current_ema_long) * 100
        
        # Volume spike
        volume_spike = volume_ratio >= volume_spike_threshold
        
        # Calculate bias and strength
        bias, strength = calculate_bias(
            rsi_signal=rsi_signal,
            current_rsi=current_rsi,
            macd_crossover=macd_crossover,
            current_histogram=current_histogram,
            ema_crossover=ema_crossover,
            price_vs_ema=price_vs_ema,
            volume_spike=volume_spike,
            rsi_oversold=rsi_oversold,
            rsi_overbought=rsi_overbought
        )
        
        return TechnicalSignal(
            symbol=symbol,
            timeframe=timeframe,
            rsi=current_rsi,
            rsi_signal=rsi_signal,
            macd=current_macd,
            macd_signal=current_signal,
            macd_histogram=current_histogram,
            macd_crossover=macd_crossover,
            ema_short=current_ema_short,
            ema_long=current_ema_long,
            ema_crossover=ema_crossover,
            price_vs_ema=price_vs_ema,
            volume_ratio=volume_ratio,
            volume_spike=volume_spike,
            current_price=current_price,
            price_change_percent=price_change,
            bias=bias,
            strength=strength
        )
        
    except Exception as e:
        logger.error(f"Error analyzing {symbol}: {e}")
        return None


def calculate_bias(
    rsi_signal: str,
    current_rsi: float,
    macd_crossover: str,
    current_histogram: float,
    ema_crossover: str,
    price_vs_ema: float,
    volume_spike: bool,
    rsi_oversold: float,
    rsi_overbought: float
) -> Tuple[str, float]:
    """
    Calculate overall trading bias and signal strength.
    
    Returns:
        Tuple of (bias, strength) where bias is 'long', 'short', or 'neutral'
        and strength is 0-10 scale
    """
    long_score = 0.0
    short_score = 0.0
    
    # RSI contribution (max 3 points)
    if rsi_signal == 'oversold':
        # The more oversold, the stronger the signal
        rsi_intensity = (rsi_oversold - current_rsi) / rsi_oversold
        long_score += 2 + min(rsi_intensity, 1)
    elif rsi_signal == 'overbought':
        rsi_intensity = (current_rsi - rsi_overbought) / (100 - rsi_overbought)
        short_score += 2 + min(rsi_intensity, 1)
    
    # MACD crossover contribution (max 2.5 points)
    if macd_crossover == 'bullish':
        long_score += 2.5
    elif macd_crossover == 'bearish':
        short_score += 2.5
    else:
        # MACD histogram direction
        if current_histogram > 0:
            long_score += 0.5
        elif current_histogram < 0:
            short_score += 0.5
    
    # EMA crossover contribution (max 2 points)
    if ema_crossover == 'bullish':
        long_score += 2
    elif ema_crossover == 'bearish':
        short_score += 2
    
    # Price position vs EMA (max 1.5 points)
    if price_vs_ema > 2:
        long_score += min(price_vs_ema / 4, 1.5)
    elif price_vs_ema < -2:
        short_score += min(abs(price_vs_ema) / 4, 1.5)
    
    # Volume spike bonus (1 point)
    if volume_spike:
        # Amplify the dominant signal
        if long_score > short_score:
            long_score += 1
        elif short_score > long_score:
            short_score += 1
    
    # Determine bias
    total_score = max(long_score, short_score)
    
    if long_score > short_score + 1:
        bias = 'long'
        strength = min(long_score, 10)
    elif short_score > long_score + 1:
        bias = 'short'
        strength = min(short_score, 10)
    else:
        bias = 'neutral'
        strength = 0
    
    return bias, round(strength, 1)
