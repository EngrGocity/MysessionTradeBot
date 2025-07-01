#!/usr/bin/env python3
"""
Test Profit Taking Functionality

This test file validates the profit taking system's functionality,
including rule creation, position monitoring, and profit taking actions.
"""

import sys
import os
import unittest
from datetime import datetime, timedelta
import time

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.core.profit_monitor import ProfitMonitor, ProfitTakingRule
from src.core.session_manager import SessionType
from src.utils.helpers import ensure_directory

class TestProfitTaking(unittest.TestCase):
    """Test cases for profit taking functionality."""
    
    def setUp(self):
        """Set up test environment."""
        ensure_directory('logs')
        ensure_directory('data')
        
        # Create profit monitor
        self.profit_monitor = ProfitMonitor({})
        
        # Sample position data
        self.sample_positions = [
            {
                'ticket': 1,
                'symbol': 'EURUSD',
                'type': 'buy',
                'volume': 0.1,
                'price_open': 1.0850,
                'price_current': 1.0870,
                'profit': 20.0,
                'profit_pips': 20.0,
                'profit_percent': 0.2,
                'time_open': datetime.now() - timedelta(hours=1)
            },
            {
                'ticket': 2,
                'symbol': 'GBPUSD',
                'type': 'sell',
                'volume': 0.05,
                'price_open': 1.2650,
                'price_current': 1.2630,
                'profit': 10.0,
                'profit_pips': 20.0,
                'profit_percent': 0.1,
                'time_open': datetime.now() - timedelta(minutes=30)
            },
            {
                'ticket': 3,
                'symbol': 'USDJPY',
                'type': 'buy',
                'volume': 0.1,
                'price_open': 150.50,
                'price_current': 150.30,
                'profit': -20.0,
                'profit_pips': -20.0,
                'profit_percent': -0.2,
                'time_open': datetime.now() - timedelta(hours=2)
            }
        ]
    
    def test_create_basic_rule(self):
        """Test creating a basic profit taking rule."""
        rule = ProfitTakingRule(
            name="Test Rule",
            enabled=True,
            time_interval_minutes=30,
            min_profit_pips=15.0,
            profit_percentage=0.5,
            max_trades_per_interval=2
        )
        
        self.assertEqual(rule.name, "Test Rule")
        self.assertTrue(rule.enabled)
        self.assertEqual(rule.time_interval_minutes, 30)
        self.assertEqual(rule.min_profit_pips, 15.0)
        self.assertEqual(rule.profit_percentage, 0.5)
        self.assertEqual(rule.max_trades_per_interval, 2)
        self.assertIsNone(rule.session_filter)
        self.assertIsNone(rule.symbol_filter)
    
    def test_create_session_specific_rule(self):
        """Test creating a session-specific rule."""
        rule = ProfitTakingRule(
            name="London Session",
            enabled=True,
            time_interval_minutes=60,
            min_profit_pips=20.0,
            profit_percentage=0.7,
            max_trades_per_interval=1,
            session_filter=SessionType.LONDON
        )
        
        self.assertEqual(rule.session_filter, SessionType.LONDON)
        self.assertIsNone(rule.symbol_filter)
    
    def test_create_symbol_specific_rule(self):
        """Test creating a symbol-specific rule."""
        rule = ProfitTakingRule(
            name="EURUSD Rule",
            enabled=True,
            time_interval_minutes=45,
            min_profit_pips=12.0,
            profit_percentage=0.6,
            max_trades_per_interval=1,
            symbol_filter="EURUSD"
        )
        
        self.assertEqual(rule.symbol_filter, "EURUSD")
        self.assertIsNone(rule.session_filter)
    
    def test_add_rule_to_monitor(self):
        """Test adding a rule to the profit monitor."""
        rule = ProfitTakingRule(
            name="Test Rule",
            enabled=True,
            time_interval_minutes=30,
            min_profit_pips=15.0,
            profit_percentage=0.5,
            max_trades_per_interval=2
        )
        
        self.profit_monitor.add_profit_taking_rule(rule)
        rules = self.profit_monitor.get_all_rules()
        
        self.assertEqual(len(rules), 1)
        self.assertEqual(rules[0].name, "Test Rule")
    
    def test_remove_rule_from_monitor(self):
        """Test removing a rule from the profit monitor."""
        rule = ProfitTakingRule(
            name="Test Rule",
            enabled=True,
            time_interval_minutes=30,
            min_profit_pips=15.0,
            profit_percentage=0.5,
            max_trades_per_interval=2
        )
        
        self.profit_monitor.add_profit_taking_rule(rule)
        self.assertEqual(len(self.profit_monitor.get_all_rules()), 1)
        
        self.profit_monitor.remove_profit_taking_rule("Test Rule")
        self.assertEqual(len(self.profit_monitor.get_all_rules()), 0)
    
    def test_enable_disable_rule(self):
        """Test enabling and disabling rules."""
        rule = ProfitTakingRule(
            name="Test Rule",
            enabled=False,
            time_interval_minutes=30,
            min_profit_pips=15.0,
            profit_percentage=0.5,
            max_trades_per_interval=2
        )
        
        self.profit_monitor.add_profit_taking_rule(rule)
        
        # Initially disabled
        rules = self.profit_monitor.get_all_rules()
        self.assertFalse(rules[0].enabled)
        
        # Enable rule
        self.profit_monitor.enable_profit_taking_rule("Test Rule")
        rules = self.profit_monitor.get_all_rules()
        self.assertTrue(rules[0].enabled)
        
        # Disable rule
        self.profit_monitor.disable_profit_taking_rule("Test Rule")
        rules = self.profit_monitor.get_all_rules()
        self.assertFalse(rules[0].enabled)
    
    def test_rule_validation(self):
        """Test rule validation."""
        # Test invalid time interval
        with self.assertRaises(ValueError):
            ProfitTakingRule(
                name="Invalid Rule",
                enabled=True,
                time_interval_minutes=0,  # Invalid
                min_profit_pips=15.0,
                profit_percentage=0.5,
                max_trades_per_interval=2
            )
        
        # Test invalid profit percentage
        with self.assertRaises(ValueError):
            ProfitTakingRule(
                name="Invalid Rule",
                enabled=True,
                time_interval_minutes=30,
                min_profit_pips=15.0,
                profit_percentage=1.5,  # Invalid (> 1.0)
                max_trades_per_interval=2
            )
        
        # Test invalid max trades
        with self.assertRaises(ValueError):
            ProfitTakingRule(
                name="Invalid Rule",
                enabled=True,
                time_interval_minutes=30,
                min_profit_pips=15.0,
                profit_percentage=0.5,
                max_trades_per_interval=0  # Invalid
            )
    
    def test_position_profit_calculation(self):
        """Test profit calculation for positions."""
        # Test profitable position
        position = self.sample_positions[0]  # EURUSD with 20 pips profit
        profit_pips = position['profit_pips']
        profit_percent = position['profit_percent']
        
        self.assertEqual(profit_pips, 20.0)
        self.assertEqual(profit_percent, 0.2)
        
        # Test losing position
        position = self.sample_positions[2]  # USDJPY with -20 pips loss
        profit_pips = position['profit_pips']
        profit_percent = position['profit_percent']
        
        self.assertEqual(profit_pips, -20.0)
        self.assertEqual(profit_percent, -0.2)
    
    def test_rule_matching(self):
        """Test rule matching logic."""
        rule = ProfitTakingRule(
            name="Test Rule",
            enabled=True,
            time_interval_minutes=30,
            min_profit_pips=15.0,
            profit_percentage=0.5,
            max_trades_per_interval=2
        )
        
        # Test matching position (20 pips profit > 15 pips minimum)
        position = self.sample_positions[0]
        should_take_profit = rule.should_take_profit(position)
        self.assertTrue(should_take_profit)
        
        # Test non-matching position (10 pips profit < 15 pips minimum)
        position = self.sample_positions[1]
        should_take_profit = rule.should_take_profit(position)
        self.assertFalse(should_take_profit)
    
    def test_session_filtering(self):
        """Test session filtering in rules."""
        rule = ProfitTakingRule(
            name="London Session Rule",
            enabled=True,
            time_interval_minutes=30,
            min_profit_pips=15.0,
            profit_percentage=0.5,
            max_trades_per_interval=2,
            session_filter=SessionType.LONDON
        )
        
        # Test with London session
        position = self.sample_positions[0]
        should_take_profit = rule.should_take_profit(position, current_session=SessionType.LONDON)
        self.assertTrue(should_take_profit)
        
        # Test with Asian session (should not match)
        should_take_profit = rule.should_take_profit(position, current_session=SessionType.ASIAN)
        self.assertFalse(should_take_profit)
    
    def test_symbol_filtering(self):
        """Test symbol filtering in rules."""
        rule = ProfitTakingRule(
            name="EURUSD Rule",
            enabled=True,
            time_interval_minutes=30,
            min_profit_pips=15.0,
            profit_percentage=0.5,
            max_trades_per_interval=2,
            symbol_filter="EURUSD"
        )
        
        # Test with EURUSD position
        position = self.sample_positions[0]  # EURUSD
        should_take_profit = rule.should_take_profit(position)
        self.assertTrue(should_take_profit)
        
        # Test with GBPUSD position (should not match)
        position = self.sample_positions[1]  # GBPUSD
        should_take_profit = rule.should_take_profit(position)
        self.assertFalse(should_take_profit)
    
    def test_profit_taking_status(self):
        """Test profit taking status reporting."""
        # Add a rule
        rule = ProfitTakingRule(
            name="Test Rule",
            enabled=True,
            time_interval_minutes=30,
            min_profit_pips=15.0,
            profit_percentage=0.5,
            max_trades_per_interval=2
        )
        self.profit_monitor.add_profit_taking_rule(rule)
        
        # Get status
        status = self.profit_monitor.get_profit_taking_status()
        
        self.assertIn('active_rules', status)
        self.assertIn('active_positions', status)
        self.assertIn('recent_actions', status)
        
        # Check active rules
        active_rules = status['active_rules']
        self.assertEqual(len(active_rules), 1)
        self.assertEqual(active_rules[0]['name'], "Test Rule")
    
    def test_rule_statistics(self):
        """Test rule statistics tracking."""
        rule = ProfitTakingRule(
            name="Test Rule",
            enabled=True,
            time_interval_minutes=30,
            min_profit_pips=15.0,
            profit_percentage=0.5,
            max_trades_per_interval=2
        )
        self.profit_monitor.add_profit_taking_rule(rule)
        
        # Simulate some actions
        self.profit_monitor._record_rule_action("Test Rule", 25.0, True)
        self.profit_monitor._record_rule_action("Test Rule", 15.0, True)
        self.profit_monitor._record_rule_action("Test Rule", 0.0, False)  # Failed action
        
        # Get statistics
        stats = self.profit_monitor.get_rule_statistics()
        
        self.assertIn("Test Rule", stats)
        rule_stats = stats["Test Rule"]
        
        self.assertEqual(rule_stats['triggers'], 3)
        self.assertEqual(rule_stats['actions'], 2)
        self.assertEqual(rule_stats['total_profit'], 40.0)
        self.assertEqual(rule_stats['success_rate'], 2/3)
    
    def test_multiple_rules(self):
        """Test multiple rules working together."""
        # Add multiple rules
        rule1 = ProfitTakingRule(
            name="Quick Profit",
            enabled=True,
            time_interval_minutes=15,
            min_profit_pips=10.0,
            profit_percentage=0.3,
            max_trades_per_interval=3
        )
        
        rule2 = ProfitTakingRule(
            name="Medium Profit",
            enabled=True,
            time_interval_minutes=60,
            min_profit_pips=20.0,
            profit_percentage=0.7,
            max_trades_per_interval=2
        )
        
        rule3 = ProfitTakingRule(
            name="EURUSD Specific",
            enabled=True,
            time_interval_minutes=30,
            min_profit_pips=15.0,
            profit_percentage=0.5,
            max_trades_per_interval=1,
            symbol_filter="EURUSD"
        )
        
        self.profit_monitor.add_profit_taking_rule(rule1)
        self.profit_monitor.add_profit_taking_rule(rule2)
        self.profit_monitor.add_profit_taking_rule(rule3)
        
        # Check all rules are added
        rules = self.profit_monitor.get_all_rules()
        self.assertEqual(len(rules), 3)
        
        # Check rule names
        rule_names = [rule.name for rule in rules]
        self.assertIn("Quick Profit", rule_names)
        self.assertIn("Medium Profit", rule_names)
        self.assertIn("EURUSD Specific", rule_names)
    
    def test_rule_performance_tracking(self):
        """Test rule performance tracking."""
        rule = ProfitTakingRule(
            name="Performance Test",
            enabled=True,
            time_interval_minutes=30,
            min_profit_pips=15.0,
            profit_percentage=0.5,
            max_trades_per_interval=2
        )
        self.profit_monitor.add_profit_taking_rule(rule)
        
        # Simulate performance data
        self.profit_monitor._record_rule_action("Performance Test", 25.0, True)
        self.profit_monitor._record_rule_action("Performance Test", 15.0, True)
        self.profit_monitor._record_rule_action("Performance Test", 30.0, True)
        
        # Get performance
        performance = self.profit_monitor.get_rule_performance()
        
        self.assertIn("Performance Test", performance)
        rule_perf = performance["Performance Test"]
        
        self.assertEqual(rule_perf['actions'], 3)
        self.assertEqual(rule_perf['total_profit'], 70.0)
        self.assertEqual(rule_perf['avg_profit'], 70.0/3)
        self.assertEqual(rule_perf['success_rate'], 1.0)
    
    def test_profit_taking_configuration(self):
        """Test profit taking configuration loading."""
        config = {
            "enabled": True,
            "rules": [
                {
                    "name": "Config Rule",
                    "enabled": True,
                    "time_interval_minutes": 30,
                    "min_profit_pips": 15.0,
                    "profit_percentage": 0.5,
                    "max_trades_per_interval": 2
                }
            ]
        }
        
        profit_monitor = ProfitMonitor(config)
        
        # Check if rule was loaded
        rules = profit_monitor.get_all_rules()
        self.assertEqual(len(rules), 1)
        self.assertEqual(rules[0].name, "Config Rule")
        self.assertTrue(rules[0].enabled)

