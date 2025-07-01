#!/usr/bin/env python3
"""
Quick start script for the Market Session Trading Bot.
"""
import os
import sys
import subprocess
from pathlib import Path
from loguru import logger


def run_command(command: str, description: str) -> bool:
    """Run a command and return success status."""
    logger.info(f"Running: {description}")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        logger.info(f"✅ {description} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ {description} failed: {e}")
        logger.error(f"Error output: {e.stderr}")
        return False


def main():
    """Quick start setup."""
    logger.info("🚀 Market Session Trading Bot - Quick Start")
    logger.info("=" * 50)
    
    # Check Python version
    if sys.version_info < (3, 8):
        logger.error("❌ Python 3.8 or higher is required")
        return False
    
    logger.info(f"✅ Python {sys.version_info.major}.{sys.version_info.minor} detected")
    
    # Install dependencies
    logger.info("\n📦 Installing dependencies...")
    if not run_command("pip install -r requirements.txt", "Installing Python dependencies"):
        return False
    
    # Create necessary directories
    logger.info("\n📁 Creating directories...")
    directories = ["config", "data", "logs", "models"]
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        logger.info(f"✅ Created {directory}/ directory")
    
    # Test installation
    logger.info("\n🧪 Testing installation...")
    if not run_command("python test_installation.py", "Running installation tests"):
        logger.warning("⚠️ Some tests failed, but continuing...")
    
    # Create configuration
    logger.info("\n⚙️ Creating configuration...")
    if not run_command("python main.py --create-config", "Creating default configuration"):
        return False
    
    # Test connection
    logger.info("\n🔗 Testing MT5 connection...")
    if not run_command("python example_usage.py", "Testing MT5 connection"):
        logger.warning("⚠️ MT5 connection test failed - this is normal if MT5 is not installed")
    
    # Run backtest
    logger.info("\n📊 Running backtest...")
    if not run_command("python main.py --backtest --backtest-days 7", "Running 7-day backtest"):
        logger.warning("⚠️ Backtest failed - this is normal if MT5 is not connected")
    
    logger.info("\n" + "=" * 50)
    logger.info("🎉 Quick start completed!")
    logger.info("\nNext steps:")
    logger.info("1. Edit config/bot_config.yaml with your broker credentials")
    logger.info("2. Test connection: python example_usage.py")
    logger.info("3. Run backtest: python main.py --backtest")
    logger.info("4. Start bot: python main.py --demo")
    logger.info("5. Access dashboard: http://localhost:8050")
    
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 