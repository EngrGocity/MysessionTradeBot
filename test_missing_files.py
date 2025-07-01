#!/usr/bin/env python3
"""
Test Missing Files

This script tests that all the previously missing files are now working correctly.
"""

import sys
import os
import importlib

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

def test_imports():
    """Test that all modules can be imported successfully."""
    print("Testing module imports...")
    
    modules_to_test = [
        'src.utils.helpers',
        'src.utils.validators', 
        'src.utils.formatters',
        'src.dashboard.dashboard',
        'src.core.profit_monitor',
        'src.core.currency_manager',
        'src.core.session_manager',
        'src.core.trading_bot',
        'src.brokers.mt5_broker',
        'src.risk_management.risk_manager',
        'src.strategies.session_breakout_strategy',
        'src.strategies.ml_strategy',
        'src.indicators.technical_indicators',
        'src.backtesting.backtester',
        'src.backtesting.simple_backtester'
    ]
    
    failed_imports = []
    
    for module_name in modules_to_test:
        try:
            module = importlib.import_module(module_name)
            print(f"✅ {module_name}")
        except Exception as e:
            print(f"❌ {module_name}: {e}")
            failed_imports.append((module_name, e))
    
    return failed_imports

def test_utils_functions():
    """Test utility functions."""
    print("\nTesting utility functions...")
    
    try:
        from src.utils.helpers import calculate_pip_value, format_currency, format_time
        from src.utils.validators import validate_config, validate_symbol
        from src.utils.formatters import format_trade_summary, format_performance_metrics
        
        # Test helper functions
        pip_value = calculate_pip_value("EURUSD", 0.1)
        print(f"✅ calculate_pip_value: {pip_value}")
        
        formatted_currency = format_currency(1234.56, "USD")
        print(f"✅ format_currency: {formatted_currency}")
        
        # Test validator functions
        test_config = {"broker": {}, "sessions": [], "risk": {}, "strategies": []}
        is_valid, errors = validate_config(test_config)
        print(f"✅ validate_config: {is_valid}")
        
        is_valid_symbol = validate_symbol("EURUSD")
        print(f"✅ validate_symbol: {is_valid_symbol}")
        
        # Test formatter functions
        trade_data = {"symbol": "EURUSD", "type": "buy", "volume": 0.1, "profit": 25.0}
        summary = format_trade_summary(trade_data)
        print(f"✅ format_trade_summary: {summary}")
        
        metrics = {"total_trades": 100, "win_rate": 0.65, "total_profit": 1250.0}
        formatted_metrics = format_performance_metrics(metrics)
        print(f"✅ format_performance_metrics: {formatted_metrics}")
        
        return True
        
    except Exception as e:
        print(f"❌ Utils test failed: {e}")
        return False

def test_dashboard():
    """Test dashboard creation."""
    print("\nTesting dashboard...")
    
    try:
        from src.dashboard.dashboard import create_dashboard
        
        # Create dashboard instance
        dashboard = create_dashboard()
        print(f"✅ Dashboard created: {type(dashboard).__name__}")
        
        # Test dashboard attributes
        assert hasattr(dashboard, 'trading_bot')
        assert hasattr(dashboard, 'host')
        assert hasattr(dashboard, 'port')
        assert hasattr(dashboard, 'create_app')
        print("✅ Dashboard has required attributes")
        
        return True
        
    except Exception as e:
        print(f"❌ Dashboard test failed: {e}")
        return False

def test_example_files():
    """Test that example files exist and are not empty."""
    print("\nTesting example files...")
    
    example_files = [
        'multi_currency_example.py',
        'profit_taking_example.py',
        'test_profit_taking.py'
    ]
    
    failed_files = []
    
    for filename in example_files:
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                content = f.read()
                if len(content.strip()) > 100:  # Should have substantial content
                    print(f"✅ {filename}: {len(content)} characters")
                else:
                    print(f"❌ {filename}: Too short ({len(content)} characters)")
                    failed_files.append(filename)
        except Exception as e:
            print(f"❌ {filename}: {e}")
            failed_files.append(filename)
    
    return failed_files

def test_config_files():
    """Test configuration files."""
    print("\nTesting configuration files...")
    
    try:
        # Test Exness config
        from src.utils.helpers import load_yaml_config
        
        config = load_yaml_config('config/exness_config.yaml')
        if config:
            print(f"✅ exness_config.yaml loaded: {len(config)} sections")
        else:
            print("❌ exness_config.yaml is empty or invalid")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Config test failed: {e}")
        return False

def main():
    """Main test function."""
    print("Market Session Trading Bot - Missing Files Test")
    print("=" * 60)
    
    # Test imports
    failed_imports = test_imports()
    
    # Test utility functions
    utils_ok = test_utils_functions()
    
    # Test dashboard
    dashboard_ok = test_dashboard()
    
    # Test example files
    failed_files = test_example_files()
    
    # Test config files
    config_ok = test_config_files()
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    if failed_imports:
        print(f"❌ Import failures: {len(failed_imports)}")
        for module, error in failed_imports:
            print(f"   - {module}: {error}")
    else:
        print("✅ All imports successful")
    
    if utils_ok:
        print("✅ Utility functions working")
    else:
        print("❌ Utility functions failed")
    
    if dashboard_ok:
        print("✅ Dashboard working")
    else:
        print("❌ Dashboard failed")
    
    if failed_files:
        print(f"❌ File issues: {len(failed_files)}")
        for file in failed_files:
            print(f"   - {file}")
    else:
        print("✅ All example files OK")
    
    if config_ok:
        print("✅ Configuration files working")
    else:
        print("❌ Configuration files failed")
    
    # Overall result
    all_passed = (not failed_imports and utils_ok and dashboard_ok and 
                  not failed_files and config_ok)
    
    if all_passed:
        print("\n🎉 All tests passed! The missing files have been successfully created.")
    else:
        print("\n⚠️  Some tests failed. Please check the issues above.")
    
    return all_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 