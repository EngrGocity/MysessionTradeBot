"""
Simple backtesting system for trading strategies.
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Any
from datetime import datetime, timedelta
from loguru import logger

from src.core.config import TradingBotConfig
from src.brokers.mt5_broker import MT5Broker


class SimpleBacktester:
    """Simple backtesting engine."""
    
    def __init__(self, config: TradingBotConfig):
        self.config = config
        self.broker = MT5Broker(config.broker.dict())
    
    def run_backtest(self, symbol: str, start_date: datetime, end_date: datetime,
                    initial_balance: float = 10000.0) -> Dict[str, Any]:
        """Run simple backtest."""
        logger.info(f"Running backtest for {symbol}")
        
        # Get historical data
        data = self._get_data(symbol, start_date, end_date)
        if data.empty:
            return {}
        
        # Simulate trading
        results = self._simulate_trading(data, initial_balance)
        
        return results
    
    def _get_data(self, symbol: str, start_date: datetime, end_date: datetime) -> pd.DataFrame:
        """Get historical data."""
        try:
            if not self.broker.connect():
                return pd.DataFrame()
            
            data = self.broker.get_historical_data(
                symbol, self.config.strategies[0].timeframe, start_date, end_date
            )
            
            self.broker.disconnect()
            return data
            
        except Exception as e:
            logger.error(f"Error getting data: {e}")
            return pd.DataFrame()
    
    def _simulate_trading(self, data: pd.DataFrame, initial_balance: float) -> Dict[str, Any]:
        """Simulate trading strategy."""
        balance = initial_balance
        position = None
        trades = []
        equity_curve = []
        
        for i in range(len(data)):
            current_price = data['close'].iloc[i]
            
            # Simple breakout strategy simulation
            if i > 20:  # Need some history
                high_20 = data['high'].iloc[i-20:i].max()
                low_20 = data['low'].iloc[i-20:i].min()
                
                # Buy signal
                if current_price > high_20 and position is None:
                    position = {
                        'type': 'BUY',
                        'entry_price': current_price,
                        'entry_time': data.index[i],
                        'volume': 0.01
                    }
                
                # Sell signal
                elif current_price < low_20 and position is None:
                    position = {
                        'type': 'SELL',
                        'entry_price': current_price,
                        'entry_time': data.index[i],
                        'volume': 0.01
                    }
                
                # Close position
                elif position:
                    if position['type'] == 'BUY' and current_price < position['entry_price'] * 0.99:
                        pnl = (current_price - position['entry_price']) * position['volume']
                        balance += pnl
                        trades.append({
                            'entry_time': position['entry_time'],
                            'exit_time': data.index[i],
                            'type': position['type'],
                            'pnl': pnl
                        })
                        position = None
                    
                    elif position['type'] == 'SELL' and current_price > position['entry_price'] * 1.01:
                        pnl = (position['entry_price'] - current_price) * position['volume']
                        balance += pnl
                        trades.append({
                            'entry_time': position['entry_time'],
                            'exit_time': data.index[i],
                            'type': position['type'],
                            'pnl': pnl
                        })
                        position = None
            
            equity_curve.append(balance)
        
        # Calculate metrics
        total_trades = len(trades)
        winning_trades = len([t for t in trades if t['pnl'] > 0])
        total_pnl = sum(t['pnl'] for t in trades)
        
        return {
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'win_rate': winning_trades / total_trades if total_trades > 0 else 0,
            'total_pnl': total_pnl,
            'final_balance': balance,
            'return_pct': (balance - initial_balance) / initial_balance * 100,
            'trades': trades,
            'equity_curve': equity_curve
        } 