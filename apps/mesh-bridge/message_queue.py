"""
Priority-based message queue with persistence for outbound mesh alerts.
"""

import asyncio
import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any, Callable
from collections import defaultdict
import heapq
import threading

from .config import config
from .models import QueuedMessage, MessageStatus, AlertPriority, Protocol

logger = logging.getLogger(__name__)


class PriorityQueue:
    """Thread-safe priority queue for messages."""

    def __init__(self):
        self._heap: List[tuple] = []
        self._lock = threading.Lock()
        self._counter = 0

    def push(self, message: QueuedMessage):
        """Add message to queue with priority ordering."""
        with self._lock:
            # Priority value (lower = higher priority), counter for FIFO within same priority
            priority_val = message.priority.value
            heapq.heappush(self._heap, (priority_val, self._counter, message))
            self._counter += 1

    def pop(self) -> Optional[QueuedMessage]:
        """Remove and return highest priority message."""
        with self._lock:
            if self._heap:
                _, _, message = heapq.heappop(self._heap)
                return message
            return None

    def peek(self) -> Optional[QueuedMessage]:
        """Return highest priority message without removing."""
        with self._lock:
            if self._heap:
                return self._heap[0][2]
            return None

    def size(self) -> int:
        """Return number of messages in queue."""
        with self._lock:
            return len(self._heap)

    def is_empty(self) -> bool:
        """Check if queue is empty."""
        with self._lock:
            return len(self._heap) == 0

    def get_all(self) -> List[QueuedMessage]:
        """Get all messages without removing them."""
        with self._lock:
            return [msg for _, _, msg in sorted(self._heap)]

    def remove(self, message_id: str) -> bool:
        """Remove a specific message by ID."""
        with self._lock:
            for i, (_, _, msg) in enumerate(self._heap):
                if msg.id == message_id:
                    self._heap.pop(i)
                    heapq.heapify(self._heap)
                    return True
            return False


