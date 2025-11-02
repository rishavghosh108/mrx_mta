"""
Queue Service - Business logic for message queue management
"""
import logging
import random
import time
from typing import List, Optional, Dict, Any

from models.message import Message, QueuedMessage
from repositories.queue_repository import QueueRepository
import config

logger = logging.getLogger(__name__)


class QueueService:
    """
    Queue management business logic
    Handles enqueuing, retry scheduling, and queue operations
    """
    
    def __init__(self, queue_repository: QueueRepository):
        self.queue_repo = queue_repository
    
    async def enqueue_message(self, sender: str, recipients: List[str], 
                             message_data: str, session_info: Dict[str, Any] = None) -> QueuedMessage:
        """
        Enqueue a new message for delivery
        """
        # Create message entity
        message = Message(
            sender=sender,
            recipients=recipients,
            data=message_data,
            session_info=session_info or {}
        )
        
        # Validate message
        if not message.validate():
            raise ValueError("Invalid message: missing required fields")
        
        # Enqueue
        queued_msg = await self.queue_repo.enqueue(message)
        logger.info(f"Enqueued message {queued_msg.queue_id} from {sender} to {len(recipients)} recipients")
        
        return queued_msg
    
    async def get_messages_for_delivery(self, limit: int = 100) -> List[QueuedMessage]:
        """
        Get messages ready for delivery
        """
        messages = await self.queue_repo.find_ready_for_delivery(limit)
        logger.debug(f"Retrieved {len(messages)} messages for delivery")
        return messages
    
    async def update_delivery_status(self, queue_id: str, recipient: str, 
                                    smtp_code: int, smtp_message: str):
        """
        Update delivery status for a recipient
        """
        queued_msg = await self.queue_repo.find_by_id(queue_id)
        if not queued_msg:
            logger.error(f"Message not found: {queue_id}")
            return False
        
        # Update recipient status
        if recipient in queued_msg.recipient_status:
            status = queued_msg.recipient_status[recipient]
            status['attempts'] += 1
            status['last_attempt'] = time.time()
            
            if 200 <= smtp_code < 300:
                # Success
                status['status'] = 'delivered'
                logger.info(f"Message {queue_id} delivered to {recipient}")
            elif 400 <= smtp_code < 500:
                # Temporary failure
                status['status'] = 'deferred'
                status['last_error'] = f"{smtp_code} {smtp_message}"
                logger.warning(f"Temporary failure for {queue_id}/{recipient}: {smtp_code} {smtp_message}")
            elif 500 <= smtp_code < 600:
                # Permanent failure
                status['status'] = 'bounce'
                status['last_error'] = f"{smtp_code} {smtp_message}"
                logger.warning(f"Permanent failure for {queue_id}/{recipient}: {smtp_code} {smtp_message}")
        
        # Update overall message status
        queued_msg.attempts += 1
        queued_msg.last_error = f"{smtp_code} {smtp_message}"
        
        # Calculate next retry if needed
        if queued_msg.pending_recipients():
            queued_msg.next_retry_at = self._calculate_next_retry(queued_msg.attempts)
            queued_msg.status = 'deferred'
        else:
            # All recipients processed
            if queued_msg.all_delivered():
                queued_msg.status = 'delivered'
                logger.info(f"Message {queue_id} fully delivered")
            else:
                queued_msg.status = 'bounce'
                logger.warning(f"Message {queue_id} bounced")
        
        # Check if expired
        if queued_msg.is_expired(config.MAX_QUEUE_AGE):
            queued_msg.status = 'bounce'
            logger.warning(f"Message {queue_id} expired")
        
        # Save updates
        await self.queue_repo.update(queued_msg)
        return True
    
    async def get_message(self, queue_id: str) -> Optional[QueuedMessage]:
        """Get message by ID"""
        return await self.queue_repo.find_by_id(queue_id)
    
    async def delete_message(self, queue_id: str) -> bool:
        """Delete message from queue"""
        result = await self.queue_repo.delete(queue_id)
        if result:
            logger.info(f"Deleted message {queue_id}")
        return result
    
    async def requeue_message(self, queue_id: str) -> bool:
        """Requeue message for immediate delivery"""
        queued_msg = await self.queue_repo.find_by_id(queue_id)
        if not queued_msg:
            return False
        
        # Reset retry time and status
        queued_msg.next_retry_at = None
        queued_msg.status = 'active'
        
        # Reset pending recipients
        for recipient, status in queued_msg.recipient_status.items():
            if status['status'] in ['deferred', 'bounce']:
                status['status'] = 'pending'
        
        await self.queue_repo.update(queued_msg)
        logger.info(f"Requeued message {queue_id}")
        return True
    
    async def get_queue_stats(self) -> Dict[str, Any]:
        """Get queue statistics"""
        stats = await self.queue_repo.get_stats()
        
        # Add additional computed stats
        stats['pending'] = stats['by_status'].get('active', 0) + stats['by_status'].get('deferred', 0)
        stats['completed'] = stats['by_status'].get('delivered', 0) + stats['by_status'].get('bounce', 0)
        
        return stats
    
    async def get_messages_by_status(self, status: str, limit: int = 100) -> List[QueuedMessage]:
        """Get messages filtered by status"""
        return await self.queue_repo.find_by_status(status, limit)
    
    def _calculate_next_retry(self, attempts: int) -> Optional[float]:
        """
        Calculate next retry time with exponential backoff + jitter
        """
        if attempts >= len(config.RETRY_SCHEDULE):
            return None  # Max retries exceeded
        
        delay = config.RETRY_SCHEDULE[attempts]
        
        # Add jitter (±20%)
        jitter = delay * 0.2 * (random.random() - 0.5) * 2
        delay_with_jitter = delay + jitter
        
        return time.time() + delay_with_jitter
    
    async def cleanup_old_messages(self, max_age: int = None):
        """Clean up old delivered/bounced messages"""
        max_age = max_age or config.MAX_QUEUE_AGE * 2
        
        for status in ['delivered', 'bounce']:
            messages = await self.queue_repo.find_by_status(status, limit=1000)
            
            cleaned = 0
            for msg in messages:
                if (time.time() - msg.created_at) > max_age:
                    await self.queue_repo.delete(msg.queue_id)
                    cleaned += 1
            
            if cleaned > 0:
                logger.info(f"Cleaned up {cleaned} old {status} messages")
