"""
Binance Futures API client for fetching market data.
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta

import pandas as pd
from binance.client import Client
from binance.exceptions import BinanceAPIException

logger = logging.getLogger(__name__)


class BinanceFuturesClient:
    """Client for interacting with Binance Futures API."""
    
    def __init__(self, api_key: str, api_secret: str):
        """Initialize the Binance client."""
        self.client = Client(api_key, api_secret)
        
    def get_top_futures_symbols(self, limit: int = 20) -> List[str]:
        """
        Get top futures trading pairs by 24h volume.
        
        Args:
            limit: Number of symbols to return
            
        Returns:
            List of symbol strings (e.g., ['BTCUSDT', 'ETHUSDT', ...])
        """
        try:
            tickers = self.client.futures_ticker()
            
            # Filter for USDT pairs and sort by quote volume
            usdt_tickers = [
                t for t in tickers 
                if t['symbol'].endswith('USDT') and not t['symbol'].endswith('_PERP')
            ]
            
            # Sort by 24h quote volume (descending)
            sorted_tickers = sorted(
                usdt_tickers,
                key=lambda x: float(x['quoteVolume']),
                reverse=True
            )
            
            return [t['symbol'] for t in sorted_tickers[:limit]]
            
        except BinanceAPIException as e:
            logger.error(f"Failed to fetch top symbols: {e}")
            raise
    
    def get_klines(
        self, 
        symbol: str, 
        interval: str, 
        limit: int = 100
    ) -> pd.DataFrame:
        """
        Fetch OHLCV candlestick data.
        
        Args:
            symbol: Trading pair symbol (e.g., 'BTCUSDT')
            interval: Kline interval (e.g., '1h', '4h', '1d')
            limit: Number of candles to fetch
            
        Returns:
            DataFrame with columns: open, high, low, close, volume, timestamp
        """
        try:
            klines = self.client.futures_klines(
                symbol=symbol,
                interval=interval,
                limit=limit
            )
            
            df = pd.DataFrame(klines, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_volume', 'trades', 'taker_buy_base',
                'taker_buy_quote', 'ignore'
            ])
            
            # Convert types
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            for col in ['open', 'high', 'low', 'close', 'volume', 'quote_volume']:
                df[col] = df[col].astype(float)
            
            # Keep only relevant columns
            df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume', 'quote_volume']]
            
            return df
            
        except BinanceAPIException as e:
            logger.error(f"Failed to fetch klines for {symbol}: {e}")
            raise
    
    def get_funding_rate(self, symbol: str) -> Dict[str, Any]:
        """
        Get current funding rate for a symbol.
        
        Args:
            symbol: Trading pair symbol
            
        Returns:
            Dict with funding rate info
        """
        try:
            # Get current funding rate
            funding_info = self.client.futures_funding_rate(symbol=symbol, limit=1)
            
            if funding_info:
                latest = funding_info[-1]
                return {
                    'symbol': symbol,
                    'funding_rate': float(latest['fundingRate']) * 100,  # Convert to percentage
                    'funding_time': datetime.fromtimestamp(latest['fundingTime'] / 1000),
                }
            
            return {'symbol': symbol, 'funding_rate': 0.0, 'funding_time': None}
            
        except BinanceAPIException as e:
            logger.error(f"Failed to fetch funding rate for {symbol}: {e}")
            return {'symbol': symbol, 'funding_rate': 0.0, 'funding_time': None}
    
    def get_funding_rates_batch(self, symbols: List[str]) -> Dict[str, Dict[str, Any]]:
        """
        Get funding rates for multiple symbols.
        
        Args:
            symbols: List of trading pair symbols
            
        Returns:
            Dict mapping symbol to funding rate info
        """
        result = {}
        for symbol in symbols:
            result[symbol] = self.get_funding_rate(symbol)
        return result
    
    def get_open_interest(self, symbol: str) -> Dict[str, Any]:
        """
        Get open interest for a symbol.
        
        Args:
            symbol: Trading pair symbol
            
        Returns:
            Dict with open interest info
        """
        try:
            oi = self.client.futures_open_interest(symbol=symbol)
            return {
                'symbol': symbol,
                'open_interest': float(oi['openInterest']),
                'timestamp': datetime.now()
            }
        except BinanceAPIException as e:
            logger.error(f"Failed to fetch open interest for {symbol}: {e}")
            return {'symbol': symbol, 'open_interest': 0.0, 'timestamp': None}
    
    def get_recent_trades(self, symbol: str, limit: int = 500) -> List[Dict[str, Any]]:
        """
        Get recent trades for a symbol.
        
        Args:
            symbol: Trading pair symbol
            limit: Number of trades to fetch
            
        Returns:
            List of trade dicts
        """
        try:
            trades = self.client.futures_recent_trades(symbol=symbol, limit=limit)
            return [{
                'price': float(t['price']),
                'qty': float(t['qty']),
                'quote_qty': float(t['quoteQty']),
                'time': datetime.fromtimestamp(t['time'] / 1000),
                'is_buyer_maker': t['isBuyerMaker']
            } for t in trades]
        except BinanceAPIException as e:
            logger.error(f"Failed to fetch recent trades for {symbol}: {e}")
            return []
    
    def get_long_short_ratio(self, symbol: str, period: str = "1h") -> Optional[Dict[str, Any]]:
        """
        Get long/short ratio for top traders.
        
        Args:
            symbol: Trading pair symbol
            period: Time period ('5m', '15m', '30m', '1h', '2h', '4h', '6h', '12h', '1d')
            
        Returns:
            Dict with long/short ratio info
        """
        try:
            ratio = self.client.futures_top_longshort_account_ratio(
                symbol=symbol,
                period=period,
                limit=1
            )
            
            if ratio:
                latest = ratio[-1]
                return {
                    'symbol': symbol,
                    'long_ratio': float(latest['longAccount']),
                    'short_ratio': float(latest['shortAccount']),
                    'long_short_ratio': float(latest['longShortRatio']),
                    'timestamp': datetime.fromtimestamp(latest['timestamp'] / 1000)
                }
            return None
            
        except BinanceAPIException as e:
            logger.error(f"Failed to fetch long/short ratio for {symbol}: {e}")
            return None
    
    def get_mark_price(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get current mark price and funding rate info.
        
        Args:
            symbol: Trading pair symbol
            
        Returns:
            Dict with mark price info
        """
        try:
            mark = self.client.futures_mark_price(symbol=symbol)
            return {
                'symbol': symbol,
                'mark_price': float(mark['markPrice']),
                'index_price': float(mark['indexPrice']),
                'last_funding_rate': float(mark['lastFundingRate']) * 100,
                'next_funding_time': datetime.fromtimestamp(mark['nextFundingTime'] / 1000)
            }
        except BinanceAPIException as e:
            logger.error(f"Failed to fetch mark price for {symbol}: {e}")
            return None
    
    def get_ticker_24h(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get 24h ticker statistics.
        
        Args:
            symbol: Trading pair symbol
            
        Returns:
            Dict with 24h stats
        """
        try:
            ticker = self.client.futures_ticker(symbol=symbol)
            return {
                'symbol': symbol,
                'price_change_percent': float(ticker['priceChangePercent']),
                'last_price': float(ticker['lastPrice']),
                'high_price': float(ticker['highPrice']),
                'low_price': float(ticker['lowPrice']),
                'volume': float(ticker['volume']),
                'quote_volume': float(ticker['quoteVolume'])
            }
        except BinanceAPIException as e:
            logger.error(f"Failed to fetch 24h ticker for {symbol}: {e}")
            return None
