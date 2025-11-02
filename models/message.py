"""
Message Model - Represents email messages
Follows Domain Model pattern
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Any, Optional
from email.utils import make_msgid
import time


@dataclass
class Message:
    """
    Core message entity
    Represents an email message with all its properties
    """
    sender: str
    recipients: List[str]
    data: str
    
    # Metadata
    message_id: Optional[str] = None
    received_at: Optional[float] = None
    size: Optional[int] = None
    
    # Session context
    session_info: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if self.message_id is None:
            self.message_id = make_msgid()
        if self.received_at is None:
            self.received_at = time.time()
        if self.size is None:
            self.size = len(self.data)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation"""
        return {
            'message_id': self.message_id,
            'sender': self.sender,
            'recipients': self.recipients,
            'data': self.data,
            'received_at': self.received_at,
            'size': self.size,
            'session_info': self.session_info
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Message':
        """Create from dictionary"""
        return cls(
            sender=data['sender'],
            recipients=data['recipients'],
            data=data['data'],
            message_id=data.get('message_id'),
            received_at=data.get('received_at'),
            size=data.get('size'),
            session_info=data.get('session_info', {})
        )
    
    def validate(self) -> bool:
        """Validate message structure"""
        if not self.sender:
            return False
        if not self.recipients:
            return False
        if not self.data:
            return False
        return True


@dataclass
class QueuedMessage:
    """
    Queued message entity with delivery tracking
    Extends Message with queue-specific attributes
    """
    queue_id: str
    message: Message
    
    # Queue status
    status: str = 'active'  # active, deferred, bounce, delivered
    created_at: float = field(default_factory=time.time)
    next_retry_at: Optional[float] = None
    attempts: int = 0
    last_error: Optional[str] = None
    
    # Per-recipient tracking
    recipient_status: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    
    def __post_init__(self):
        if not self.recipient_status:
            self.recipient_status = {
                rcpt: {
                    'status': 'pending',
                    'attempts': 0,
                    'last_error': None,
                    'last_attempt': None
                }
                for rcpt in self.message.recipients
            }
    
    def pending_recipients(self) -> List[str]:
        """Get recipients that still need delivery"""
        return [
            rcpt for rcpt, status in self.recipient_status.items()
            if status['status'] in ['pending', 'deferred']
        ]
    
    def is_expired(self, max_age: int) -> bool:
        """Check if message exceeded max queue age"""
        return (time.time() - self.created_at) > max_age
    
    def all_delivered(self) -> bool:
        """Check if all recipients delivered successfully"""
        return all(
            status['status'] == 'delivered'
            for status in self.recipient_status.values()
        )
    
    def any_permanent_failure(self) -> bool:
        """Check if any recipient has permanent failure"""
        return any(
            status['status'] == 'bounce'
            for status in self.recipient_status.values()
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'queue_id': self.queue_id,
            'sender': self.message.sender,
            'recipients': self.message.recipients,
            'message_data': self.message.data,
            'session_info': self.message.session_info,
            'status': self.status,
            'created_at': self.created_at,
            'next_retry_at': self.next_retry_at,
            'attempts': self.attempts,
            'last_error': self.last_error,
            'recipient_status': self.recipient_status
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'QueuedMessage':
        """Create from dictionary"""
        message = Message(
            sender=data['sender'],
            recipients=data['recipients'],
            data=data['message_data'],
            message_id=data.get('message_id'),
            session_info=data.get('session_info', {})
        )
        
        return cls(
            queue_id=data['queue_id'],
            message=message,
            status=data.get('status', 'active'),
            created_at=data.get('created_at', time.time()),
            next_retry_at=data.get('next_retry_at'),
            attempts=data.get('attempts', 0),
            last_error=data.get('last_error'),
            recipient_status=data.get('recipient_status', {})
        )
