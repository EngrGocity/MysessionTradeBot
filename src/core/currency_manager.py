"""
Multi-currency pair manager for handling multiple trading instruments.
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Set, Tuple, Optional, Any
from datetime import datetime, timedelta
from loguru import logger
from dataclasses import dataclass

from src.core.config import SessionType


@dataclass
class CurrencyPair:
    """Represents a currency pair with its properties."""
    symbol: str
    base_currency: str
    quote_currency: str
    pip_value: float
    min_lot: float
    max_lot: float
    lot_step: float
    spread: float
    commission: float
    swap_long: float
    swap_short: float
    session_preference: List[SessionType]
    volatility_profile: Dict[str, float]
    correlation_groups: List[str]


class CurrencyManager:
    """Manages multiple currency pairs with correlation and risk analysis."""
    
    def __init__(self):
        self.pairs: Dict[str, CurrencyPair] = {}
        self.correlation_matrix: pd.DataFrame = None
        self.active_pairs: Set[str] = set()
        self.max_correlated_pairs = 3
        self.correlation_threshold = 0.7
        
        # Initialize default currency pairs
        self._initialize_default_pairs()
    
    def _initialize_default_pairs(self):
        """Initialize default currency pairs with their properties."""
        default_pairs = [
            # Major pairs
            CurrencyPair(
                symbol="EURUSD",
                base_currency="EUR",
                quote_currency="USD",
                pip_value=0.0001,
                min_lot=0.01,
                max_lot=100.0,
                lot_step=0.01,
                spread=1.0,
                commission=0.0,
                swap_long=-2.0,
                swap_short=1.0,
                session_preference=[SessionType.LONDON, SessionType.NEW_YORK],
                volatility_profile={"asian": 0.3, "london": 0.8, "new_york": 0.9},
                correlation_groups=["majors", "eur_pairs"]
            ),
            CurrencyPair(
                symbol="GBPUSD",
                base_currency="GBP",
                quote_currency="USD",
                pip_value=0.0001,
                min_lot=0.01,
                max_lot=100.0,
                lot_step=0.01,
                spread=1.5,
                commission=0.0,
                swap_long=-3.0,
                swap_short=1.5,
                session_preference=[SessionType.LONDON, SessionType.NEW_YORK],
                volatility_profile={"asian": 0.2, "london": 0.9, "new_york": 0.8},
                correlation_groups=["majors", "gbp_pairs"]
            ),
            CurrencyPair(
                symbol="USDJPY",
                base_currency="USD",
                quote_currency="JPY",
                pip_value=0.01,
                min_lot=0.01,
                max_lot=100.0,
                lot_step=0.01,
                spread=1.2,
                commission=0.0,
                swap_long=1.0,
                swap_short=-2.0,
                session_preference=[SessionType.ASIAN, SessionType.LONDON],
                volatility_profile={"asian": 0.7, "london": 0.6, "new_york": 0.5},
                correlation_groups=["majors", "jpy_pairs"]
            ),
            CurrencyPair(
                symbol="AUDUSD",
                base_currency="AUD",
                quote_currency="USD",
                pip_value=0.0001,
                min_lot=0.01,
                max_lot=100.0,
                lot_step=0.01,
                spread=1.3,
                commission=0.0,
                swap_long=-1.5,
                swap_short=0.8,
                session_preference=[SessionType.ASIAN, SessionType.LONDON],
                volatility_profile={"asian": 0.8, "london": 0.5, "new_york": 0.4},
                correlation_groups=["commodity", "aud_pairs"]
            ),
            CurrencyPair(
                symbol="USDCAD",
                base_currency="USD",
                quote_currency="CAD",
                pip_value=0.0001,
                min_lot=0.01,
                max_lot=100.0,
                lot_step=0.01,
                spread=1.4,
                commission=0.0,
                swap_long=0.5,
                swap_short=-1.0,
                session_preference=[SessionType.NEW_YORK, SessionType.LONDON],
                volatility_profile={"asian": 0.2, "london": 0.4, "new_york": 0.7},
                correlation_groups=["commodity", "cad_pairs"]
            ),
            CurrencyPair(
                symbol="NZDUSD",
                base_currency="NZD",
                quote_currency="USD",
                pip_value=0.0001,
                min_lot=0.01,
                max_lot=100.0,
                lot_step=0.01,
                spread=1.6,
                commission=0.0,
                swap_long=-2.0,
                swap_short=1.0,
                session_preference=[SessionType.ASIAN, SessionType.LONDON],
                volatility_profile={"asian": 0.6, "london": 0.4, "new_york": 0.3},
                correlation_groups=["commodity", "nzd_pairs"]
            ),
            # Minor pairs
            CurrencyPair(
                symbol="EURGBP",
                base_currency="EUR",
                quote_currency="GBP",
                pip_value=0.0001,
                min_lot=0.01,
                max_lot=100.0,
                lot_step=0.01,
                spread=2.0,
                commission=0.0,
                swap_long=-1.0,
                swap_short=0.5,
                session_preference=[SessionType.LONDON],
                volatility_profile={"asian": 0.1, "london": 0.6, "new_york": 0.3},
                correlation_groups=["crosses", "eur_pairs", "gbp_pairs"]
            ),
            CurrencyPair(
                symbol="EURJPY",
                base_currency="EUR",
                quote_currency="JPY",
                pip_value=0.01,
                min_lot=0.01,
                max_lot=100.0,
                lot_step=0.01,
                spread=1.8,
                commission=0.0,
                swap_long=-1.5,
                swap_short=1.0,
                session_preference=[SessionType.ASIAN, SessionType.LONDON],
                volatility_profile={"asian": 0.8, "london": 0.7, "new_york": 0.5},
                correlation_groups=["crosses", "eur_pairs", "jpy_pairs"]
            ),
            CurrencyPair(
                symbol="GBPJPY",
                base_currency="GBP",
                quote_currency="JPY",
                pip_value=0.01,
                min_lot=0.01,
                max_lot=100.0,
                lot_step=0.01,
                spread=2.2,
                commission=0.0,
                swap_long=-2.5,
                swap_short=1.5,
                session_preference=[SessionType.ASIAN, SessionType.LONDON],
                volatility_profile={"asian": 0.9, "london": 0.8, "new_york": 0.6},
                correlation_groups=["crosses", "gbp_pairs", "jpy_pairs"]
            ),
            CurrencyPair(
                symbol="AUDJPY",
                base_currency="AUD",
                quote_currency="JPY",
                pip_value=0.01,
                min_lot=0.01,
                max_lot=100.0,
                lot_step=0.01,
                spread=2.0,
                commission=0.0,
                swap_long=-1.0,
                swap_short=0.8,
                session_preference=[SessionType.ASIAN],
                volatility_profile={"asian": 0.9, "london": 0.5, "new_york": 0.3},
                correlation_groups=["commodity", "aud_pairs", "jpy_pairs"]
            )
        ]
        
        for pair in default_pairs:
            self.pairs[pair.symbol] = pair
    
    def add_pair(self, pair: CurrencyPair):
        """Add a new currency pair."""
        self.pairs[pair.symbol] = pair
        logger.info(f"Added currency pair: {pair.symbol}")
    
    def remove_pair(self, symbol: str):
        """Remove a currency pair."""
        if symbol in self.pairs:
            del self.pairs[symbol]
            self.active_pairs.discard(symbol)
            logger.info(f"Removed currency pair: {symbol}")
    
    def get_pairs_for_session(self, session_type: SessionType) -> List[str]:
        """Get currency pairs suitable for a specific session."""
        suitable_pairs = []
        
        for symbol, pair in self.pairs.items():
            if session_type in pair.session_preference:
                suitable_pairs.append(symbol)
        
        return suitable_pairs
    
    def get_pairs_by_volatility(self, session_type: SessionType, 
                               min_volatility: float = 0.0) -> List[str]:
        """Get currency pairs with minimum volatility for a session."""
        session_name = session_type.value
        suitable_pairs = []
        
        for symbol, pair in self.pairs.items():
            volatility = pair.volatility_profile.get(session_name, 0.0)
            if volatility >= min_volatility:
                suitable_pairs.append(symbol)
        
        return suitable_pairs
    
    def get_correlated_pairs(self, symbol: str, threshold: float = None) -> List[str]:
        """Get pairs correlated with the given symbol."""
        if threshold is None:
            threshold = self.correlation_threshold
        
        if self.correlation_matrix is None:
            return []
        
        if symbol not in self.correlation_matrix.index:
            return []
        
        correlations = self.correlation_matrix[symbol].abs()
        correlated = correlations[correlations > threshold].index.tolist()
        correlated.remove(symbol)  # Remove self-correlation
        
        return correlated
    
    def update_correlation_matrix(self, price_data: Dict[str, pd.DataFrame]):
        """Update correlation matrix based on price data."""
        try:
            # Prepare price data for correlation calculation
            returns_data = {}
            
            for symbol, data in price_data.items():
                if not data.empty and 'close' in data.columns:
                    returns = data['close'].pct_change().dropna()
                    if len(returns) > 30:  # Minimum data requirement
                        returns_data[symbol] = returns
            
            if len(returns_data) < 2:
                logger.warning("Insufficient data for correlation calculation")
                return
            
            # Create returns dataframe
            returns_df = pd.DataFrame(returns_data)
            
            # Calculate correlation matrix
            self.correlation_matrix = returns_df.corr()
            
            logger.info(f"Updated correlation matrix for {len(returns_data)} pairs")
            
        except Exception as e:
            logger.error(f"Error updating correlation matrix: {e}")
    
    def can_open_position(self, symbol: str, current_positions: List[str]) -> Tuple[bool, str]:
        """Check if a new position can be opened considering correlations."""
        if symbol not in self.pairs:
            return False, "Symbol not found"
        
        # Check correlation limits
        correlated_pairs = self.get_correlated_pairs(symbol)
        correlated_positions = [pos for pos in current_positions if pos in correlated_pairs]
        
        if len(correlated_positions) >= self.max_correlated_pairs:
            return False, f"Too many correlated positions: {correlated_positions}"
        
        return True, "Position can be opened"
    
    def get_optimal_pairs(self, session_type: SessionType, 
                         max_pairs: int = 5) -> List[str]:
        """Get optimal currency pairs for a session."""
        # Get suitable pairs for the session
        suitable_pairs = self.get_pairs_for_session(session_type)
        
        if len(suitable_pairs) <= max_pairs:
            return suitable_pairs
        
        # Sort by volatility for the session
        session_name = session_type.value
        pair_volatilities = []
        
        for symbol in suitable_pairs:
            pair = self.pairs[symbol]
            volatility = pair.volatility_profile.get(session_name, 0.0)
            pair_volatilities.append((symbol, volatility))
        
        # Sort by volatility (descending) and return top pairs
        pair_volatilities.sort(key=lambda x: x[1], reverse=True)
        return [pair[0] for pair in pair_volatilities[:max_pairs]]
    
    def get_pair_info(self, symbol: str) -> Optional[CurrencyPair]:
        """Get information about a currency pair."""
        return self.pairs.get(symbol)
    
    def get_all_pairs(self) -> List[str]:
        """Get all available currency pairs."""
        return list(self.pairs.keys())
    
    def get_pairs_by_group(self, group: str) -> List[str]:
        """Get currency pairs by correlation group."""
        pairs = []
        for symbol, pair in self.pairs.items():
            if group in pair.correlation_groups:
                pairs.append(symbol)
        return pairs
    
    def calculate_position_size(self, symbol: str, risk_amount: float, 
                              stop_loss_pips: float) -> float:
        """Calculate position size for a currency pair."""
        pair = self.pairs.get(symbol)
        if not pair:
            return 0.0
        
        # Calculate position size based on pip value and stop loss
        risk_per_lot = stop_loss_pips * pair.pip_value
        if risk_per_lot <= 0:
            return 0.0
        
        position_size = risk_amount / risk_per_lot
        
        # Apply pair-specific limits
        position_size = max(pair.min_lot, min(pair.max_lot, position_size))
        
        # Round to lot step
        position_size = round(position_size / pair.lot_step) * pair.lot_step
        
        return position_size
    
    def get_session_volatility(self, symbol: str, session_type: SessionType) -> float:
        """Get volatility profile for a pair in a specific session."""
        pair = self.pairs.get(symbol)
        if not pair:
            return 0.0
        
        session_name = session_type.value
        return pair.volatility_profile.get(session_name, 0.0)
    
    def get_correlation_summary(self) -> Dict[str, Any]:
        """Get summary of correlation analysis."""
        if self.correlation_matrix is None:
            return {"error": "No correlation data available"}
        
        summary = {
            "total_pairs": len(self.correlation_matrix),
            "high_correlations": 0,
            "correlation_groups": {}
        }
        
        # Count high correlations
        high_corr_mask = self.correlation_matrix.abs() > self.correlation_threshold
        summary["high_correlations"] = high_corr_mask.sum().sum() - len(self.correlation_matrix)
        
        # Group correlations by currency
        for symbol in self.correlation_matrix.index:
            pair = self.pairs.get(symbol)
            if pair:
                for group in pair.correlation_groups:
                    if group not in summary["correlation_groups"]:
                        summary["correlation_groups"][group] = []
                    summary["correlation_groups"][group].append(symbol)
        
        return summary 