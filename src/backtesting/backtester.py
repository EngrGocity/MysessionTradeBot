"""
Backtesting system for trading strategies.
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import seaborn as sns
from loguru import logger

from src.core.config import TradingBotConfig, StrategyConfig
from src.brokers.mt5_broker import MT5Broker
from src.core.session_manager import SessionManager
from src.risk_management.risk_manager import RiskManager
from src.strategies.session_breakout_strategy import SessionBreakoutStrategy
from src.strategies.ml_strategy import MLStrategy


class BacktestResult:
    """Container for backtest results."""
    
    def __init__(self):
        self.trades: List[Dict] = []
        self.equity_curve: pd.Series = None
        self.returns: pd.Series = None
        self.metrics: Dict[str, float] = {}
        self.strategy_performance: Dict[str, Dict] = {}
    
    def add_trade(self, trade: Dict):
        """Add a trade to the results."""
        self.trades.append(trade)
    
    def calculate_metrics(self):
        """Calculate performance metrics."""
        if not self.trades:
            return
        
        # Convert trades to DataFrame
        trades_df = pd.DataFrame(self.trades)
        
        # Basic metrics
        total_trades = len(trades_df)
        winning_trades = len(trades_df[trades_df['pnl'] > 0])
        losing_trades = len(trades_df[trades_df['pnl'] < 0])
        
        self.metrics = {
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'win_rate': winning_trades / total_trades if total_trades > 0 else 0,
            'total_pnl': trades_df['pnl'].sum(),
            'avg_win': trades_df[trades_df['pnl'] > 0]['pnl'].mean() if winning_trades > 0 else 0,
            'avg_loss': trades_df[trades_df['pnl'] < 0]['pnl'].mean() if losing_trades > 0 else 0,
            'profit_factor': abs(trades_df[trades_df['pnl'] > 0]['pnl'].sum() / 
                               trades_df[trades_df['pnl'] < 0]['pnl'].sum()) if losing_trades > 0 else float('inf'),
            'max_drawdown': self._calculate_max_drawdown(),
            'sharpe_ratio': self._calculate_sharpe_ratio(),
            'sortino_ratio': self._calculate_sortino_ratio()
        }
    
    def _calculate_max_drawdown(self) -> float:
        """Calculate maximum drawdown."""
        if self.equity_curve is None:
            return 0.0
        
        peak = self.equity_curve.expanding().max()
        drawdown = (self.equity_curve - peak) / peak
        return abs(drawdown.min())
    
    def _calculate_sharpe_ratio(self) -> float:
        """Calculate Sharpe ratio."""
        if self.returns is None or len(self.returns) < 2:
            return 0.0
        
        return self.returns.mean() / self.returns.std() * np.sqrt(252)  # Annualized
    
    def _calculate_sortino_ratio(self) -> float:
        """Calculate Sortino ratio."""
        if self.returns is None or len(self.returns) < 2:
            return 0.0
        
        negative_returns = self.returns[self.returns < 0]
        if len(negative_returns) == 0:
            return float('inf')
        
        downside_std = negative_returns.std()
        return self.returns.mean() / downside_std * np.sqrt(252)  # Annualized


class Backtester:
    """Backtesting engine for trading strategies."""
    
    def __init__(self, config: TradingBotConfig):
        self.config = config
        self.results: Dict[str, BacktestResult] = {}
        
        # Initialize components
        self.broker = MT5Broker(config.broker.dict())
        self.session_manager = SessionManager()
        self.risk_manager = RiskManager(config.risk, self.broker)
        
        # Initialize strategies
        self.strategies = {}
        self._initialize_strategies()
        
        # Initialize sessions
        self._initialize_sessions()
    
    def _initialize_strategies(self):
        """Initialize strategies for backtesting."""
        for strategy_config in self.config.strategies:
            if strategy_config.name == "session_breakout":
                strategy = SessionBreakoutStrategy(
                    strategy_config, self.broker, self.risk_manager, self.session_manager
                )
                self.strategies[strategy_config.name] = strategy
            elif strategy_config.name == "ml_strategy":
                strategy = MLStrategy(
                    strategy_config, self.broker, self.risk_manager, self.session_manager
                )
                self.strategies[strategy_config.name] = strategy
    
    def _initialize_sessions(self):
        """Initialize market sessions."""
        for session_config in self.config.sessions:
            self.session_manager.add_session(session_config)
    
    def run_backtest(self, symbol: str, start_date: datetime, end_date: datetime,
                    initial_balance: float = 10000.0) -> Dict[str, BacktestResult]:
        """Run backtest for all strategies."""
        logger.info(f"Starting backtest for {symbol} from {start_date} to {end_date}")
        
        # Get historical data
        data = self._get_historical_data(symbol, start_date, end_date)
        if data.empty:
            logger.error("No historical data available for backtesting")
            return {}
        
        # Run backtest for each strategy
        for strategy_name, strategy in self.strategies.items():
            logger.info(f"Running backtest for {strategy_name}")
            result = self._run_strategy_backtest(strategy, symbol, data, initial_balance)
            self.results[strategy_name] = result
        
        return self.results
    
    def _get_historical_data(self, symbol: str, start_date: datetime, 
                           end_date: datetime) -> pd.DataFrame:
        """Get historical data for backtesting."""
        try:
            # Connect to broker
            if not self.broker.connect():
                logger.error("Failed to connect to broker for data")
                return pd.DataFrame()
            
            # Get data
            data = self.broker.get_historical_data(
                symbol, self.config.strategies[0].timeframe, start_date, end_date
            )
            
            # Disconnect
            self.broker.disconnect()
            
            return data
            
        except Exception as e:
            logger.error(f"Error getting historical data: {e}")
            return pd.DataFrame()
    
    def _run_strategy_backtest(self, strategy, symbol: str, data: pd.DataFrame,
                             initial_balance: float) -> BacktestResult:
        """Run backtest for a single strategy."""
        result = BacktestResult()
        
        # Initialize variables
        balance = initial_balance
        equity = initial_balance
        position = None
        equity_curve = []
        
        # Process each bar
        for i in range(len(data)):
            current_bar = data.iloc[i:i+1]
            current_time = current_bar.index[0]
            
            # Check if session is active
            active_sessions = self.session_manager.get_active_sessions()
            if not active_sessions:
                continue
            
            # Check if strategy should trade
            should_trade = False
            for session in active_sessions:
                if strategy.should_trade(symbol, session):
                    should_trade = True
                    break
            
            if not should_trade:
                continue
            
            # Get historical data up to current bar
            historical_data = data.iloc[:i+1]
            
            # Calculate indicators
            data_with_indicators = strategy.calculate_indicators(historical_data)
            
            # Generate signal
            signal = strategy.generate_signals(data_with_indicators)
            
            # Execute trades
            if signal.get('signal') in ['BUY', 'SELL'] and position is None:
                # Open position
                position = self._open_position(signal, current_bar, balance)
                if position:
                    balance -= position['cost']
            
            elif position is not None:
                # Check if position should be closed
                if self._should_close_position(position, current_bar, signal):
                    # Close position
                    pnl = self._close_position(position, current_bar)
                    balance += pnl
                    
                    # Record trade
                    trade = {
                        'entry_time': position['entry_time'],
                        'exit_time': current_time,
                        'symbol': symbol,
                        'type': position['type'],
                        'entry_price': position['entry_price'],
                        'exit_price': current_bar['close'].iloc[0],
                        'volume': position['volume'],
                        'pnl': pnl,
                        'strategy': strategy.config.name
                    }
                    result.add_trade(trade)
                    
                    position = None
            
            # Update equity
            if position:
                # Calculate unrealized P&L
                unrealized_pnl = self._calculate_unrealized_pnl(position, current_bar)
                equity = balance + unrealized_pnl
            else:
                equity = balance
            
            equity_curve.append(equity)
        
        # Close any remaining position
        if position:
            pnl = self._close_position(position, data.iloc[-1:])
            balance += pnl
            
            trade = {
                'entry_time': position['entry_time'],
                'exit_time': data.index[-1],
                'symbol': symbol,
                'type': position['type'],
                'entry_price': position['entry_price'],
                'exit_price': data['close'].iloc[-1],
                'volume': position['volume'],
                'pnl': pnl,
                'strategy': strategy.config.name
            }
            result.add_trade(trade)
        
        # Calculate final metrics
        result.equity_curve = pd.Series(equity_curve, index=data.index[:len(equity_curve)])
        result.returns = result.equity_curve.pct_change().dropna()
        result.calculate_metrics()
        
        return result
    
    def _open_position(self, signal: Dict, bar: pd.DataFrame, balance: float) -> Optional[Dict]:
        """Open a new position."""
        try:
            # Calculate position size
            risk_amount = balance * self.config.risk.max_position_size
            volume = 0.01  # Default volume
            
            # Calculate entry price
            if signal['signal'] == 'BUY':
                entry_price = bar['high'].iloc[0]  # Slippage simulation
                position_type = 'BUY'
            else:
                entry_price = bar['low'].iloc[0]  # Slippage simulation
                position_type = 'SELL'
            
            # Calculate cost
            cost = volume * entry_price
            
            if cost > balance:
                return None
            
            return {
                'type': position_type,
                'entry_price': entry_price,
                'volume': volume,
                'entry_time': bar.index[0],
                'cost': cost,
                'stop_loss': signal.get('stop_loss_pips', 50),
                'take_profit': signal.get('take_profit_pips', 100)
            }
            
        except Exception as e:
            logger.error(f"Error opening position: {e}")
            return None
    
    def _should_close_position(self, position: Dict, bar: pd.DataFrame, signal: Dict) -> bool:
        """Check if position should be closed."""
        current_price = bar['close'].iloc[0]
        
        # Check stop loss
        if position['type'] == 'BUY':
            stop_loss_price = position['entry_price'] - (position['stop_loss'] * 0.0001)
            if current_price <= stop_loss_price:
                return True
            
            take_profit_price = position['entry_price'] + (position['take_profit'] * 0.0001)
            if current_price >= take_profit_price:
                return True
        else:
            stop_loss_price = position['entry_price'] + (position['stop_loss'] * 0.0001)
            if current_price >= stop_loss_price:
                return True
            
            take_profit_price = position['entry_price'] - (position['take_profit'] * 0.0001)
            if current_price <= take_profit_price:
                return True
        
        # Check for opposite signal
        if signal.get('signal') != position['type']:
            return True
        
        return False
    
    def _close_position(self, position: Dict, bar: pd.DataFrame) -> float:
        """Close position and calculate P&L."""
        exit_price = bar['close'].iloc[0]
        
        if position['type'] == 'BUY':
            pnl = (exit_price - position['entry_price']) * position['volume']
        else:
            pnl = (position['entry_price'] - exit_price) * position['volume']
        
        return pnl
    
    def _calculate_unrealized_pnl(self, position: Dict, bar: pd.DataFrame) -> float:
        """Calculate unrealized P&L for open position."""
        current_price = bar['close'].iloc[0]
        
        if position['type'] == 'BUY':
            pnl = (current_price - position['entry_price']) * position['volume']
        else:
            pnl = (position['entry_price'] - current_price) * position['volume']
        
        return pnl
    
    def generate_report(self) -> str:
        """Generate backtest report."""
        report = []
        report.append("=" * 60)
        report.append("BACKTEST REPORT")
        report.append("=" * 60)
        
        for strategy_name, result in self.results.items():
            report.append(f"\nStrategy: {strategy_name}")
            report.append("-" * 40)
            
            if result.metrics:
                report.append(f"Total Trades: {result.metrics['total_trades']}")
                report.append(f"Win Rate: {result.metrics['win_rate']:.2%}")
                report.append(f"Total P&L: ${result.metrics['total_pnl']:.2f}")
                report.append(f"Profit Factor: {result.metrics['profit_factor']:.2f}")
                report.append(f"Max Drawdown: {result.metrics['max_drawdown']:.2%}")
                report.append(f"Sharpe Ratio: {result.metrics['sharpe_ratio']:.2f}")
                report.append(f"Sortino Ratio: {result.metrics['sortino_ratio']:.2f}")
            else:
                report.append("No trades executed")
        
        return "\n".join(report)
    
    def plot_results(self, save_path: str = None):
        """Plot backtest results."""
        try:
            fig, axes = plt.subplots(2, 2, figsize=(15, 10))
            
            # Equity curves
            ax1 = axes[0, 0]
            for strategy_name, result in self.results.items():
                if result.equity_curve is not None:
                    ax1.plot(result.equity_curve.index, result.equity_curve.values, 
                            label=strategy_name)
            ax1.set_title('Equity Curves')
            ax1.set_xlabel('Date')
            ax1.set_ylabel('Equity')
            ax1.legend()
            ax1.grid(True)
            
            # Drawdown
            ax2 = axes[0, 1]
            for strategy_name, result in self.results.items():
                if result.equity_curve is not None:
                    peak = result.equity_curve.expanding().max()
                    drawdown = (result.equity_curve - peak) / peak
                    ax2.fill_between(drawdown.index, drawdown.values, 0, alpha=0.3, label=strategy_name)
            ax2.set_title('Drawdown')
            ax2.set_xlabel('Date')
            ax2.set_ylabel('Drawdown %')
            ax2.legend()
            ax2.grid(True)
            
            # Returns distribution
            ax3 = axes[1, 0]
            for strategy_name, result in self.results.items():
                if result.returns is not None:
                    ax3.hist(result.returns.values, bins=30, alpha=0.5, label=strategy_name)
            ax3.set_title('Returns Distribution')
            ax3.set_xlabel('Returns')
            ax3.set_ylabel('Frequency')
            ax3.legend()
            ax3.grid(True)
            
            # Performance metrics
            ax4 = axes[1, 1]
            metrics_data = []
            strategy_names = []
            for strategy_name, result in self.results.items():
                if result.metrics:
                    metrics_data.append([
                        result.metrics['win_rate'],
                        result.metrics['sharpe_ratio'],
                        result.metrics['max_drawdown']
                    ])
                    strategy_names.append(strategy_name)
            
            if metrics_data:
                metrics_df = pd.DataFrame(metrics_data, 
                                        columns=['Win Rate', 'Sharpe Ratio', 'Max Drawdown'],
                                        index=strategy_names)
                metrics_df.plot(kind='bar', ax=ax4)
                ax4.set_title('Performance Metrics')
                ax4.set_ylabel('Value')
                ax4.legend()
                ax4.grid(True)
            
            plt.tight_layout()
            
            if save_path:
                plt.savefig(save_path, dpi=300, bbox_inches='tight')
                logger.info(f"Backtest plots saved to {save_path}")
            
            plt.show()
            
        except Exception as e:
            logger.error(f"Error plotting results: {e}") 