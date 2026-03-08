"""
Gas Optimization Module
Calculates precise gas costs and optimizes position sizing
Architectural Choice: Separate gas economics from trading logic for maintainability
"""

from typing import Dict, Tuple, Optional
from dataclasses import dataclass
from decimal import Decimal
import logging
from web3 import Web3

logger = logging.getLogger(__name__)

@dataclass
class GasEstimate:
    """Structured gas estimation results"""
    base_fee_gwei: float
    priority_fee_gwei: float
    total_fee_gwei: float
    gas_limit: int
    total_cost_eth: Decimal
    total_cost_usd: Decimal
    confidence: float  # 0-1 confidence score in estimate

class GasOptimizer:
    """Gas optimization and cost calculation engine"""
    
    def __init__(self, web3_client: Web3, eth_usd_price: float = 2500.0):
        """
        Initialize gas optimizer
        
        Args:
            web3_client: Web3 client instance
            eth_usd_price: Current ETH/USD price (can be updated dynamically)
        """
        self.web3 = web3_client
        self.eth_usd_price = Decimal(str(eth_usd_price))
        self.cached_gas_price = None
        self.cache_time = 0
        self.CACHE_TTL_SECONDS = 30
        
        # Standard gas limits for different operations (Base L2 optimized)
        self.GAS_LIMITS = {
            "token_approve": 45000,
            "swap_exact_tokens": 180000,
            "add_liquidity": 250000,
            "remove_liquidity": 150000,
            "transfer": 21000
        }
        
        logger.info("GasOptimizer initialized")
    
    def estimate_transaction_cost(self, 
                                 operation_type: str,
                                 priority_level: str = "medium") -> GasEstimate:
        """
        Estimate gas cost for a specific operation
        
        Args:
            operation_type: Type of operation (from GAS_LIMITS keys)
            priority_level: "low", "medium", "high", "custom"
            
        Returns:
            GasEstimate object with cost details
            
        Raises:
            ValueError: If operation_type is invalid
        """
        try:
            # Validate operation type
            if operation_type not in self.GAS_LIMITS:
                raise ValueError(f"Invalid operation type: {operation_type}. Valid types: {list(self.GAS_LIMITS.keys())}")
            
            # Get current gas prices
            base_fee, priority_fee = self._get_current_gas_prices(priority_level)
            
            # Calculate total fee
            gas_limit = self.GAS_LIMITS[operation_type]
            total_fee_gwei = base_fee +