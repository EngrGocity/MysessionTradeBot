#!/usr/bin/env python3
"""
Profit Taking Example

This example demonstrates the bot's advanced time-based profit taking system,
showing how to configure and use different profit taking rules for various
trading scenarios and market sessions.
"""

import sys
import os
import logging
from datetime import datetime, timedelta
import time

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.core.trading_bot import TradingBot
from src.core.config import Config
from src.core.profit_monitor import ProfitMonitor, ProfitTakingRule
from src.core.session_manager import SessionType
from src.brokers.mt5_broker import MT5Broker
from src.risk_management.risk_manager import RiskManager
from src.strategies.session_breakout_strategy import SessionBreakoutStrategy
from src.utils.helpers import load_yaml_config, ensure_directory

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/profit_taking_example.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

def create_profit_taking_config():
    """Create a configuration focused on profit taking features."""
    config = {
        "broker": {
            "name": "Exness Demo",
            "server": "Exness-Demo",
            "login": 12345678,  # Replace with your demo account
            "password": "your_password",  # Replace with your password
            "timeout": 60000,
            "enable_real_trading": False
        },
        "sessions": [
            {
                "session_type": "asian",
                "start_time": "00:00",
                "end_time": "08:00",
                "timezone": "UTC",
                "enabled": True
            },
            {
                "session_type": "london",
                "start_time": "08:00",
                "end_time": "16:00",
                "timezone": "UTC",
                "enabled": True
            },
            {
                "session_type": "new_york",
                "start_time": "13:00",
                "end_time": "21:00",
                "timezone": "UTC",
                "enabled": True
            }
        ],
        "risk": {
            "max_position_size": 0.03,  # 3% per position
            "max_daily_loss": 0.05,     # 5% daily loss limit
            "max_open_positions": 5,
            "stop_loss_pips": 40.0,     # Tighter stop loss for profit taking
            "take_profit_pips": 80.0,   # Lower take profit since we use profit taking
            "trailing_stop": True,
            "trailing_stop_pips": 15.0
        },
        "strategies": [
            {
                "name": "session_breakout",
                "enabled": True,
                "symbols": ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD"],
                "timeframe": "H1",
                "parameters": {
                    "breakout_period": 15,
                    "breakout_multiplier": 1.2,
                    "atr_period": 14,
                    "min_volume": 0.01,
                    "max_volume": 0.5
                }
            }
        ],
        "profit_taking": {
            "enabled": True,
            "rules": [
                {
                    "name": "Scalping Quick Profit",
                    "enabled": True,
                    "time_interval_minutes": 15,
                    "min_profit_pips": 8.0,
                    "profit_percentage": 0.4,
                    "max_trades_per_interval": 3,
                    "session_filter": None,
                    "symbol_filter": None
                },
                {
                    "name": "Asian Session Profit",
                    "enabled": True,
                    "time_interval_minutes": 120,
                    "min_profit_pips": 12.0,
                    "profit_percentage": 0.6,
                    "max_trades_per_interval": 2,
                    "session_filter": "asian",
                    "symbol_filter": None
                },
                {
                    "name": "London Session Profit",
                    "enabled": True,
                    "time_interval_minutes": 90,
                    "min_profit_pips": 18.0,
                    "profit_percentage": 0.7,
                    "max_trades_per_interval": 2,
                    "session_filter": "london",
                    "symbol_filter": None
                },
                {
                    "name": "New York Session Profit",
                    "enabled": True,
                    "time_interval_minutes": 60,
                    "min_profit_pips": 15.0,
                    "profit_percentage": 0.65,
                    "max_trades_per_interval": 2,
                    "session_filter": "new_york",
                    "symbol_filter": None
                },
                {
                    "name": "EURUSD Specific",
                    "enabled": True,
                    "time_interval_minutes": 45,
                    "min_profit_pips": 10.0,
                    "profit_percentage": 0.5,
                    "max_trades_per_interval": 1,
                    "session_filter": None,
                    "symbol_filter": "EURUSD"
                },
                {
                    "name": "Session End Cleanup",
                    "enabled": True,
                    "time_interval_minutes": 240,
                    "min_profit_pips": 25.0,
                    "profit_percentage": 0.8,
                    "max_trades_per_interval": 1,
                    "session_filter": None,
                    "symbol_filter": None
                }
            ]
        }
    }
    
    return config

