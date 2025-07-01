#!/usr/bin/env python3
"""
Main entry point for the Market Session Trading Bot.
"""
import os
import sys
import signal
import argparse
from pathlib import Path
from datetime import datetime, timedelta
from loguru import logger
import yaml

# Add src to path
sys.path.append(str(Path(__file__).parent / "src"))

from src.core.config import TradingBotConfig, StrategyConfig, SessionType, TimeFrame
from src.core.trading_bot import TradingBot


def setup_logging(log_level: str = "INFO", log_file: str = "logs/trading_bot.log"):
    """Setup logging configuration."""
    # Create logs directory
    os.makedirs("logs", exist_ok=True)
    
    # Remove default logger
    logger.remove()
    
    # Add console logger
    logger.add(
        sys.stdout,
        level=log_level,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
    )
    
    # Add file logger
    logger.add(
        log_file,
        level=log_level,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        rotation="1 day",
        retention="30 days",
        compression="zip"
    )


def load_config(config_file: str = "config/bot_config.yaml") -> TradingBotConfig:
    """Load configuration from YAML file."""
    try:
        if not os.path.exists(config_file):
            logger.warning(f"Config file {config_file} not found, using default configuration")
            return TradingBotConfig.from_env()
        
        with open(config_file, 'r') as f:
            config_data = yaml.safe_load(f)
        
        # Convert YAML data to TradingBotConfig
        config = TradingBotConfig(**config_data)
        logger.info(f"Loaded configuration from {config_file}")
        return config
        
    except Exception as e:
        logger.error(f"Error loading configuration: {e}")
        logger.info("Using default configuration")
        return TradingBotConfig.from_env()


