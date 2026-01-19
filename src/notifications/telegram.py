"""
Telegram notification module.
Sends formatted trading signals to Telegram.
"""

import logging
from typing import List, Optional
from datetime import datetime

import telegram
from telegram.constants import ParseMode

from ..analysis.signals import AggregatedSignal, SignalType, SignalStrength

logger = logging.getLogger(__name__)


class TelegramNotifier:
    """Telegram bot for sending trading signal notifications."""
    
    def __init__(self, bot_token: str, chat_id: str):
        """
        Initialize Telegram notifier.
        
        Args:
            bot_token: Telegram bot token from @BotFather
            chat_id: Target chat/user ID for notifications
        """
        self.bot = telegram.Bot(token=bot_token)
        self.chat_id = chat_id
    
    async def send_message(self, text: str, parse_mode: str = ParseMode.HTML) -> bool:
        """
        Send a text message to the configured chat.
        
        Args:
            text: Message text (supports HTML formatting)
            parse_mode: Telegram parse mode
            
        Returns:
            True if message sent successfully
        """
        try:
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=text,
                parse_mode=parse_mode
            )
            return True
        except Exception as e:
            logger.error(f"Failed to send Telegram message: {e}")
            return False
    
    async def send_signal(self, signal: AggregatedSignal) -> bool:
        """
        Send a formatted trading signal notification.
        
        Args:
            signal: Aggregated trading signal
            
        Returns:
            True if message sent successfully
        """
        message = format_signal_message(signal)
        return await self.send_message(message)
    
    async def send_signals_summary(
        self, 
        long_signals: List[AggregatedSignal],
        short_signals: List[AggregatedSignal]
    ) -> bool:
        """
        Send a summary of all trading signals.
        
        Args:
            long_signals: List of long signals
            short_signals: List of short signals
            
        Returns:
            True if message sent successfully
        """
        message = format_signals_summary(long_signals, short_signals)
        return await self.send_message(message)
    
    async def send_no_signals_message(self) -> bool:
        """Send notification when no strong signals are found."""
        message = (
            "📊 <b>Crypto Futures Analysis</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "No strong trading signals detected.\n\n"
            f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}"
        )
        return await self.send_message(message)


def format_signal_message(signal: AggregatedSignal) -> str:
    """
    Format a single signal into a Telegram message.
    
    Args:
        signal: Aggregated trading signal
        
    Returns:
        Formatted HTML message string
    """
    # Signal emoji and header
    if signal.signal_type == SignalType.LONG:
        emoji = "🟢"
        direction = "LONG"
    else:
        emoji = "🔴"
        direction = "SHORT"
    
    # Strength indicator
    strength_stars = get_strength_stars(signal.strength)
    
    # Build message
    lines = [
        f"{emoji} <b>{direction} Signal: {signal.symbol}</b>",
        "━━━━━━━━━━━━━━━━━━━━",
        f"Score: <b>{signal.total_score}/10</b> {strength_stars}",
        f"Timeframe: {signal.timeframe}",
        ""
    ]
    
    # Technical details
    if signal.technical_signal:
        tech = signal.technical_signal
        lines.extend([
            "📊 <b>Technical Analysis:</b>",
            f"  • RSI: {tech.rsi:.1f} ({tech.rsi_signal})",
            f"  • MACD: {tech.macd_crossover}",
            f"  • Price vs EMA: {tech.price_vs_ema:+.2f}%",
        ])
        if tech.volume_spike:
            lines.append(f"  • Volume Spike: {tech.volume_ratio:.1f}x avg")
        lines.append("")
    
    # Funding rate
    if signal.funding_signal:
        funding = signal.funding_signal
        lines.extend([
            f"💰 <b>Funding Rate:</b> {funding.funding_rate:.4f}%",
            f"  • {funding.description}",
            ""
        ])
    
    # Liquidations
    if signal.liquidation_signal and signal.liquidation_signal.signal != 'neutral':
        liq = signal.liquidation_signal
        lines.extend([
            "💥 <b>Liquidations:</b>",
            f"  • Longs: ${liq.total_long_liquidations_usd:,.0f}",
            f"  • Shorts: ${liq.total_short_liquidations_usd:,.0f}",
            ""
        ])
    
    # Score breakdown
    lines.extend([
        "📈 <b>Score Breakdown:</b>",
        f"  • Technical: {signal.technical_score:.1f}",
        f"  • Funding: {signal.funding_score:.1f}",
        f"  • Liquidations: {signal.liquidation_score:.1f}",
    ])
    
    if signal.confluence_bonus > 0:
        lines.append(f"  • Confluence Bonus: +{signal.confluence_bonus:.1f}")
    
    lines.extend([
        "",
        f"⏰ {signal.timestamp.strftime('%Y-%m-%d %H:%M UTC')}"
    ])
    
    return "\n".join(lines)


