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