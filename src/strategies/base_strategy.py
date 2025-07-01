"""
Base strategy class for all trading strategies.
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import pandas as pd
from loguru import logger

from src.core.config import StrategyConfig, TimeFrame, OrderType, SessionType


class BaseStrategy(ABC):
    """Abstract base class for all trading strategies."""
    
    def __init__(self, config: StrategyConfig, broker, risk_manager, session_manager):
        self.config = config
        self.broker = broker
        self.risk_manager = risk_manager
        self.session_manager = session_manager
        self.enabled = config.enabled
        self.symbols = config.symbols
        self.timeframe = config.timeframe
        self.parameters = config.parameters
        
        # Strategy state
        self.positions: Dict[str, Dict] = {}
        self.last_signals: Dict[str, Dict] = {}
        self.performance_metrics: Dict[str, Any] = {}
        
    @abstractmethod
    def calculate_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """Calculate technical indicators for the strategy."""
        pass
    
    @abstractmethod
    def generate_signals(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Generate trading signals based on indicators."""
        pass
    
    @abstractmethod
    def should_trade(self, symbol: str, session_type: SessionType) -> bool:
        """Check if the strategy should trade in the current session."""
        pass
    
    def get_data(self, symbol: str, lookback_periods: int = 100) -> pd.DataFrame:
        """Get historical data for analysis."""
        try:
            end_date = datetime.now()
            start_date = end_date - pd.Timedelta(days=lookback_periods)
            
            data = self.broker.get_historical_data(
                symbol, self.timeframe, start_date, end_date
            )
            
            if data.empty:
                logger.warning(f"No data received for {symbol}")
                return pd.DataFrame()
            
            return data
            
        except Exception as e:
            logger.error(f"Error getting data for {symbol}: {e}")
            return pd.DataFrame()
    
    def analyze_symbol(self, symbol: str) -> Dict[str, Any]:
        """Analyze a symbol and return trading signals."""
        if not self.enabled:
            return {'signal': 'DISABLED', 'reason': 'Strategy disabled'}
        
        # Get market data
        data = self.get_data(symbol)
        if data.empty:
            return {'signal': 'NO_DATA', 'reason': 'No market data available'}
        
        # Check if we should trade in current session
        active_sessions = self.session_manager.get_active_sessions()
        if not active_sessions:
            return {'signal': 'NO_SESSION', 'reason': 'No active trading sessions'}
        
        should_trade = False
        for session in active_sessions:
            if self.should_trade(symbol, session):
                should_trade = True
                break
        
        if not should_trade:
            return {'signal': 'NO_TRADE', 'reason': 'Strategy not suitable for current session'}
        
        # Calculate indicators
        data_with_indicators = self.calculate_indicators(data)
        if data_with_indicators.empty:
            return {'signal': 'NO_INDICATORS', 'reason': 'Unable to calculate indicators'}
        
        # Generate signals
        signals = self.generate_signals(data_with_indicators)
        
        # Store last signal
        self.last_signals[symbol] = signals
        
        return signals
    
    def execute_signal(self, symbol: str, signal: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a trading signal."""
        if signal.get('signal') not in ['BUY', 'SELL']:
            return {'success': False, 'reason': 'Invalid signal'}
        
        # Check risk management
        volume = signal.get('volume', 0.01)
        stop_loss_pips = signal.get('stop_loss_pips', self.risk_manager.config.stop_loss_pips)
        
        can_trade, reason = self.risk_manager.can_open_position(symbol, volume, stop_loss_pips)
        if not can_trade:
            return {'success': False, 'reason': reason}
        
        # Calculate position size
        account_info = self.broker.get_account_info()
        if not account_info:
            return {'success': False, 'reason': 'Unable to get account info'}
        
        risk_amount = account_info.get('balance', 0) * self.risk_manager.config.max_position_size
        volume = self.risk_manager.calculate_position_size(symbol, risk_amount, stop_loss_pips)
        
        if volume <= 0:
            return {'success': False, 'reason': 'Invalid position size'}
        
        # Determine order type
        order_type = OrderType.BUY if signal['signal'] == 'BUY' else OrderType.SELL
        
        # Calculate stop loss and take profit
        current_price = self.broker.get_current_price(symbol)
        if not current_price:
            return {'success': False, 'reason': 'Unable to get current price'}
        
        if order_type == OrderType.BUY:
            price = current_price['ask']
            sl = price - (stop_loss_pips * 0.0001)
            tp = price + (signal.get('take_profit_pips', self.risk_manager.config.take_profit_pips) * 0.0001)
        else:
            price = current_price['bid']
            sl = price + (stop_loss_pips * 0.0001)
            tp = price - (signal.get('take_profit_pips', self.risk_manager.config.take_profit_pips) * 0.0001)
        
        # Place order
        result = self.broker.place_order(
            symbol=symbol,
            order_type=order_type,
            volume=volume,
            price=price,
            sl=sl,
            tp=tp,
            comment=f"{self.config.name}_{signal['signal']}"
        )
        
        if result['success']:
            # Track position
            from src.risk_management.risk_manager import Position
            position = Position(
                ticket=result['ticket'],
                symbol=symbol,
                order_type=order_type,
                volume=volume,
                price=price,
                sl=sl,
                tp=tp
            )
            self.risk_manager.add_position(position)
            
            logger.info(f"Executed {signal['signal']} order for {symbol}: {result}")
        
        return result
    
    def update_performance(self, symbol: str, pnl: float) -> None:
        """Update performance metrics."""
        if symbol not in self.performance_metrics:
            self.performance_metrics[symbol] = {
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'total_pnl': 0.0,
                'max_profit': 0.0,
                'max_loss': 0.0,
            }
        
        metrics = self.performance_metrics[symbol]
        metrics['total_trades'] += 1
        metrics['total_pnl'] += pnl
        
        if pnl > 0:
            metrics['winning_trades'] += 1
            metrics['max_profit'] = max(metrics['max_profit'], pnl)
        else:
            metrics['losing_trades'] += 1
            metrics['max_loss'] = min(metrics['max_loss'], pnl)
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary for the strategy."""
        total_trades = sum(m['total_trades'] for m in self.performance_metrics.values())
        total_pnl = sum(m['total_pnl'] for m in self.performance_metrics.values())
        winning_trades = sum(m['winning_trades'] for m in self.performance_metrics.values())
        
        return {
            'strategy_name': self.config.name,
            'enabled': self.enabled,
            'symbols': self.symbols,
            'timeframe': self.timeframe,
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'win_rate': winning_trades / total_trades if total_trades > 0 else 0,
            'total_pnl': total_pnl,
            'average_pnl': total_pnl / total_trades if total_trades > 0 else 0,
            'parameters': self.parameters,
        }
    
    def get_strategy_status(self) -> Dict[str, Any]:
        """Get current strategy status."""
        return {
            'name': self.config.name,
            'enabled': self.enabled,
            'symbols': self.symbols,
            'timeframe': self.timeframe,
            'last_signals': self.last_signals,
            'performance': self.get_performance_summary(),
        }
    
    def enable(self) -> None:
        """Enable the strategy."""
        self.enabled = True
        logger.info(f"Strategy {self.config.name} enabled")
    
    def disable(self) -> None:
        """Disable the strategy."""
        self.enabled = False
        logger.info(f"Strategy {self.config.name} disabled")
    
    def update_parameters(self, parameters: Dict[str, Any]) -> None:
        """Update strategy parameters."""
        self.parameters.update(parameters)
        logger.info(f"Updated parameters for {self.config.name}: {parameters}")
    
    def reset_performance(self) -> None:
        """Reset performance metrics."""
        self.performance_metrics = {}
        self.last_signals = {}
        logger.info(f"Reset performance metrics for {self.config.name}") 