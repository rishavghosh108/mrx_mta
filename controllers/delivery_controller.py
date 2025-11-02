"""
Delivery Controller - Orchestrate delivery workers
"""
import asyncio
import logging
from typing import List

from services.queue_service import QueueService
from services.delivery_service import DeliveryService
import config

logger = logging.getLogger(__name__)


class DeliveryWorker:
    """
    Individual delivery worker
    Processes messages from the queue
    """
    
    def __init__(self, worker_id: int, queue_service: QueueService, 
                 delivery_service: DeliveryService):
        self.worker_id = worker_id
        self.queue_service = queue_service
        self.delivery_service = delivery_service
        self.running = False
        self.task = None
    
    async def start(self):
        """Start the worker"""
        self.running = True
        self.task = asyncio.create_task(self._run())
        logger.info(f"Delivery worker {self.worker_id} started")
    
    async def stop(self):
        """Stop the worker"""
        self.running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        logger.info(f"Delivery worker {self.worker_id} stopped")
    
    async def _run(self):
        """Main worker loop"""
        while self.running:
            try:
                # Get messages ready for delivery
                messages = await self.queue_service.get_messages_for_delivery(limit=10)
                
                if not messages:
                    # No messages ready, sleep
                    await asyncio.sleep(config.DELIVERY_INTERVAL)
                    continue
                
                # Process messages
                for message in messages:
                    if not self.running:
                        break
                    
                    try:
                        logger.debug(f"Worker {self.worker_id} processing message {message.queue_id}")
                        await self.delivery_service.deliver_message(message)
                    except Exception as e:
                        logger.exception(f"[{message.queue_id}] Worker {self.worker_id} error: {e}")
                        # Update with temporary failure
                        for recipient in message.pending_recipients():
                            await self.queue_service.update_delivery_status(
                                message.queue_id, recipient, 451, f"Worker error: {str(e)}"
                            )
            
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.exception(f"Worker {self.worker_id} error: {e}")
                await asyncio.sleep(5)


class DeliveryController:
    """
    Delivery Controller - Manages pool of delivery workers
    """
    
    def __init__(self, queue_service: QueueService, delivery_service: DeliveryService,
                 num_workers: int = None):
        self.queue_service = queue_service
        self.delivery_service = delivery_service
        self.num_workers = num_workers or config.DELIVERY_WORKERS
        self.workers: List[DeliveryWorker] = []
    
    async def start(self):
        """Start all delivery workers"""
        for i in range(self.num_workers):
            worker = DeliveryWorker(i, self.queue_service, self.delivery_service)
            await worker.start()
            self.workers.append(worker)
        
        logger.info(f"Started {self.num_workers} delivery workers")
    
    async def stop(self):
        """Stop all delivery workers"""
        logger.info("Stopping delivery workers...")
        
        # Stop all workers
        stop_tasks = [worker.stop() for worker in self.workers]
        await asyncio.gather(*stop_tasks, return_exceptions=True)
        
        self.workers.clear()
        logger.info("All delivery workers stopped")
    
    async def restart(self):
        """Restart all delivery workers"""
        await self.stop()
        await self.start()
    
    def get_worker_count(self) -> int:
        """Get number of active workers"""
        return len([w for w in self.workers if w.running])
    
    async def add_worker(self):
        """Add a new worker to the pool"""
        worker_id = len(self.workers)
        worker = DeliveryWorker(worker_id, self.queue_service, self.delivery_service)
        await worker.start()
        self.workers.append(worker)
        logger.info(f"Added delivery worker {worker_id}")
    
    async def remove_worker(self):
        """Remove a worker from the pool"""
        if not self.workers:
            return False
        
        worker = self.workers.pop()
        await worker.stop()
        logger.info(f"Removed delivery worker {worker.worker_id}")
        return True
