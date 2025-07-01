"""
Technical indicators for trading strategies.
"""
import pandas as pd
import numpy as np
import ta
from loguru import logger


class TechnicalIndicators:
    """Technical indicators collection."""
    
    @staticmethod
    def add_all_indicators(data: pd.DataFrame) -> pd.DataFrame:
        """Add all technical indicators to the dataframe."""
        df = data.copy()
        
        # Trend indicators
        df = TechnicalIndicators.add_moving_averages(df)
        df = TechnicalIndicators.add_bollinger_bands(df)
        df = TechnicalIndicators.add_rsi(df)
        df = TechnicalIndicators.add_macd(df)
        df = TechnicalIndicators.add_atr(df)
        
        return df
    
    @staticmethod
    def add_moving_averages(df: pd.DataFrame) -> pd.DataFrame:
        """Add moving averages."""
        try:
            df['sma_20'] = ta.trend.sma_indicator(df['close'], window=20)
            df['sma_50'] = ta.trend.sma_indicator(df['close'], window=50)
            df['ema_12'] = ta.trend.ema_indicator(df['close'], window=12)
            df['ema_26'] = ta.trend.ema_indicator(df['close'], window=26)
            
            # Crossovers
            df['sma_cross'] = np.where(df['sma_20'] > df['sma_50'], 1, -1)
            df['ema_cross'] = np.where(df['ema_12'] > df['ema_26'], 1, -1)
            
        except Exception as e:
            logger.error(f"Error adding moving averages: {e}")
        
        return df
    
    @staticmethod
    def add_bollinger_bands(df: pd.DataFrame) -> pd.DataFrame:
        """Add Bollinger Bands."""
        try:
            bb = ta.volatility.BollingerBands(df['close'], window=20, window_dev=2)
            df['bb_upper'] = bb.bollinger_hband()
            df['bb_middle'] = bb.bollinger_mavg()
            df['bb_lower'] = bb.bollinger_lband()
            df['bb_width'] = bb.bollinger_wband()
            
        except Exception as e:
            logger.error(f"Error adding Bollinger Bands: {e}")
        
        return df
    
    @staticmethod
    def add_rsi(df: pd.DataFrame) -> pd.DataFrame:
        """Add RSI indicator."""
        try:
            df['rsi'] = ta.momentum.rsi(df['close'], window=14)
            df['rsi_overbought'] = df['rsi'] > 70
            df['rsi_oversold'] = df['rsi'] < 30
            
        except Exception as e:
            logger.error(f"Error adding RSI: {e}")
        
        return df
    
    @staticmethod
    def add_macd(df: pd.DataFrame) -> pd.DataFrame:
        """Add MACD indicator."""
        try:
            macd = ta.trend.MACD(df['close'])
            df['macd'] = macd.macd()
            df['macd_signal'] = macd.macd_signal()
            df['macd_histogram'] = macd.macd_diff()
            
        except Exception as e:
            logger.error(f"Error adding MACD: {e}")
        
        return df
    
    @staticmethod
    def add_atr(df: pd.DataFrame) -> pd.DataFrame:
        """Add Average True Range."""
        try:
            df['atr'] = ta.volatility.average_true_range(df['high'], df['low'], df['close'], window=14)
            
        except Exception as e:
            logger.error(f"Error adding ATR: {e}")
        
        return df 