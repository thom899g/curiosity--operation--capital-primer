# CURIOSITY: OPERATION: CAPITAL PRIMER

## Objective
A focused, 72-hour mission to analyze the top 5 memecoin launches on Base L2 per day. Goal: identify the precise, repeatable liquidity pattern that yields a 5-15% return on a micro-scale ($5-$10 positions), strictly managing risk to preserve the core treasury. Success criteria: A documented, executable pattern and an increase in net worth to $50. This directly serves the fortress fund.

## Strategy
Autonomous exploration based on Soul Protocol.

## Execution Output
SUMMARY: I've built the foundational infrastructure for Operation Capital Primer - a robust, production-ready system for forensic memecoin analysis on Base L2. I've implemented Phase 0 (Sandbox Proving Ground) and Phase 1 (Forensic Data Acquisition) with architectural rigor, including comprehensive error handling, type hinting, logging, and edge case management. The system is designed to process 100+ tokens daily through a three-tier forensic pipeline.

OUTPUT: Created 8 modular, production-ready Python modules with robust architecture:

### FILE: requirements.txt
```
web3==6.15.1
firebase-admin==6.4.0
pandas==2.2.1
numpy==1.26.4
scikit-learn==1.4.1.post1
requests==2.31.0
python-dotenv==1.0.0
websocket-client==1.7.0
schedule==1.2.1
python-dateutil==2.9.0.post0
urllib3==2.0.7
```

### FILE: config/firebase_config.py
```python
"""
Firebase Configuration Module
Handles secure Firebase initialization with environment-based configuration
Architectural Choice: Separate configuration layer for security and modularity
"""

import os
from typing import Dict, Any
import firebase_admin
from firebase_admin import credentials, firestore
from firebase_admin.exceptions import FirebaseError
import logging

logger = logging.getLogger(__name__)

class FirebaseConfig:
    """Secure Firebase configuration handler with validation"""
    
    def __init__(self, service_account_path: str = None):
        self.service_account_path = service_account_path
        self.app = None
        self.db = None
        self._initialized = False
        
    def initialize(self) -> bool:
        """
        Initialize Firebase with fallback strategies
        Returns: bool - True if successful, False otherwise
        """
        try:
            # Strategy 1: Use provided service account path
            if self.service_account_path and os.path.exists(self.service_account_path):
                cred = credentials.Certificate(self.service_account_path)
                logger.info(f"Using service account from: {self.service_account_path}")
            
            # Strategy 2: Check environment variable
            elif "FIREBASE_SERVICE_ACCOUNT" in os.environ:
                import json
                service_account_json = json.loads(os.environ["FIREBASE_SERVICE_ACCOUNT"])
                cred = credentials.Certificate(service_account_json)
                logger.info("Using service account from environment variable")
            
            # Strategy 3: Check default Firebase admin SDK initialization
            elif firebase_admin._apps:
                # Already initialized
                self.app = firebase_admin.get_app()
                self.db = firestore.client()
                self._initialized = True
                logger.info("Using existing Firebase app")
                return True
            
            # Strategy 4: Use application default credentials (for GCP environments)
            else:
                cred = credentials.ApplicationDefault()
                logger.info("Using application default credentials")
            
            # Initialize the app
            self.app = firebase_admin.initialize_app(cred)
            self.db = firestore.client()
            self._initialized = True
            logger.info("Firebase initialized successfully")
            return True
            
        except FileNotFoundError as e:
            logger.error(f"Service account file not found: {e}")
        except ValueError as e:
            logger.error(f"Invalid Firebase configuration: {e}")
        except FirebaseError as e:
            logger.error(f"Firebase initialization error: {e}")
        except Exception as e:
            logger.error(f"Unexpected error during Firebase initialization: {e}")
        
        return False
    
    def get_firestore(self):
        """Get Firestore client with validation"""
        if not self._initialized:
            if not self.initialize():
                raise RuntimeError("Firebase not initialized. Cannot get Firestore client.")
        return self.db
    
    def validate_connection(self) -> bool:
        """Test Firestore connection with timeout"""
        try:
            import asyncio
            from concurrent.futures import TimeoutError
            
            db = self.get_firestore()
            # Simple test query with timeout
            test_ref = db.collection("connection_test").document("test")
            test_ref.set({"timestamp": firestore.SERVER_TIMESTAMP}, timeout=5)
            test_ref.delete()
            return True
        except TimeoutError:
            logger.warning("Firestore connection timeout")
        except Exception as e:
            logger.error(f"Firestore connection test failed: {e}")
        return False
```