class MessageQueue:
    """
    Persistent message queue for outbound mesh alerts.

    Features:
    - Priority-based message ordering
    - Persistent storage for crash recovery
    - Automatic retry with exponential backoff
    - Batch processing support
    - Statistics and monitoring
    """

    def __init__(self, send_callback: Optional[Callable] = None):
        self.queue = PriorityQueue()
        self.send_callback = send_callback
        self.failed_messages: Dict[str, QueuedMessage] = {}
        self.sent_messages: Dict[str, QueuedMessage] = {}
        self._running = False
        self._process_task: Optional[asyncio.Task] = None
        self._persistence_path = Path(config.queue.persistence_path)
        self._lock = threading.Lock()

        # Statistics
        self.stats = {
            "total_queued": 0,
            "total_sent": 0,
            "total_failed": 0,
            "total_retried": 0,
            "avg_queue_time_ms": 0
        }

        # Ensure persistence directory exists
        self._persistence_path.mkdir(parents=True, exist_ok=True)

    async def start(self):
        """Start the message queue processor."""
        self._running = True
        await self._load_persisted_messages()
        self._process_task = asyncio.create_task(self._process_loop())
        logger.info("Message queue started")

    async def stop(self):
        """Stop the queue processor and persist remaining messages."""
        self._running = False
        if self._process_task:
            self._process_task.cancel()
            try:
                await self._process_task
            except asyncio.CancelledError:
                pass
        await self._persist_messages()
        logger.info("Message queue stopped")

    def set_send_callback(self, callback: Callable):
        """Set the callback for sending messages."""
        self.send_callback = callback

    async def enqueue(
        self,
        text: str,
        destination: Optional[str] = None,
        priority: AlertPriority = AlertPriority.MEDIUM,
        protocol: Protocol = Protocol.MESHTASTIC,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Add a message to the queue.

        Returns:
            Message ID
        """
        if self.queue.size() >= config.queue.max_queue_size:
            logger.warning("Queue full, dropping lowest priority message")
            self._drop_lowest_priority()

        message = QueuedMessage(
            text=text,
            destination=destination,
            priority=priority,
            protocol=protocol,
            max_retries=config.alerts.max_retries,
            metadata=metadata or {}
        )

        self.queue.push(message)
        self.stats["total_queued"] += 1

        logger.debug(f"Enqueued message {message.id} with priority {priority.name}")
        return message.id

    async def enqueue_message(self, message: QueuedMessage) -> str:
        """Add an existing message object to the queue."""
        if self.queue.size() >= config.queue.max_queue_size:
            logger.warning("Queue full, dropping lowest priority message")
            self._drop_lowest_priority()

        self.queue.push(message)
        self.stats["total_queued"] += 1
        return message.id

    def _drop_lowest_priority(self):
        """Remove lowest priority message to make room."""
        messages = self.queue.get_all()
        if messages:
            # Find lowest priority (highest value)
            lowest = max(messages, key=lambda m: m.priority.value)
            self.queue.remove(lowest.id)
            self.failed_messages[lowest.id] = lowest
            lowest.status = MessageStatus.FAILED
            logger.warning(f"Dropped message {lowest.id} due to queue overflow")

    async def _process_loop(self):
        """Main processing loop for the queue."""
        while self._running:
            try:
                await self._process_batch()
                await asyncio.sleep(config.queue.flush_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in queue processing loop: {e}")
                await asyncio.sleep(1)

    async def _process_batch(self):
        """Process a batch of messages from the queue."""
        if not self.send_callback or self.queue.is_empty():
            return

        batch_count = 0
        while batch_count < config.queue.batch_size and not self.queue.is_empty():
            message = self.queue.pop()
            if message:
                await self._send_message(message)
                batch_count += 1

    async def _send_message(self, message: QueuedMessage):
        """Attempt to send a single message."""
        message.status = MessageStatus.SENDING
        message.sent_at = datetime.utcnow()

        try:
            # Call the send callback
            result = await self.send_callback(message)

            if result:
                message.status = MessageStatus.DELIVERED
                message.delivered_at = datetime.utcnow()
                self.sent_messages[message.id] = message
                self.stats["total_sent"] += 1

                # Calculate average queue time
                queue_time = (message.delivered_at - message.created_at).total_seconds() * 1000
                total = self.stats["total_sent"]
                self.stats["avg_queue_time_ms"] = (
                    (self.stats["avg_queue_time_ms"] * (total - 1) + queue_time) / total
                )

                logger.info(f"Message {message.id} delivered")
            else:
                await self._handle_send_failure(message)

        except Exception as e:
            logger.error(f"Error sending message {message.id}: {e}")
            await self._handle_send_failure(message)

    async def _handle_send_failure(self, message: QueuedMessage):
        """Handle a failed message send attempt."""
        message.retry_count += 1
        self.stats["total_retried"] += 1

        if message.retry_count < message.max_retries:
            # Re-queue with backoff
            message.status = MessageStatus.PENDING
            # Lower priority for retries
            if message.priority != AlertPriority.CRITICAL:
                message.priority = AlertPriority(
                    min(message.priority.value + 1, AlertPriority.INFO.value)
                )
            self.queue.push(message)
            logger.warning(f"Message {message.id} retry {message.retry_count}/{message.max_retries}")
        else:
            # Max retries exceeded
            message.status = MessageStatus.FAILED
            self.failed_messages[message.id] = message
            self.stats["total_failed"] += 1
            logger.error(f"Message {message.id} failed after {message.max_retries} retries")

    async def _persist_messages(self):
        """Persist queue to disk for crash recovery."""
        try:
            data = {
                "pending": [msg.to_dict() for msg in self.queue.get_all()],
                "failed": [msg.to_dict() for msg in self.failed_messages.values()],
                "stats": self.stats,
                "timestamp": datetime.utcnow().isoformat()
            }

            persist_file = self._persistence_path / "queue.json"
            with open(persist_file, "w") as f:
                json.dump(data, f, indent=2)

            logger.info(f"Persisted {len(data['pending'])} pending messages")

        except Exception as e:
            logger.error(f"Error persisting message queue: {e}")

    async def _load_persisted_messages(self):
        """Load persisted messages from disk."""
        persist_file = self._persistence_path / "queue.json"
        if not persist_file.exists():
            return

        try:
            with open(persist_file, "r") as f:
                data = json.load(f)

            # Restore pending messages
            for msg_data in data.get("pending", []):
                message = self._dict_to_message(msg_data)
                if message:
                    self.queue.push(message)

            # Restore failed messages
            for msg_data in data.get("failed", []):
                message = self._dict_to_message(msg_data)
                if message:
                    self.failed_messages[message.id] = message

            logger.info(f"Loaded {self.queue.size()} persisted messages")

        except Exception as e:
            logger.error(f"Error loading persisted messages: {e}")

    def _dict_to_message(self, data: Dict) -> Optional[QueuedMessage]:
        """Convert dictionary to QueuedMessage."""
        try:
            return QueuedMessage(
                id=data["id"],
                text=data["text"],
                destination=data.get("destination"),
                priority=AlertPriority[data["priority"]],
                protocol=Protocol[data["protocol"]],
                status=MessageStatus[data["status"]],
                created_at=datetime.fromisoformat(data["created_at"]),
                retry_count=data.get("retry_count", 0),
                max_retries=data.get("max_retries", 3),
                metadata=data.get("metadata", {})
            )
        except Exception as e:
            logger.error(f"Error converting message data: {e}")
            return None

    def get_queue_status(self) -> Dict[str, Any]:
        """Get current queue status."""
        return {
            "pending": self.queue.size(),
            "failed": len(self.failed_messages),
            "sent": len(self.sent_messages),
            "stats": self.stats
        }

    def get_message(self, message_id: str) -> Optional[QueuedMessage]:
        """Get a specific message by ID."""
        # Check pending queue
        for msg in self.queue.get_all():
            if msg.id == message_id:
                return msg

        # Check sent/failed
        return self.sent_messages.get(message_id) or self.failed_messages.get(message_id)

    def retry_failed(self, message_id: str) -> bool:
        """Retry a specific failed message."""
        if message_id in self.failed_messages:
            message = self.failed_messages.pop(message_id)
            message.status = MessageStatus.PENDING
            message.retry_count = 0
            self.queue.push(message)
            return True
        return False

    def retry_all_failed(self) -> int:
        """Retry all failed messages. Returns count of retried messages."""
        count = 0
        for msg_id in list(self.failed_messages.keys()):
            if self.retry_failed(msg_id):
                count += 1
        return count

    def clear_sent_history(self):
        """Clear sent message history to free memory."""
        self.sent_messages.clear()

    def clear_failed(self):
        """Clear failed messages."""
        self.failed_messages.clear()
