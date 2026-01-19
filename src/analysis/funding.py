"""
Funding rate analysis module.
Extreme funding rates can indicate potential reversals.
"""

import logging
from dataclasses import dataclass
from typing import Dict, Any, Optional, List
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class FundingSignal:
    """Funding rate analysis result."""
    symbol: str
    funding_rate: float  # Current funding rate in percentage
    funding_rate_raw: float  # Raw funding rate
    next_funding_time: Optional[datetime]
    
    # Analysis
    signal: str  # 'long', 'short', 'neutral'
    intensity: str  # 'extreme', 'high', 'moderate', 'low'
    description: str
    
    # Score contribution
    score: float  # 0-10 scale


def analyze_funding_rate(
    symbol: str,
    funding_rate: float,
    next_funding_time: Optional[datetime] = None,
    extreme_positive_threshold: float = 0.1,  # 0.1%
    extreme_negative_threshold: float = -0.1,  # -0.1%
    high_positive_threshold: float = 0.05,  # 0.05%
    high_negative_threshold: float = -0.05  # -0.05%
) -> FundingSignal:
    """
    Analyze funding rate for trading signals.
    
    Funding rate logic:
    - Positive funding: Longs pay shorts -> Market is bullish -> Potential short opportunity
    - Negative funding: Shorts pay longs -> Market is bearish -> Potential long opportunity
    - Extreme rates often precede reversals
    
    Args:
        symbol: Trading pair symbol
        funding_rate: Current funding rate in percentage
        next_funding_time: Time of next funding payment
        extreme_positive_threshold: Threshold for extreme positive funding
        extreme_negative_threshold: Threshold for extreme negative funding
        high_positive_threshold: Threshold for high positive funding
        high_negative_threshold: Threshold for high negative funding
        
    Returns:
        FundingSignal with analysis results
    """
    signal = 'neutral'
    intensity = 'low'
    score = 0.0
    
    # Extreme negative funding -> Strong long signal
    if funding_rate <= extreme_negative_threshold:
        signal = 'long'
        intensity = 'extreme'
        # Score based on how extreme the rate is
        score = min(abs(funding_rate) / abs(extreme_negative_threshold) * 5, 10)
        description = (
            f"Extreme negative funding ({funding_rate:.4f}%). "
            "Shorts are paying longs heavily - potential long opportunity."
        )
    
    # High negative funding -> Moderate long signal
    elif funding_rate <= high_negative_threshold:
        signal = 'long'
        intensity = 'high'
        score = min(abs(funding_rate) / abs(extreme_negative_threshold) * 4, 7)
        description = (
            f"High negative funding ({funding_rate:.4f}%). "
            "Shorts paying longs - consider long positions."
        )
    
    # Extreme positive funding -> Strong short signal
    elif funding_rate >= extreme_positive_threshold:
        signal = 'short'
        intensity = 'extreme'
        score = min(funding_rate / extreme_positive_threshold * 5, 10)
        description = (
            f"Extreme positive funding ({funding_rate:.4f}%). "
            "Longs are paying shorts heavily - potential short opportunity."
        )
    
    # High positive funding -> Moderate short signal
    elif funding_rate >= high_positive_threshold:
        signal = 'short'
        intensity = 'high'
        score = min(funding_rate / extreme_positive_threshold * 4, 7)
        description = (
            f"High positive funding ({funding_rate:.4f}%). "
            "Longs paying shorts - consider short positions."
        )
    
    # Moderate positive
    elif funding_rate > 0.01:
        signal = 'short'
        intensity = 'moderate'
        score = 2
        description = f"Moderate positive funding ({funding_rate:.4f}%). Slight bearish bias."
    
    # Moderate negative
    elif funding_rate < -0.01:
        signal = 'long'
        intensity = 'moderate'
        score = 2
        description = f"Moderate negative funding ({funding_rate:.4f}%). Slight bullish bias."
    
    # Neutral
    else:
        signal = 'neutral'
        intensity = 'low'
        score = 0
        description = f"Neutral funding rate ({funding_rate:.4f}%). No clear signal."
    
    return FundingSignal(
        symbol=symbol,
        funding_rate=funding_rate,
        funding_rate_raw=funding_rate / 100,
        next_funding_time=next_funding_time,
        signal=signal,
        intensity=intensity,
        description=description,
        score=round(score, 1)
    )


def analyze_funding_rates_batch(
    funding_data: Dict[str, Dict[str, Any]],
    extreme_positive_threshold: float = 0.1,
    extreme_negative_threshold: float = -0.1
) -> Dict[str, FundingSignal]:
    """
    Analyze funding rates for multiple symbols.
    
    Args:
        funding_data: Dict mapping symbol to funding rate info
        extreme_positive_threshold: Threshold for extreme positive
        extreme_negative_threshold: Threshold for extreme negative
        
    Returns:
        Dict mapping symbol to FundingSignal
    """
    results = {}
    
    for symbol, data in funding_data.items():
        funding_rate = data.get('funding_rate', 0.0)
        funding_time = data.get('funding_time')
        
        results[symbol] = analyze_funding_rate(
            symbol=symbol,
            funding_rate=funding_rate,
            next_funding_time=funding_time,
            extreme_positive_threshold=extreme_positive_threshold,
            extreme_negative_threshold=extreme_negative_threshold
        )
    
    return results


def get_extreme_funding_symbols(
    signals: Dict[str, FundingSignal],
    min_score: float = 5.0
) -> List[FundingSignal]:
    """
    Filter and sort symbols with extreme funding rates.
    
    Args:
        signals: Dict of FundingSignal objects
        min_score: Minimum score threshold
        
    Returns:
        List of FundingSignal sorted by score descending
    """
    extreme_signals = [
        signal for signal in signals.values()
        if signal.score >= min_score
    ]
    
    return sorted(extreme_signals, key=lambda x: x.score, reverse=True)