def create_default_config(config_file: str = "config/bot_config.yaml"):
    """Create a default configuration file."""
    os.makedirs("config", exist_ok=True)
    
    default_config = {
        "broker": {
            "name": "Exness Demo",
            "server": "Exness-Demo",
            "login": 0,
            "password": "",
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
            "max_position_size": 0.02,
            "max_daily_loss": 0.05,
            "max_open_positions": 5,
            "stop_loss_pips": 50.0,
            "take_profit_pips": 100.0,
            "trailing_stop": False,
            "trailing_stop_pips": 20.0
        },
        "strategies": [
            {
                "name": "session_breakout",
                "enabled": True,
                "symbols": ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD"],
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
        "symbols": ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD"],
        "data_path": "data",
        "logs_path": "logs",
        "enable_dashboard": True,
        "dashboard_port": 8050,
        "enable_notifications": False
    }
    
    with open(config_file, 'w') as f:
        yaml.dump(default_config, f, default_flow_style=False, indent=2)
    
    logger.info(f"Created default configuration file: {config_file}")


def signal_handler(signum, frame):
    """Handle shutdown signals."""
    logger.info(f"Received signal {signum}, shutting down...")
    if hasattr(signal_handler, 'bot') and signal_handler.bot:
        signal_handler.bot.stop()
    sys.exit(0)


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Market Session Trading Bot")
    parser.add_argument("--config", "-c", default="config/bot_config.yaml", 
                       help="Configuration file path")
    parser.add_argument("--log-level", "-l", default="INFO", 
                       choices=["DEBUG", "INFO", "WARNING", "ERROR"],
                       help="Logging level")
    parser.add_argument("--create-config", action="store_true",
                       help="Create default configuration file")
    parser.add_argument("--demo", action="store_true",
                       help="Run in demo mode (paper trading)")
    parser.add_argument("--backtest", action="store_true",
                       help="Run backtest instead of live trading")
    parser.add_argument("--backtest-symbol", default="EURUSD",
                       help="Symbol for backtesting")
    parser.add_argument("--backtest-days", type=int, default=30,
                       help="Number of days to backtest")
    
    # Add dashboard option
    parser.add_argument('--dashboard', action='store_true', 
                       help='Start the web dashboard')
    parser.add_argument('--dashboard-host', default='localhost',
                       help='Dashboard host (default: localhost)')
    parser.add_argument('--dashboard-port', type=int, default=8050,
                       help='Dashboard port (default: 8050)')
    
    # Add profit monitoring options
    parser.add_argument('--generate-report', action='store_true',
                       help='Generate a comprehensive trading report')
    parser.add_argument('--report-type', default='comprehensive',
                       choices=['comprehensive', 'summary', 'risk'],
                       help='Type of report to generate (default: comprehensive)')
    parser.add_argument('--save-report', action='store_true',
                       help='Save the generated report to file')
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.log_level)
    
    logger.info("Starting Market Session Trading Bot")
    logger.info(f"Python version: {sys.version}")
    logger.info(f"Working directory: {os.getcwd()}")
    
    # Create default config if requested
    if args.create_config:
        create_default_config(args.config)
        return
    
    # Load configuration
    config = load_config(args.config)
    
    # Override for demo mode
    if args.demo:
        config.broker.enable_real_trading = False
        logger.info("Running in demo mode (paper trading)")
    
    # Run backtest if requested
    if args.backtest:
        from src.backtesting.simple_backtester import SimpleBacktester
        
        backtester = SimpleBacktester(config)
        end_date = datetime.now()
        start_date = end_date - timedelta(days=args.backtest_days)
        
        logger.info(f"Running backtest for {args.backtest_symbol} from {start_date} to {end_date}")
        results = backtester.run_backtest(args.backtest_symbol, start_date, end_date)
        
        if results:
            logger.info("Backtest Results:")
            logger.info(f"Total Trades: {results['total_trades']}")
            logger.info(f"Win Rate: {results['win_rate']:.2%}")
            logger.info(f"Total P&L: ${results['total_pnl']:.2f}")
            logger.info(f"Return: {results['return_pct']:.2f}%")
        else:
            logger.error("Backtest failed")
        
        return 0
    
    # Create trading bot
    bot = TradingBot(config)
    
    # Store bot reference for signal handler
    signal_handler.bot = bot
    
    # Setup signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Generate report if requested
    if args.generate_report:
        logger.info(f"Generating {args.report_type} trading report...")
        report = bot.generate_trading_report(args.report_type)
        
        if args.save_report:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"trading_report_{args.report_type}_{timestamp}.json"
            bot.save_trading_report(report, filename)
            logger.info(f"Report saved to: {filename}")
        else:
            # Print report summary
            logger.info("Report Summary:")
            logger.info(f"Total Trades: {report['summary']['total_trades']}")
            logger.info(f"Net Profit: ${report['summary']['net_profit']:.2f}")
            logger.info(f"Win Rate: {report['summary']['win_rate']:.2%}")
            logger.info(f"Profit Factor: {report['summary']['profit_factor']:.2f}")
            logger.info(f"Max Drawdown: ${report['summary']['max_drawdown']:.2f}")
            logger.info(f"Sharpe Ratio: {report['summary']['sharpe_ratio']:.2f}")
        
        return 0
    
    # Start dashboard if requested
    if args.dashboard:
        try:
            from src.dashboard.dashboard import create_dashboard
            
            logger.info(f"Starting dashboard on http://{args.dashboard_host}:{args.dashboard_port}")
            dashboard = create_dashboard(bot, args.dashboard_host, args.dashboard_port)
            dashboard.run()
            return 0
        except ImportError as e:
            logger.error(f"Dashboard dependencies not available: {e}")
            logger.info("Install dashboard dependencies: pip install dash plotly")
            return 1
        except Exception as e:
            logger.error(f"Failed to start dashboard: {e}")
            return 1
    
    try:
        # Start the bot
        if bot.start():
            logger.info("Trading bot started successfully")
            
            # Keep the main thread alive
            while bot.running:
                try:
                    # Get status every 60 seconds
                    import time
                    time.sleep(60)
                    
                    # Log status
                    status = bot.get_status()
                    if status['risk_metrics']['alerts']:
                        logger.warning(f"Risk alerts: {status['risk_metrics']['alerts']}")
                    
                except KeyboardInterrupt:
                    break
        else:
            logger.error("Failed to start trading bot")
            return 1
            
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return 1
    
    finally:
        # Stop the bot
        bot.stop()
        logger.info("Trading bot stopped")
    
    return 0


if __name__ == "__main__":
    sys.exit(main()) 