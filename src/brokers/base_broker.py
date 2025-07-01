"""
Base broker interface for trading operations.
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
import pandas as pd
from src.core.config import TimeFrame, OrderType


class BaseBroker(ABC):
    """Abstract base class for broker interfaces."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.connected = False
        self.account_info = None
    
    @abstractmethod
    def connect(self) -> bool:
        """Connect to the broker."""
        pass
    
    @abstractmethod
    def disconnect(self) -> bool:
        """Disconnect from the broker."""
        pass
    
    @abstractmethod
    def get_account_info(self) -> Dict[str, Any]:
        """Get account information."""
        pass
    
    @abstractmethod
    def get_symbols(self) -> List[str]:
        """Get available symbols."""
        pass
    
    @abstractmethod
    def get_symbol_info(self, symbol: str) -> Dict[str, Any]:
        """Get symbol information."""
        pass
    
    @abstractmethod
    def get_historical_data(self, symbol: str, timeframe: TimeFrame, 
                          start_date: datetime, end_date: datetime) -> pd.DataFrame:
        """Get historical price data."""
        pass
    
    @abstractmethod
    def place_order(self, symbol: str, order_type: OrderType, volume: float,
                   price: Optional[float] = None, sl: Optional[float] = None,
                   tp: Optional[float] = None, comment: str = "") -> Dict[str, Any]:
        """Place a trading order."""
        pass
    
    @abstractmethod
    def modify_order(self, ticket: int, price: Optional[float] = None,
                    sl: Optional[float] = None, tp: Optional[float] = None) -> bool:
        """Modify an existing order."""
        pass
    
    @abstractmethod
    def close_order(self, ticket: int, volume: Optional[float] = None) -> bool:
        """Close an order."""
        pass
    
    @abstractmethod
    def get_open_orders(self) -> List[Dict[str, Any]]:
        """Get all open orders."""
        pass
    
    @abstractmethod
    def get_order_history(self, start_date: datetime, end_date: datetime) -> List[Dict[str, Any]]:
        """Get order history."""
        pass
    
    @abstractmethod
    def get_current_price(self, symbol: str) -> Dict[str, float]:
        """Get current bid/ask prices."""
        pass
    
    def is_connected(self) -> bool:
        """Check if connected to broker."""
        return self.connected
    
    def calculate_position_size(self, symbol: str, risk_amount: float, 
                              stop_loss_pips: float) -> float:
        """Calculate position size based on risk management."""
        account_info = self.get_account_info()
        symbol_info = self.get_symbol_info(symbol)
        
        if not account_info or not symbol_info:
            return 0.0
        
        balance = account_info.get('balance', 0)
        pip_value = symbol_info.get('pip_value', 0.0001)
        
        if stop_loss_pips <= 0 or pip_value <= 0:
            return 0.0
        
        risk_per_lot = stop_loss_pips * pip_value
        if risk_per_lot <= 0:
            return 0.0
        
        position_size = risk_amount / risk_per_lot
        return min(position_size, balance * 0.1)  # Max 10% of balance 