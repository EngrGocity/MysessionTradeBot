#!/usr/bin/env python3
"""
Example usage of the Market Session Trading Bot.
"""
import sys
from pathlib import Path
import time
from loguru import logger

# Add src to path
sys.path.append(str(Path(__file__).parent / "src"))

from src.core.config import TradingBotConfig, StrategyConfig, SessionType, TimeFrame
from src.core.trading_bot import TradingBot


def create_example_config():
    """Create an example configuration for Exness MT5."""
    config = TradingBotConfig(
        broker={
            "name": "Exness Demo",
            "server": "Exness-Demo",
            "login": 0,  # Replace with your account number
            "password": "",  # Replace with your password
            "timeout": 60000,
            "enable_real_trading": False  # Demo mode for safety
        },
        sessions=[
            {
                "session_type": SessionType.ASIAN,
                "start_time": "00:00",
                "end_time": "08:00",
                "timezone": "UTC",
                "enabled": True
            },
            {
                "session_type": SessionType.LONDON,
                "start_time": "08:00",
                "end_time": "16:00",
                "timezone": "UTC",
                "enabled": True
            },
            {
                "session_type": SessionType.NEW_YORK,
                "start_time": "13:00",
                "end_time": "21:00",
                "timezone": "UTC",
                "enabled": True
            }
        ],
        risk={
            "max_position_size": 0.02,  # 2% per position
            "max_daily_loss": 0.05,     # 5% daily limit
            "max_open_positions": 3,    # Conservative limit
            "stop_loss_pips": 50.0,
            "take_profit_pips": 100.0,
            "trailing_stop": True,
            "trailing_stop_pips": 20.0
        },
        strategies=[
            StrategyConfig(
                name="session_breakout",
                enabled=True,
                symbols=["EURUSD", "GBPUSD", "USDJPY"],
                timeframe=TimeFrame.H1,
                parameters={
                    "breakout_period": 20,
                    "breakout_multiplier": 1.5,
                    "atr_period": 14,
                    "min_volume": 0.01,
                    "max_volume": 0.5
                }
            )
        ],
        symbols=["EURUSD", "GBPUSD", "USDJPY"],
        enable_dashboard=True,
        dashboard_port=8050
    )
    
    return config


def run_bot_example():
    """Run the trading bot with example configuration."""
    logger.info("Starting Market Session Trading Bot Example")
    
    # Create configuration
    config = create_example_config()
    
    # Create trading bot
    bot = TradingBot(config)
    
    try:
        # Start the bot
        if bot.start():
            logger.info("Bot started successfully!")
            
            # Monitor for 5 minutes
            logger.info("Monitoring bot for 5 minutes...")
            start_time = time.time()
            
            while time.time() - start_time < 300:  # 5 minutes
                # Get status
                status = bot.get_status()
                
                # Print status
                logger.info(f"Bot running: {status['running']}")
                logger.info(f"Connected: {status['connected']}")
                logger.info(f"Active sessions: {status['active_sessions']}")
                logger.info(f"Open positions: {len(status['positions'])}")
                
                # Check for alerts
                alerts = status['risk_metrics']['alerts']
                if alerts:
                    logger.warning(f"Risk alerts: {alerts}")
                
                # Sleep for 30 seconds
                time.sleep(30)
            
            # Get final performance summary
            performance = bot.get_performance_summary()
            logger.info("Performance Summary:")
            logger.info(f"Total trades: {performance['risk_metrics']['total_trades']}")
            logger.info(f"Win rate: {performance['risk_metrics']['win_rate']:.1%}")
            logger.info(f"Total P&L: ${performance['risk_metrics']['total_pnl']:.2f}")
            
        else:
            logger.error("Failed to start bot")
            return False
            
    except KeyboardInterrupt:
        logger.info("Received interrupt signal")
    except Exception as e:
        logger.error(f"Error running bot: {e}")
        return False
    finally:
        # Stop the bot
        bot.stop()
        logger.info("Bot stopped")
    
    return True


def test_connection():
    """Test MT5 connection without trading."""
    logger.info("Testing MT5 connection...")
    
    config = create_example_config()
    bot = TradingBot(config)
    
    try:
        # Test connection
        if bot.broker.connect():
            logger.info("✅ MT5 connection successful!")
            
            # Get account info
            account_info = bot.broker.get_account_info()
            if account_info:
                logger.info(f"Account: {account_info.get('login')}")
                logger.info(f"Server: {account_info.get('server')}")
                logger.info(f"Balance: ${account_info.get('balance', 0):,.2f}")
                logger.info(f"Currency: {account_info.get('currency')}")
            
            # Get available symbols
            symbols = bot.broker.get_symbols()
            logger.info(f"Available symbols: {len(symbols)}")
            logger.info(f"Sample symbols: {symbols[:5]}")
            
            # Test symbol info
            if symbols:
                symbol_info = bot.broker.get_symbol_info(symbols[0])
                if symbol_info:
                    logger.info(f"Symbol info for {symbols[0]}:")
                    logger.info(f"  Bid: {symbol_info.get('bid')}")
                    logger.info(f"  Ask: {symbol_info.get('ask')}")
                    logger.info(f"  Spread: {symbol_info.get('spread')}")
            
            return True
        else:
            logger.error("❌ MT5 connection failed!")
            return False
            
    except Exception as e:
        logger.error(f"❌ Connection test error: {e}")
        return False
    finally:
        bot.broker.disconnect()


def analyze_session():
    """Analyze current market session."""
    logger.info("Analyzing current market session...")
    
    config = create_example_config()
    bot = TradingBot(config)
    
    try:
        # Initialize session manager
        bot.session_manager.start()
        
        # Get session info
        sessions_info = bot.session_manager.get_all_sessions_info()
        
        logger.info("Market Sessions:")
        for session_type, info in sessions_info.items():
            if info:
                status = "🟢 ACTIVE" if info['is_active'] else "🔴 INACTIVE"
                logger.info(f"  {session_type}: {status}")
                logger.info(f"    Time: {info['start_time']} - {info['end_time']}")
                logger.info(f"    Next start: {info['next_start']}")
        
        # Get active sessions
        active_sessions = bot.session_manager.get_active_sessions()
        if active_sessions:
            logger.info(f"Currently active: {active_sessions}")
        else:
            logger.info("No active sessions")
        
        return True
        
    except Exception as e:
        logger.error(f"Session analysis error: {e}")
        return False
    finally:
        bot.session_manager.stop()


def main():
    """Main example function."""
    logger.info("Market Session Trading Bot - Example Usage")
    logger.info("=" * 50)
    
    # Test 1: Connection test
    logger.info("\n1. Testing MT5 Connection")
    logger.info("-" * 30)
    if not test_connection():
        logger.error("Connection test failed. Please check your MT5 setup.")
        return
    
    # Test 2: Session analysis
    logger.info("\n2. Analyzing Market Sessions")
    logger.info("-" * 30)
    analyze_session()
    
    # Test 3: Run bot (optional)
    logger.info("\n3. Running Trading Bot (Demo Mode)")
    logger.info("-" * 30)
    logger.info("This will run the bot in demo mode for 5 minutes.")
    logger.info("Press Ctrl+C to stop early.")
    
    response = input("Do you want to run the bot? (y/n): ").lower().strip()
    if response == 'y':
        run_bot_example()
    else:
        logger.info("Skipping bot execution.")
    
    logger.info("\nExample completed!")


if __name__ == "__main__":
    main() 