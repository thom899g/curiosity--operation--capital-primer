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