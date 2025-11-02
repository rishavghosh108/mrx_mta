"""
Queue Repository - Handles message queue persistence
"""
import json
import sqlite3
import asyncio
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any
from email.utils import make_msgid

from models.message import QueuedMessage, Message

logger = logging.getLogger(__name__)


class QueueRepository:
    """
    Repository for QueuedMessage entities
    Uses SQLite for durable storage
    """
    
    def __init__(self, db_path: str, message_dir: str = None):
        self.db_path = db_path
        self.message_dir = message_dir or str(Path(db_path).parent / "queue")
        self.lock = asyncio.Lock()
        self._init_db()
        self._ensure_message_dir()
    
    def _init_db(self):
        """Initialize database schema"""
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS queue (
                queue_id TEXT PRIMARY KEY,
                sender TEXT NOT NULL,
                recipients TEXT NOT NULL,
                message_path TEXT NOT NULL,
                session_info TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at REAL NOT NULL,
                next_retry_at REAL,
                attempts INTEGER DEFAULT 0,
                last_error TEXT,
                recipient_status TEXT NOT NULL
            )
        """)
        
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_status 
            ON queue(status)
        """)
        
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_next_retry 
            ON queue(next_retry_at)
            WHERE next_retry_at IS NOT NULL
        """)
        
        conn.commit()
        conn.close()
        logger.info(f"Initialized queue database at {self.db_path}")
    
    def _ensure_message_dir(self):
        """Ensure message directory exists"""
        Path(self.message_dir).mkdir(parents=True, exist_ok=True)
    
    def _get_message_path(self, queue_id: str) -> str:
        """Get filesystem path for message data"""
        return str(Path(self.message_dir) / f"{queue_id}.eml")
    
    async def enqueue(self, message: Message) -> QueuedMessage:
        """Add message to queue"""
        async with self.lock:
            queue_id = make_msgid().strip('<>')
            
            # Save message data to filesystem
            message_path = self._get_message_path(queue_id)
            Path(message_path).write_text(message.data)
            
            # Create queued message
            queued_msg = QueuedMessage(
                queue_id=queue_id,
                message=message
            )
            
            # Save to database
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()
            
            cur.execute("""
                INSERT INTO queue (
                    queue_id, sender, recipients, message_path,
                    session_info, status, created_at, next_retry_at,
                    attempts, last_error, recipient_status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                queued_msg.queue_id,
                queued_msg.message.sender,
                json.dumps(queued_msg.message.recipients),
                message_path,
                json.dumps(queued_msg.message.session_info),
                queued_msg.status,
                queued_msg.created_at,
                queued_msg.next_retry_at,
                queued_msg.attempts,
                queued_msg.last_error,
                json.dumps(queued_msg.recipient_status)
            ))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Enqueued message {queue_id} from {message.sender}")
            return queued_msg
    
    async def find_by_id(self, queue_id: str) -> Optional[QueuedMessage]:
        """Find message by queue ID"""
        async with self.lock:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            
            cur.execute("""
                SELECT * FROM queue WHERE queue_id = ?
            """, (queue_id,))
            
            row = cur.fetchone()
            conn.close()
            
            if row:
                return self._row_to_queued_message(row)
            return None
    
    async def find_ready_for_delivery(self, limit: int = 100) -> List[QueuedMessage]:
        """Find messages ready for delivery"""
        async with self.lock:
            import time
            now = time.time()
            
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            
            cur.execute("""
                SELECT * FROM queue
                WHERE status IN ('active', 'deferred')
                AND (next_retry_at IS NULL OR next_retry_at <= ?)
                ORDER BY created_at ASC
                LIMIT ?
            """, (now, limit))
            
            rows = cur.fetchall()
            conn.close()
            
            return [self._row_to_queued_message(row) for row in rows]
    
    async def update(self, queued_msg: QueuedMessage) -> bool:
        """Update queued message"""
        async with self.lock:
            try:
                conn = sqlite3.connect(self.db_path)
                cur = conn.cursor()
                
                cur.execute("""
                    UPDATE queue SET
                        status = ?,
                        next_retry_at = ?,
                        attempts = ?,
                        last_error = ?,
                        recipient_status = ?
                    WHERE queue_id = ?
                """, (
                    queued_msg.status,
                    queued_msg.next_retry_at,
                    queued_msg.attempts,
                    queued_msg.last_error,
                    json.dumps(queued_msg.recipient_status),
                    queued_msg.queue_id
                ))
                
                conn.commit()
                conn.close()
                return True
            except Exception as e:
                logger.error(f"Failed to update message {queued_msg.queue_id}: {e}")
                return False
    
    async def delete(self, queue_id: str) -> bool:
        """Delete message from queue"""
        async with self.lock:
            try:
                # Delete from database
                conn = sqlite3.connect(self.db_path)
                cur = conn.cursor()
                cur.execute("DELETE FROM queue WHERE queue_id = ?", (queue_id,))
                conn.commit()
                conn.close()
                
                # Delete message file
                message_path = self._get_message_path(queue_id)
                Path(message_path).unlink(missing_ok=True)
                
                logger.info(f"Deleted message {queue_id}")
                return True
            except Exception as e:
                logger.error(f"Failed to delete message {queue_id}: {e}")
                return False
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get queue statistics"""
        async with self.lock:
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()
            
            # Count by status
            cur.execute("""
                SELECT status, COUNT(*) as count
                FROM queue
                GROUP BY status
            """)
            status_counts = {row[0]: row[1] for row in cur.fetchall()}
            
            # Total messages
            cur.execute("SELECT COUNT(*) FROM queue")
            total = cur.fetchone()[0]
            
            conn.close()
            
            return {
                'total': total,
                'by_status': status_counts
            }
    
    async def find_by_status(self, status: str, limit: int = 100) -> List[QueuedMessage]:
        """Find messages by status"""
        async with self.lock:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            
            cur.execute("""
                SELECT * FROM queue
                WHERE status = ?
                ORDER BY created_at DESC
                LIMIT ?
            """, (status, limit))
            
            rows = cur.fetchall()
            conn.close()
            
            return [self._row_to_queued_message(row) for row in rows]
    
    def _row_to_queued_message(self, row: sqlite3.Row) -> QueuedMessage:
        """Convert database row to QueuedMessage"""
        # Load message data from filesystem
        message_data = Path(row['message_path']).read_text()
        
        message = Message(
            sender=row['sender'],
            recipients=json.loads(row['recipients']),
            data=message_data,
            session_info=json.loads(row['session_info'])
        )
        
        return QueuedMessage(
            queue_id=row['queue_id'],
            message=message,
            status=row['status'],
            created_at=row['created_at'],
            next_retry_at=row['next_retry_at'],
            attempts=row['attempts'],
            last_error=row['last_error'],
            recipient_status=json.loads(row['recipient_status'])
        )