def create_custom_profit_rules():
    """Create custom profit taking rules for demonstration."""
    rules = []
    
    # Rule 1: Ultra-fast scalping
    rule1 = ProfitTakingRule(
        name="Ultra Scalping",
        enabled=True,
        time_interval_minutes=5,
        min_profit_pips=5.0,
        profit_percentage=0.3,
        max_trades_per_interval=5,
        session_filter=None,
        symbol_filter=None
    )
    rules.append(rule1)
    
    # Rule 2: GBPUSD specific rule
    rule2 = ProfitTakingRule(
        name="GBPUSD Volatility",
        enabled=True,
        time_interval_minutes=30,
        min_profit_pips=12.0,
        profit_percentage=0.6,
        max_trades_per_interval=2,
        session_filter=None,
        symbol_filter="GBPUSD"
    )
    rules.append(rule2)
    
    # Rule 3: High volatility session rule
    rule3 = ProfitTakingRule(
        name="High Volatility Session",
        enabled=True,
        time_interval_minutes=20,
        min_profit_pips=15.0,
        profit_percentage=0.7,
        max_trades_per_interval=3,
        session_filter=SessionType.LONDON,
        symbol_filter=None
    )
    rules.append(rule3)
    
    return rules

def run_profit_taking_demo():
    """Run the profit taking demo."""
    logger.info("Starting Profit Taking Demo")
    
    try:
        # Ensure directories exist
        ensure_directory('logs')
        ensure_directory('data')
        
        # Create configuration
        config = create_profit_taking_config()
        
        # Initialize components
        logger.info("Initializing trading components...")
        
        # Create broker
        broker = MT5Broker(config['broker'])
        
        # Create risk manager
        risk_manager = RiskManager(config['risk'])
        
        # Create profit monitor with enhanced configuration
        profit_monitor = ProfitMonitor(config['profit_taking'])
        
        # Add custom rules
        custom_rules = create_custom_profit_rules()
        for rule in custom_rules:
            profit_monitor.add_profit_taking_rule(rule)
            logger.info(f"Added custom rule: {rule.name}")
        
        # Create trading bot
        bot = TradingBot(
            broker=broker,
            risk_manager=risk_manager,
            profit_monitor=profit_monitor,
            config=config
        )
        
        # Initialize bot
        logger.info("Initializing trading bot...")
        if not bot.initialize():
            logger.error("Failed to initialize trading bot")
            return False
        
        # Display profit taking configuration
        logger.info("=== Profit Taking Configuration ===")
        logger.info(f"Profit Taking Enabled: {config['profit_taking']['enabled']}")
        logger.info(f"Total Rules: {len(profit_monitor.get_all_rules())}")
        
        # Display all rules
        logger.info("\nActive Profit Taking Rules:")
        for rule in profit_monitor.get_all_rules():
            logger.info(f"  - {rule.name}: {rule.time_interval_minutes}min, "
                       f"{rule.min_profit_pips}pips, {rule.profit_percentage*100:.0f}%")
            if rule.session_filter:
                logger.info(f"    Session Filter: {rule.session_filter}")
            if rule.symbol_filter:
                logger.info(f"    Symbol Filter: {rule.symbol_filter}")
        
        logger.info("=" * 50)
        
        # Display initial information
        logger.info("=== Profit Taking Bot Initialized ===")
        logger.info(f"Account Balance: ${bot.broker.get_account_info()['balance']:.2f}")
        logger.info(f"Risk per Position: {config['risk']['max_position_size']*100:.1f}%")
        logger.info(f"Stop Loss: {config['risk']['stop_loss_pips']} pips")
        logger.info(f"Take Profit: {config['risk']['take_profit_pips']} pips")
        logger.info("=" * 50)
        
        # Start trading
        logger.info("\nStarting profit taking demo...")
        logger.info("Press Ctrl+C to stop")
        
        # Trading loop with profit taking monitoring
        start_time = datetime.now()
        last_status_check = start_time
        
        while True:
            try:
                # Check if bot should continue
                if not bot.is_running:
                    logger.warning("Bot stopped running")
                    break
                
                current_time = datetime.now()
                
                # Get current session
                current_session = bot.session_manager.get_current_session()
                if current_session:
                    logger.info(f"Current session: {current_session.session_type}")
                
                # Get open positions
                open_positions = bot.broker.get_open_positions()
                if open_positions:
                    logger.info(f"Open positions: {len(open_positions)}")
                    for pos in open_positions:
                        profit_pips = pos.get('profit_pips', 0)
                        profit_percent = pos.get('profit_percent', 0)
                        logger.info(f"  {pos['symbol']} {pos['type']} {pos['volume']} lots")
                        logger.info(f"    P&L: ${pos['profit']:.2f} ({profit_pips:.1f} pips, {profit_percent:.1f}%)")
                
                # Get daily P&L
                daily_pnl = bot.profit_monitor.get_daily_pnl()
                logger.info(f"Daily P&L: ${daily_pnl:.2f}")
                
                # Check profit taking status every 5 minutes
                if (current_time - last_status_check).total_seconds() >= 300:
                    profit_status = bot.profit_monitor.get_profit_taking_status()
                    
                    logger.info("\n=== Profit Taking Status ===")
                    
                    # Active positions with profit potential
                    if profit_status.get('active_positions'):
                        logger.info("Positions with Profit Potential:")
                        for position in profit_status['active_positions']:
                            symbol = position.get('symbol', 'Unknown')
                            profit_pips = position.get('profit_pips', 0)
                            profit_percent = position.get('profit_percent', 0)
                            logger.info(f"  {symbol}: {profit_pips:.1f} pips ({profit_percent:.1f}%)")
                    
                    # Recent profit taking actions
                    if profit_status.get('recent_actions'):
                        logger.info("Recent Profit Taking Actions:")
                        for action in profit_status['recent_actions'][-5:]:  # Last 5 actions
                            symbol = action.get('symbol', 'Unknown')
                            action_type = action.get('action', 'Unknown')
                            profit = action.get('profit', 0)
                            time_str = action.get('time', 'Unknown')
                            logger.info(f"  {time_str}: {symbol} {action_type} (Profit: ${profit:.2f})")
                    
                    # Rule statistics
                    rule_stats = profit_monitor.get_rule_statistics()
                    if rule_stats:
                        logger.info("Rule Statistics:")
                        for rule_name, stats in rule_stats.items():
                            triggers = stats.get('triggers', 0)
                            actions = stats.get('actions', 0)
                            total_profit = stats.get('total_profit', 0)
                            logger.info(f"  {rule_name}: {triggers} triggers, {actions} actions, ${total_profit:.2f} profit")
                    
                    logger.info("=" * 30)
                    last_status_check = current_time
                
                # Sleep for a while
                time.sleep(30)  # Check every 30 seconds
                
            except KeyboardInterrupt:
                logger.info("Received stop signal")
                break
            except Exception as e:
                logger.error(f"Error in trading loop: {e}")
                time.sleep(10)
        
        # Stop bot
        logger.info("Stopping trading bot...")
        bot.stop()
        
        # Generate final profit taking report
        logger.info("Generating final profit taking report...")
        
        # Get profit taking statistics
        profit_stats = profit_monitor.get_profit_taking_statistics()
        
        logger.info("=== Final Profit Taking Report ===")
        logger.info(f"Total Profit Taking Actions: {profit_stats.get('total_actions', 0)}")
        logger.info(f"Total Profit from Taking: ${profit_stats.get('total_profit_taken', 0):.2f}")
        logger.info(f"Average Profit per Action: ${profit_stats.get('avg_profit_per_action', 0):.2f}")
        logger.info(f"Most Active Rule: {profit_stats.get('most_active_rule', 'None')}")
        logger.info(f"Most Profitable Rule: {profit_stats.get('most_profitable_rule', 'None')}")
        
        # Rule performance breakdown
        rule_performance = profit_monitor.get_rule_performance()
        if rule_performance:
            logger.info("\nRule Performance Breakdown:")
            for rule_name, performance in rule_performance.items():
                actions = performance.get('actions', 0)
                total_profit = performance.get('total_profit', 0)
                avg_profit = performance.get('avg_profit', 0)
                success_rate = performance.get('success_rate', 0) * 100
                logger.info(f"  {rule_name}:")
                logger.info(f"    Actions: {actions}")
                logger.info(f"    Total Profit: ${total_profit:.2f}")
                logger.info(f"    Avg Profit: ${avg_profit:.2f}")
                logger.info(f"    Success Rate: {success_rate:.1f}%")
        
        # Session performance with profit taking
        session_performance = bot.profit_monitor.get_session_performance()
        logger.info("\nSession Performance (with Profit Taking):")
        for session, data in session_performance.items():
            profit = data.get('profit', 0)
            trades = data.get('trades', 0)
            win_rate = data.get('win_rate', 0) * 100
            profit_taken = data.get('profit_taken', 0)
            logger.info(f"  {session}: {trades} trades, ${profit:.2f} total, ${profit_taken:.2f} taken, {win_rate:.1f}% win rate")
        
        # Overall performance metrics
        final_metrics = bot.profit_monitor.get_performance_metrics()
        logger.info("\nOverall Performance:")
        logger.info(f"Total Trades: {final_metrics.get('total_trades', 0)}")
        logger.info(f"Win Rate: {final_metrics.get('win_rate', 0)*100:.1f}%")
        logger.info(f"Total Profit: ${final_metrics.get('total_profit', 0):.2f}")
        logger.info(f"Profit Factor: {final_metrics.get('profit_factor', 0):.2f}")
        logger.info(f"Sharpe Ratio: {final_metrics.get('sharpe_ratio', 0):.2f}")
        
        logger.info("=" * 50)
        logger.info("Profit Taking Demo completed")
        
        return True
        
    except Exception as e:
        logger.error(f"Error in profit taking demo: {e}")
        return False

