"""
Policy Models - Represents policy rules and limits
"""
from dataclasses import dataclass, field
from typing import Optional, List
import time


@dataclass
class PolicyRule:
    """
    Generic policy rule entity
    """
    rule_id: str
    rule_type: str  # 'blacklist', 'whitelist', 'rate_limit', 'content_filter'
    target: str  # IP, domain, email, pattern
    action: str  # 'reject', 'defer', 'accept', 'quarantine'
    
    # Optional fields
    reason: Optional[str] = None
    enabled: bool = True
    created_at: float = field(default_factory=time.time)
    expires_at: Optional[float] = None
    
    def is_expired(self) -> bool:
        """Check if rule has expired"""
        if self.expires_at is None:
            return False
        return time.time() > self.expires_at
    
    def is_active(self) -> bool:
        """Check if rule is currently active"""
        return self.enabled and not self.is_expired()
    
    def to_dict(self):
        return {
            'rule_id': self.rule_id,
            'rule_type': self.rule_type,
            'target': self.target,
            'action': self.action,
            'reason': self.reason,
            'enabled': self.enabled,
            'created_at': self.created_at,
            'expires_at': self.expires_at
        }
    
    @classmethod
    def from_dict(cls, data):
        return cls(**data)


@dataclass
class RateLimit:
    """
    Rate limit tracking entity
    Implements token bucket algorithm
    """
    identifier: str  # IP, user, domain
    limit_type: str  # 'ip', 'user', 'domain'
    
    # Token bucket parameters
    capacity: int  # Max tokens
    tokens: float  # Current tokens
    refill_rate: float  # Tokens per second
    last_refill: float = field(default_factory=time.time)
    
    # Tracking
    total_requests: int = 0
    rejected_requests: int = 0
    
    def refill(self):
        """Refill tokens based on time elapsed"""
        now = time.time()
        elapsed = now - self.last_refill
        
        # Add tokens based on elapsed time
        self.tokens = min(
            self.capacity,
            self.tokens + (elapsed * self.refill_rate)
        )
        self.last_refill = now
    
    def consume(self, tokens: int = 1) -> bool:
        """
        Try to consume tokens
        Returns True if allowed, False if rate limited
        """
        self.refill()
        self.total_requests += 1
        
        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        else:
            self.rejected_requests += 1
            return False
    
    def to_dict(self):
        return {
            'identifier': self.identifier,
            'limit_type': self.limit_type,
            'capacity': self.capacity,
            'tokens': self.tokens,
            'refill_rate': self.refill_rate,
            'last_refill': self.last_refill,
            'total_requests': self.total_requests,
            'rejected_requests': self.rejected_requests
        }


@dataclass
class GreylistEntry:
    """
    Greylisting entry
    Tracks sender/recipient/IP triplets
    """
    triplet: str  # f"{sender}:{recipient}:{ip}"
    first_seen: float = field(default_factory=time.time)
    last_seen: float = field(default_factory=time.time)
    attempts: int = 1
    passed: bool = False
    
    def should_defer(self, min_delay: int, max_age: int) -> bool:
        """
        Check if message should be deferred
        Returns True if should defer, False if should accept
        """
        now = time.time()
        age = now - self.first_seen
        
        # If too new, defer
        if age < min_delay:
            return True
        
        # If too old, reject (start over)
        if age > max_age:
            return True
        
        # In the window, accept
        return False
    
    def update(self):
        """Update last seen timestamp"""
        self.last_seen = time.time()
        self.attempts += 1
    
    def mark_passed(self):
        """Mark as passed greylisting"""
        self.passed = True
        self.last_seen = time.time()
    
    def to_dict(self):
        return {
            'triplet': self.triplet,
            'first_seen': self.first_seen,
            'last_seen': self.last_seen,
            'attempts': self.attempts,
            'passed': self.passed
        }
    
    @classmethod
    def from_dict(cls, data):
        return cls(**data)
