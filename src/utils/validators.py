"""
Validation utility functions for the Market Session Trading Bot.
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
import re

logger = logging.getLogger(__name__)

def validate_config(config: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Validate configuration dictionary.
    
    Args:
        config: Configuration dictionary
    
    Returns:
        Tuple of (is_valid, error_messages)
    """
    errors = []
    
    # Check required top-level keys
    required_keys = ["broker", "sessions", "risk", "strategies"]
    for key in required_keys:
        if key not in config:
            errors.append(f"Missing required configuration key: {key}")
    
    if errors:
        return False, errors
    
    # Validate broker configuration
    broker_errors = validate_broker_config(config.get("broker", {}))
    errors.extend(broker_errors)
    
    # Validate sessions configuration
    session_errors = validate_sessions_config(config.get("sessions", []))
    errors.extend(session_errors)
    
    # Validate risk configuration
    risk_errors = validate_risk_config(config.get("risk", {}))
    errors.extend(risk_errors)
    
    # Validate strategies configuration
    strategy_errors = validate_strategies_config(config.get("strategies", []))
    errors.extend(strategy_errors)
    
    return len(errors) == 0, errors

def validate_broker_config(broker_config: Dict[str, Any]) -> List[str]:
    """
    Validate broker configuration.
    
    Args:
        broker_config: Broker configuration dictionary
    
    Returns:
        List of error messages
    """
    errors = []
    
    required_fields = ["name", "server", "login", "password"]
    for field in required_fields:
        if field not in broker_config:
            errors.append(f"Missing broker field: {field}")
    
    if "timeout" in broker_config:
        timeout = broker_config["timeout"]
        if not isinstance(timeout, (int, float)) or timeout <= 0:
            errors.append("Broker timeout must be a positive number")
    
    if "enable_real_trading" in broker_config:
        if not isinstance(broker_config["enable_real_trading"], bool):
            errors.append("enable_real_trading must be a boolean")
    
    return errors

def validate_sessions_config(sessions_config: List[Dict[str, Any]]) -> List[str]:
    """
    Validate sessions configuration.
    
    Args:
        sessions_config: Sessions configuration list
    
    Returns:
        List of error messages
    """
    errors = []
    
    if not isinstance(sessions_config, list):
        errors.append("Sessions configuration must be a list")
        return errors
    
    valid_session_types = ["asian", "london", "new_york"]
    
    for i, session in enumerate(sessions_config):
        if not isinstance(session, dict):
            errors.append(f"Session {i} must be a dictionary")
            continue
        
        # Check required fields
        required_fields = ["session_type", "start_time", "end_time", "timezone"]
        for field in required_fields:
            if field not in session:
                errors.append(f"Session {i} missing field: {field}")
        
        # Validate session type
        if "session_type" in session:
            if session["session_type"] not in valid_session_types:
                errors.append(f"Session {i} invalid session_type: {session['session_type']}")
        
        # Validate time format
        for time_field in ["start_time", "end_time"]:
            if time_field in session:
                if not validate_time_format(session[time_field]):
                    errors.append(f"Session {i} invalid {time_field} format: {session[time_field]}")
        
        # Validate timezone
        if "timezone" in session:
            if not validate_timezone(session["timezone"]):
                errors.append(f"Session {i} invalid timezone: {session['timezone']}")
    
    return errors

def validate_risk_config(risk_config: Dict[str, Any]) -> List[str]:
    """
    Validate risk configuration.
    
    Args:
        risk_config: Risk configuration dictionary
    
    Returns:
        List of error messages
    """
    errors = []
    
    # Validate position size
    if "max_position_size" in risk_config:
        size = risk_config["max_position_size"]
        if not isinstance(size, (int, float)) or size <= 0 or size > 1:
            errors.append("max_position_size must be between 0 and 1")
    
    # Validate daily loss limit
    if "max_daily_loss" in risk_config:
        loss = risk_config["max_daily_loss"]
        if not isinstance(loss, (int, float)) or loss <= 0 or loss > 1:
            errors.append("max_daily_loss must be between 0 and 1")
    
    # Validate max open positions
    if "max_open_positions" in risk_config:
        positions = risk_config["max_open_positions"]
        if not isinstance(positions, int) or positions <= 0:
            errors.append("max_open_positions must be a positive integer")
    
    # Validate stop loss and take profit
    for field in ["stop_loss_pips", "take_profit_pips", "trailing_stop_pips"]:
        if field in risk_config:
            value = risk_config[field]
            if not isinstance(value, (int, float)) or value <= 0:
                errors.append(f"{field} must be a positive number")
    
    # Validate trailing stop boolean
    if "trailing_stop" in risk_config:
        if not isinstance(risk_config["trailing_stop"], bool):
            errors.append("trailing_stop must be a boolean")
    
    return errors

def validate_strategies_config(strategies_config: List[Dict[str, Any]]) -> List[str]:
    """
    Validate strategies configuration.
    
    Args:
        strategies_config: Strategies configuration list
    
    Returns:
        List of error messages
    """
    errors = []
    
    if not isinstance(strategies_config, list):
        errors.append("Strategies configuration must be a list")
        return errors
    
    for i, strategy in enumerate(strategies_config):
        if not isinstance(strategy, dict):
            errors.append(f"Strategy {i} must be a dictionary")
            continue
        
        # Check required fields
        required_fields = ["name", "enabled"]
        for field in required_fields:
            if field not in strategy:
                errors.append(f"Strategy {i} missing field: {field}")
        
        # Validate enabled field
        if "enabled" in strategy:
            if not isinstance(strategy["enabled"], bool):
                errors.append(f"Strategy {i} enabled must be a boolean")
        
        # Validate symbols if present
        if "symbols" in strategy:
            if not isinstance(strategy["symbols"], list):
                errors.append(f"Strategy {i} symbols must be a list")
            else:
                for symbol in strategy["symbols"]:
                    if not validate_symbol(symbol):
                        errors.append(f"Strategy {i} invalid symbol: {symbol}")
    
    return errors

def validate_time_format(time_str: str) -> bool:
    """
    Validate time format (HH:MM).
    
    Args:
        time_str: Time string to validate
    
    Returns:
        True if valid, False otherwise
    """
    pattern = r'^([01]?[0-9]|2[0-3]):[0-5][0-9]$'
    return bool(re.match(pattern, time_str))

def validate_timezone(timezone_str: str) -> bool:
    """
    Validate timezone string.
    
    Args:
        timezone_str: Timezone string to validate
    
    Returns:
        True if valid, False otherwise
    """
    try:
        import pytz
        pytz.timezone(timezone_str)
        return True
    except pytz.exceptions.UnknownTimeZoneError:
        return False

def validate_symbol(symbol: str) -> bool:
    """
    Validate currency pair symbol.
    
    Args:
        symbol: Symbol to validate
    
    Returns:
        True if valid, False otherwise
    """
    # Basic validation for currency pairs
    pattern = r'^[A-Z]{6}$'
    return bool(re.match(pattern, symbol))

def validate_lot_size(lot_size: float) -> bool:
    """
    Validate lot size.
    
    Args:
        lot_size: Lot size to validate
    
    Returns:
        True if valid, False otherwise
    """
    return isinstance(lot_size, (int, float)) and lot_size > 0 and lot_size <= 100

def validate_pip_value(pip_value: float) -> bool:
    """
    Validate pip value.
    
    Args:
        pip_value: Pip value to validate
    
    Returns:
        True if valid, False otherwise
    """
    return isinstance(pip_value, (int, float)) and pip_value >= 0 