def demonstrate_profit_taking_features():
    """Demonstrate various profit taking features."""
    logger.info("=== Profit Taking Features Demonstration ===")
    
    # Create profit monitor
    profit_monitor = ProfitMonitor({})
    
    # Example 1: Basic rule
    logger.info("\n1. Basic Profit Taking Rule:")
    basic_rule = ProfitTakingRule(
        name="Basic Rule",
        enabled=True,
        time_interval_minutes=30,
        min_profit_pips=15.0,
        profit_percentage=0.5,
        max_trades_per_interval=2
    )
    logger.info(f"   - Check every {basic_rule.time_interval_minutes} minutes")
    logger.info(f"   - Minimum profit: {basic_rule.min_profit_pips} pips")
    logger.info(f"   - Take {basic_rule.profit_percentage*100:.0f}% of profit")
    
    # Example 2: Session-specific rule
    logger.info("\n2. Session-Specific Rule:")
    session_rule = ProfitTakingRule(
        name="London Session",
        enabled=True,
        time_interval_minutes=60,
        min_profit_pips=20.0,
        profit_percentage=0.7,
        max_trades_per_interval=1,
        session_filter=SessionType.LONDON
    )
    logger.info(f"   - Only active during London session")
    logger.info(f"   - Higher profit threshold: {session_rule.min_profit_pips} pips")
    logger.info(f"   - Take {session_rule.profit_percentage*100:.0f}% of profit")
    
    # Example 3: Symbol-specific rule
    logger.info("\n3. Symbol-Specific Rule:")
    symbol_rule = ProfitTakingRule(
        name="EURUSD Specific",
        enabled=True,
        time_interval_minutes=45,
        min_profit_pips=12.0,
        profit_percentage=0.6,
        max_trades_per_interval=1,
        symbol_filter="EURUSD"
    )
    logger.info(f"   - Only applies to EURUSD")
    logger.info(f"   - Check every {symbol_rule.time_interval_minutes} minutes")
    logger.info(f"   - Take {symbol_rule.profit_percentage*100:.0f}% of profit")
    
    # Example 4: Scalping rule
    logger.info("\n4. Scalping Rule:")
    scalping_rule = ProfitTakingRule(
        name="Scalping",
        enabled=True,
        time_interval_minutes=10,
        min_profit_pips=5.0,
        profit_percentage=0.3,
        max_trades_per_interval=5
    )
    logger.info(f"   - Very frequent checks: {scalping_rule.time_interval_minutes} minutes")
    logger.info(f"   - Low profit threshold: {scalping_rule.min_profit_pips} pips")
    logger.info(f"   - Take {scalping_rule.profit_percentage*100:.0f}% of profit")
    logger.info(f"   - Allow multiple trades: {scalping_rule.max_trades_per_interval}")
    
    logger.info("\n" + "=" * 50)

def main():
    """Main function."""
    print("Market Session Trading Bot - Profit Taking Example")
    print("=" * 60)
    print("This example demonstrates:")
    print("- Time-based profit taking rules")
    print("- Session-specific profit taking")
    print("- Symbol-specific profit taking")
    print("- Scalping profit taking strategies")
    print("- Profit taking statistics and monitoring")
    print("=" * 60)
    
    # Show profit taking features
    demonstrate_profit_taking_features()
    
    # Check if user wants to continue
    response = input("\nDo you want to start the profit taking demo? (y/n): ")
    if response.lower() != 'y':
        print("Demo cancelled")
        return
    
    # Run demo
    success = run_profit_taking_demo()
    
    if success:
        print("\nDemo completed successfully!")
        print("Check the logs for detailed profit taking statistics.")
    else:
        print("\nDemo failed. Check logs for details.")

if __name__ == "__main__":
    main()
