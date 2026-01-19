"""
Signal aggregation module.
Combines technical, funding, and liquidation signals into unified trading signals.
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum

from .technical import TechnicalSignal
from .funding import FundingSignal
from .liquidation import LiquidationSignal

logger = logging.getLogger(__name__)


class SignalType(Enum):
    LONG = "long"
    SHORT = "short"
    NEUTRAL = "neutral"


class SignalStrength(Enum):
    WEAK = "weak"          # Score 3-5
    MODERATE = "moderate"  # Score 5-7
    STRONG = "strong"      # Score 7-8.5
    VERY_STRONG = "very_strong"  # Score 8.5+


@dataclass
class AggregatedSignal:
    """Combined signal from all analysis modules."""
    symbol: str
    signal_type: SignalType
    strength: SignalStrength
    total_score: float  # 0-10 scale
    
    # Component signals
    technical_signal: Optional[TechnicalSignal] = None
    funding_signal: Optional[FundingSignal] = None
    liquidation_signal: Optional[LiquidationSignal] = None
    
    # Score breakdown
    technical_score: float = 0.0
    funding_score: float = 0.0
    liquidation_score: float = 0.0
    
    # Confluence (how many signals agree)
    confluence_count: int = 0
    confluence_bonus: float = 0.0
    
    # Metadata
    timeframe: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    
    # Summary
    reasons: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'symbol': self.symbol,
            'signal_type': self.signal_type.value,
            'strength': self.strength.value,
            'total_score': self.total_score,
            'technical_score': self.technical_score,
            'funding_score': self.funding_score,
            'liquidation_score': self.liquidation_score,
            'confluence_count': self.confluence_count,
            'timeframe': self.timeframe,
            'timestamp': self.timestamp.isoformat(),
            'reasons': self.reasons
        }


def calculate_signal_strength(score: float) -> SignalStrength:
    """Determine signal strength from score."""
    if score >= 8.5:
        return SignalStrength.VERY_STRONG
    elif score >= 7:
        return SignalStrength.STRONG
    elif score >= 5:
        return SignalStrength.MODERATE
    else:
        return SignalStrength.WEAK


def aggregate_signals(
    symbol: str,
    timeframe: str,
    technical: Optional[TechnicalSignal] = None,
    funding: Optional[FundingSignal] = None,
    liquidation: Optional[LiquidationSignal] = None,
    weights: Optional[Dict[str, float]] = None
) -> AggregatedSignal:
    """
    Aggregate signals from different analysis modules.
    
    Weighting:
    - Technical: 50% (most reliable)
    - Funding: 30% (good contrarian indicator)
    - Liquidation: 20% (can be noisy)
    
    Confluence bonus: +1 point for each additional agreeing signal
    
    Args:
        symbol: Trading pair symbol
        timeframe: Analysis timeframe
        technical: Technical analysis signal
        funding: Funding rate signal
        liquidation: Liquidation signal
        weights: Optional custom weights for each signal type
        
    Returns:
        AggregatedSignal with combined analysis
    """
    if weights is None:
        weights = {
            'technical': 0.50,
            'funding': 0.30,
            'liquidation': 0.20
        }
    
    # Initialize scores
    long_score = 0.0
    short_score = 0.0
    
    technical_contribution = 0.0
    funding_contribution = 0.0
    liquidation_contribution = 0.0
    
    reasons = []
    signals_agreeing_long = 0
    signals_agreeing_short = 0
    
    # Process technical signal
    if technical and technical.bias != 'neutral':
        technical_contribution = technical.strength * weights['technical']
        
        if technical.bias == 'long':
            long_score += technical_contribution
            signals_agreeing_long += 1
            reasons.append(f"Technical: {technical.bias.upper()} (RSI: {technical.rsi:.1f}, MACD: {technical.macd_crossover})")
        elif technical.bias == 'short':
            short_score += technical_contribution
            signals_agreeing_short += 1
            reasons.append(f"Technical: {technical.bias.upper()} (RSI: {technical.rsi:.1f}, MACD: {technical.macd_crossover})")
    
    # Process funding signal
    if funding and funding.signal != 'neutral':
        funding_contribution = funding.score * weights['funding']
        
        if funding.signal == 'long':
            long_score += funding_contribution
            signals_agreeing_long += 1
            reasons.append(f"Funding: {funding.intensity.upper()} negative ({funding.funding_rate:.4f}%)")
        elif funding.signal == 'short':
            short_score += funding_contribution
            signals_agreeing_short += 1
            reasons.append(f"Funding: {funding.intensity.upper()} positive ({funding.funding_rate:.4f}%)")
    
    # Process liquidation signal
    if liquidation and liquidation.signal != 'neutral':
        liquidation_contribution = liquidation.score * weights['liquidation']
        
        if liquidation.signal == 'long':
            long_score += liquidation_contribution
            signals_agreeing_long += 1
            reasons.append(f"Liquidations: Long cascade (${liquidation.total_long_liquidations_usd:,.0f})")
        elif liquidation.signal == 'short':
            short_score += liquidation_contribution
            signals_agreeing_short += 1
            reasons.append(f"Liquidations: Short squeeze (${liquidation.total_short_liquidations_usd:,.0f})")
    
    # Determine final signal direction
    if long_score > short_score:
        signal_type = SignalType.LONG
        base_score = long_score
        confluence_count = signals_agreeing_long
    elif short_score > long_score:
        signal_type = SignalType.SHORT
        base_score = short_score
        confluence_count = signals_agreeing_short
    else:
        signal_type = SignalType.NEUTRAL
        base_score = 0
        confluence_count = 0
    
    # Apply confluence bonus
    # Multiple signals agreeing increases confidence
    confluence_bonus = 0.0
    if confluence_count >= 3:
        confluence_bonus = 1.5
        reasons.append("Strong confluence: All 3 signals agree")
    elif confluence_count == 2:
        confluence_bonus = 0.75
        reasons.append("Good confluence: 2 signals agree")
    
    # Calculate final score (capped at 10)
    total_score = min(base_score + confluence_bonus, 10)
    
    # Determine strength
    strength = calculate_signal_strength(total_score)
    
    return AggregatedSignal(
        symbol=symbol,
        signal_type=signal_type,
        strength=strength,
        total_score=round(total_score, 1),
        technical_signal=technical,
        funding_signal=funding,
        liquidation_signal=liquidation,
        technical_score=round(technical_contribution, 1),
        funding_score=round(funding_contribution, 1),
        liquidation_score=round(liquidation_contribution, 1),
        confluence_count=confluence_count,
        confluence_bonus=confluence_bonus,
        timeframe=timeframe,
        timestamp=datetime.now(),
        reasons=reasons
    )


def filter_signals(
    signals: List[AggregatedSignal],
    min_score: float = 7.0,
    signal_types: Optional[List[SignalType]] = None
) -> List[AggregatedSignal]:
    """
    Filter signals by score and type.
    
    Args:
        signals: List of aggregated signals
        min_score: Minimum score threshold
        signal_types: Optional list of signal types to include
        
    Returns:
        Filtered and sorted list of signals
    """
    filtered = []
    
    for signal in signals:
        # Skip neutral signals
        if signal.signal_type == SignalType.NEUTRAL:
            continue
        
        # Check score threshold
        if signal.total_score < min_score:
            continue
        
        # Check signal type filter
        if signal_types and signal.signal_type not in signal_types:
            continue
        
        filtered.append(signal)
    
    # Sort by score descending
    return sorted(filtered, key=lambda x: x.total_score, reverse=True)


def rank_signals(signals: List[AggregatedSignal], top_n: int = 10) -> Dict[str, List[AggregatedSignal]]:
    """
    Rank signals and separate into long/short categories.
    
    Args:
        signals: List of aggregated signals
        top_n: Number of top signals to return per category
        
    Returns:
        Dict with 'long' and 'short' keys containing top signals
    """
    long_signals = [s for s in signals if s.signal_type == SignalType.LONG]
    short_signals = [s for s in signals if s.signal_type == SignalType.SHORT]
    
    # Sort by score
    long_signals.sort(key=lambda x: x.total_score, reverse=True)
    short_signals.sort(key=lambda x: x.total_score, reverse=True)
    
    return {
        'long': long_signals[:top_n],
        'short': short_signals[:top_n]
    }
