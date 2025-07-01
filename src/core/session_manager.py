"""
Market session manager for handling different trading sessions.
"""
from typing import Dict, List, Optional, Callable
from datetime import datetime, time, timedelta
import pytz
from loguru import logger
import schedule
import time as time_module
from threading import Thread, Event

from src.core.config import SessionConfig, SessionType


class MarketSession:
    """Represents a market trading session."""
    
    def __init__(self, config: SessionConfig):
        self.config = config
        self.timezone = pytz.timezone(config.timezone)
        self.is_active = False
        self.start_time = self._parse_time(config.start_time)
        self.end_time = self._parse_time(config.end_time)
    
    def _parse_time(self, time_str: str) -> time:
        """Parse time string to time object."""
        hours, minutes = map(int, time_str.split(':'))
        return time(hours, minutes)
    
    def is_session_active(self, current_time: Optional[datetime] = None) -> bool:
        """Check if the session is currently active."""
        if current_time is None:
            current_time = datetime.now(self.timezone)
        
        current_time_local = current_time.astimezone(self.timezone).time()
        
        # Handle sessions that span midnight
        if self.start_time > self.end_time:
            return current_time_local >= self.start_time or current_time_local <= self.end_time
        else:
            return self.start_time <= current_time_local <= self.end_time
    
    def get_session_duration(self) -> timedelta:
        """Get the duration of the session."""
        start_dt = datetime.combine(datetime.today(), self.start_time)
        end_dt = datetime.combine(datetime.today(), self.end_time)
        
        if self.start_time > self.end_time:
            end_dt += timedelta(days=1)
        
        return end_dt - start_dt
    
    def get_next_session_start(self, current_time: Optional[datetime] = None) -> datetime:
        """Get the next session start time."""
        if current_time is None:
            current_time = datetime.now(self.timezone)
        
        current_time_local = current_time.astimezone(self.timezone)
        today_start = datetime.combine(current_time_local.date(), self.start_time)
        today_start = self.timezone.localize(today_start)
        
        if current_time_local.time() < self.start_time:
            return today_start
        else:
            tomorrow_start = today_start + timedelta(days=1)
            return tomorrow_start


