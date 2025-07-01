"""
Formatting utility functions for the Market Session Trading Bot.
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import json

logger = logging.getLogger(__name__)

def format_trade_summary(trade_data: Dict[str, Any]) -> str:
    """
    Format trade summary for display.
    
    Args:
        trade_data: Trade data dictionary
    
    Returns:
        Formatted trade summary string
    """
    try:
        symbol = trade_data.get('symbol', 'Unknown')
        type_str = trade_data.get('type', 'Unknown')
        volume = trade_data.get('volume', 0)
        open_price = trade_data.get('price_open', 0)
        close_price = trade_data.get('price_close', 0)
        profit = trade_data.get('profit', 0)
        
        summary = f"{symbol} {type_str.upper()} {volume:.2f} lots"
        if open_price:
            summary += f" @ {open_price:.5f}"
        if close_price:
            summary += f" -> {close_price:.5f}"
        if profit is not None:
            summary += f" (P&L: {profit:.2f})"
        
        return summary
    except Exception as e:
        logger.error(f"Error formatting trade summary: {e}")
        return "Trade summary unavailable"

def format_performance_metrics(metrics: Dict[str, Any]) -> str:
    """
    Format performance metrics for display.
    
    Args:
        metrics: Performance metrics dictionary
    
    Returns:
        Formatted metrics string
    """
    try:
        lines = []
        
        # Basic metrics
        if 'total_trades' in metrics:
            lines.append(f"Total Trades: {metrics['total_trades']}")
        
        if 'win_rate' in metrics:
            win_rate = metrics['win_rate'] * 100
            lines.append(f"Win Rate: {win_rate:.1f}%")
        
        if 'profit_factor' in metrics:
            lines.append(f"Profit Factor: {metrics['profit_factor']:.2f}")
        
        if 'total_profit' in metrics:
            lines.append(f"Total Profit: {metrics['total_profit']:.2f}")
        
        # Risk metrics
        if 'sharpe_ratio' in metrics:
            lines.append(f"Sharpe Ratio: {metrics['sharpe_ratio']:.2f}")
        
        if 'max_drawdown' in metrics:
            lines.append(f"Max Drawdown: {metrics['max_drawdown']:.2f}%")
        
        if 'var_95' in metrics:
            lines.append(f"VaR (95%): {metrics['var_95']:.2f}")
        
        return "\n".join(lines)
    except Exception as e:
        logger.error(f"Error formatting performance metrics: {e}")
        return "Performance metrics unavailable"

def format_session_performance(session_data: Dict[str, Any]) -> str:
    """
    Format session performance for display.
    
    Args:
        session_data: Session performance data
    
    Returns:
        Formatted session performance string
    """
    try:
        lines = []
        
        for session_type, data in session_data.items():
            if isinstance(data, dict):
                profit = data.get('profit', 0)
                trades = data.get('trades', 0)
                win_rate = data.get('win_rate', 0) * 100
                
                lines.append(f"{session_type.title()}: {trades} trades, "
                           f"{profit:.2f} profit, {win_rate:.1f}% win rate")
        
        return "\n".join(lines) if lines else "No session data available"
    except Exception as e:
        logger.error(f"Error formatting session performance: {e}")
        return "Session performance unavailable"

def format_currency_pair_performance(pair_data: Dict[str, Any]) -> str:
    """
    Format currency pair performance for display.
    
    Args:
        pair_data: Currency pair performance data
    
    Returns:
        Formatted pair performance string
    """
    try:
        lines = []
        
        for pair, data in pair_data.items():
            if isinstance(data, dict):
                profit = data.get('profit', 0)
                trades = data.get('trades', 0)
                win_rate = data.get('win_rate', 0) * 100
                
                lines.append(f"{pair}: {trades} trades, "
                           f"{profit:.2f} profit, {win_rate:.1f}% win rate")
        
        return "\n".join(lines) if lines else "No pair data available"
    except Exception as e:
        logger.error(f"Error formatting currency pair performance: {e}")
        return "Currency pair performance unavailable"

def format_correlation_matrix(correlation_data: Dict[str, Dict[str, float]]) -> str:
    """
    Format correlation matrix for display.
    
    Args:
        correlation_data: Correlation matrix data
    
    Returns:
        Formatted correlation matrix string
    """
    try:
        if not correlation_data:
            return "No correlation data available"
        
        # Get all pairs
        pairs = list(correlation_data.keys())
        if not pairs:
            return "No correlation data available"
        
        # Create header
        header = "Pair".ljust(10)
        for pair in pairs:
            header += f"{pair}".rjust(8)
        lines = [header]
        lines.append("-" * len(header))
        
        # Create matrix rows
        for pair1 in pairs:
            row = pair1.ljust(10)
            for pair2 in pairs:
                if pair1 == pair2:
                    correlation = 1.0
                else:
                    correlation = correlation_data.get(pair1, {}).get(pair2, 0.0)
                row += f"{correlation:8.3f}"
            lines.append(row)
        
        return "\n".join(lines)
    except Exception as e:
        logger.error(f"Error formatting correlation matrix: {e}")
        return "Correlation matrix unavailable"

def format_risk_report(risk_data: Dict[str, Any]) -> str:
    """
    Format risk report for display.
    
    Args:
        risk_data: Risk data dictionary
    
    Returns:
        Formatted risk report string
    """
    try:
        lines = []
        
        # Current risk metrics
        if 'current_drawdown' in risk_data:
            lines.append(f"Current Drawdown: {risk_data['current_drawdown']:.2f}%")
        
        if 'daily_loss' in risk_data:
            lines.append(f"Daily Loss: {risk_data['daily_loss']:.2f}")
        
        if 'open_positions' in risk_data:
            lines.append(f"Open Positions: {risk_data['open_positions']}")
        
        if 'total_exposure' in risk_data:
            lines.append(f"Total Exposure: {risk_data['total_exposure']:.2f}%")
        
        # Risk limits
        if 'max_daily_loss_limit' in risk_data:
            lines.append(f"Daily Loss Limit: {risk_data['max_daily_loss_limit']:.2f}%")
        
        if 'max_position_size_limit' in risk_data:
            lines.append(f"Position Size Limit: {risk_data['max_position_size_limit']:.2f}%")
        
        # Risk alerts
        if 'risk_alerts' in risk_data and risk_data['risk_alerts']:
            lines.append("\nRisk Alerts:")
            for alert in risk_data['risk_alerts']:
                lines.append(f"  - {alert}")
        
        return "\n".join(lines) if lines else "No risk data available"
    except Exception as e:
        logger.error(f"Error formatting risk report: {e}")
        return "Risk report unavailable"

def format_profit_taking_status(profit_data: Dict[str, Any]) -> str:
    """
    Format profit taking status for display.
    
    Args:
        profit_data: Profit taking data
    
    Returns:
        Formatted profit taking status string
    """
    try:
        lines = []
        
        # Active rules
        if 'active_rules' in profit_data:
            lines.append("Active Profit Taking Rules:")
            for rule in profit_data['active_rules']:
                name = rule.get('name', 'Unknown')
                enabled = "Enabled" if rule.get('enabled', False) else "Disabled"
                lines.append(f"  - {name}: {enabled}")
        
        # Active positions
        if 'active_positions' in profit_data:
            lines.append("\nPositions with Profit Potential:")
            for position in profit_data['active_positions']:
                symbol = position.get('symbol', 'Unknown')
                profit_pips = position.get('profit_pips', 0)
                profit_percent = position.get('profit_percent', 0)
                lines.append(f"  - {symbol}: {profit_pips:.1f} pips ({profit_percent:.1f}%)")
        
        # Recent profit taking actions
        if 'recent_actions' in profit_data:
            lines.append("\nRecent Profit Taking Actions:")
            for action in profit_data['recent_actions']:
                symbol = action.get('symbol', 'Unknown')
                action_type = action.get('action', 'Unknown')
                profit = action.get('profit', 0)
                time = action.get('time', 'Unknown')
                lines.append(f"  - {time}: {symbol} {action_type} (Profit: {profit:.2f})")
        
        return "\n".join(lines) if lines else "No profit taking data available"
    except Exception as e:
        logger.error(f"Error formatting profit taking status: {e}")
        return "Profit taking status unavailable"

def format_json_pretty(data: Any) -> str:
    """
    Format data as pretty JSON string.
    
    Args:
        data: Data to format
    
    Returns:
        Pretty formatted JSON string
    """
    try:
        return json.dumps(data, indent=2, default=str)
    except Exception as e:
        logger.error(f"Error formatting JSON: {e}")
        return str(data)

def format_timestamp(timestamp: datetime) -> str:
    """
    Format timestamp for display.
    
    Args:
        timestamp: Datetime object
    
    Returns:
        Formatted timestamp string
    """
    try:
        return timestamp.strftime("%Y-%m-%d %H:%M:%S")
    except Exception as e:
        logger.error(f"Error formatting timestamp: {e}")
        return str(timestamp)

def format_duration(duration: timedelta) -> str:
    """
    Format duration for display.
    
    Args:
        duration: Timedelta object
    
    Returns:
        Formatted duration string
    """
    try:
        total_seconds = int(duration.total_seconds())
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        
        if hours > 0:
            return f"{hours}h {minutes}m {seconds}s"
        elif minutes > 0:
            return f"{minutes}m {seconds}s"
        else:
            return f"{seconds}s"
    except Exception as e:
        logger.error(f"Error formatting duration: {e}")
        return str(duration) 