def format_signals_summary(
    long_signals: List[AggregatedSignal],
    short_signals: List[AggregatedSignal]
) -> str:
    """
    Format a summary of multiple signals.
    
    Args:
        long_signals: List of long signals
        short_signals: List of short signals
        
    Returns:
        Formatted HTML message string
    """
    lines = [
        "📊 <b>Crypto Futures Analysis Summary</b>",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        ""
    ]
    
    # Long signals
    if long_signals:
        lines.append("🟢 <b>LONG Opportunities:</b>")
        for i, signal in enumerate(long_signals[:5], 1):
            stars = get_strength_stars(signal.strength)
            lines.append(
                f"  {i}. <b>{signal.symbol}</b> - Score: {signal.total_score}/10 {stars}"
            )
            # Add brief reason
            if signal.reasons:
                lines.append(f"      └ {signal.reasons[0]}")
        lines.append("")
    else:
        lines.extend(["🟢 <b>LONG Opportunities:</b>", "  No strong long signals", ""])
    
    # Short signals
    if short_signals:
        lines.append("🔴 <b>SHORT Opportunities:</b>")
        for i, signal in enumerate(short_signals[:5], 1):
            stars = get_strength_stars(signal.strength)
            lines.append(
                f"  {i}. <b>{signal.symbol}</b> - Score: {signal.total_score}/10 {stars}"
            )
            if signal.reasons:
                lines.append(f"      └ {signal.reasons[0]}")
        lines.append("")
    else:
        lines.extend(["🔴 <b>SHORT Opportunities:</b>", "  No strong short signals", ""])
    
    # Footer
    total_signals = len(long_signals) + len(short_signals)
    lines.extend([
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        f"Total signals found: {total_signals}",
        f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}"
    ])
    
    return "\n".join(lines)


def get_strength_stars(strength: SignalStrength) -> str:
    """Get star rating for signal strength."""
    if strength == SignalStrength.VERY_STRONG:
        return "⭐⭐⭐⭐"
    elif strength == SignalStrength.STRONG:
        return "⭐⭐⭐"
    elif strength == SignalStrength.MODERATE:
        return "⭐⭐"
    else:
        return "⭐"


def format_detailed_signal(signal: AggregatedSignal) -> str:
    """
    Format a detailed single signal for high-priority alerts.
    
    Args:
        signal: Aggregated trading signal
        
    Returns:
        Formatted HTML message string
    """
    if signal.signal_type == SignalType.LONG:
        header = "🚀 <b>STRONG LONG OPPORTUNITY</b> 🚀"
        emoji = "🟢"
    else:
        header = "📉 <b>STRONG SHORT OPPORTUNITY</b> 📉"
        emoji = "🔴"
    
    lines = [
        header,
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        "",
        f"{emoji} <b>{signal.symbol}</b>",
        f"Score: <b>{signal.total_score}/10</b> {get_strength_stars(signal.strength)}",
        f"Timeframe: {signal.timeframe}",
        "",
    ]
    
    # Current price
    if signal.technical_signal:
        lines.append(f"💵 Current Price: ${signal.technical_signal.current_price:,.4f}")
        lines.append("")
    
    # Key reasons
    lines.append("📋 <b>Key Signals:</b>")
    for reason in signal.reasons:
        lines.append(f"  ✓ {reason}")
    
    lines.extend([
        "",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        "⚠️ <i>Always do your own research. This is not financial advice.</i>",
        "",
        f"⏰ {signal.timestamp.strftime('%Y-%m-%d %H:%M UTC')}"
    ])
    
    return "\n".join(lines)
