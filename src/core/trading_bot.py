"""
Main trading bot class that orchestrates all components.
"""
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import time
from threading import Thread, Event
from loguru import logger
import schedule
import pandas as pd

from src.core.config import TradingBotConfig, SessionType
from src.brokers.mt5_broker import MT5Broker
from src.core.session_manager import SessionManager
from src.core.currency_manager import CurrencyManager
from src.core.profit_monitor import ProfitMonitor, TradeRecord
from src.risk_management.risk_manager import RiskManager
from src.strategies.session_breakout_strategy import SessionBreakoutStrategy
from src.strategies.ml_strategy import MLStrategy


class TradingBot:
    """Main trading bot class."""
    
    def __init__(self, config: TradingBotConfig):
        self.config = config
        self.running = False
        self.stop_event = Event()
        
        # Initialize components
        self.broker = MT5Broker(config.broker.dict())
        self.session_manager = SessionManager()
        self.risk_manager = RiskManager(config.risk, self.broker)
        
        # Initialize currency manager and profit monitor
        self.currency_manager = CurrencyManager()
        self.profit_monitor = ProfitMonitor()
        
        # Set broker reference for profit monitor
        self.profit_monitor.set_broker(self.broker)
        
        # --- Add 5-minute profit taking rule for each trading pair ---
        self.profit_monitor.profit_taking_rules = []  # Remove default rules
        for symbol in self.config.symbols:
            rule = ProfitMonitor.__annotations__['profit_taking_rules'][0](
                name=f"{symbol} 5min TP",
                enabled=True,
                time_interval_minutes=5,
                min_profit_pips=5.0,  # You can adjust this threshold
                profit_percentage=1.0, # 100% of position (full close)
                max_trades_per_interval=1,
                session_filter=None,
                symbol_filter=symbol
            )
            self.profit_monitor.add_profit_taking_rule(rule)
        # ------------------------------------------------------------
        
        # Initialize strategies
        self.strategies: Dict[str, Any] = {}
        self._initialize_strategies()
        
        # Initialize sessions
        self._initialize_sessions()
        
        # Trading state
        self.last_analysis_time = {}
        self.analysis_interval = 60  # seconds
        
        # Multi-currency state
        self.active_positions: Dict[str, List[str]] = {}  # symbol -> list of ticket numbers
        self.correlation_data: Dict[str, pd.DataFrame] = {}
        
    def _initialize_strategies(self) -> None:
        """Initialize trading strategies."""
        for strategy_config in self.config.strategies:
            if strategy_config.name == "session_breakout":
                strategy = SessionBreakoutStrategy(
                    strategy_config, self.broker, self.risk_manager, self.session_manager
                )
                self.strategies[strategy_config.name] = strategy
                logger.info(f"Initialized strategy: {strategy_config.name}")
            elif strategy_config.name == "ml_strategy":
                strategy = MLStrategy(
                    strategy_config, self.broker, self.risk_manager, self.session_manager
                )
                self.strategies[strategy_config.name] = strategy
                logger.info(f"Initialized strategy: {strategy_config.name}")
    
    def _initialize_sessions(self) -> None:
        """Initialize market sessions."""
        for session_config in self.config.sessions:
            self.session_manager.add_session(session_config)
            
            # Add session callbacks
            self.session_manager.add_session_callback(
                session_config.session_type, self._on_session_event
            )
        
        logger.info(f"Initialized {len(self.config.sessions)} market sessions")
    
    def _on_session_event(self, session_type: SessionType, event_type: str) -> None:
        """Handle session events."""
        logger.info(f"Session event: {session_type} - {event_type}")
        
        if event_type == "start":
            # Start analysis for this session
            self._start_session_analysis(session_type)
        elif event_type == "end":
            # Stop analysis for this session
            self._stop_session_analysis(session_type)
    
    def _start_session_analysis(self, session_type: SessionType) -> None:
        """Start analysis for a specific session."""
        logger.info(f"Starting analysis for {session_type} session")
        
        # Schedule periodic analysis
        schedule.every(30).seconds.do(
            self._analyze_symbols_for_session, session_type
        ).tag(f"analysis_{session_type}")
    
    def _stop_session_analysis(self, session_type: SessionType) -> None:
        """Stop analysis for a specific session."""
        logger.info(f"Stopping analysis for {session_type} session")
        
        # Clear scheduled analysis
        schedule.clear(f"analysis_{session_type}")
    
    def _analyze_symbols_for_session(self, session_type: SessionType) -> None:
        """Analyze symbols for a specific session."""
        if not self.running:
            return
        
        try:
            # Get optimal pairs for this session
            optimal_pairs = self.currency_manager.get_optimal_pairs(session_type, max_pairs=5)
            
            # Update correlation data if needed
            self._update_correlation_data()
            
            for symbol in optimal_pairs:
                # Check if enough time has passed since last analysis
                current_time = datetime.now()
                last_time = self.last_analysis_time.get(symbol, datetime.min)
                
                if (current_time - last_time).total_seconds() < self.analysis_interval:
                    continue
                
                self.last_analysis_time[symbol] = current_time
                
                # Check correlation limits
                current_positions = list(self.active_positions.keys())
                can_open, reason = self.currency_manager.can_open_position(symbol, current_positions)
                
                if not can_open:
                    logger.debug(f"Cannot open position for {symbol}: {reason}")
                    continue
                
                # Analyze with each strategy
                for strategy_name, strategy in self.strategies.items():
                    if not strategy.enabled:
                        continue
                    
                    # Check if strategy should trade in this session
                    if not strategy.should_trade(symbol, session_type):
                        continue
                    
                    # Analyze symbol
                    signals = strategy.analyze_symbol(symbol)
                    
                    # Execute signals
                    if signals.get('signal') in ['BUY', 'SELL']:
                        self._execute_strategy_signal(strategy, symbol, signals, session_type)
                        
        except Exception as e:
            logger.error(f"Error in session analysis: {e}")
    
    def _execute_strategy_signal(self, strategy, symbol: str, signals: Dict[str, Any], session_type: SessionType) -> None:
        """Execute a strategy signal."""
        try:
            # Execute the signal
            result = strategy.execute_signal(symbol, signals)
            
            if result.get('success'):
                logger.info(f"Executed {signals['signal']} signal for {symbol}: {result}")
                
                # Record trade in profit monitor
                self._record_trade(symbol, signals, result, session_type, strategy.__class__.__name__)
                
                # Update active positions
                ticket = result.get('ticket')
                if ticket:
                    if symbol not in self.active_positions:
                        self.active_positions[symbol] = []
                    self.active_positions[symbol].append(str(ticket))
                
            else:
                logger.warning(f"Failed to execute signal for {symbol}: {result.get('reason', 'Unknown error')}")
                
        except Exception as e:
            logger.error(f"Error executing signal for {symbol}: {e}")
    
    def _record_trade(self, symbol: str, signals: Dict[str, Any], result: Dict[str, Any], 
                     session_type: SessionType, strategy_name: str) -> None:
        """Record a trade in the profit monitor."""
        try:
            # Get current price for the trade
            current_price = self.broker.get_current_price(symbol)
            if not current_price:
                return
            
            ticket = result.get('ticket', 0)
            
            # Create trade record
            trade = TradeRecord(
                ticket=ticket,
                symbol=symbol,
                order_type=signals.get('signal', 'UNKNOWN'),
                volume=result.get('volume', 0.0),
                open_price=current_price,
                close_price=None,
                open_time=datetime.now(),
                close_time=None,
                profit=0.0,  # Will be calculated when closed
                swap=0.0,
                commission=result.get('commission', 0.0),
                session=session_type,
                strategy=strategy_name,
                stop_loss=signals.get('stop_loss'),
                take_profit=signals.get('take_profit'),
                exit_reason=None
            )
            
            # Add to profit monitor
            self.profit_monitor.add_trade(trade)
            
            # Add to active positions for profit taking
            if ticket:
                from src.core.profit_monitor import ActivePosition
                active_position = ActivePosition(
                    ticket=ticket,
                    symbol=symbol,
                    order_type=signals.get('signal', 'UNKNOWN'),
                    volume=result.get('volume', 0.0),
                    open_price=current_price,
                    open_time=datetime.now(),
                    current_profit=0.0,
                    current_profit_pips=0.0,
                    session=session_type,
                    strategy=strategy_name
                )
                self.profit_monitor.add_active_position(active_position)
            
        except Exception as e:
            logger.error(f"Error recording trade: {e}")
    
    def _check_profit_taking(self) -> None:
        """Check and execute profit taking rules."""
        try:
            # Update position profits
            self._update_position_profits()
            
            # Check profit taking rules
            closed_tickets = self.profit_monitor.check_profit_taking()
            
            if closed_tickets:
                logger.info(f"Profit taking executed: {len(closed_tickets)} positions closed")
                
                # Update active positions tracking
                for ticket in closed_tickets:
                    self.profit_monitor.remove_active_position(ticket)
                    
                    # Remove from active positions by symbol
                    for symbol, tickets in self.active_positions.items():
                        if str(ticket) in tickets:
                            tickets.remove(str(ticket))
                            if not tickets:
                                del self.active_positions[symbol]
                            break
                            
        except Exception as e:
            logger.error(f"Error in profit taking check: {e}")
    
    def _update_position_profits(self) -> None:
        """Update profit calculations for active positions."""
        try:
            for position in self.profit_monitor.active_positions.values():
                # Get current price
                current_price = self.broker.get_mid_price(position.symbol)
                if not current_price:
                    continue
                
                # Calculate profit in pips
                symbol_info = self.broker.get_symbol_info(position.symbol)
                if not symbol_info:
                    continue
                
                pip_value = symbol_info.get('point', 0.0001) * 10
                
                if position.order_type == "BUY":
                    profit_pips = (current_price - position.open_price) / pip_value
                else:
                    profit_pips = (position.open_price - current_price) / pip_value
                
                # Update position profit
                self.profit_monitor.update_position_profit(
                    position.ticket, current_price, profit_pips
                )
                
        except Exception as e:
            logger.error(f"Error updating position profits: {e}")
    
    def _update_correlation_data(self) -> None:
        """Update correlation data for currency pairs."""
        try:
            # Get historical data for all pairs
            all_pairs = self.currency_manager.get_all_pairs()
            price_data = {}
            
            for symbol in all_pairs:
                # Get last 100 candles for correlation calculation
                data = self.broker.get_historical_data(symbol, 'H1', 100)
                if data is not None and not data.empty:
                    price_data[symbol] = data
            
            # Update correlation matrix
            if price_data:
                self.currency_manager.update_correlation_matrix(price_data)
                
        except Exception as e:
            logger.error(f"Error updating correlation data: {e}")
    
    def start(self) -> bool:
        """Start the trading bot."""
        try:
            # Connect to broker
            if not self.broker.connect():
                logger.error("Failed to connect to broker")
                return False
            
            # Start session manager
            self.session_manager.start()
            
            # Start the main trading loop
            self.running = True
            self.stop_event.clear()
            
            # Start main thread
            self.main_thread = Thread(target=self._main_loop, daemon=True)
            self.main_thread.start()
            
            logger.info("Trading bot started successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start trading bot: {e}")
            return False
    
    def stop(self) -> None:
        """Stop the trading bot."""
        if not self.running:
            return
        
        logger.info("Stopping trading bot...")
        
        self.running = False
        self.stop_event.set()
        
        # Stop session manager
        self.session_manager.stop()
        
        # Disconnect from broker
        self.broker.disconnect()
        
        logger.info("Trading bot stopped")
    
    def _main_loop(self) -> None:
        """Main trading loop."""
        last_profit_check = datetime.now()
        profit_check_interval = 60  # Check profit taking every 60 seconds
        
        while self.running and not self.stop_event.is_set():
            try:
                # Run scheduled tasks
                schedule.run_pending()
                
                # Update risk management
                self._update_risk_management()
                
                # Check profit taking at regular intervals
                current_time = datetime.now()
                if (current_time - last_profit_check).total_seconds() >= profit_check_interval:
                    self._check_profit_taking()
                    last_profit_check = current_time
                
                # Sleep for a short interval
                time.sleep(1)
                
            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                time.sleep(5)
    
    def _update_risk_management(self) -> None:
        """Update risk management components."""
        try:
            # Update position prices
            self.risk_manager.update_positions()
            
            # Check stop losses and take profits
            sl_tickets = self.risk_manager.check_stop_losses()
            tp_tickets = self.risk_manager.check_take_profits()
            
            # Close positions that hit stop loss or take profit
            for ticket in sl_tickets + tp_tickets:
                if self.broker.close_order(ticket):
                    self.risk_manager.remove_position(ticket)
            
            # Apply trailing stops
            trailing_tickets = self.risk_manager.apply_trailing_stop()
            for ticket in trailing_tickets:
                position = self.risk_manager.positions.get(ticket)
                if position:
                    self.broker.modify_order(ticket, sl=position.sl)
            
            # Check if all positions should be closed
            if self.risk_manager.should_close_all_positions():
                self._close_all_positions()
                
        except Exception as e:
            logger.error(f"Error updating risk management: {e}")
    
    def _close_all_positions(self) -> None:
        """Close all open positions."""
        logger.warning("Closing all positions due to risk limits")
        
        positions = self.risk_manager.get_position_summary()
        for position in positions:
            if self.broker.close_order(position['ticket']):
                self.risk_manager.remove_position(position['ticket'])
    
    def get_status(self) -> Dict[str, Any]:
        """Get current bot status."""
        account_info = self.broker.get_account_info()
        
        return {
            'running': self.running,
            'connected': self.broker.is_connected(),
            'account_info': account_info,
            'active_sessions': self.session_manager.get_active_sessions(),
            'risk_metrics': self.risk_manager.get_risk_metrics(),
            'profit_status': self.profit_monitor.get_realtime_status(),
            'profit_taking_status': self.profit_monitor.get_profit_taking_status(),
            'currency_pairs': {
                'total_pairs': len(self.currency_manager.get_all_pairs()),
                'active_pairs': len(self.active_positions),
                'correlation_summary': self.currency_manager.get_correlation_summary()
            },
            'strategies': {
                name: strategy.get_strategy_status()
                for name, strategy in self.strategies.items()
            },
            'positions': self.risk_manager.get_position_summary(),
            'alerts': self.risk_manager.get_risk_alerts(),
        }
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary."""
        risk_metrics = self.risk_manager.get_risk_metrics()
        strategy_performance = {}
        
        for name, strategy in self.strategies.items():
            strategy_performance[name] = strategy.get_performance_summary()
        
        return {
            'risk_metrics': risk_metrics,
            'profit_metrics': self.profit_monitor.get_performance_metrics(),
            'session_performance': self.profit_monitor.get_session_performance(),
            'pair_performance': self.profit_monitor.get_pair_performance(),
            'strategy_performance': strategy_performance,
            'session_info': self.session_manager.get_all_sessions_info(),
        }
    
    def enable_strategy(self, strategy_name: str) -> bool:
        """Enable a specific strategy."""
        if strategy_name in self.strategies:
            self.strategies[strategy_name].enable()
            logger.info(f"Enabled strategy: {strategy_name}")
            return True
        return False
    
    def disable_strategy(self, strategy_name: str) -> bool:
        """Disable a specific strategy."""
        if strategy_name in self.strategies:
            self.strategies[strategy_name].disable()
            logger.info(f"Disabled strategy: {strategy_name}")
            return True
        return False
    
    def update_strategy_parameters(self, strategy_name: str, parameters: Dict[str, Any]) -> bool:
        """Update strategy parameters."""
        if strategy_name in self.strategies:
            self.strategies[strategy_name].update_parameters(parameters)
            logger.info(f"Updated parameters for {strategy_name}: {parameters}")
            return True
        return False
    
    def get_available_symbols(self) -> List[str]:
        """Get available symbols from broker."""
        return self.broker.get_symbols()
    
    def add_symbol(self, symbol: str) -> bool:
        """Add a symbol to the trading list."""
        if symbol not in self.config.symbols:
            self.config.symbols.append(symbol)
            logger.info(f"Added symbol: {symbol}")
            return True
        return False
    
    def remove_symbol(self, symbol: str) -> bool:
        """Remove a symbol from the trading list."""
        if symbol in self.config.symbols:
            self.config.symbols.remove(symbol)
            logger.info(f"Removed symbol: {symbol}")
            return True
        return False
    
    def generate_trading_report(self, report_type: str = "comprehensive") -> Dict[str, Any]:
        """Generate a comprehensive trading report."""
        return self.profit_monitor.generate_report(report_type)
    
    def save_trading_report(self, report: Dict[str, Any], filename: Optional[str] = None) -> None:
        """Save a trading report to file."""
        self.profit_monitor.save_report(report, filename)
    
    def get_currency_pair_info(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get information about a specific currency pair."""
        pair = self.currency_manager.get_pair_info(symbol)
        if not pair:
            return None
        
        return {
            'symbol': pair.symbol,
            'base_currency': pair.base_currency,
            'quote_currency': pair.quote_currency,
            'pip_value': pair.pip_value,
            'min_lot': pair.min_lot,
            'max_lot': pair.max_lot,
            'spread': pair.spread,
            'session_preference': [s.value for s in pair.session_preference],
            'volatility_profile': pair.volatility_profile,
            'correlation_groups': pair.correlation_groups
        }
    
    def get_optimal_pairs_for_session(self, session_type: SessionType, max_pairs: int = 5) -> List[str]:
        """Get optimal currency pairs for a specific session."""
        return self.currency_manager.get_optimal_pairs(session_type, max_pairs)
    
    def get_correlated_pairs(self, symbol: str) -> List[str]:
        """Get pairs correlated with the given symbol."""
        return self.currency_manager.get_correlated_pairs(symbol)
    
    def calculate_position_size(self, symbol: str, risk_amount: float, stop_loss_pips: float) -> float:
        """Calculate position size for a currency pair."""
        return self.currency_manager.calculate_position_size(symbol, risk_amount, stop_loss_pips) 