"""
User Model - Represents authenticated users
"""
from dataclasses import dataclass, field
from typing import Dict, Any, Optional
import hashlib
import time


@dataclass
class User:
    """
    User entity for authentication
    """
    username: str
    password_hash: str
    enabled: bool = True
    admin: bool = False
    rate_limit: int = 100
    
    # Tracking
    created_at: Optional[float] = None
    last_login: Optional[float] = None
    login_count: int = 0
    
    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = time.time()
    
    def verify_password(self, password: str) -> bool:
        """Verify password against stored hash"""
        # For production, use bcrypt.checkpw()
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        return password_hash == self.password_hash
    
    @staticmethod
    def hash_password(password: str) -> str:
        """Hash password for storage"""
        # For production, use bcrypt.hashpw(password.encode(), bcrypt.gensalt())
        return hashlib.sha256(password.encode()).hexdigest()
    
    def record_login(self):
        """Record successful login"""
        self.last_login = time.time()
        self.login_count += 1
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary (without password)"""
        return {
            'username': self.username,
            'enabled': self.enabled,
            'admin': self.admin,
            'rate_limit': self.rate_limit,
            'created_at': self.created_at,
            'last_login': self.last_login,
            'login_count': self.login_count,
            'metadata': self.metadata
        }
    
    def to_dict_with_hash(self) -> Dict[str, Any]:
        """Convert to dictionary including password hash (for storage)"""
        data = self.to_dict()
        data['password_hash'] = self.password_hash
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'User':
        """Create user from dictionary"""
        return cls(
            username=data['username'],
            password_hash=data['password_hash'],
            enabled=data.get('enabled', True),
            admin=data.get('admin', False),
            rate_limit=data.get('rate_limit', 100),
            created_at=data.get('created_at'),
            last_login=data.get('last_login'),
            login_count=data.get('login_count', 0),
            metadata=data.get('metadata', {})
        )
    
    @classmethod
    def create(cls, username: str, password: str, **kwargs) -> 'User':
        """Factory method to create new user"""
        return cls(
            username=username,
            password_hash=cls.hash_password(password),
            **kwargs
        )
