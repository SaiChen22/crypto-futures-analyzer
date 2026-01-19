"""
Exchange manager with automatic fallback support.
Tries exchanges in priority order: Binance -> Bybit -> OKX
"""

import logging
from typing import List, Optional, Tuple

from .base import BaseExchangeClient
from .binance import BinanceFuturesClient
from .bybit import BybitFuturesClient
from .okx import OKXFuturesClient

logger = logging.getLogger(__name__)


class ExchangeManager:
    """
    Manages multiple exchanges with automatic fallback.
    
    Priority order:
    1. Binance (Primary) - May fail from restricted regions
    2. Bybit (Secondary) - No geographic restrictions
    3. OKX (Tertiary) - No geographic restrictions
    """
    
    def __init__(
        self,
        binance_api_key: str = "",
        binance_api_secret: str = "",
        preferred_exchange: str = "auto"
    ):
        """
        Initialize exchange manager.
        
        Args:
            binance_api_key: Binance API key (optional)
            binance_api_secret: Binance API secret (optional)
            preferred_exchange: Preferred exchange ('auto', 'binance', 'bybit', 'okx')
        """
        self.preferred_exchange = preferred_exchange.lower()
        self.binance_api_key = binance_api_key
        self.binance_api_secret = binance_api_secret
        
        self._exchanges: List[BaseExchangeClient] = []
        self._active_exchange: Optional[BaseExchangeClient] = None
        self._initialize_exchanges()
    
    def _initialize_exchanges(self):
        """Initialize all exchange clients in priority order."""
        
        # Priority 1: Binance (if credentials provided or testing)
        try:
            binance = BinanceFuturesClient(
                api_key=self.binance_api_key,
                api_secret=self.binance_api_secret
            )
            self._exchanges.append(binance)
            logger.info("Initialized Binance client")
        except Exception as e:
            logger.warning(f"Failed to initialize Binance client: {e}")
        
        # Priority 2: Bybit (public endpoints, no API key needed)
        try:
            bybit = BybitFuturesClient()
            self._exchanges.append(bybit)
            logger.info("Initialized Bybit client")
        except Exception as e:
            logger.warning(f"Failed to initialize Bybit client: {e}")
        
        # Priority 3: OKX (public endpoints, no API key needed)
        try:
            okx = OKXFuturesClient()
            self._exchanges.append(okx)
            logger.info("Initialized OKX client")
        except Exception as e:
            logger.warning(f"Failed to initialize OKX client: {e}")
        
        if not self._exchanges:
            raise RuntimeError("No exchanges could be initialized")
        
        logger.info(f"Initialized {len(self._exchanges)} exchanges")
    
    def _get_exchange_by_name(self, name: str) -> Optional[BaseExchangeClient]:
        """Get an exchange client by name."""
        name = name.lower()
        for exchange in self._exchanges:
            if exchange.name.lower() == name:
                return exchange
        return None
    
    def get_working_client(self) -> BaseExchangeClient:
        """
        Get a working exchange client, with fallback on failure.
        
        Returns:
            Working BaseExchangeClient instance
            
        Raises:
            RuntimeError: If all exchanges are unavailable
        """
        # If we have a cached active exchange, verify it's still working
        if self._active_exchange is not None:
            try:
                if self._active_exchange.health_check():
                    return self._active_exchange
                else:
                    logger.warning(f"{self._active_exchange.name} is no longer available")
                    self._active_exchange = None
            except Exception:
                self._active_exchange = None
        
        # If user specified a preferred exchange, try it first
        if self.preferred_exchange != "auto":
            preferred = self._get_exchange_by_name(self.preferred_exchange)
            if preferred:
                try:
                    if preferred.health_check():
                        logger.info(f"Using preferred exchange: {preferred.name}")
                        self._active_exchange = preferred
                        return preferred
                except Exception as e:
                    logger.warning(f"Preferred exchange {preferred.name} failed: {e}")
        
        # Try exchanges in priority order
        for exchange in self._exchanges:
            try:
                logger.info(f"Trying {exchange.name}...")
                if exchange.health_check():
                    logger.info(f"Successfully connected to {exchange.name}")
                    self._active_exchange = exchange
                    return exchange
            except Exception as e:
                logger.warning(f"{exchange.name} unavailable: {e}")
                continue
        
        raise RuntimeError(
            "All exchanges unavailable. Please check your network connection "
            "and API credentials."
        )
    
    def get_active_exchange_name(self) -> str:
        """Get the name of the currently active exchange."""
        if self._active_exchange:
            return self._active_exchange.name
        return "None"
    
    def list_available_exchanges(self) -> List[str]:
        """List all configured exchanges."""
        return [e.name for e in self._exchanges]
    
    def force_exchange(self, name: str) -> bool:
        """
        Force using a specific exchange.
        
        Args:
            name: Exchange name ('binance', 'bybit', 'okx')
            
        Returns:
            True if exchange is available, False otherwise
        """
        exchange = self._get_exchange_by_name(name)
        if exchange and exchange.health_check():
            self._active_exchange = exchange
            logger.info(f"Forced exchange to {exchange.name}")
            return True
        return False
