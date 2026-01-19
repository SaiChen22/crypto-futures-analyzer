"""
OKX Futures API client using public endpoints.
No API key required for market data.
"""

import logging
from typing import Dict, List, Any
from datetime import datetime

import pandas as pd
import requests

from .base import BaseExchangeClient

logger = logging.getLogger(__name__)


class OKXFuturesClient(BaseExchangeClient):
    """OKX Futures API client - No geographic restrictions."""
    
    name = "OKX"
    BASE_URL = "https://www.okx.com"
    
    # Interval mapping: unified -> OKX format
    INTERVAL_MAP = {
        '1m': '1m',
        '3m': '3m',
        '5m': '5m',
        '15m': '15m',
        '30m': '30m',
        '1h': '1H',
        '2h': '2H',
        '4h': '4H',
        '6h': '6H',
        '12h': '12H',
        '1d': '1D',
        '1w': '1W',
        '1M': '1M',
    }
    
    def __init__(self):
        """Initialize OKX client with public endpoints."""
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json'
        })
    
    def _request(self, endpoint: str, params: Dict = None) -> Dict:
        """Make a GET request to OKX API."""
        url = f"{self.BASE_URL}{endpoint}"
        try:
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if data.get('code') != '0':
                raise Exception(f"OKX API error: {data.get('msg')}")
            
            return data.get('data', [])
        except requests.exceptions.RequestException as e:
            logger.error(f"OKX request failed: {e}")
            raise
    
    def _to_okx_symbol(self, symbol: str) -> str:
        """Convert BTCUSDT -> BTC-USDT-SWAP"""
        # Remove USDT suffix and format
        base = symbol.replace('USDT', '')
        return f"{base}-USDT-SWAP"
    
    def _from_okx_symbol(self, symbol: str) -> str:
        """Convert BTC-USDT-SWAP -> BTCUSDT"""
        parts = symbol.split('-')
        if len(parts) >= 2:
            return f"{parts[0]}{parts[1]}"
        return symbol
    
    def get_top_futures_symbols(self, limit: int = 20) -> List[str]:
        """Get top USDT perpetual futures by 24h volume."""
        try:
            result = self._request('/api/v5/market/tickers', {
                'instType': 'SWAP'
            })
            
            # Filter USDT-SWAP pairs
            usdt_tickers = [
                t for t in result
                if '-USDT-SWAP' in t.get('instId', '')
            ]
            
            # Sort by 24h volume (volCcy24h is quote volume)
            sorted_tickers = sorted(
                usdt_tickers,
                key=lambda x: float(x.get('volCcy24h', 0)),
                reverse=True
            )
            
            # Convert to unified symbol format
            return [
                self._from_okx_symbol(t['instId']) 
                for t in sorted_tickers[:limit]
            ]
            
        except Exception as e:
            logger.error(f"Failed to fetch OKX top symbols: {e}")
            raise
    
    def get_klines(
        self, 
        symbol: str, 
        interval: str, 
        limit: int = 100
    ) -> pd.DataFrame:
        """Fetch OHLCV candlestick data from OKX."""
        try:
            okx_symbol = self._to_okx_symbol(symbol)
            okx_interval = self._convert_interval(interval)
            
            result = self._request('/api/v5/market/candles', {
                'instId': okx_symbol,
                'bar': okx_interval,
                'limit': str(limit)
            })
            
            if not result:
                raise Exception(f"No kline data for {symbol}")
            
            # OKX returns newest first, reverse for chronological order
            klines = list(reversed(result))
            
            # OKX kline format: [ts, o, h, l, c, vol, volCcy, volCcyQuote, confirm]
            df = pd.DataFrame(klines, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 
                'volume', 'vol_ccy', 'quote_volume', 'confirm'
            ])
            
            df['timestamp'] = pd.to_datetime(df['timestamp'].astype(int), unit='ms')
            for col in ['open', 'high', 'low', 'close', 'volume', 'quote_volume']:
                df[col] = df[col].astype(float)
            
            # Keep only needed columns
            df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume', 'quote_volume']]
            
            return df
            
        except Exception as e:
            logger.error(f"Failed to fetch OKX klines for {symbol}: {e}")
            raise
    
    def get_funding_rate(self, symbol: str) -> Dict[str, Any]:
        """Get current funding rate for a symbol."""
        try:
            okx_symbol = self._to_okx_symbol(symbol)
            
            result = self._request('/api/v5/public/funding-rate', {
                'instId': okx_symbol
            })
            
            if result:
                data = result[0]
                funding_rate = float(data.get('fundingRate', 0)) * 100  # Convert to percentage
                
                next_funding = data.get('nextFundingTime', '')
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
            logger.error(f"Failed to fetch OKX funding rate for {symbol}: {e}")
            return {'symbol': symbol, 'funding_rate': 0.0, 'funding_time': None}
    
    def get_recent_trades(
        self, 
        symbol: str, 
        limit: int = 500
    ) -> List[Dict[str, Any]]:
        """Get recent trades for a symbol."""
        try:
            okx_symbol = self._to_okx_symbol(symbol)
            
            result = self._request('/api/v5/market/trades', {
                'instId': okx_symbol,
                'limit': str(min(limit, 500))  # OKX max is 500
            })
            
            return [{
                'price': float(t['px']),
                'qty': float(t['sz']),
                'quote_qty': float(t['px']) * float(t['sz']),
                'time': datetime.fromtimestamp(int(t['ts']) / 1000),
                'is_buyer_maker': t['side'] == 'sell'
            } for t in result]
            
        except Exception as e:
            logger.error(f"Failed to fetch OKX trades for {symbol}: {e}")
            return []
    
    def _convert_interval(self, interval: str) -> str:
        """Convert unified interval to OKX format."""
        return self.INTERVAL_MAP.get(interval, '1H')  # Default to 1h