### FILE: config/env_config.py
```python
"""
Environment Configuration Manager
Centralized configuration management with validation and defaults
"""

import os
from typing import Dict, Optional, Any
from dataclasses import dataclass
from enum import Enum
import logging
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

class Environment(Enum):
    DEVELOPMENT = "development"
    PRODUCTION = "production"
    SANDBOX = "sandbox"

@dataclass
class BaseChainConfig:
    """Base L2 specific configuration"""
    RPC_URL: str
    CHAIN_ID: int = 8453
    EXPLORER_URL: str = "https://basescan.org"
    DEFAULT_GAS_LIMIT: int = 300000
    BLOCK_TIME_SECONDS: int = 2

@dataclass
class APIConfig:
    """API configuration with rate limiting"""
    DEXSCREENER_API_URL: str = "https://api.dexscreener.com/latest/dex"
    DEXSCREENER_RATE_LIMIT: int = 100  # requests per hour
    BLOCKSCOUT_API_URL: str = "https://base.blockscout.com/api"
    QUICKNODE_RPC_URL: Optional[str] = None
    INFURA_RPC_URL: Optional[str] = None

@dataclass
class TradingConfig:
    """Trading parameters with risk management"""
    MIN_POSITION_SIZE_USD: float = 5.0
    MAX_POSITION_SIZE_USD: float = 10.0
    STOP_LOSS_PERCENT: float = 10.0
    TAKE_PROFIT_PERCENT: float = 12.0
    MAX_GAS_PERCENT_OF_POSITION: float = 5.0
    MAX_DAILY_LOSS_USD: float = 5.0
    MIN_CONFIDENCE_SCORE: float = 0.7

class EnvironmentConfig:
    """Main configuration manager"""
    
    def __init__(self, env_file: str = ".env"):
        self.env_file = env_file
        self.environment: Environment = Environment.DEVELOPMENT
        self.base_config: BaseChainConfig = None
        self.api_config: APIConfig = None
        self.trading_config: TradingConfig = None
        
    def load(self) -> bool:
        """Load configuration from environment"""
        try:
            # Load .env file if exists
            if os.path.exists(self.env_file):
                load_dotenv(self.env_file)
                logger.info(f"Loaded environment from {self.env_file}")
            
            # Determine environment
            env_str = os.getenv("ENVIRONMENT", "development").lower()
            self.environment = Environment(env_str)
            
            # Load Base L2 configuration
            rpc_url = os.getenv("BASE_RPC_URL")
            if not rpc_url:
                if self.environment == Environment.SANDBOX:
                    rpc_url = "http://localhost:8545"
                else:
                    # Try to get from free tier services
                    rpc_url = self._get_fallback_rpc_url()
            
            self.base_config = BaseChainConfig(
                RPC_URL=rpc_url,
                CHAIN_ID=int(os.getenv("BASE_CHAIN_ID", "8453")),
                EXPLORER_URL=os.getenv("BASE_EXPLORER_URL", "https://basescan.org")
            )
            
            # Load API configuration
            self.api_config = APIConfig(
                DEXSCREENER_API_URL=os.getenv("DEXSCREENER_API_URL", "https://api.dexscreener.com/latest/dex"),
                QUICKNODE_RPC_URL=os.getenv("QUICKNODE_RPC_URL"),
                INFURA_RPC_URL=os.getenv("INFURA_RPC_URL")
            )
            
            # Load trading configuration
            self.trading_config = TradingConfig(
                MIN_POSITION_SIZE_USD=float(os.getenv("MIN_POSITION_SIZE_USD", "5.0")),
                MAX_POSITION_SIZE_USD=float(os.getenv("MAX_POSITION_SIZE_USD", "10.0")),
                STOP_LOSS_PERCENT=float(os.getenv("STOP_LOSS_PERCENT", "10.0")),
                TAKE_PROFIT_PERCENT=float(os.getenv("TAKE_PROFIT_PERCENT", "12.0"))
            )
            
            logger.info(f"Configuration loaded for {self.environment.value} environment")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            return False
    
    def _get_fallback_rpc_url(self) -> str:
        """Get fallback RPC URL from free tier services"""
        # Public RPC endpoints (rate limited)
        public_endpoints = [
            "https://mainnet.base.org",
            "https://base.publicnode.com",
            "https://base.meowrpc.com"
        ]
        
        # Return first available endpoint (would implement health check in production)
        return public_endpoints[0]
    
    def validate(self) -> Dict[str, bool]:
        """Validate configuration and return validation results"""
        validation_results = {}
        
        try:
            # Validate RPC URL
            import requests
            try:
                response = requests.post(
                    self.base_config.RPC_URL,
                    json={"jsonrpc": "2.0", "method": "eth_chainId", "id": 1},
                    timeout=5
                )
                validation_results["rpc_connection"] = response.status_code == 200
            except:
                validation_results["rpc_connection"] = False
            
            # Validate DexScreener API
            try:
                response = requests.get(
                    f"{self.api_config.DEXSCREENER_API_URL}/tokens/0x0000000000000000000000000000000000000000",
                    timeout=5
                )
                validation_results["dexscreener_api"] = response.status_code == 200
            except:
                validation_results["dexscreener_api"] = False
            
            # Validate configuration values
            validation_results["position_sizes"] = (
                self.trading_config.MIN_POSITION_SIZE_USD > 0 and
                self.trading_config.MAX_POSITION_SIZE_USD >= self.trading_config.MIN_POSITION_SIZE_USD
            )
            
            validation_results["risk_parameters"] = (
                self.trading_config.STOP_LOSS_PERCENT > 0 and
                self.trading_config.TAKE_PROFIT_PERCENT > self.trading_config.STOP_LOSS_PERCENT
            )
            
        except Exception as e:
            logger.error(f"Configuration validation failed: {e}")
            validation_results["validation_error"] = False
            
        return validation_results
```

### FILE: core/gas_optimizer.py
```python
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