"""
MT5 broker implementation with support for Exness and other MT5 brokers.
"""
import MetaTrader5 as mt5
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import pytz
from loguru import logger

from src.brokers.base_broker import BaseBroker
from src.core.config import TimeFrame, OrderType


class MT5Broker(BaseBroker):
    """MT5 broker implementation."""
    
    # MT5 timeframe mapping
    TIMEFRAME_MAP = {
        TimeFrame.M1: mt5.TIMEFRAME_M1,
        TimeFrame.M5: mt5.TIMEFRAME_M5,
        TimeFrame.M15: mt5.TIMEFRAME_M15,
        TimeFrame.M30: mt5.TIMEFRAME_M30,
        TimeFrame.H1: mt5.TIMEFRAME_H1,
        TimeFrame.H4: mt5.TIMEFRAME_H4,
        TimeFrame.D1: mt5.TIMEFRAME_D1,
    }
    
    # Order type mapping
    ORDER_TYPE_MAP = {
        OrderType.BUY: mt5.ORDER_TYPE_BUY,
        OrderType.SELL: mt5.ORDER_TYPE_SELL,
        OrderType.BUY_LIMIT: mt5.ORDER_TYPE_BUY_LIMIT,
        OrderType.SELL_LIMIT: mt5.ORDER_TYPE_SELL_LIMIT,
        OrderType.BUY_STOP: mt5.ORDER_TYPE_BUY_STOP,
        OrderType.SELL_STOP: mt5.ORDER_TYPE_SELL_STOP,
    }
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.mt5 = mt5
        self.timezone = pytz.UTC
        
    def connect(self) -> bool:
        """Connect to MT5 broker."""
        try:
            # Initialize MT5
            if not self.mt5.initialize():
                logger.error(f"MT5 initialization failed: {self.mt5.last_error()}")
                return False
            
            # Login to account
            if not self.mt5.login(
                login=self.config['login'],
                password=self.config['password'],
                server=self.config['server']
            ):
                logger.error(f"MT5 login failed: {self.mt5.last_error()}")
                return False
            
            self.connected = True
            logger.info(f"Connected to MT5 broker: {self.config['server']}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to MT5: {e}")
            return False
    
    def disconnect(self) -> bool:
        """Disconnect from MT5 broker."""
        try:
            self.mt5.shutdown()
            self.connected = False
            logger.info("Disconnected from MT5 broker")
            return True
        except Exception as e:
            logger.error(f"Failed to disconnect from MT5: {e}")
            return False
    
    def get_account_info(self) -> Dict[str, Any]:
        """Get account information."""
        if not self.connected:
            return {}
        
        try:
            account_info = self.mt5.account_info()
            if account_info is None:
                return {}
            
            return {
                'login': account_info.login,
                'server': account_info.server,
                'balance': account_info.balance,
                'equity': account_info.equity,
                'margin': account_info.margin,
                'margin_free': account_info.margin_free,
                'profit': account_info.profit,
                'currency': account_info.currency,
                'leverage': account_info.leverage,
                'trade_mode': account_info.trade_mode,
            }
        except Exception as e:
            logger.error(f"Failed to get account info: {e}")
            return {}
    
    def get_symbols(self) -> List[str]:
        """Get available symbols."""
        if not self.connected:
            return []
        
        try:
            symbols = self.mt5.symbols_get()
            if symbols is None:
                return []
            
            return [symbol.name for symbol in symbols]
        except Exception as e:
            logger.error(f"Failed to get symbols: {e}")
            return []
    
    def get_symbol_info(self, symbol: str) -> Dict[str, Any]:
        """Get symbol information."""
        if not self.connected:
            return {}
        
        try:
            symbol_info = self.mt5.symbol_info(symbol)
            if symbol_info is None:
                return {}
            
            return {
                'name': symbol_info.name,
                'bid': symbol_info.bid,
                'ask': symbol_info.ask,
                'point': symbol_info.point,
                'digits': symbol_info.digits,
                'spread': symbol_info.spread,
                'trade_mode': symbol_info.trade_mode,
                'volume_min': symbol_info.volume_min,
                'volume_max': symbol_info.volume_max,
                'volume_step': symbol_info.volume_step,
                'pip_value': symbol_info.point * 10,  # For most forex pairs
            }
        except Exception as e:
            logger.error(f"Failed to get symbol info for {symbol}: {e}")
            return {}
    
    def get_historical_data(self, symbol: str, timeframe: TimeFrame, 
                          start_date: datetime, end_date: datetime) -> pd.DataFrame:
        """Get historical price data."""
        if not self.connected:
            return pd.DataFrame()
        
        try:
            # Convert to MT5 timeframe
            mt5_timeframe = self.TIMEFRAME_MAP.get(timeframe)
            if mt5_timeframe is None:
                logger.error(f"Unsupported timeframe: {timeframe}")
                return pd.DataFrame()
            
            # Convert dates to UTC
            start_utc = start_date.astimezone(self.timezone)
            end_utc = end_date.astimezone(self.timezone)
            
            # Get historical data
            rates = self.mt5.copy_rates_range(symbol, mt5_timeframe, start_utc, end_utc)
            if rates is None or len(rates) == 0:
                return pd.DataFrame()
            
            # Convert to DataFrame
            df = pd.DataFrame(rates)
            df['time'] = pd.to_datetime(df['time'], unit='s')
            df.set_index('time', inplace=True)
            
            return df
            
        except Exception as e:
            logger.error(f"Failed to get historical data for {symbol}: {e}")
            return pd.DataFrame()
    
    def place_order(self, symbol: str, order_type: OrderType, volume: float,
                   price: Optional[float] = None, sl: Optional[float] = None,
                   tp: Optional[float] = None, comment: str = "") -> Dict[str, Any]:
        """Place a trading order."""
        if not self.connected:
            return {'success': False, 'error': 'Not connected'}
        
        try:
            # Get symbol info for current prices
            symbol_info = self.get_symbol_info(symbol)
            if not symbol_info:
                return {'success': False, 'error': 'Symbol not found'}
            
            # Set default price if not provided
            if price is None:
                if order_type in [OrderType.BUY, OrderType.BUY_LIMIT, OrderType.BUY_STOP]:
                    price = symbol_info['ask']
                else:
                    price = symbol_info['bid']
            
            # Prepare order request
            request = {
                "action": self.mt5.TRADE_ACTION_DEAL,
                "symbol": symbol,
                "volume": volume,
                "type": self.ORDER_TYPE_MAP[order_type],
                "price": price,
                "deviation": 20,
                "magic": 234000,
                "comment": comment,
                "type_time": self.mt5.ORDER_TIME_GTC,
                "type_filling": self.mt5.ORDER_FILLING_IOC,
            }
            
            # Add stop loss and take profit
            if sl is not None:
                request["sl"] = sl
            if tp is not None:
                request["tp"] = tp
            
            # Send order
            result = self.mt5.order_send(request)
            
            if result.retcode != self.mt5.TRADE_RETCODE_DONE:
                return {
                    'success': False,
                    'error': f"Order failed: {result.retcode} - {result.comment}"
                }
            
            return {
                'success': True,
                'ticket': result.order,
                'volume': result.volume,
                'price': result.price,
                'comment': result.comment
            }
            
        except Exception as e:
            logger.error(f"Failed to place order: {e}")
            return {'success': False, 'error': str(e)}
    
    def modify_order(self, ticket: int, price: Optional[float] = None,
                    sl: Optional[float] = None, tp: Optional[float] = None) -> bool:
        """Modify an existing order."""
        if not self.connected:
            return False
        
        try:
            request = {
                "action": self.mt5.TRADE_ACTION_MODIFY,
                "order": ticket,
                "deviation": 20,
            }
            
            if price is not None:
                request["price"] = price
            if sl is not None:
                request["sl"] = sl
            if tp is not None:
                request["tp"] = tp
            
            result = self.mt5.order_send(request)
            return result.retcode == self.mt5.TRADE_RETCODE_DONE
            
        except Exception as e:
            logger.error(f"Failed to modify order {ticket}: {e}")
            return False
    
    def close_order(self, ticket: int, volume: Optional[float] = None) -> bool:
        """Close an order."""
        if not self.connected:
            return False
        
        try:
            # Get order info
            order = self.mt5.order_get(ticket=ticket)
            if order is None:
                return False
            
            if volume is None:
                volume = order.volume
            
            # Determine close price
            symbol_info = self.get_symbol_info(order.symbol)
            if not symbol_info:
                return False
            
            close_price = symbol_info['bid'] if order.type == self.mt5.ORDER_TYPE_BUY else symbol_info['ask']
            
            request = {
                "action": self.mt5.TRADE_ACTION_DEAL,
                "symbol": order.symbol,
                "volume": volume,
                "type": self.mt5.ORDER_TYPE_SELL if order.type == self.mt5.ORDER_TYPE_BUY else self.mt5.ORDER_TYPE_BUY,
                "position": ticket,
                "price": close_price,
                "deviation": 20,
                "magic": 234000,
                "comment": "Close order",
                "type_time": self.mt5.ORDER_TIME_GTC,
                "type_filling": self.mt5.ORDER_FILLING_IOC,
            }
            
            result = self.mt5.order_send(request)
            return result.retcode == self.mt5.TRADE_RETCODE_DONE
            
        except Exception as e:
            logger.error(f"Failed to close order {ticket}: {e}")
            return False
    
    def close_order_partial(self, ticket: int, volume: float) -> bool:
        """Close a partial order (for profit taking)."""
        if not self.connected:
            return False
        
        try:
            # Get order info
            order = self.mt5.order_get(ticket=ticket)
            if order is None:
                logger.error(f"Order {ticket} not found")
                return False
            
            # Validate volume
            if volume >= order.volume:
                logger.warning(f"Partial close volume {volume} >= order volume {order.volume}, closing full order")
                return self.close_order(ticket)
            
            symbol_info = self.get_symbol_info(order.symbol)
            if not symbol_info:
                return False
            
            if volume < symbol_info.get('volume_min', 0.01):
                logger.error(f"Partial close volume {volume} below minimum")
                return False
            
            # Determine close price
            close_price = symbol_info['bid'] if order.type == self.mt5.ORDER_TYPE_BUY else symbol_info['ask']
            
            request = {
                "action": self.mt5.TRADE_ACTION_DEAL,
                "symbol": order.symbol,
                "volume": volume,
                "type": self.mt5.ORDER_TYPE_SELL if order.type == self.mt5.ORDER_TYPE_BUY else self.mt5.ORDER_TYPE_BUY,
                "position": ticket,
                "price": close_price,
                "deviation": 20,
                "magic": 234000,
                "comment": f"Partial close {volume} lots",
                "type_time": self.mt5.ORDER_TIME_GTC,
                "type_filling": self.mt5.ORDER_FILLING_IOC,
            }
            
            result = self.mt5.order_send(request)
            if result.retcode != self.mt5.TRADE_RETCODE_DONE:
                logger.error(f"Failed to partially close order {ticket}: {result.comment}")
                return False
            
            logger.info(f"Partially closed order {ticket}: {volume} lots, {result.comment}")
            return True
            
        except Exception as e:
            logger.error(f"Error partially closing order {ticket}: {e}")
            return False
    
    def get_open_orders(self) -> List[Dict[str, Any]]:
        """Get all open orders."""
        if not self.connected:
            return []
        
        try:
            orders = self.mt5.orders_get()
            if orders is None:
                return []
            
            return [{
                'ticket': order.ticket,
                'symbol': order.symbol,
                'type': order.type,
                'volume': order.volume,
                'price': order.price,
                'sl': order.sl,
                'tp': order.tp,
                'time_setup': datetime.fromtimestamp(order.time_setup),
                'comment': order.comment,
            } for order in orders]
            
        except Exception as e:
            logger.error(f"Failed to get open orders: {e}")
            return []
    
    def get_order_history(self, start_date: datetime, end_date: datetime) -> List[Dict[str, Any]]:
        """Get order history."""
        if not self.connected:
            return []
        
        try:
            start_utc = start_date.astimezone(self.timezone)
            end_utc = end_date.astimezone(self.timezone)
            
            history = self.mt5.history_deals_get(start_utc, end_utc)
            if history is None:
                return []
            
            return [{
                'ticket': deal.ticket,
                'order': deal.order,
                'symbol': deal.symbol,
                'type': deal.type,
                'volume': deal.volume,
                'price': deal.price,
                'profit': deal.profit,
                'time': datetime.fromtimestamp(deal.time),
                'comment': deal.comment,
            } for deal in history]
            
        except Exception as e:
            logger.error(f"Failed to get order history: {e}")
            return []
    
    def get_current_price(self, symbol: str) -> Dict[str, float]:
        """Get current bid/ask prices."""
        symbol_info = self.get_symbol_info(symbol)
        if not symbol_info:
            return {}
        
        return {
            'bid': symbol_info.get('bid', 0),
            'ask': symbol_info.get('ask', 0),
            'spread': symbol_info.get('spread', 0),
        }
    
    def get_mid_price(self, symbol: str) -> Optional[float]:
        """Get current mid price for profit taking calculations."""
        symbol_info = self.get_symbol_info(symbol)
        if not symbol_info:
            return None
        
        bid = symbol_info.get('bid', 0)
        ask = symbol_info.get('ask', 0)
        
        if bid > 0 and ask > 0:
            return (bid + ask) / 2  # Return mid price
        elif bid > 0:
            return bid
        elif ask > 0:
            return ask
        else:
            return None
    
    def get_positions(self) -> List[Dict[str, Any]]:
        """Get open positions."""
        if not self.connected:
            return []
        
        try:
            positions = self.mt5.positions_get()
            if positions is None:
                return []
            
            return [{
                'ticket': pos.ticket,
                'symbol': pos.symbol,
                'type': pos.type,
                'volume': pos.volume,
                'price_open': pos.price_open,
                'price_current': pos.price_current,
                'sl': pos.sl,
                'tp': pos.tp,
                'profit': pos.profit,
                'time': datetime.fromtimestamp(pos.time),
                'comment': pos.comment,
            } for pos in positions]
            
        except Exception as e:
            logger.error(f"Failed to get positions: {e}")
            return [] 