"""
Delivery Status Models - Track delivery attempts and results
"""
from dataclasses import dataclass, field
from typing import Optional, Dict, Any
from enum import Enum
import time


class DeliveryState(Enum):
    """Delivery state enumeration"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    DELIVERED = "delivered"
    DEFERRED = "deferred"
    BOUNCE = "bounce"
    EXPIRED = "expired"


class SMTPReplyCode(Enum):
    """Common SMTP reply codes"""
    # Success
    OK = 250
    WILL_FORWARD = 251
    
    # Temporary failures (4xx)
    TEMP_FAILURE = 450
    MAILBOX_BUSY = 450
    LOCAL_ERROR = 451
    INSUFFICIENT_STORAGE = 452
    TEMP_UNABLE_TO_ROUTE = 453
    
    # Permanent failures (5xx)
    PERM_FAILURE = 550
    USER_NOT_LOCAL = 551
    EXCEEDED_STORAGE = 552
    MAILBOX_NAME_INVALID = 553
    TRANSACTION_FAILED = 554


@dataclass
class RecipientStatus:
    """
    Per-recipient delivery status
    """
    recipient: str
    state: DeliveryState = DeliveryState.PENDING
    
    # Attempt tracking
    attempts: int = 0
    last_attempt: Optional[float] = None
    next_attempt: Optional[float] = None
    
    # Result tracking
    smtp_code: Optional[int] = None
    smtp_message: Optional[str] = None
    last_error: Optional[str] = None
    
    # Delivery info
    delivered_at: Optional[float] = None
    mx_host: Optional[str] = None
    
    def is_final_state(self) -> bool:
        """Check if in final state (delivered or bounced)"""
        return self.state in [
            DeliveryState.DELIVERED,
            DeliveryState.BOUNCE,
            DeliveryState.EXPIRED
        ]
    
    def is_temporary_failure(self) -> bool:
        """Check if last failure was temporary"""
        if self.smtp_code is None:
            return False
        return 400 <= self.smtp_code < 500
    
    def is_permanent_failure(self) -> bool:
        """Check if last failure was permanent"""
        if self.smtp_code is None:
            return False
        return 500 <= self.smtp_code < 600
    
    def record_attempt(self, smtp_code: int, smtp_message: str):
        """Record delivery attempt"""
        self.attempts += 1
        self.last_attempt = time.time()
        self.smtp_code = smtp_code
        self.smtp_message = smtp_message
        
        # Update state based on SMTP code
        if 200 <= smtp_code < 300:
            self.state = DeliveryState.DELIVERED
            self.delivered_at = time.time()
        elif 400 <= smtp_code < 500:
            self.state = DeliveryState.DEFERRED
            self.last_error = f"{smtp_code} {smtp_message}"
        elif 500 <= smtp_code < 600:
            self.state = DeliveryState.BOUNCE
            self.last_error = f"{smtp_code} {smtp_message}"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'recipient': self.recipient,
            'state': self.state.value,
            'attempts': self.attempts,
            'last_attempt': self.last_attempt,
            'next_attempt': self.next_attempt,
            'smtp_code': self.smtp_code,
            'smtp_message': self.smtp_message,
            'last_error': self.last_error,
            'delivered_at': self.delivered_at,
            'mx_host': self.mx_host
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RecipientStatus':
        state = DeliveryState(data['state']) if 'state' in data else DeliveryState.PENDING
        return cls(
            recipient=data['recipient'],
            state=state,
            attempts=data.get('attempts', 0),
            last_attempt=data.get('last_attempt'),
            next_attempt=data.get('next_attempt'),
            smtp_code=data.get('smtp_code'),
            smtp_message=data.get('smtp_message'),
            last_error=data.get('last_error'),
            delivered_at=data.get('delivered_at'),
            mx_host=data.get('mx_host')
        )


@dataclass
class DeliveryStatus:
    """
    Overall delivery status for a queued message
    """
    queue_id: str
    sender: str
    recipients: Dict[str, RecipientStatus] = field(default_factory=dict)
    
    # Overall status
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    
    def add_recipient(self, recipient: str):
        """Add recipient to track"""
        if recipient not in self.recipients:
            self.recipients[recipient] = RecipientStatus(recipient=recipient)
    
    def update_recipient(self, recipient: str, smtp_code: int, smtp_message: str, mx_host: str = None):
        """Update recipient status"""
        if recipient not in self.recipients:
            self.add_recipient(recipient)
        
        status = self.recipients[recipient]
        status.record_attempt(smtp_code, smtp_message)
        if mx_host:
            status.mx_host = mx_host
        
        self.updated_at = time.time()
    
    def all_delivered(self) -> bool:
        """Check if all recipients delivered"""
        return all(
            status.state == DeliveryState.DELIVERED
            for status in self.recipients.values()
        )
    
    def any_pending(self) -> bool:
        """Check if any recipients still pending"""
        return any(
            status.state in [DeliveryState.PENDING, DeliveryState.DEFERRED]
            for status in self.recipients.values()
        )
    
    def pending_recipients(self) -> list:
        """Get list of pending recipients"""
        return [
            rcpt for rcpt, status in self.recipients.items()
            if status.state in [DeliveryState.PENDING, DeliveryState.DEFERRED]
        ]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'queue_id': self.queue_id,
            'sender': self.sender,
            'recipients': {
                rcpt: status.to_dict()
                for rcpt, status in self.recipients.items()
            },
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }
