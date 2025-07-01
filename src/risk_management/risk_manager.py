"""
Risk management system for the trading bot.
"""
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import pandas as pd
from loguru import logger

from src.core.config import RiskConfig, OrderType


class Position:
    """Represents a trading position."""
    
    def __init__(self, ticket: int, symbol: str, order_type: OrderType, 
                 volume: float, price: float, sl: Optional[float] = None, 
                 tp: Optional[float] = None, open_time: datetime = None):
        self.ticket = ticket
        self.symbol = symbol
        self.order_type = order_type
        self.volume = volume
        self.price = price
        self.sl = sl
        self.tp = tp
        self.open_time = open_time or datetime.now()
        self.current_price = price
        self.unrealized_pnl = 0.0
        self.realized_pnl = 0.0
    
    def update_price(self, current_price: float) -> None:
        """Update current price and calculate unrealized P&L."""
        self.current_price = current_price
        
        # Calculate unrealized P&L
        if self.order_type == OrderType.BUY:
            self.unrealized_pnl = (current_price - self.price) * self.volume
        else:
            self.unrealized_pnl = (self.price - current_price) * self.volume
    
    def close(self, close_price: float, close_time: datetime = None) -> float:
        """Close the position and return realized P&L."""
        if self.order_type == OrderType.BUY:
            self.realized_pnl = (close_price - self.price) * self.volume
        else:
            self.realized_pnl = (self.price - close_price) * self.volume
        
        return self.realized_pnl


