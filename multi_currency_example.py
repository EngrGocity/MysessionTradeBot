#!/usr/bin/env python3
"""
Multi-Currency Trading Example

This example demonstrates the bot's multi-currency trading capabilities,
including correlation analysis, session-specific trading, and risk management
across multiple currency pairs.
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
from src.core.currency_manager import CurrencyManager
from src.core.profit_monitor import ProfitMonitor
from src.brokers.mt5_broker import MT5Broker
from src.risk_management.risk_manager import RiskManager
from src.strategies.session_breakout_strategy import SessionBreakoutStrategy
from src.utils.helpers import load_yaml_config, ensure_directory

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/multi_currency_example.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

def create_multi_currency_config():
    """Create a configuration for multi-currency trading."""
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
            "max_position_size": 0.02,  # 2% per position
            "max_daily_loss": 0.05,     # 5% daily loss limit
            "max_open_positions": 8,    # Allow more positions for multi-currency
            "stop_loss_pips": 50.0,
            "take_profit_pips": 100.0,
            "trailing_stop": True,
            "trailing_stop_pips": 20.0
        },
        "strategies": [
            {
                "name": "session_breakout",
                "enabled": True,
                "symbols": [
                    "EURUSD", "GBPUSD", "USDJPY", "AUDUSD",
                    "USDCAD", "NZDUSD", "EURGBP", "EURJPY"
                ],
                "timeframe": "H1",
                "parameters": {
                    "breakout_period": 20,
                    "breakout_multiplier": 1.5,
                    "atr_period": 14,
                    "min_volume": 0.01,
                    "max_volume": 1.0
                }
            }
        ],
        "currency_pairs": {
            "EURUSD": {
                "session_preferences": ["london", "new_york"],
                "volatility_profile": {
                    "asian": 0.3,
                    "london": 0.8,
                    "new_york": 0.9
                },
                "correlation_group": "majors",
                "pip_value": 0.1,
                "max_position_size": 0.03
            },
            "GBPUSD": {
                "session_preferences": ["london", "new_york"],
                "volatility_profile": {
                    "asian": 0.2,
                    "london": 0.9,
                    "new_york": 0.8
                },
                "correlation_group": "majors",
                "pip_value": 0.1,
                "max_position_size": 0.03
            },
            "USDJPY": {
                "session_preferences": ["asian", "london"],
                "volatility_profile": {
                    "asian": 0.7,
                    "london": 0.6,
                    "new_york": 0.4
                },
                "correlation_group": "majors",
                "pip_value": 0.1,
                "max_position_size": 0.025
            },
            "AUDUSD": {
                "session_preferences": ["asian", "london"],
                "volatility_profile": {
                    "asian": 0.8,
                    "london": 0.5,
                    "new_york": 0.3
                },
                "correlation_group": "commodity",
                "pip_value": 0.1,
                "max_position_size": 0.025
            },
            "USDCAD": {
                "session_preferences": ["london", "new_york"],
                "volatility_profile": {
                    "asian": 0.2,
                    "london": 0.6,
                    "new_york": 0.7
                },
                "correlation_group": "commodity",
                "pip_value": 0.1,
                "max_position_size": 0.025
            },
            "NZDUSD": {
                "session_preferences": ["asian", "london"],
                "volatility_profile": {
                    "asian": 0.6,
                    "london": 0.4,
                    "new_york": 0.3
                },
                "correlation_group": "commodity",
                "pip_value": 0.1,
                "max_position_size": 0.02
            },
            "EURGBP": {
                "session_preferences": ["london"],
                "volatility_profile": {
                    "asian": 0.3,
                    "london": 0.8,
                    "new_york": 0.4
                },
                "correlation_group": "crosses",
                "pip_value": 0.1,
                "max_position_size": 0.02
            },
            "EURJPY": {
                "session_preferences": ["asian", "london"],
                "volatility_profile": {
                    "asian": 0.8,
                    "london": 0.7,
                    "new_york": 0.4
                },
                "correlation_group": "crosses",
                "pip_value": 0.1,
                "max_position_size": 0.02
            }
        },
        "profit_taking": {
            "enabled": True,
            "rules": [
                {
                    "name": "Scalping Quick Profit",
                    "enabled": True,
                    "time_interval_minutes": 15,
                    "min_profit_pips": 10.0,
                    "profit_percentage": 0.5,
                    "max_trades_per_interval": 3
                },
                {
                    "name": "Medium Term Profit",
                    "enabled": True,
                    "time_interval_minutes": 60,
                    "min_profit_pips": 20.0,
                    "profit_percentage": 0.7,
                    "max_trades_per_interval": 2
                },
                {
                    "name": "Session End Profit",
                    "enabled": True,
                    "time_interval_minutes": 240,
                    "min_profit_pips": 30.0,
                    "profit_percentage": 0.8,
                    "max_trades_per_interval": 1
                }
            ]
        }
    }
    
    return config

def run_multi_currency_demo():
    """Run the multi-currency trading demo."""
    logger.info("Starting Multi-Currency Trading Demo")
    
    try:
        # Ensure directories exist
        ensure_directory('logs')
        ensure_directory('data')
        
        # Create configuration
        config = create_multi_currency_config()
        
        # Initialize components
        logger.info("Initializing trading components...")
        
        # Create broker
        broker = MT5Broker(config['broker'])
        
        # Create risk manager
        risk_manager = RiskManager(config['risk'])
        
        # Create currency manager
        currency_manager = CurrencyManager(config['currency_pairs'])
        
        # Create profit monitor
        profit_monitor = ProfitMonitor(config.get('profit_taking', {}))
        
        # Create trading bot
        bot = TradingBot(
            broker=broker,
            risk_manager=risk_manager,
            currency_manager=currency_manager,
            profit_monitor=profit_monitor,
            config=config
        )
        
        # Initialize bot
        logger.info("Initializing trading bot...")
        if not bot.initialize():
            logger.error("Failed to initialize trading bot")
            return False
        
        # Display initial information
        logger.info("=== Multi-Currency Trading Bot Initialized ===")
        logger.info(f"Account Balance: ${bot.broker.get_account_info()['balance']:.2f}")
        logger.info(f"Currency Pairs: {len(config['currency_pairs'])}")
        logger.info(f"Max Open Positions: {config['risk']['max_open_positions']}")
        logger.info(f"Risk per Position: {config['risk']['max_position_size']*100:.1f}%")
        logger.info("=" * 50)
        
        # Display correlation matrix
        logger.info("Correlation Matrix:")
        correlation_matrix = currency_manager.get_correlation_matrix()
        for pair1 in correlation_matrix:
            row = f"{pair1}: "
            for pair2 in correlation_matrix[pair1]:
                correlation = correlation_matrix[pair1][pair2]
                row += f"{pair2}={correlation:.2f} "
            logger.info(row)
        
        # Display session preferences
        logger.info("\nSession Preferences:")
        for pair, settings in config['currency_pairs'].items():
            sessions = settings['session_preferences']
            logger.info(f"{pair}: {', '.join(sessions)}")
        
        # Start trading
        logger.info("\nStarting multi-currency trading...")
        logger.info("Press Ctrl+C to stop")
        
        # Trading loop
        start_time = datetime.now()
        while True:
            try:
                # Check if bot should continue
                if not bot.is_running:
                    logger.warning("Bot stopped running")
                    break
                
                # Get current session
                current_session = bot.session_manager.get_current_session()
                if current_session:
                    logger.info(f"Current session: {current_session.session_type}")
                
                # Get open positions
                open_positions = bot.broker.get_open_positions()
                if open_positions:
                    logger.info(f"Open positions: {len(open_positions)}")
                    for pos in open_positions:
                        logger.info(f"  {pos['symbol']} {pos['type']} {pos['volume']} lots - P&L: ${pos['profit']:.2f}")
                
                # Get daily P&L
                daily_pnl = bot.profit_monitor.get_daily_pnl()
                logger.info(f"Daily P&L: ${daily_pnl:.2f}")
                
                # Get correlation status
                correlation_status = currency_manager.get_correlation_status()
                if correlation_status['high_correlation_warning']:
                    logger.warning(f"High correlation detected: {correlation_status['correlated_pairs']}")
                
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
        
        # Generate final report
        logger.info("Generating final report...")
        final_metrics = bot.profit_monitor.get_performance_metrics()
        
        logger.info("=== Final Performance Report ===")
        logger.info(f"Total Trades: {final_metrics.get('total_trades', 0)}")
        logger.info(f"Win Rate: {final_metrics.get('win_rate', 0)*100:.1f}%")
        logger.info(f"Total Profit: ${final_metrics.get('total_profit', 0):.2f}")
        logger.info(f"Profit Factor: {final_metrics.get('profit_factor', 0):.2f}")
        logger.info(f"Sharpe Ratio: {final_metrics.get('sharpe_ratio', 0):.2f}")
        logger.info(f"Max Drawdown: {final_metrics.get('max_drawdown', 0):.2f}%")
        
        # Session performance
        session_performance = bot.profit_monitor.get_session_performance()
        logger.info("\nSession Performance:")
        for session, data in session_performance.items():
            profit = data.get('profit', 0)
            trades = data.get('trades', 0)
            win_rate = data.get('win_rate', 0) * 100
            logger.info(f"  {session}: {trades} trades, ${profit:.2f} profit, {win_rate:.1f}% win rate")
        
        # Pair performance
        pair_performance = bot.profit_monitor.get_pair_performance()
        logger.info("\nPair Performance:")
        for pair, data in pair_performance.items():
            profit = data.get('profit', 0)
            trades = data.get('trades', 0)
            win_rate = data.get('win_rate', 0) * 100
            logger.info(f"  {pair}: {trades} trades, ${profit:.2f} profit, {win_rate:.1f}% win rate")
        
        logger.info("=" * 50)
        logger.info("Multi-Currency Trading Demo completed")
        
        return True
        
    except Exception as e:
        logger.error(f"Error in multi-currency demo: {e}")
        return False

def main():
    """Main function."""
    print("Market Session Trading Bot - Multi-Currency Example")
    print("=" * 60)
    print("This example demonstrates:")
    print("- Multi-currency trading across 8 pairs")
    print("- Session-specific trading strategies")
    print("- Correlation analysis and risk management")
    print("- Profit taking with time-based rules")
    print("- Comprehensive performance monitoring")
    print("=" * 60)
    
    # Check if user wants to continue
    response = input("\nDo you want to start the multi-currency demo? (y/n): ")
    if response.lower() != 'y':
        print("Demo cancelled")
        return
    
    # Run demo
    success = run_multi_currency_demo()
    
    if success:
        print("\nDemo completed successfully!")
    else:
        print("\nDemo failed. Check logs for details.")

if __name__ == "__main__":
    main() 