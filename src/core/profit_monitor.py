"""
Comprehensive profit monitoring system for trading bot.
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from loguru import logger
import json
import os
from pathlib import Path

from src.core.config import SessionType


@dataclass
class TradeRecord:
    """Record of a single trade."""
    ticket: int
    symbol: str
    order_type: str
    volume: float
    open_price: float
    close_price: Optional[float]
    open_time: datetime
    close_time: Optional[datetime]
    profit: float
    swap: float
    commission: float
    session: SessionType
    strategy: str
    stop_loss: Optional[float]
    take_profit: Optional[float]
    exit_reason: Optional[str]


@dataclass
class PerformanceMetrics:
    """Performance metrics for a trading period."""
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    total_profit: float
    total_loss: float
    net_profit: float
    profit_factor: float
    average_win: float
    average_loss: float
    largest_win: float
    largest_loss: float
    max_drawdown: float
    sharpe_ratio: float
    sortino_ratio: float
    calmar_ratio: float
    total_volume: float
    average_trade_duration: timedelta


@dataclass
class SessionPerformance:
    """Performance metrics for a specific session."""
    session: SessionType
    total_trades: int
    winning_trades: int
    win_rate: float
    total_profit: float
    average_profit: float
    profit_factor: float
    best_pair: str
    worst_pair: str


@dataclass
class ProfitTakingRule:
    """Rule for automatic profit taking."""
    name: str
    enabled: bool
    time_interval_minutes: int  # Time interval in minutes
    min_profit_pips: float      # Minimum profit in pips to take
    profit_percentage: float    # Percentage of profit to take (0.0-1.0)
    max_trades_per_interval: int  # Maximum trades to close per interval
    session_filter: Optional[SessionType] = None  # Apply only to specific session
    symbol_filter: Optional[str] = None  # Apply only to specific symbol
    last_execution: Optional[datetime] = None


@dataclass
class ActivePosition:
    """Track active position for profit taking."""
    ticket: int
    symbol: str
    order_type: str
    volume: float
    open_price: float
    open_time: datetime
    current_profit: float
    current_profit_pips: float
    session: SessionType
    strategy: str


class ProfitMonitor:
    """Comprehensive profit monitoring and analysis system."""
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        
        self.trades: List[TradeRecord] = []
        self.daily_pnl: Dict[str, float] = {}
        self.session_pnl: Dict[str, Dict[str, float]] = {}
        self.pair_pnl: Dict[str, float] = {}
        self.strategy_pnl: Dict[str, float] = {}
        
        # Performance tracking
        self.current_balance = 0.0
        self.peak_balance = 0.0
        self.max_drawdown = 0.0
        self.max_drawdown_pct = 0.0
        
        # Risk metrics
        self.daily_var_95 = 0.0
        self.weekly_var_95 = 0.0
        self.max_daily_loss = 0.0
        self.consecutive_losses = 0
        self.max_consecutive_losses = 0
        
        # Time-based profit taking
        self.profit_taking_rules: List[ProfitTakingRule] = []
        self.active_positions: Dict[int, ActivePosition] = {}
        self.broker = None  # Will be set by trading bot
        
        # Initialize default profit taking rules
        self._initialize_default_profit_taking_rules()
        
        # Load existing data
        self._load_data()
    
    def _initialize_default_profit_taking_rules(self):
        """Initialize default profit taking rules."""
        default_rules = [
            # Quick profit taking for scalping (15 minutes)
            ProfitTakingRule(
                name="Scalping Quick Profit",
                enabled=True,
                time_interval_minutes=15,
                min_profit_pips=10.0,
                profit_percentage=0.5,  # Take 50% of profit
                max_trades_per_interval=3,
                session_filter=None,
                symbol_filter=None
            ),
            # Medium-term profit taking (1 hour)
            ProfitTakingRule(
                name="Medium Term Profit",
                enabled=True,
                time_interval_minutes=60,
                min_profit_pips=20.0,
                profit_percentage=0.7,  # Take 70% of profit
                max_trades_per_interval=5,
                session_filter=None,
                symbol_filter=None
            ),
            # Session end profit taking (4 hours)
            ProfitTakingRule(
                name="Session End Profit",
                enabled=True,
                time_interval_minutes=240,
                min_profit_pips=30.0,
                profit_percentage=0.8,  # Take 80% of profit
                max_trades_per_interval=10,
                session_filter=None,
                symbol_filter=None
            ),
            # Asian session specific (lower volatility)
            ProfitTakingRule(
                name="Asian Session Profit",
                enabled=True,
                time_interval_minutes=120,
                min_profit_pips=15.0,
                profit_percentage=0.6,
                max_trades_per_interval=3,
                session_filter=SessionType.ASIAN,
                symbol_filter=None
            ),
            # London session specific (higher volatility)
            ProfitTakingRule(
                name="London Session Profit",
                enabled=True,
                time_interval_minutes=90,
                min_profit_pips=25.0,
                profit_percentage=0.7,
                max_trades_per_interval=5,
                session_filter=SessionType.LONDON,
                symbol_filter=None
            )
        ]
        
        self.profit_taking_rules = default_rules
        logger.info(f"Initialized {len(default_rules)} default profit taking rules")
    
    def set_broker(self, broker):
        """Set broker reference for order operations."""
        self.broker = broker
        logger.info("Broker reference set for profit monitor")
    
    def add_profit_taking_rule(self, rule: ProfitTakingRule):
        """Add a new profit taking rule."""
        self.profit_taking_rules.append(rule)
        logger.info(f"Added profit taking rule: {rule.name}")
    
    def remove_profit_taking_rule(self, rule_name: str):
        """Remove a profit taking rule by name."""
        self.profit_taking_rules = [r for r in self.profit_taking_rules if r.name != rule_name]
        logger.info(f"Removed profit taking rule: {rule_name}")
    
    def enable_profit_taking_rule(self, rule_name: str):
        """Enable a profit taking rule."""
        for rule in self.profit_taking_rules:
            if rule.name == rule_name:
                rule.enabled = True
                logger.info(f"Enabled profit taking rule: {rule_name}")
                break
    
    def disable_profit_taking_rule(self, rule_name: str):
        """Disable a profit taking rule."""
        for rule in self.profit_taking_rules:
            if rule.name == rule_name:
                rule.enabled = False
                logger.info(f"Disabled profit taking rule: {rule_name}")
                break
    
    def add_active_position(self, position: ActivePosition):
        """Add an active position for profit taking monitoring."""
        self.active_positions[position.ticket] = position
        logger.debug(f"Added active position: {position.symbol} (Ticket: {position.ticket})")
    
    def remove_active_position(self, ticket: int):
        """Remove an active position."""
        if ticket in self.active_positions:
            del self.active_positions[ticket]
            logger.debug(f"Removed active position: {ticket}")
    
    def update_position_profit(self, ticket: int, current_price: float, profit_pips: float):
        """Update position profit for profit taking calculations."""
        if ticket in self.active_positions:
            position = self.active_positions[ticket]
            
            # Calculate current profit
            if position.order_type == "BUY":
                position.current_profit = (current_price - position.open_price) * position.volume
            else:
                position.current_profit = (position.open_price - current_price) * position.volume
            
            position.current_profit_pips = profit_pips
            logger.debug(f"Updated position {ticket} profit: ${position.current_profit:.2f} ({profit_pips:.1f} pips)")
    
    def check_profit_taking(self, current_time: datetime = None) -> List[int]:
        """Check and execute profit taking rules. Returns list of closed ticket numbers."""
        if not self.broker or not self.active_positions:
            return []
        
        if current_time is None:
            current_time = datetime.now()
        
        closed_tickets = []
        
        for rule in self.profit_taking_rules:
            if not rule.enabled:
                continue
            
            # Check if it's time to execute this rule
            if rule.last_execution:
                time_since_last = current_time - rule.last_execution
                if time_since_last.total_seconds() < rule.time_interval_minutes * 60:
                    continue
            
            # Get positions that match this rule
            matching_positions = self._get_matching_positions(rule)
            
            if not matching_positions:
                continue
            
            # Sort by profit (highest first)
            matching_positions.sort(key=lambda p: p.current_profit_pips, reverse=True)
            
            # Execute profit taking
            closed_count = 0
            for position in matching_positions:
                if closed_count >= rule.max_trades_per_interval:
                    break
                
                if position.current_profit_pips >= rule.min_profit_pips:
                    if self._execute_profit_taking(position, rule):
                        closed_tickets.append(position.ticket)
                        closed_count += 1
            
            # Update rule execution time
            if closed_count > 0:
                rule.last_execution = current_time
                logger.info(f"Executed profit taking rule '{rule.name}': closed {closed_count} positions")
        
        return closed_tickets
    
    def _get_matching_positions(self, rule: ProfitTakingRule) -> List[ActivePosition]:
        """Get positions that match a profit taking rule."""
        matching_positions = []
        
        for position in self.active_positions.values():
            # Check session filter
            if rule.session_filter and position.session != rule.session_filter:
                continue
            
            # Check symbol filter
            if rule.symbol_filter and position.symbol != rule.symbol_filter:
                continue
            
            # Check if position is profitable
            if position.current_profit_pips > 0:
                matching_positions.append(position)
        
        return matching_positions
    
    def _execute_profit_taking(self, position: ActivePosition, rule: ProfitTakingRule) -> bool:
        """Execute profit taking for a position."""
        try:
            # Calculate partial close volume
            close_volume = position.volume * rule.profit_percentage
            
            # Get current price
            current_price = self.broker.get_mid_price(position.symbol)
            if not current_price:
                logger.warning(f"Cannot get current price for {position.symbol}")
                return False
            
            # Close partial position
            if self.broker.close_order_partial(position.ticket, close_volume):
                # Update position volume
                position.volume -= close_volume
                
                # Calculate realized profit
                if position.order_type == "BUY":
                    realized_profit = (current_price - position.open_price) * close_volume
                else:
                    realized_profit = (position.open_price - current_price) * close_volume
                
                logger.info(f"Profit taking executed: {position.symbol} (Ticket: {position.ticket}) "
                           f"Closed {close_volume:.2f} lots, Profit: ${realized_profit:.2f}")
                
                # If position is fully closed, remove from active positions
                if position.volume <= 0.01:  # Minimum lot size
                    self.remove_active_position(position.ticket)
                
                return True
            else:
                logger.error(f"Failed to execute profit taking for position {position.ticket}")
                return False
                
        except Exception as e:
            logger.error(f"Error executing profit taking: {e}")
            return False
    
    def get_profit_taking_status(self) -> Dict[str, Any]:
        """Get status of profit taking rules and active positions."""
        return {
            'rules': [
                {
                    'name': rule.name,
                    'enabled': rule.enabled,
                    'time_interval_minutes': rule.time_interval_minutes,
                    'min_profit_pips': rule.min_profit_pips,
                    'profit_percentage': rule.profit_percentage,
                    'last_execution': rule.last_execution.isoformat() if rule.last_execution else None
                }
                for rule in self.profit_taking_rules
            ],
            'active_positions': len(self.active_positions),
            'total_profit_potential': sum(p.current_profit for p in self.active_positions.values()),
            'positions_by_profit': [
                {
                    'ticket': p.ticket,
                    'symbol': p.symbol,
                    'profit_pips': p.current_profit_pips,
                    'profit_usd': p.current_profit,
                    'session': p.session.value
                }
                for p in sorted(self.active_positions.values(), 
                              key=lambda x: x.current_profit_pips, reverse=True)
            ]
        }
    
    def _load_data(self):
        """Load existing trade data from files."""
        trades_file = self.data_dir / "trades.json"
        if trades_file.exists():
            try:
                with open(trades_file, 'r') as f:
                    trades_data = json.load(f)
                
                for trade_data in trades_data:
                    trade = TradeRecord(
                        ticket=trade_data['ticket'],
                        symbol=trade_data['symbol'],
                        order_type=trade_data['order_type'],
                        volume=trade_data['volume'],
                        open_price=trade_data['open_price'],
                        close_price=trade_data.get('close_price'),
                        open_time=datetime.fromisoformat(trade_data['open_time']),
                        close_time=datetime.fromisoformat(trade_data['close_time']) if trade_data.get('close_time') else None,
                        profit=trade_data['profit'],
                        swap=trade_data['swap'],
                        commission=trade_data['commission'],
                        session=SessionType(trade_data['session']),
                        strategy=trade_data['strategy'],
                        stop_loss=trade_data.get('stop_loss'),
                        take_profit=trade_data.get('take_profit'),
                        exit_reason=trade_data.get('exit_reason')
                    )
                    self.trades.append(trade)
                
                logger.info(f"Loaded {len(self.trades)} historical trades")
                self._recalculate_metrics()
                
            except Exception as e:
                logger.error(f"Error loading trade data: {e}")
    
    def _save_data(self):
        """Save trade data to files."""
        try:
            trades_file = self.data_dir / "trades.json"
            trades_data = []
            
            for trade in self.trades:
                trade_dict = asdict(trade)
                trade_dict['open_time'] = trade.open_time.isoformat()
                if trade.close_time:
                    trade_dict['close_time'] = trade.close_time.isoformat()
                trade_dict['session'] = trade.session.value
                trades_data.append(trade_dict)
            
            with open(trades_file, 'w') as f:
                json.dump(trades_data, f, indent=2)
            
        except Exception as e:
            logger.error(f"Error saving trade data: {e}")
    
    def add_trade(self, trade: TradeRecord):
        """Add a new trade record."""
        self.trades.append(trade)
        self._update_metrics(trade)
        self._save_data()
        
        logger.info(f"Added trade: {trade.symbol} {trade.order_type} "
                   f"Profit: {trade.profit:.2f}")
    
    def close_trade(self, ticket: int, close_price: float, 
                   close_time: datetime, exit_reason: str = "manual"):
        """Close an existing trade."""
        for trade in self.trades:
            if trade.ticket == ticket and trade.close_price is None:
                trade.close_price = close_price
                trade.close_time = close_time
                trade.exit_reason = exit_reason
                
                # Recalculate profit if needed
                if trade.order_type == "BUY":
                    trade.profit = (close_price - trade.open_price) * trade.volume
                else:
                    trade.profit = (trade.open_price - close_price) * trade.volume
                
                self._update_metrics(trade)
                self._save_data()
                
                logger.info(f"Closed trade {ticket}: {trade.symbol} "
                           f"Profit: {trade.profit:.2f}")
                break
    
    def _update_metrics(self, trade: TradeRecord):
        """Update performance metrics with new trade."""
        # Update daily P&L
        date_str = trade.open_time.strftime("%Y-%m-%d")
        self.daily_pnl[date_str] = self.daily_pnl.get(date_str, 0.0) + trade.profit
        
        # Update session P&L
        session_str = trade.session.value
        if session_str not in self.session_pnl:
            self.session_pnl[session_str] = {}
        self.session_pnl[session_str][date_str] = \
            self.session_pnl[session_str].get(date_str, 0.0) + trade.profit
        
        # Update pair P&L
        self.pair_pnl[trade.symbol] = self.pair_pnl.get(trade.symbol, 0.0) + trade.profit
        
        # Update strategy P&L
        self.strategy_pnl[trade.strategy] = self.strategy_pnl.get(trade.strategy, 0.0) + trade.profit
        
        # Update balance and drawdown
        self.current_balance += trade.profit
        if self.current_balance > self.peak_balance:
            self.peak_balance = self.current_balance
        
        # Calculate drawdown
        if self.peak_balance > 0:
            drawdown = (self.peak_balance - self.current_balance) / self.peak_balance
            if drawdown > self.max_drawdown_pct:
                self.max_drawdown_pct = drawdown
                self.max_drawdown = self.peak_balance - self.current_balance
        
        # Update consecutive losses
        if trade.profit < 0:
            self.consecutive_losses += 1
            if self.consecutive_losses > self.max_consecutive_losses:
                self.max_consecutive_losses = self.consecutive_losses
        else:
            self.consecutive_losses = 0
    
    def _recalculate_metrics(self):
        """Recalculate all metrics from trade history."""
        self.daily_pnl.clear()
        self.session_pnl.clear()
        self.pair_pnl.clear()
        self.strategy_pnl.clear()
        
        self.current_balance = 0.0
        self.peak_balance = 0.0
        self.max_drawdown = 0.0
        self.max_drawdown_pct = 0.0
        self.consecutive_losses = 0
        self.max_consecutive_losses = 0
        
        for trade in self.trades:
            self._update_metrics(trade)
    
    def get_performance_metrics(self, start_date: Optional[datetime] = None,
                               end_date: Optional[datetime] = None) -> PerformanceMetrics:
        """Calculate comprehensive performance metrics."""
        # Filter trades by date range
        filtered_trades = self.trades
        if start_date:
            filtered_trades = [t for t in filtered_trades if t.open_time >= start_date]
        if end_date:
            filtered_trades = [t for t in filtered_trades if t.open_time <= end_date]
        
        if not filtered_trades:
            return PerformanceMetrics(
                total_trades=0, winning_trades=0, losing_trades=0,
                win_rate=0.0, total_profit=0.0, total_loss=0.0,
                net_profit=0.0, profit_factor=0.0, average_win=0.0,
                average_loss=0.0, largest_win=0.0, largest_loss=0.0,
                max_drawdown=self.max_drawdown, sharpe_ratio=0.0,
                sortino_ratio=0.0, calmar_ratio=0.0, total_volume=0.0,
                average_trade_duration=timedelta(0)
            )
        
        # Basic metrics
        total_trades = len(filtered_trades)
        winning_trades = len([t for t in filtered_trades if t.profit > 0])
        losing_trades = len([t for t in filtered_trades if t.profit < 0])
        win_rate = winning_trades / total_trades if total_trades > 0 else 0.0
        
        # Profit metrics
        total_profit = sum(t.profit for t in filtered_trades if t.profit > 0)
        total_loss = abs(sum(t.profit for t in filtered_trades if t.profit < 0))
        net_profit = sum(t.profit for t in filtered_trades)
        profit_factor = total_profit / total_loss if total_loss > 0 else float('inf')
        
        # Average metrics
        wins = [t.profit for t in filtered_trades if t.profit > 0]
        losses = [t.profit for t in filtered_trades if t.profit < 0]
        average_win = np.mean(wins) if wins else 0.0
        average_loss = np.mean(losses) if losses else 0.0
        largest_win = max(wins) if wins else 0.0
        largest_loss = min(losses) if losses else 0.0
        
        # Volume and duration
        total_volume = sum(t.volume for t in filtered_trades)
        durations = []
        for trade in filtered_trades:
            if trade.close_time:
                duration = trade.close_time - trade.open_time
                durations.append(duration)
        average_duration = np.mean(durations) if durations else timedelta(0)
        
        # Risk-adjusted metrics
        returns = [t.profit for t in filtered_trades]
        sharpe_ratio = self._calculate_sharpe_ratio(returns)
        sortino_ratio = self._calculate_sortino_ratio(returns)
        calmar_ratio = net_profit / self.max_drawdown if self.max_drawdown > 0 else 0.0
        
        return PerformanceMetrics(
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            win_rate=win_rate,
            total_profit=total_profit,
            total_loss=total_loss,
            net_profit=net_profit,
            profit_factor=profit_factor,
            average_win=average_win,
            average_loss=average_loss,
            largest_win=largest_win,
            largest_loss=largest_loss,
            max_drawdown=self.max_drawdown,
            sharpe_ratio=sharpe_ratio,
            sortino_ratio=sortino_ratio,
            calmar_ratio=calmar_ratio,
            total_volume=total_volume,
            average_trade_duration=average_duration
        )
    
    def _calculate_sharpe_ratio(self, returns: List[float], risk_free_rate: float = 0.02) -> float:
        """Calculate Sharpe ratio."""
        if not returns:
            return 0.0
        
        returns_array = np.array(returns)
        excess_returns = returns_array - (risk_free_rate / 252)  # Daily risk-free rate
        
        if len(excess_returns) < 2:
            return 0.0
        
        return np.mean(excess_returns) / np.std(excess_returns) if np.std(excess_returns) > 0 else 0.0
    
    def _calculate_sortino_ratio(self, returns: List[float], risk_free_rate: float = 0.02) -> float:
        """Calculate Sortino ratio."""
        if not returns:
            return 0.0
        
        returns_array = np.array(returns)
        excess_returns = returns_array - (risk_free_rate / 252)
        negative_returns = excess_returns[excess_returns < 0]
        
        if len(negative_returns) < 2:
            return 0.0
        
        downside_deviation = np.std(negative_returns)
        return np.mean(excess_returns) / downside_deviation if downside_deviation > 0 else 0.0
    
    def get_session_performance(self) -> List[SessionPerformance]:
        """Get performance metrics by session."""
        session_performance = []
        
        for session in SessionType:
            session_trades = [t for t in self.trades if t.session == session]
            
            if not session_trades:
                continue
            
            total_trades = len(session_trades)
            winning_trades = len([t for t in session_trades if t.profit > 0])
            win_rate = winning_trades / total_trades
            total_profit = sum(t.profit for t in session_trades)
            average_profit = total_profit / total_trades
            
            # Calculate profit factor
            session_wins = sum(t.profit for t in session_trades if t.profit > 0)
            session_losses = abs(sum(t.profit for t in session_trades if t.profit < 0))
            profit_factor = session_wins / session_losses if session_losses > 0 else float('inf')
            
            # Find best and worst pairs
            pair_profits = {}
            for trade in session_trades:
                pair_profits[trade.symbol] = pair_profits.get(trade.symbol, 0.0) + trade.profit
            
            if pair_profits:
                best_pair = max(pair_profits, key=pair_profits.get)
                worst_pair = min(pair_profits, key=pair_profits.get)
            else:
                best_pair = "N/A"
                worst_pair = "N/A"
            
            session_performance.append(SessionPerformance(
                session=session,
                total_trades=total_trades,
                winning_trades=winning_trades,
                win_rate=win_rate,
                total_profit=total_profit,
                average_profit=average_profit,
                profit_factor=profit_factor,
                best_pair=best_pair,
                worst_pair=worst_pair
            ))
        
        return session_performance
    
    def get_pair_performance(self) -> Dict[str, Dict[str, Any]]:
        """Get performance metrics by currency pair."""
        pair_performance = {}
        
        for trade in self.trades:
            symbol = trade.symbol
            if symbol not in pair_performance:
                pair_performance[symbol] = {
                    'total_trades': 0,
                    'winning_trades': 0,
                    'total_profit': 0.0,
                    'total_volume': 0.0,
                    'average_profit': 0.0,
                    'win_rate': 0.0,
                    'profit_factor': 0.0,
                    'best_session': None,
                    'worst_session': None
                }
            
            pair_performance[symbol]['total_trades'] += 1
            pair_performance[symbol]['total_profit'] += trade.profit
            pair_performance[symbol]['total_volume'] += trade.volume
            
            if trade.profit > 0:
                pair_performance[symbol]['winning_trades'] += 1
        
        # Calculate derived metrics
        for symbol, metrics in pair_performance.items():
            if metrics['total_trades'] > 0:
                metrics['win_rate'] = metrics['winning_trades'] / metrics['total_trades']
                metrics['average_profit'] = metrics['total_profit'] / metrics['total_trades']
                
                # Calculate profit factor
                symbol_trades = [t for t in self.trades if t.symbol == symbol]
                wins = sum(t.profit for t in symbol_trades if t.profit > 0)
                losses = abs(sum(t.profit for t in symbol_trades if t.profit < 0))
                metrics['profit_factor'] = wins / losses if losses > 0 else float('inf')
                
                # Find best and worst sessions
                session_profits = {}
                for trade in symbol_trades:
                    session = trade.session.value
                    session_profits[session] = session_profits.get(session, 0.0) + trade.profit
                
                if session_profits:
                    metrics['best_session'] = max(session_profits, key=session_profits.get)
                    metrics['worst_session'] = min(session_profits, key=session_profits.get)
        
        return pair_performance
    
    def get_daily_pnl(self, days: int = 30) -> Dict[str, float]:
        """Get daily P&L for the last N days."""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        daily_pnl = {}
        current_date = start_date
        
        while current_date <= end_date:
            date_str = current_date.strftime("%Y-%m-%d")
            daily_pnl[date_str] = self.daily_pnl.get(date_str, 0.0)
            current_date += timedelta(days=1)
        
        return daily_pnl
    
    def get_risk_metrics(self) -> Dict[str, Any]:
        """Get comprehensive risk metrics."""
        if not self.trades:
            return {}
        
        # Calculate Value at Risk
        returns = [t.profit for t in self.trades]
        returns_array = np.array(returns)
        
        daily_var_95 = np.percentile(returns_array, 5) if len(returns_array) > 0 else 0.0
        
        # Calculate weekly VaR (assuming 5 trades per week)
        weekly_returns = []
        for i in range(0, len(returns), 5):
            weekly_returns.append(sum(returns[i:i+5]))
        weekly_var_95 = np.percentile(weekly_returns, 5) if weekly_returns else 0.0
        
        # Maximum daily loss
        max_daily_loss = min(self.daily_pnl.values()) if self.daily_pnl else 0.0
        
        return {
            'daily_var_95': daily_var_95,
            'weekly_var_95': weekly_var_95,
            'max_daily_loss': max_daily_loss,
            'max_drawdown': self.max_drawdown,
            'max_drawdown_pct': self.max_drawdown_pct,
            'max_consecutive_losses': self.max_consecutive_losses,
            'current_consecutive_losses': self.consecutive_losses,
            'total_trades': len(self.trades),
            'current_balance': self.current_balance,
            'peak_balance': self.peak_balance
        }
    
    def generate_report(self, report_type: str = "comprehensive") -> Dict[str, Any]:
        """Generate a comprehensive trading report."""
        report = {
            'generated_at': datetime.now().isoformat(),
            'report_type': report_type,
            'summary': {},
            'performance': {},
            'risk_metrics': {},
            'session_analysis': {},
            'pair_analysis': {},
            'recommendations': []
        }
        
        # Overall performance
        metrics = self.get_performance_metrics()
        report['performance'] = asdict(metrics)
        
        # Risk metrics
        report['risk_metrics'] = self.get_risk_metrics()
        
        # Session analysis
        session_perf = self.get_session_performance()
        report['session_analysis'] = [asdict(sp) for sp in session_perf]
        
        # Pair analysis
        pair_perf = self.get_pair_performance()
        report['pair_analysis'] = pair_perf
        
        # Summary
        report['summary'] = {
            'total_trades': metrics.total_trades,
            'net_profit': metrics.net_profit,
            'win_rate': metrics.win_rate,
            'profit_factor': metrics.profit_factor,
            'max_drawdown': self.max_drawdown,
            'sharpe_ratio': metrics.sharpe_ratio
        }
        
        # Generate recommendations
        recommendations = []
        
        if metrics.win_rate < 0.4:
            recommendations.append("Consider reviewing strategy parameters - low win rate detected")
        
        if metrics.profit_factor < 1.2:
            recommendations.append("Profit factor below optimal level - review risk management")
        
        if self.max_drawdown_pct > 0.2:
            recommendations.append("High drawdown detected - consider reducing position sizes")
        
        # Find best performing session
        if session_perf:
            best_session = max(session_perf, key=lambda x: x.total_profit)
            recommendations.append(f"Best performing session: {best_session.session.value}")
        
        # Find best performing pair
        if pair_perf:
            best_pair = max(pair_perf.items(), key=lambda x: x[1]['total_profit'])
            recommendations.append(f"Best performing pair: {best_pair[0]}")
        
        report['recommendations'] = recommendations
        
        return report
    
    def save_report(self, report: Dict[str, Any], filename: Optional[str] = None):
        """Save report to file."""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"trading_report_{timestamp}.json"
        
        report_file = self.data_dir / filename
        
        try:
            with open(report_file, 'w') as f:
                json.dump(report, f, indent=2)
            
            logger.info(f"Trading report saved to {report_file}")
            
        except Exception as e:
            logger.error(f"Error saving report: {e}")
    
    def get_realtime_status(self) -> Dict[str, Any]:
        """Get real-time trading status."""
        if not self.trades:
            return {
                'status': 'No trades yet',
                'current_balance': 0.0,
                'total_trades': 0,
                'today_pnl': 0.0
            }
        
        # Today's P&L
        today = datetime.now().strftime("%Y-%m-%d")
        today_pnl = self.daily_pnl.get(today, 0.0)
        
        # Recent trades
        recent_trades = sorted(self.trades, key=lambda x: x.open_time, reverse=True)[:5]
        
        return {
            'status': 'Active',
            'current_balance': self.current_balance,
            'peak_balance': self.peak_balance,
            'total_trades': len(self.trades),
            'today_pnl': today_pnl,
            'max_drawdown': self.max_drawdown,
            'max_drawdown_pct': self.max_drawdown_pct,
            'consecutive_losses': self.consecutive_losses,
            'recent_trades': [
                {
                    'symbol': t.symbol,
                    'type': t.order_type,
                    'profit': t.profit,
                    'time': t.open_time.strftime("%H:%M:%S")
                }
                for t in recent_trades
            ]
        } 