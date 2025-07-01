"""
Configuration management for the trading bot.
"""
from typing import Dict, List, Optional, Union
from pydantic import BaseModel, Field, validator
from enum import Enum
import os
from dotenv import load_dotenv

load_dotenv()


class SessionType(str, Enum):
    """Market session types."""
    ASIAN = "asian"
    LONDON = "london"
    NEW_YORK = "new_york"
    OVERLAP = "overlap"


class TimeFrame(str, Enum):
    """MT5 timeframes."""
    M1 = "M1"
    M5 = "M5"
    M15 = "M15"
    M30 = "M30"
    H1 = "H1"
    H4 = "H4"
    D1 = "D1"


class OrderType(str, Enum):
    """Order types."""
    BUY = "BUY"
    SELL = "SELL"
    BUY_LIMIT = "BUY_LIMIT"
    SELL_LIMIT = "SELL_LIMIT"
    BUY_STOP = "BUY_STOP"
    SELL_STOP = "SELL_STOP"


class BrokerConfig(BaseModel):
    """Broker configuration."""
    name: str
    server: str
    login: int
    password: str
    timeout: int = 60000
    enable_real_trading: bool = False
    
    class Config:
        env_prefix = "BROKER_"


class SessionConfig(BaseModel):
    """Market session configuration."""
    session_type: SessionType
    start_time: str  # Format: "HH:MM"
    end_time: str    # Format: "HH:MM"
    timezone: str = "UTC"
    enabled: bool = True
    
    @validator('start_time', 'end_time')
    def validate_time_format(cls, v):
        try:
            hours, minutes = map(int, v.split(':'))
            if not (0 <= hours <= 23 and 0 <= minutes <= 59):
                raise ValueError
        except ValueError:
            raise ValueError('Time must be in HH:MM format')
        return v


class RiskConfig(BaseModel):
    """Risk management configuration."""
    max_position_size: float = 0.02  # 2% of account
    max_daily_loss: float = 0.05     # 5% of account
    max_open_positions: int = 5
    stop_loss_pips: float = 50.0
    take_profit_pips: float = 100.0
    trailing_stop: bool = False
    trailing_stop_pips: float = 20.0


class StrategyConfig(BaseModel):
    """Strategy configuration."""
    name: str
    enabled: bool = True
    symbols: List[str] = Field(default_factory=list)
    timeframe: TimeFrame = TimeFrame.H1
    parameters: Dict[str, Union[str, int, float, bool]] = Field(default_factory=dict)


class TradingBotConfig(BaseModel):
    """Main trading bot configuration."""
    broker: BrokerConfig
    sessions: List[SessionConfig]
    risk: RiskConfig
    strategies: List[StrategyConfig]
    symbols: List[str] = Field(default_factory=list)
    data_path: str = "data"
    logs_path: str = "logs"
    enable_dashboard: bool = True
    dashboard_port: int = 8050
    enable_notifications: bool = False
    
    @classmethod
    def from_env(cls):
        """Load configuration from environment variables."""
        return cls(
            broker=BrokerConfig(
                name=os.getenv("BROKER_NAME", "Demo"),
                server=os.getenv("BROKER_SERVER", ""),
                login=int(os.getenv("BROKER_LOGIN", "0")),
                password=os.getenv("BROKER_PASSWORD", ""),
                enable_real_trading=os.getenv("BROKER_ENABLE_REAL_TRADING", "false").lower() == "true"
            ),
            sessions=[
                SessionConfig(
                    session_type=SessionType.ASIAN,
                    start_time="00:00",
                    end_time="08:00",
                    enabled=True
                ),
                SessionConfig(
                    session_type=SessionType.LONDON,
                    start_time="08:00",
                    end_time="16:00",
                    enabled=True
                ),
                SessionConfig(
                    session_type=SessionType.NEW_YORK,
                    start_time="13:00",
                    end_time="21:00",
                    enabled=True
                )
            ],
            risk=RiskConfig(),
            strategies=[],
            symbols=["EURUSD", "GBPUSD", "USDJPY", "AUDUSD"]
        ) 