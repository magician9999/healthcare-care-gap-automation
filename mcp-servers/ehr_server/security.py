import os
import hashlib
import secrets
from datetime import datetime
from typing import Dict, Any, Optional
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
import logging
import json

from config import settings

logger = logging.getLogger(__name__)


class HIIPAASecurityManager:
    """HIPAA-compliant security manager for data encryption and audit logging"""
    
    def __init__(self):
        self.encryption_key = self._get_or_create_encryption_key()
        self.fernet = Fernet(self.encryption_key) if self.encryption_key else None
        
    def _get_or_create_encryption_key(self) -> Optional[bytes]:
        """Get existing encryption key or create a new one"""
        try:
            if settings.ENCRYPTION_KEY:
                # Derive key from provided password
                password = settings.ENCRYPTION_KEY.encode()
                salt = b'healthcare_salt_2024'  # In production, use random salt stored securely
                kdf = PBKDF2HMAC(
                    algorithm=hashes.SHA256(),
                    length=32,
                    salt=salt,
                    iterations=100000,
                )
                key = base64.urlsafe_b64encode(kdf.derive(password))
                return key
            else:
                logger.warning("No encryption key provided. Encryption disabled.")
                return None
        except Exception as e:
            logger.error(f"Failed to initialize encryption key: {e}")
            return None
    
    def encrypt_sensitive_data(self, data: str) -> str:
        """Encrypt sensitive patient data"""
        if not self.fernet:
            logger.warning("Encryption not available. Returning data as-is.")
            return data
            
        try:
            encrypted_data = self.fernet.encrypt(data.encode())
            return base64.urlsafe_b64encode(encrypted_data).decode()
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            return data
    
    def decrypt_sensitive_data(self, encrypted_data: str) -> str:
        """Decrypt sensitive patient data"""
        if not self.fernet:
            logger.warning("Decryption not available. Returning data as-is.")
            return encrypted_data
            
        try:
            encrypted_bytes = base64.urlsafe_b64decode(encrypted_data.encode())
            decrypted_data = self.fernet.decrypt(encrypted_bytes)
            return decrypted_data.decode()
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            return encrypted_data
    
    def hash_patient_id(self, patient_id: int) -> str:
        """Create a hash of patient ID for audit logging"""
        return hashlib.sha256(f"patient_{patient_id}".encode()).hexdigest()[:16]
    
    def log_audit_event(self, 
                       event_type: str, 
                       patient_id: Optional[int] = None,
                       user_id: Optional[str] = None,
                       details: Optional[Dict[str, Any]] = None):
        """Log HIPAA audit event"""
        if not settings.AUDIT_LOG_ENABLED:
            return
            
        audit_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": event_type,
            "patient_hash": self.hash_patient_id(patient_id) if patient_id else None,
            "user_id": user_id or "mcp_ehr_server",
            "session_id": secrets.token_hex(8),
            "details": details or {}
        }
        
        # Log to structured audit log
        audit_logger = logging.getLogger("audit")
        audit_logger.info(json.dumps(audit_entry))


class DataValidator:
    """Validate and sanitize healthcare data"""
    
    @staticmethod
    def sanitize_patient_data(data: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize patient data input"""
        sanitized = {}
        
        # Define allowed fields and their types
        allowed_fields = {
            "name": str,
            "age": int,
            "email": str,
            "phone": str,
            "date_of_birth": str,
            "insurance_info": dict,
            "risk_factors": str,
            "preferred_contact_method": str
        }
        
        for field, expected_type in allowed_fields.items():
            if field in data:
                value = data[field]
                if isinstance(value, expected_type):
                    # Additional sanitization
                    if field == "email":
                        sanitized[field] = value.lower().strip()
                    elif field == "phone":
                        sanitized[field] = ''.join(filter(str.isdigit, value))
                    elif field == "name":
                        sanitized[field] = value.strip()
                    else:
                        sanitized[field] = value
                else:
                    logger.warning(f"Invalid type for field {field}: expected {expected_type}, got {type(value)}")
        
        return sanitized
    
    @staticmethod
    def validate_age_range(min_age: int, max_age: int) -> bool:
        """Validate age range parameters"""
        return 0 <= min_age <= max_age <= 150


# Global security manager instance
security_manager = HIIPAASecurityManager()
data_validator = DataValidator()

__all__ = [
    "security_manager",
    "data_validator",
    "HIIPAASecurityManager",
    "DataValidator"
]