class SessionManager:
    """Manages multiple market sessions."""
    
    def __init__(self):
        self.sessions: Dict[SessionType, MarketSession] = {}
        self.session_callbacks: Dict[SessionType, List[Callable]] = {}
        self.running = False
        self.stop_event = Event()
        self.scheduler_thread: Optional[Thread] = None
    
    def add_session(self, config: SessionConfig) -> None:
        """Add a market session."""
        session = MarketSession(config)
        self.sessions[config.session_type] = session
        
        # Schedule session start and end
        if config.enabled:
            self._schedule_session(session)
    
    def _schedule_session(self, session: MarketSession) -> None:
        """Schedule session start and end events."""
        start_time = session.start_time.strftime("%H:%M")
        end_time = session.end_time.strftime("%H:%M")
        
        # Schedule session start
        schedule.every().day.at(start_time).do(
            self._on_session_start, session.config.session_type
        )
        
        # Schedule session end
        schedule.every().day.at(end_time).do(
            self._on_session_end, session.config.session_type
        )
        
        logger.info(f"Scheduled {session.config.session_type} session: {start_time} - {end_time}")
    
    def add_session_callback(self, session_type: SessionType, callback: Callable) -> None:
        """Add a callback function for session events."""
        if session_type not in self.session_callbacks:
            self.session_callbacks[session_type] = []
        self.session_callbacks[session_type].append(callback)
    
    def _on_session_start(self, session_type: SessionType) -> None:
        """Handle session start event."""
        logger.info(f"Session started: {session_type}")
        
        if session_type in self.sessions:
            self.sessions[session_type].is_active = True
        
        # Execute callbacks
        if session_type in self.session_callbacks:
            for callback in self.session_callbacks[session_type]:
                try:
                    callback(session_type, "start")
                except Exception as e:
                    logger.error(f"Error in session start callback: {e}")
    
    def _on_session_end(self, session_type: SessionType) -> None:
        """Handle session end event."""
        logger.info(f"Session ended: {session_type}")
        
        if session_type in self.sessions:
            self.sessions[session_type].is_active = False
        
        # Execute callbacks
        if session_type in self.session_callbacks:
            for callback in self.session_callbacks[session_type]:
                try:
                    callback(session_type, "end")
                except Exception as e:
                    logger.error(f"Error in session end callback: {e}")
    
    def get_active_sessions(self) -> List[SessionType]:
        """Get currently active sessions."""
        active_sessions = []
        current_time = datetime.now()
        
        for session_type, session in self.sessions.items():
            if session.is_session_active(current_time):
                active_sessions.append(session_type)
        
        return active_sessions
    
    def is_session_active(self, session_type: SessionType) -> bool:
        """Check if a specific session is active."""
        if session_type not in self.sessions:
            return False
        
        return self.sessions[session_type].is_session_active()
    
    def get_session_info(self, session_type: SessionType) -> Optional[Dict]:
        """Get information about a specific session."""
        if session_type not in self.sessions:
            return None
        
        session = self.sessions[session_type]
        current_time = datetime.now()
        
        return {
            'type': session_type,
            'is_active': session.is_session_active(current_time),
            'start_time': session.start_time.strftime("%H:%M"),
            'end_time': session.end_time.strftime("%H:%M"),
            'timezone': session.config.timezone,
            'duration': str(session.get_session_duration()),
            'next_start': session.get_next_session_start(current_time).isoformat(),
        }
    
    def get_all_sessions_info(self) -> Dict[SessionType, Dict]:
        """Get information about all sessions."""
        return {
            session_type: self.get_session_info(session_type)
            for session_type in self.sessions.keys()
        }
    
    def start(self) -> None:
        """Start the session manager."""
        if self.running:
            logger.warning("Session manager is already running")
            return
        
        self.running = True
        self.stop_event.clear()
        
        # Start scheduler thread
        self.scheduler_thread = Thread(target=self._run_scheduler, daemon=True)
        self.scheduler_thread.start()
        
        logger.info("Session manager started")
    
    def stop(self) -> None:
        """Stop the session manager."""
        if not self.running:
            return
        
        self.running = False
        self.stop_event.set()
        
        if self.scheduler_thread:
            self.scheduler_thread.join(timeout=5)
        
        logger.info("Session manager stopped")
    
    def _run_scheduler(self) -> None:
        """Run the scheduler loop."""
        while self.running and not self.stop_event.is_set():
            try:
                schedule.run_pending()
                time_module.sleep(1)
            except Exception as e:
                logger.error(f"Error in scheduler: {e}")
                time_module.sleep(5)
    
    def get_session_overlap(self) -> List[SessionType]:
        """Get sessions that are currently overlapping."""
        active_sessions = self.get_active_sessions()
        if len(active_sessions) > 1:
            return active_sessions
        return []
    
    def get_session_volatility_profile(self, session_type: SessionType) -> Dict[str, float]:
        """Get typical volatility profile for a session."""
        volatility_profiles = {
            SessionType.ASIAN: {
                'low_volatility': 0.7,
                'medium_volatility': 0.2,
                'high_volatility': 0.1
            },
            SessionType.LONDON: {
                'low_volatility': 0.2,
                'medium_volatility': 0.5,
                'high_volatility': 0.3
            },
            SessionType.NEW_YORK: {
                'low_volatility': 0.1,
                'medium_volatility': 0.4,
                'high_volatility': 0.5
            }
        }
        
        return volatility_profiles.get(session_type, {
            'low_volatility': 0.33,
            'medium_volatility': 0.34,
            'high_volatility': 0.33
        }) 