"""
Abstract base class for exchange API clients.
Defines the common interface that all exchange clients must implement.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from datetime import datetime

import pandas as pd


class BaseExchangeClient(ABC):
    """Abstract base class for exchange API clients."""
    
    name: str = "base"
    
    @abstractmethod
    def get_top_futures_symbols(self, limit: int = 20) -> List[str]:
        """
        Get top futures trading pairs by 24h volume.
        
        Args:
            limit: Number of symbols to return
            
        Returns:
            List of symbol strings in unified format (e.g., ['BTCUSDT', 'ETHUSDT'])
        """
        pass
    
    @abstractmethod
    def get_klines(
        self, 
        symbol: str, 
        interval: str, 
        limit: int = 100
    ) -> pd.DataFrame:
        """
        Fetch OHLCV candlestick data.
        
        Args:
            symbol: Trading pair symbol (unified format, e.g., 'BTCUSDT')
            interval: Kline interval (e.g., '1h', '4h', '1d')
            limit: Number of candles to fetch
            
        Returns:
            DataFrame with columns: timestamp, open, high, low, close, volume
        """
        pass
    
    @abstractmethod
    def get_funding_rate(self, symbol: str) -> Dict[str, Any]:
        """
        Get current funding rate for a symbol.
        
        Args:
            symbol: Trading pair symbol
            
        Returns:
            Dict with keys: symbol, funding_rate (percentage), funding_time
        """
        pass
    
    @abstractmethod
    def get_recent_trades(
        self, 
        symbol: str, 
        limit: int = 500
    ) -> List[Dict[str, Any]]:
        """
        Get recent trades for a symbol.
        
        Args:
            symbol: Trading pair symbol
            limit: Number of trades to fetch
            
        Returns:
            List of trade dicts with keys: price, qty, quote_qty, time, is_buyer_maker
        """
        pass
    
    def health_check(self) -> bool:
        """
        Test if the exchange API is accessible.
        
        Returns:
            True if exchange is reachable and working
        """
        try:
            symbols = self.get_top_futures_symbols(limit=1)
            return len(symbols) > 0
        except Exception:
            return False
    
    def _convert_interval(self, interval: str) -> str:
        """
        Convert unified interval format to exchange-specific format.
        Override in subclasses if needed.
        
        Args:
            interval: Unified interval (e.g., '1h', '4h', '1d')
            
        Returns:
            Exchange-specific interval string
        """
        return interval
    
    def _to_unified_symbol(self, symbol: str) -> str:
        """
        Convert exchange-specific symbol to unified format (BTCUSDT).
        Override in subclasses if needed.
        
        Args:
            symbol: Exchange-specific symbol
            
        Returns:
            Unified symbol format
        """
        return symbol
    
    def _from_unified_symbol(self, symbol: str) -> str:
        """
        Convert unified symbol format to exchange-specific format.
        Override in subclasses if needed.
        
        Args:
            symbol: Unified symbol (e.g., 'BTCUSDT')
            
        Returns:
            Exchange-specific symbol format
        """
        return symbol
