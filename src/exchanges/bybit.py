"""
Bybit Futures API client using public endpoints.
No API key required for market data.
"""

import logging
from typing import Dict, List, Any
from datetime import datetime

import pandas as pd
import requests

from .base import BaseExchangeClient

logger = logging.getLogger(__name__)


class BybitFuturesClient(BaseExchangeClient):
    """Bybit Futures API client - No geographic restrictions."""
    
    name = "Bybit"
    BASE_URL = "https://api.bybit.com"
    
    # Interval mapping: unified -> Bybit format
    INTERVAL_MAP = {
        '1m': '1',
        '3m': '3',
        '5m': '5',
        '15m': '15',
        '30m': '30',
        '1h': '60',
        '2h': '120',
        '4h': '240',
        '6h': '360',
        '12h': '720',
        '1d': 'D',
        '1w': 'W',
        '1M': 'M',
    }
    
    def __init__(self):
        """Initialize Bybit client with public endpoints."""
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json'
        })
    
    def _request(self, endpoint: str, params: Dict = None) -> Dict:
        """Make a GET request to Bybit API."""
        url = f"{self.BASE_URL}{endpoint}"
        try:
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if data.get('retCode') != 0:
                raise Exception(f"Bybit API error: {data.get('retMsg')}")
            
            return data.get('result', {})
        except requests.exceptions.RequestException as e:
            logger.error(f"Bybit request failed: {e}")
            raise
    
    def get_top_futures_symbols(self, limit: int = 20) -> List[str]:
        """Get top USDT perpetual futures by 24h volume."""
        try:
            result = self._request('/v5/market/tickers', {
                'category': 'linear'
            })
            
            tickers = result.get('list', [])
            
            # Filter USDT pairs and sort by 24h turnover
            usdt_tickers = [
                t for t in tickers
                if t['symbol'].endswith('USDT') and not t['symbol'].endswith('PERP')
            ]
            
            sorted_tickers = sorted(
                usdt_tickers,
                key=lambda x: float(x.get('turnover24h', 0)),
                reverse=True
            )
            
            return [t['symbol'] for t in sorted_tickers[:limit]]
            
        except Exception as e:
            logger.error(f"Failed to fetch Bybit top symbols: {e}")
            raise
    
    def get_klines(
        self, 
        symbol: str, 
        interval: str, 
        limit: int = 100
    ) -> pd.DataFrame:
        """Fetch OHLCV candlestick data from Bybit."""
        try:
            bybit_interval = self._convert_interval(interval)
            
            result = self._request('/v5/market/kline', {
                'category': 'linear',
                'symbol': symbol,
                'interval': bybit_interval,
                'limit': limit
            })
            
            klines = result.get('list', [])
            
            if not klines:
                raise Exception(f"No kline data for {symbol}")
            
            # Bybit returns newest first, reverse for chronological order
            klines = list(reversed(klines))
            
            # Bybit kline format: [startTime, openPrice, highPrice, lowPrice, closePrice, volume, turnover]
            df = pd.DataFrame(klines, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume', 'quote_volume'
            ])
            
            df['timestamp'] = pd.to_datetime(df['timestamp'].astype(int), unit='ms')
            for col in ['open', 'high', 'low', 'close', 'volume', 'quote_volume']:
                df[col] = df[col].astype(float)
            
            return df
            
        except Exception as e:
            logger.error(f"Failed to fetch Bybit klines for {symbol}: {e}")
            raise
    
    def get_funding_rate(self, symbol: str) -> Dict[str, Any]:
        """Get current funding rate for a symbol."""
        try:
            # Get current funding rate from tickers
            result = self._request('/v5/market/tickers', {
                'category': 'linear',
                'symbol': symbol
            })
            
            tickers = result.get('list', [])
            
            if tickers:
                ticker = tickers[0]
                funding_rate = float(ticker.get('fundingRate', 0)) * 100  # Convert to percentage
                
                # Get next funding time
                next_funding = ticker.get('nextFundingTime', '')
                if next_funding:
                    funding_time = datetime.fromtimestamp(int(next_funding) / 1000)
                else:
                    funding_time = None
                
                return {
                    'symbol': symbol,
                    'funding_rate': funding_rate,
                    'funding_time': funding_time
                }
            
            return {'symbol': symbol, 'funding_rate': 0.0, 'funding_time': None}
            
        except Exception as e:
            logger.error(f"Failed to fetch Bybit funding rate for {symbol}: {e}")
            return {'symbol': symbol, 'funding_rate': 0.0, 'funding_time': None}
    
    def get_recent_trades(
        self, 
        symbol: str, 
        limit: int = 500
    ) -> List[Dict[str, Any]]:
        """Get recent trades for a symbol."""
        try:
            result = self._request('/v5/market/recent-trade', {
                'category': 'linear',
                'symbol': symbol,
                'limit': min(limit, 1000)  # Bybit max is 1000
            })
            
            trades = result.get('list', [])
            
            return [{
                'price': float(t['price']),
                'qty': float(t['size']),
                'quote_qty': float(t['price']) * float(t['size']),
                'time': datetime.fromtimestamp(int(t['time']) / 1000),
                'is_buyer_maker': t['side'] == 'Sell'  # If side is Sell, buyer is maker
            } for t in trades]
            
        except Exception as e:
            logger.error(f"Failed to fetch Bybit trades for {symbol}: {e}")
            return []
    
    def _convert_interval(self, interval: str) -> str:
        """Convert unified interval to Bybit format."""
        return self.INTERVAL_MAP.get(interval, '60')  # Default to 1h