def run_profit_taking_tests():
    """Run all profit taking tests."""
    print("Running Profit Taking Tests...")
    print("=" * 50)
    
    # Create test suite
    suite = unittest.TestLoader().loadTestsFromTestCase(TestProfitTaking)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "=" * 50)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    
    if result.failures:
        print("\nFailures:")
        for test, traceback in result.failures:
            print(f"  {test}: {traceback}")
    
    if result.errors:
        print("\nErrors:")
        for test, traceback in result.errors:
            print(f"  {test}: {traceback}")
    
    if result.wasSuccessful():
        print("\nAll tests passed! ✅")
    else:
        print("\nSome tests failed! ❌")
    
    return result.wasSuccessful()

def main():
    """Main function."""
    print("Market Session Trading Bot - Profit Taking Tests")
    print("=" * 60)
    print("This test suite validates:")
    print("- Profit taking rule creation and validation")
    print("- Rule filtering (session, symbol)")
    print("- Position profit calculation")
    print("- Rule statistics and performance tracking")
    print("- Configuration loading")
    print("=" * 60)
    
    # Run tests
    success = run_profit_taking_tests()
    
    if success:
        print("\nAll profit taking functionality tests passed!")
    else:
        print("\nSome tests failed. Please check the output above.")

if __name__ == "__main__":
    main()
