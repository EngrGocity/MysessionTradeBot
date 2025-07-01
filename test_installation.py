#!/usr/bin/env python3
"""
Test script to verify installation and basic functionality.
"""
import sys
import importlib
from pathlib import Path
from loguru import logger

# Add src to path
sys.path.append(str(Path(__file__).parent / "src"))


def test_imports():
    """Test that all required modules can be imported."""
    logger.info("Testing module imports...")
    
    modules_to_test = [
        "MetaTrader5",
        "pandas",
        "numpy",
        "ta",
        "pydantic",
        "loguru",
        "schedule",
        "pytz",
        "yaml"
    ]
    
    failed_imports = []
    
    for module in modules_to_test:
        try:
            importlib.import_module(module)
            logger.info(f"✅ {module}")
        except ImportError as e:
            logger.error(f"❌ {module}: {e}")
            failed_imports.append(module)
    
    if failed_imports:
        logger.error(f"Failed to import: {failed_imports}")
        logger.error("Please install missing dependencies: pip install -r requirements.txt")
        return False
    
    logger.info("All required modules imported successfully!")
    return True


def test_project_modules():
    """Test that project modules can be imported."""
    logger.info("Testing project modules...")
    
    project_modules = [
        "src.core.config",
        "src.core.session_manager",
        "src.core.trading_bot",
        "src.brokers.base_broker",
        "src.brokers.mt5_broker",
        "src.strategies.base_strategy",
        "src.strategies.session_breakout_strategy",
        "src.risk_management.risk_manager"
    ]
    
    failed_imports = []
    
    for module in project_modules:
        try:
            importlib.import_module(module)
            logger.info(f"✅ {module}")
        except ImportError as e:
            logger.error(f"❌ {module}: {e}")
            failed_imports.append(module)
    
    if failed_imports:
        logger.error(f"Failed to import project modules: {failed_imports}")
        return False
    
    logger.info("All project modules imported successfully!")
    return True


def test_config_creation():
    """Test configuration creation."""
    logger.info("Testing configuration creation...")
    
    try:
        from src.core.config import TradingBotConfig, SessionType, TimeFrame
        
        # Test basic config creation
        config = TradingBotConfig.from_env()
        logger.info("✅ Configuration created successfully")
        
        # Test session types
        logger.info(f"Session types: {[s.value for s in SessionType]}")
        
        # Test timeframes
        logger.info(f"Timeframes: {[t.value for t in TimeFrame]}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Configuration test failed: {e}")
        return False


def test_mt5_connection():
    """Test MT5 connection (without trading)."""
    logger.info("Testing MT5 connection...")
    
    try:
        import MetaTrader5 as mt5
        
        # Initialize MT5
        if not mt5.initialize():
            logger.warning("⚠️ MT5 initialization failed - this is normal if MT5 is not installed")
            logger.warning("MT5 terminal must be installed and running for full functionality")
            return True  # Not a critical failure
        
        # Get terminal info
        terminal_info = mt5.terminal_info()
        if terminal_info:
            logger.info(f"✅ MT5 Terminal: {terminal_info.name}")
            logger.info(f"   Version: {terminal_info.version}")
            logger.info(f"   Connected: {terminal_info.connected}")
        
        # Shutdown
        mt5.shutdown()
        
        return True
        
    except ImportError:
        logger.warning("⚠️ MetaTrader5 module not available")
        logger.warning("Install with: pip install MetaTrader5")
        return True  # Not a critical failure
    except Exception as e:
        logger.error(f"❌ MT5 test error: {e}")
        return False


def test_file_structure():
    """Test that required files and directories exist."""
    logger.info("Testing file structure...")
    
    required_files = [
        "requirements.txt",
        "main.py",
        "README.md",
        "src/__init__.py",
        "src/core/__init__.py",
        "src/core/config.py",
        "src/core/session_manager.py",
        "src/core/trading_bot.py",
        "src/brokers/__init__.py",
        "src/brokers/base_broker.py",
        "src/brokers/mt5_broker.py",
        "src/strategies/__init__.py",
        "src/strategies/base_strategy.py",
        "src/strategies/session_breakout_strategy.py",
        "src/risk_management/__init__.py",
        "src/risk_management/risk_manager.py"
    ]
    
    missing_files = []
    
    for file_path in required_files:
        if Path(file_path).exists():
            logger.info(f"✅ {file_path}")
        else:
            logger.error(f"❌ {file_path}")
            missing_files.append(file_path)
    
    if missing_files:
        logger.error(f"Missing files: {missing_files}")
        return False
    
    logger.info("All required files present!")
    return True


def main():
    """Run all tests."""
    logger.info("Market Session Trading Bot - Installation Test")
    logger.info("=" * 50)
    
    tests = [
        ("File Structure", test_file_structure),
        ("Module Imports", test_imports),
        ("Project Modules", test_project_modules),
        ("Configuration", test_config_creation),
        ("MT5 Connection", test_mt5_connection)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        logger.info(f"\n{test_name}")
        logger.info("-" * 30)
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            logger.error(f"Test {test_name} failed with exception: {e}")
            results.append((test_name, False))
    
    # Summary
    logger.info("\n" + "=" * 50)
    logger.info("TEST SUMMARY")
    logger.info("=" * 50)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        logger.info(f"{test_name}: {status}")
        if result:
            passed += 1
    
    logger.info(f"\nPassed: {passed}/{total}")
    
    if passed == total:
        logger.info("🎉 All tests passed! Installation is complete.")
        logger.info("\nNext steps:")
        logger.info("1. Create configuration: python main.py --create-config")
        logger.info("2. Edit config/bot_config.yaml with your settings")
        logger.info("3. Test connection: python example_usage.py")
        logger.info("4. Run bot: python main.py --demo")
    else:
        logger.error("❌ Some tests failed. Please check the errors above.")
        logger.info("\nTroubleshooting:")
        logger.info("1. Install dependencies: pip install -r requirements.txt")
        logger.info("2. Ensure MT5 terminal is installed (optional)")
        logger.info("3. Check file permissions and paths")
    
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 