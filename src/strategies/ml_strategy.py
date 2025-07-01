"""
Machine Learning-based trading strategy.
"""
import pandas as pd
import numpy as np
from typing import Dict, Any, List
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from loguru import logger
import joblib
import os

from src.strategies.base_strategy import BaseStrategy
from src.core.config import SessionType, TimeFrame
from src.indicators.technical_indicators import TechnicalIndicators


class MLStrategy(BaseStrategy):
    """Machine Learning-based trading strategy."""
    
    def __init__(self, config, broker, risk_manager, session_manager):
        super().__init__(config, broker, risk_manager, session_manager)
        
        # ML parameters
        self.lookback_period = self.parameters.get('lookback_period', 20)
        self.prediction_threshold = self.parameters.get('prediction_threshold', 0.6)
        self.retrain_interval = self.parameters.get('retrain_interval', 100)
        self.model_path = f"models/{self.config.name}_model.pkl"
        
        # ML components
        self.model = None
        self.scaler = StandardScaler()
        self.feature_columns = []
        self.trade_count = 0
        
        # Load or create model
        self._load_or_create_model()
    
    def _load_or_create_model(self):
        """Load existing model or create new one."""
        try:
            if os.path.exists(self.model_path):
                self.model = joblib.load(self.model_path)
                logger.info(f"Loaded existing model from {self.model_path}")
            else:
                self.model = RandomForestClassifier(n_estimators=100, random_state=42)
                logger.info("Created new Random Forest model")
        except Exception as e:
            logger.error(f"Error loading/creating model: {e}")
            self.model = RandomForestClassifier(n_estimators=100, random_state=42)
    
    def _save_model(self):
        """Save the trained model."""
        try:
            os.makedirs("models", exist_ok=True)
            joblib.dump(self.model, self.model_path)
            logger.info(f"Model saved to {self.model_path}")
        except Exception as e:
            logger.error(f"Error saving model: {e}")
    
    def calculate_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """Calculate technical indicators for ML features."""
        if data.empty:
            return data
        
        try:
            # Add all technical indicators
            df = TechnicalIndicators.add_all_indicators(data)
            
            # Add price-based features
            df['price_change'] = df['close'].pct_change()
            df['price_change_5'] = df['close'].pct_change(5)
            df['price_change_10'] = df['close'].pct_change(10)
            
            # Add volatility features
            df['volatility'] = df['price_change'].rolling(window=10).std()
            df['volatility_ratio'] = df['volatility'] / df['volatility'].rolling(window=20).mean()
            
            # Add volume features
            df['volume_ratio'] = df['tick_volume'] / df['tick_volume'].rolling(window=20).mean()
            
            # Add time-based features
            df['hour'] = df.index.hour
            df['day_of_week'] = df.index.dayofweek
            
            return df
            
        except Exception as e:
            logger.error(f"Error calculating indicators: {e}")
            return data
    
    def _prepare_features(self, data: pd.DataFrame) -> pd.DataFrame:
        """Prepare features for ML model."""
        try:
            # Select feature columns
            feature_cols = [
                'sma_20', 'sma_50', 'ema_12', 'ema_26',
                'bb_upper', 'bb_middle', 'bb_lower', 'bb_width',
                'rsi', 'macd', 'macd_signal', 'macd_histogram',
                'atr', 'price_change', 'price_change_5', 'price_change_10',
                'volatility', 'volatility_ratio', 'volume_ratio',
                'hour', 'day_of_week'
            ]
            
            # Filter available columns
            available_cols = [col for col in feature_cols if col in data.columns]
            self.feature_columns = available_cols
            
            # Create feature dataframe
            features = data[available_cols].copy()
            
            # Handle missing values
            features = features.fillna(method='ffill').fillna(0)
            
            return features
            
        except Exception as e:
            logger.error(f"Error preparing features: {e}")
            return pd.DataFrame()
    
    def _create_labels(self, data: pd.DataFrame, forward_period: int = 5) -> pd.Series:
        """Create labels for supervised learning."""
        try:
            # Calculate future returns
            future_returns = data['close'].shift(-forward_period) / data['close'] - 1
            
            # Create binary labels (1 for positive return, 0 for negative)
            labels = (future_returns > 0).astype(int)
            
            # Remove NaN values
            labels = labels.dropna()
            
            return labels
            
        except Exception as e:
            logger.error(f"Error creating labels: {e}")
            return pd.Series()
    
    def _train_model(self, data: pd.DataFrame):
        """Train the ML model."""
        try:
            if len(data) < 100:
                logger.warning("Insufficient data for training")
                return
            
            # Prepare features and labels
            features = self._prepare_features(data)
            labels = self._create_labels(data)
            
            # Align features and labels
            common_index = features.index.intersection(labels.index)
            features = features.loc[common_index]
            labels = labels.loc[common_index]
            
            if len(features) < 50:
                logger.warning("Insufficient aligned data for training")
                return
            
            # Split data
            X_train, X_test, y_train, y_test = train_test_split(
                features, labels, test_size=0.2, random_state=42
            )
            
            # Scale features
            X_train_scaled = self.scaler.fit_transform(X_train)
            X_test_scaled = self.scaler.transform(X_test)
            
            # Train model
            self.model.fit(X_train_scaled, y_train)
            
            # Evaluate model
            train_score = self.model.score(X_train_scaled, y_train)
            test_score = self.model.score(X_test_scaled, y_test)
            
            logger.info(f"Model trained - Train accuracy: {train_score:.3f}, Test accuracy: {test_score:.3f}")
            
            # Save model
            self._save_model()
            
        except Exception as e:
            logger.error(f"Error training model: {e}")
    
    def generate_signals(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Generate trading signals using ML predictions."""
        if data.empty or len(data) < self.lookback_period:
            return {'signal': 'NO_SIGNAL', 'reason': 'Insufficient data'}
        
        try:
            # Prepare features
            features = self._prepare_features(data)
            if features.empty:
                return {'signal': 'NO_FEATURES', 'reason': 'No features available'}
            
            # Get latest features
            latest_features = features.iloc[-1:].copy()
            
            # Scale features
            latest_scaled = self.scaler.transform(latest_features)
            
            # Make prediction
            prediction_proba = self.model.predict_proba(latest_scaled)[0]
            prediction = self.model.predict(latest_scaled)[0]
            
            # Get confidence
            confidence = max(prediction_proba)
            
            # Generate signal based on prediction and confidence
            if confidence < self.prediction_threshold:
                return {'signal': 'NO_SIGNAL', 'reason': f'Low confidence: {confidence:.3f}'}
            
            if prediction == 1 and confidence >= self.prediction_threshold:
                return {
                    'signal': 'BUY',
                    'reason': f'ML Bullish (confidence: {confidence:.3f})',
                    'confidence': confidence,
                    'prediction_proba': prediction_proba.tolist()
                }
            elif prediction == 0 and confidence >= self.prediction_threshold:
                return {
                    'signal': 'SELL',
                    'reason': f'ML Bearish (confidence: {confidence:.3f})',
                    'confidence': confidence,
                    'prediction_proba': prediction_proba.tolist()
                }
            
            return {'signal': 'NO_SIGNAL', 'reason': 'No clear prediction'}
            
        except Exception as e:
            logger.error(f"Error generating ML signals: {e}")
            return {'signal': 'ERROR', 'reason': str(e)}
    
    def should_trade(self, symbol: str, session_type: SessionType) -> bool:
        """Check if the strategy should trade in the current session."""
        # ML strategy can trade in any session
        return True
    
    def analyze_symbol(self, symbol: str) -> Dict[str, Any]:
        """Analyze symbol and potentially retrain model."""
        # Increment trade count
        self.trade_count += 1
        
        # Retrain model periodically
        if self.trade_count % self.retrain_interval == 0:
            logger.info(f"Retraining model for {symbol}")
            data = self.get_data(symbol, lookback_periods=500)
            if not data.empty:
                data_with_indicators = self.calculate_indicators(data)
                self._train_model(data_with_indicators)
        
        # Call parent method
        return super().analyze_symbol(symbol)
    
    def get_strategy_info(self) -> Dict[str, Any]:
        """Get detailed strategy information."""
        return {
            'name': 'Machine Learning Strategy',
            'description': 'Uses Random Forest classifier to predict price movements',
            'parameters': {
                'lookback_period': self.lookback_period,
                'prediction_threshold': self.prediction_threshold,
                'retrain_interval': self.retrain_interval,
                'model_path': self.model_path
            },
            'model_info': {
                'type': 'RandomForestClassifier',
                'feature_count': len(self.feature_columns),
                'features': self.feature_columns,
                'trade_count': self.trade_count
            },
            'suitable_sessions': 'All sessions',
            'indicators': 'Technical indicators + ML features',
            'signal_types': ['BUY', 'SELL'],
            'risk_management': 'Confidence-based position sizing'
        } 