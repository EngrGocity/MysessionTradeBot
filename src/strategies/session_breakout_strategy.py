"""
Session-based breakout strategy for trading breakouts during market sessions.
"""
import pandas as pd
import numpy as np
from typing import Dict, Any
from loguru import logger

from src.strategies.base_strategy import BaseStrategy
from src.core.config import SessionType, TimeFrame


class SessionBreakoutStrategy(BaseStrategy):
    """Session-based breakout strategy."""
    
    def __init__(self, config, broker, risk_manager, session_manager):
        super().__init__(config, broker, risk_manager, session_manager)
        
        # Strategy parameters with defaults
        self.breakout_period = self.parameters.get('breakout_period', 20)
        self.breakout_multiplier = self.parameters.get('breakout_multiplier', 1.5)
        self.atr_period = self.parameters.get('atr_period', 14)
        self.min_volume = self.parameters.get('min_volume', 0.01)
        self.max_volume = self.parameters.get('max_volume', 1.0)
        
        # Session-specific parameters
        self.session_configs = {
            SessionType.ASIAN: {
                'enabled': True,
                'breakout_multiplier': 1.2,  # Lower volatility
                'min_atr': 0.0005,
                'max_atr': 0.0020,
            },
            SessionType.LONDON: {
                'enabled': True,
                'breakout_multiplier': 1.5,  # Medium volatility
                'min_atr': 0.0008,
                'max_atr': 0.0030,
            },
            SessionType.NEW_YORK: {
                'enabled': True,
                'breakout_multiplier': 1.8,  # Higher volatility
                'min_atr': 0.0010,
                'max_atr': 0.0040,
            }
        }
    
    def calculate_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """Calculate technical indicators for breakout strategy."""
        if data.empty:
            return data
        
        try:
            df = data.copy()
            
            # Calculate ATR (Average True Range)
            df['high_low'] = df['high'] - df['low']
            df['high_close'] = np.abs(df['high'] - df['close'].shift())
            df['low_close'] = np.abs(df['low'] - df['close'].shift())
            df['true_range'] = df[['high_low', 'high_close', 'low_close']].max(axis=1)
            df['atr'] = df['true_range'].rolling(window=self.atr_period).mean()
            
            # Calculate session highs and lows
            df['session_high'] = df['high'].rolling(window=self.breakout_period).max()
            df['session_low'] = df['low'].rolling(window=self.breakout_period).min()
            
            # Calculate breakout levels
            df['upper_breakout'] = df['session_high'] + (df['atr'] * self.breakout_multiplier)
            df['lower_breakout'] = df['session_low'] - (df['atr'] * self.breakout_multiplier)
            
            # Calculate volume indicators
            df['volume_sma'] = df['tick_volume'].rolling(window=20).mean()
            df['volume_ratio'] = df['tick_volume'] / df['volume_sma']
            
            # Calculate momentum indicators
            df['price_change'] = df['close'].pct_change()
            df['momentum'] = df['price_change'].rolling(window=5).sum()
            
            # Calculate volatility
            df['volatility'] = df['price_change'].rolling(window=10).std()
            
            return df
            
        except Exception as e:
            logger.error(f"Error calculating indicators: {e}")
            return pd.DataFrame()
    
    def generate_signals(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Generate trading signals based on breakout analysis."""
        if data.empty or len(data) < self.breakout_period:
            return {'signal': 'NO_SIGNAL', 'reason': 'Insufficient data'}
        
        try:
            # Get latest data
            latest = data.iloc[-1]
            previous = data.iloc[-2] if len(data) > 1 else latest
            
            # Get current session
            active_sessions = self.session_manager.get_active_sessions()
            if not active_sessions:
                return {'signal': 'NO_SESSION', 'reason': 'No active sessions'}
            
            current_session = active_sessions[0]  # Use first active session
            session_config = self.session_configs.get(current_session, {})
            
            if not session_config.get('enabled', True):
                return {'signal': 'SESSION_DISABLED', 'reason': f'{current_session} session disabled'}
            
            # Check ATR conditions
            atr = latest['atr']
            min_atr = session_config.get('min_atr', 0.0005)
            max_atr = session_config.get('max_atr', 0.0030)
            
            if atr < min_atr or atr > max_atr:
                return {'signal': 'ATR_OUT_OF_RANGE', 'reason': f'ATR {atr:.6f} outside range'}
            
            # Check volume conditions
            volume_ratio = latest['volume_ratio']
            if volume_ratio < 1.2:  # Require above-average volume
                return {'signal': 'LOW_VOLUME', 'reason': f'Volume ratio {volume_ratio:.2f} too low'}
            
            # Check for breakout signals
            current_price = latest['close']
            upper_breakout = latest['upper_breakout']
            lower_breakout = latest['lower_breakout']
            
            # Bullish breakout
            if (current_price > upper_breakout and 
                previous['close'] <= previous['upper_breakout'] and
                latest['momentum'] > 0):
                
                # Calculate position size and risk
                stop_loss_pips = atr * 2  # 2x ATR for stop loss
                take_profit_pips = atr * 3  # 3x ATR for take profit
                
                return {
                    'signal': 'BUY',
                    'reason': 'Bullish breakout',
                    'price': current_price,
                    'stop_loss_pips': stop_loss_pips,
                    'take_profit_pips': take_profit_pips,
                    'confidence': min(volume_ratio / 2, 0.9),
                    'session': current_session,
                    'atr': atr,
                    'volume_ratio': volume_ratio
                }
            
            # Bearish breakout
            elif (current_price < lower_breakout and 
                  previous['close'] >= previous['lower_breakout'] and
                  latest['momentum'] < 0):
                
                # Calculate position size and risk
                stop_loss_pips = atr * 2  # 2x ATR for stop loss
                take_profit_pips = atr * 3  # 3x ATR for take profit
                
                return {
                    'signal': 'SELL',
                    'reason': 'Bearish breakout',
                    'price': current_price,
                    'stop_loss_pips': stop_loss_pips,
                    'take_profit_pips': take_profit_pips,
                    'confidence': min(volume_ratio / 2, 0.9),
                    'session': current_session,
                    'atr': atr,
                    'volume_ratio': volume_ratio
                }
            
            return {'signal': 'NO_BREAKOUT', 'reason': 'No breakout detected'}
            
        except Exception as e:
            logger.error(f"Error generating signals: {e}")
            return {'signal': 'ERROR', 'reason': str(e)}
    
    def should_trade(self, symbol: str, session_type: SessionType) -> bool:
        """Check if the strategy should trade in the current session."""
        session_config = self.session_configs.get(session_type, {})
        
        if not session_config.get('enabled', True):
            return False
        
        # Check if symbol is suitable for the session
        if session_type == SessionType.ASIAN:
            # Asian session: prefer JPY pairs and AUD pairs
            asian_pairs = ['USDJPY', 'EURJPY', 'GBPJPY', 'AUDUSD', 'AUDJPY', 'NZDUSD']
            return symbol in asian_pairs
        
        elif session_type == SessionType.LONDON:
            # London session: prefer EUR and GBP pairs
            london_pairs = ['EURUSD', 'GBPUSD', 'EURGBP', 'GBPEUR', 'EURCHF', 'GBPCHF']
            return symbol in london_pairs
        
        elif session_type == SessionType.NEW_YORK:
            # New York session: prefer USD pairs
            ny_pairs = ['EURUSD', 'GBPUSD', 'USDJPY', 'USDCHF', 'USDCAD', 'AUDUSD']
            return symbol in ny_pairs
        
        return True
    
    def get_strategy_info(self) -> Dict[str, Any]:
        """Get detailed strategy information."""
        return {
            'name': 'Session Breakout Strategy',
            'description': 'Trades breakouts during specific market sessions with session-specific parameters',
            'parameters': {
                'breakout_period': self.breakout_period,
                'breakout_multiplier': self.breakout_multiplier,
                'atr_period': self.atr_period,
                'session_configs': self.session_configs
            },
            'suitable_sessions': list(self.session_configs.keys()),
            'indicators': ['ATR', 'Session High/Low', 'Volume Ratio', 'Momentum', 'Volatility'],
            'signal_types': ['BUY', 'SELL'],
            'risk_management': 'ATR-based stop loss and take profit'
        } 