class RiskManager:
    """Comprehensive risk management system."""
    
    def __init__(self, config: RiskConfig, broker):
        self.config = config
        self.broker = broker
        self.positions: Dict[int, Position] = {}
        self.daily_pnl = 0.0
        self.daily_trades = 0
        self.max_daily_loss_reached = False
        self.last_reset_date = datetime.now().date()
        
        # Risk metrics
        self.total_trades = 0
        self.winning_trades = 0
        self.losing_trades = 0
        self.max_drawdown = 0.0
        self.current_drawdown = 0.0
        self.peak_balance = 0.0
        
    def reset_daily_metrics(self) -> None:
        """Reset daily metrics."""
        current_date = datetime.now().date()
        if current_date > self.last_reset_date:
            self.daily_pnl = 0.0
            self.daily_trades = 0
            self.max_daily_loss_reached = False
            self.last_reset_date = current_date
            logger.info("Daily risk metrics reset")
    
    def can_open_position(self, symbol: str, volume: float, 
                         stop_loss_pips: float) -> Tuple[bool, str]:
        """Check if a new position can be opened."""
        self.reset_daily_metrics()
        
        # Check if daily loss limit reached
        if self.max_daily_loss_reached:
            return False, "Daily loss limit reached"
        
        # Check maximum open positions
        if len(self.positions) >= self.config.max_open_positions:
            return False, "Maximum open positions reached"
        
        # Check position size
        account_info = self.broker.get_account_info()
        if not account_info:
            return False, "Unable to get account information"
        
        balance = account_info.get('balance', 0)
        max_position_value = balance * self.config.max_position_size
        
        # Calculate position value
        symbol_info = self.broker.get_symbol_info(symbol)
        if not symbol_info:
            return False, "Unable to get symbol information"
        
        position_value = volume * symbol_info.get('ask', 0)
        if position_value > max_position_value:
            return False, f"Position size exceeds maximum ({max_position_value:.2f})"
        
        # Check daily loss limit
        if abs(self.daily_pnl) >= balance * self.config.max_daily_loss:
            self.max_daily_loss_reached = True
            return False, "Daily loss limit would be exceeded"
        
        return True, "Position can be opened"
    
    def calculate_position_size(self, symbol: str, risk_amount: float, 
                              stop_loss_pips: float) -> float:
        """Calculate optimal position size based on risk."""
        symbol_info = self.broker.get_symbol_info(symbol)
        if not symbol_info:
            return 0.0
        
        pip_value = symbol_info.get('pip_value', 0.0001)
        if stop_loss_pips <= 0 or pip_value <= 0:
            return 0.0
        
        # Calculate position size based on risk
        risk_per_lot = stop_loss_pips * pip_value
        if risk_per_lot <= 0:
            return 0.0
        
        position_size = risk_amount / risk_per_lot
        
        # Apply broker limits
        min_volume = symbol_info.get('volume_min', 0.01)
        max_volume = symbol_info.get('volume_max', 100.0)
        volume_step = symbol_info.get('volume_step', 0.01)
        
        position_size = max(min_volume, min(max_volume, position_size))
        
        # Round to volume step
        position_size = round(position_size / volume_step) * volume_step
        
        return position_size
    
    def add_position(self, position: Position) -> None:
        """Add a new position to track."""
        self.positions[position.ticket] = position
        self.daily_trades += 1
        self.total_trades += 1
        logger.info(f"Added position {position.ticket} for {position.symbol}")
    
    def remove_position(self, ticket: int) -> None:
        """Remove a position from tracking."""
        if ticket in self.positions:
            position = self.positions[ticket]
            
            # Update statistics
            if position.realized_pnl > 0:
                self.winning_trades += 1
            elif position.realized_pnl < 0:
                self.losing_trades += 1
            
            self.daily_pnl += position.realized_pnl
            
            del self.positions[ticket]
            logger.info(f"Removed position {ticket}, P&L: {position.realized_pnl:.2f}")
    
    def update_positions(self) -> None:
        """Update all position prices and P&L."""
        for ticket, position in self.positions.items():
            current_price = self.broker.get_current_price(position.symbol)
            if current_price:
                if position.order_type == OrderType.BUY:
                    price = current_price.get('bid', position.current_price)
                else:
                    price = current_price.get('ask', position.current_price)
                
                position.update_price(price)
    
    def check_stop_losses(self) -> List[int]:
        """Check and return tickets of positions that hit stop loss."""
        tickets_to_close = []
        
        for ticket, position in self.positions.items():
            if position.sl is None:
                continue
            
            if position.order_type == OrderType.BUY and position.current_price <= position.sl:
                tickets_to_close.append(ticket)
            elif position.order_type == OrderType.SELL and position.current_price >= position.sl:
                tickets_to_close.append(ticket)
        
        return tickets_to_close
    
    def check_take_profits(self) -> List[int]:
        """Check and return tickets of positions that hit take profit."""
        tickets_to_close = []
        
        for ticket, position in self.positions.items():
            if position.tp is None:
                continue
            
            if position.order_type == OrderType.BUY and position.current_price >= position.tp:
                tickets_to_close.append(ticket)
            elif position.order_type == OrderType.SELL and position.current_price <= position.tp:
                tickets_to_close.append(ticket)
        
        return tickets_to_close
    
    def apply_trailing_stop(self) -> List[int]:
        """Apply trailing stop and return tickets to modify."""
        tickets_to_modify = []
        
        if not self.config.trailing_stop:
            return tickets_to_modify
        
        for ticket, position in self.positions.items():
            if position.sl is None:
                continue
            
            # Calculate new stop loss
            if position.order_type == OrderType.BUY:
                new_sl = position.current_price - (self.config.trailing_stop_pips * 0.0001)
                if new_sl > position.sl:
                    position.sl = new_sl
                    tickets_to_modify.append(ticket)
            else:
                new_sl = position.current_price + (self.config.trailing_stop_pips * 0.0001)
                if new_sl < position.sl:
                    position.sl = new_sl
                    tickets_to_modify.append(ticket)
        
        return tickets_to_modify
    
    def get_risk_metrics(self) -> Dict:
        """Get current risk metrics."""
        account_info = self.broker.get_account_info()
        balance = account_info.get('balance', 0) if account_info else 0
        
        # Calculate total unrealized P&L
        total_unrealized = sum(pos.unrealized_pnl for pos in self.positions.values())
        
        # Calculate drawdown
        current_equity = balance + self.daily_pnl + total_unrealized
        if current_equity > self.peak_balance:
            self.peak_balance = current_equity
        
        self.current_drawdown = (self.peak_balance - current_equity) / self.peak_balance if self.peak_balance > 0 else 0
        self.max_drawdown = max(self.max_drawdown, self.current_drawdown)
        
        return {
            'total_positions': len(self.positions),
            'daily_pnl': self.daily_pnl,
            'daily_trades': self.daily_trades,
            'total_trades': self.total_trades,
            'winning_trades': self.winning_trades,
            'losing_trades': self.losing_trades,
            'win_rate': self.winning_trades / self.total_trades if self.total_trades > 0 else 0,
            'total_unrealized_pnl': total_unrealized,
            'current_drawdown': self.current_drawdown,
            'max_drawdown': self.max_drawdown,
            'max_daily_loss_reached': self.max_daily_loss_reached,
            'balance': balance,
            'equity': current_equity,
        }
    
    def get_position_summary(self) -> List[Dict]:
        """Get summary of all positions."""
        return [{
            'ticket': pos.ticket,
            'symbol': pos.symbol,
            'type': pos.order_type,
            'volume': pos.volume,
            'open_price': pos.price,
            'current_price': pos.current_price,
            'sl': pos.sl,
            'tp': pos.tp,
            'unrealized_pnl': pos.unrealized_pnl,
            'open_time': pos.open_time.isoformat(),
        } for pos in self.positions.values()]
    
    def should_close_all_positions(self) -> bool:
        """Check if all positions should be closed due to risk limits."""
        self.reset_daily_metrics()
        
        account_info = self.broker.get_account_info()
        if not account_info:
            return False
        
        balance = account_info.get('balance', 0)
        
        # Check daily loss limit
        if abs(self.daily_pnl) >= balance * self.config.max_daily_loss:
            return True
        
        # Check maximum drawdown
        if self.current_drawdown >= 0.1:  # 10% drawdown
            return True
        
        return False
    
    def get_risk_alerts(self) -> List[str]:
        """Get current risk alerts."""
        alerts = []
        
        if self.max_daily_loss_reached:
            alerts.append("Daily loss limit reached")
        
        if len(self.positions) >= self.config.max_open_positions:
            alerts.append("Maximum open positions reached")
        
        if self.current_drawdown >= 0.05:  # 5% drawdown
            alerts.append(f"High drawdown: {self.current_drawdown:.2%}")
        
        account_info = self.broker.get_account_info()
        if account_info:
            balance = account_info.get('balance', 0)
            if abs(self.daily_pnl) >= balance * self.config.max_daily_loss * 0.8:  # 80% of limit
                alerts.append("Approaching daily loss limit")
        
        return alerts 