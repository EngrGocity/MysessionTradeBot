"""
Helper utility functions for the Market Session Trading Bot.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
import pytz
import yaml
import os

logger = logging.getLogger(__name__)

def calculate_pip_value(symbol: str, lot_size: float, account_currency: str = "USD") -> float:
    """
    Calculate the pip value for a given symbol and lot size.
    
    Args:
        symbol: Currency pair symbol (e.g., "EURUSD")
        lot_size: Position size in lots
        account_currency: Account currency (default: "USD")
    
    Returns:
        Pip value in account currency
    """
    # Standard pip values for major pairs (per 0.01 lot)
    pip_values = {
        "EURUSD": 0.1, "GBPUSD": 0.1, "USDJPY": 0.1, "AUDUSD": 0.1,
        "USDCAD": 0.1, "NZDUSD": 0.1, "EURGBP": 0.1, "EURJPY": 0.1,
        "GBPJPY": 0.1, "AUDJPY": 0.1, "CADJPY": 0.1, "NZDJPY": 0.1
    }
    
    base_pip_value = pip_values.get(symbol, 0.1)
    return base_pip_value * lot_size * 100  # Convert to full lot

def format_currency(amount: float, currency: str = "USD") -> str:
    """
    Format currency amount with proper decimal places.
    
    Args:
        amount: Amount to format
        currency: Currency code
    
    Returns:
        Formatted currency string
    """
    if currency in ["JPY", "JPY"]:
        return f"{amount:.0f} {currency}"
    else:
        return f"{amount:.2f} {currency}"

def format_time(dt: datetime, timezone: str = "UTC") -> str:
    """
    Format datetime for display.
    
    Args:
        dt: Datetime object
        timezone: Timezone string
    
    Returns:
        Formatted time string
    """
    tz = pytz.timezone(timezone)
    if dt.tzinfo is None:
        dt = pytz.utc.localize(dt)
    local_dt = dt.astimezone(tz)
    return local_dt.strftime("%Y-%m-%d %H:%M:%S %Z")

def load_yaml_config(file_path: str) -> Dict[str, Any]:
    """
    Load YAML configuration file.
    
    Args:
        file_path: Path to YAML file
    
    Returns:
        Configuration dictionary
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            return yaml.safe_load(file)
    except FileNotFoundError:
        logger.error(f"Configuration file not found: {file_path}")
        return {}
    except yaml.YAMLError as e:
        logger.error(f"Error parsing YAML file {file_path}: {e}")
        return {}

def save_yaml_config(config: Dict[str, Any], file_path: str) -> bool:
    """
    Save configuration to YAML file.
    
    Args:
        config: Configuration dictionary
        file_path: Path to save the file
    
    Returns:
        True if successful, False otherwise
    """
    try:
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as file:
            yaml.dump(config, file, default_flow_style=False, indent=2)
        return True
    except Exception as e:
        logger.error(f"Error saving configuration to {file_path}: {e}")
        return False

def ensure_directory(path: str) -> bool:
    """
    Ensure directory exists, create if it doesn't.
    
    Args:
        path: Directory path
    
    Returns:
        True if successful, False otherwise
    """
    try:
        os.makedirs(path, exist_ok=True)
        return True
    except Exception as e:
        logger.error(f"Error creating directory {path}: {e}")
        return False

def get_session_time_range(session_type: str) -> Tuple[datetime, datetime]:
    """
    Get the time range for a market session.
    
    Args:
        session_type: Session type ("asian", "london", "new_york")
    
    Returns:
        Tuple of (start_time, end_time) as datetime objects
    """
    now = datetime.now(pytz.UTC)
    
    session_times = {
        "asian": ("00:00", "08:00"),
        "london": ("08:00", "16:00"),
        "new_york": ("13:00", "21:00")
    }
    
    if session_type not in session_times:
        raise ValueError(f"Invalid session type: {session_type}")
    
    start_time_str, end_time_str = session_times[session_type]
    
    # Parse times
    start_hour, start_minute = map(int, start_time_str.split(":"))
    end_hour, end_minute = map(int, end_time_str.split(":"))
    
    # Create datetime objects for today
    start_time = now.replace(hour=start_hour, minute=start_minute, second=0, microsecond=0)
    end_time = now.replace(hour=end_hour, minute=end_minute, second=0, microsecond=0)
    
    return start_time, end_time

def is_market_open(session_type: str) -> bool:
    """
    Check if a market session is currently open.
    
    Args:
        session_type: Session type ("asian", "london", "new_york")
    
    Returns:
        True if session is open, False otherwise
    """
    try:
        start_time, end_time = get_session_time_range(session_type)
        now = datetime.now(pytz.UTC)
        
        # Handle sessions that cross midnight
        if start_time > end_time:
            return now >= start_time or now <= end_time
        else:
            return start_time <= now <= end_time
    except Exception as e:
        logger.error(f"Error checking market session {session_type}: {e}")
        return False 