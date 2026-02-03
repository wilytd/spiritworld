"""
Data models for the Mesh Bridge service.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any, List
import uuid


class MessageStatus(Enum):
    """Status of a message in the queue."""
    PENDING = "pending"
    SENDING = "sending"
    DELIVERED = "delivered"
    FAILED = "failed"
    ACKNOWLEDGED = "acknowledged"


class AlertPriority(Enum):
    """Priority levels for alerts."""
    CRITICAL = 1
    HIGH = 2
    MEDIUM = 3
    LOW = 4
    INFO = 5


class Protocol(Enum):
    """Communication protocol types."""
    MESHTASTIC = "meshtastic"
    NOMADNET = "nomadnet"
    BOTH = "both"


@dataclass
class MeshNode:
    """Represents a node in the mesh network."""
    node_id: str
    long_name: Optional[str] = None
    short_name: Optional[str] = None
    hw_model: Optional[str] = None
    snr: Optional[float] = None
    rssi: Optional[int] = None
    last_heard: Optional[datetime] = None
    battery_level: Optional[int] = None
    voltage: Optional[float] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    altitude: Optional[float] = None
    is_licensed: bool = False
    role: Optional[str] = None
    hops_away: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "node_id": self.node_id,
            "long_name": self.long_name,
            "short_name": self.short_name,
            "hw_model": self.hw_model,
            "snr": self.snr,
            "rssi": self.rssi,
            "last_heard": self.last_heard.isoformat() if self.last_heard else None,
            "battery_level": self.battery_level,
            "voltage": self.voltage,
            "position": {
                "latitude": self.latitude,
                "longitude": self.longitude,
                "altitude": self.altitude
            } if self.latitude is not None else None,
            "is_licensed": self.is_licensed,
            "role": self.role,
            "hops_away": self.hops_away
        }


@dataclass
class QueuedMessage:
    """A message queued for sending."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    text: str = ""
    destination: Optional[str] = None  # None = broadcast
    priority: AlertPriority = AlertPriority.MEDIUM
    protocol: Protocol = Protocol.MESHTASTIC
    status: MessageStatus = MessageStatus.PENDING
    created_at: datetime = field(default_factory=datetime.utcnow)
    sent_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    retry_count: int = 0
    max_retries: int = 3
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "id": self.id,
            "text": self.text,
            "destination": self.destination,
            "priority": self.priority.name,
            "protocol": self.protocol.name,
            "status": self.status.name,
            "created_at": self.created_at.isoformat(),
            "sent_at": self.sent_at.isoformat() if self.sent_at else None,
            "delivered_at": self.delivered_at.isoformat() if self.delivered_at else None,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "metadata": self.metadata
        }


@dataclass
class DeliveryConfirmation:
    """Confirmation of message delivery."""
    message_id: str
    node_id: str
    received_at: datetime = field(default_factory=datetime.utcnow)
    acknowledged: bool = False
    acknowledged_at: Optional[datetime] = None


@dataclass
class Alert:
    """An alert to be sent via mesh network."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    title: str = ""
    message: str = ""
    priority: AlertPriority = AlertPriority.MEDIUM
    source: str = "aegis-core"
    category: str = "general"
    created_at: datetime = field(default_factory=datetime.utcnow)
    acknowledged: bool = False
    acknowledged_by: Optional[str] = None
    acknowledged_at: Optional[datetime] = None
    escalated: bool = False
    escalated_at: Optional[datetime] = None
    routing_protocol: Protocol = Protocol.MESHTASTIC
    target_nodes: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_mesh_message(self) -> str:
        """Format alert for mesh transmission."""
        priority_prefix = {
            AlertPriority.CRITICAL: "[!!!]",
            AlertPriority.HIGH: "[!!]",
            AlertPriority.MEDIUM: "[!]",
            AlertPriority.LOW: "[i]",
            AlertPriority.INFO: "[.]"
        }
        prefix = priority_prefix.get(self.priority, "[?]")
        return f"{prefix} {self.title}: {self.message}"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "id": self.id,
            "title": self.title,
            "message": self.message,
            "priority": self.priority.name,
            "source": self.source,
            "category": self.category,
            "created_at": self.created_at.isoformat(),
            "acknowledged": self.acknowledged,
            "acknowledged_by": self.acknowledged_by,
            "acknowledged_at": self.acknowledged_at.isoformat() if self.acknowledged_at else None,
            "escalated": self.escalated,
            "escalated_at": self.escalated_at.isoformat() if self.escalated_at else None,
            "routing_protocol": self.routing_protocol.name,
            "target_nodes": self.target_nodes,
            "metadata": self.metadata
        }


@dataclass
class ISPStatus:
    """Status of ISP connectivity."""
    is_online: bool = True
    last_check: datetime = field(default_factory=datetime.utcnow)
    failed_checks: int = 0
    latency_ms: Optional[float] = None
    failover_active: bool = False
    failover_triggered_at: Optional[datetime] = None
