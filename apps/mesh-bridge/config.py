"""
Configuration for the Mesh Bridge service.
"""

import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class MeshtasticConfig:
    """Configuration for Meshtastic connection."""
    device_path: str = os.getenv("MESH_DEVICE_PATH", "/dev/ttyUSB0")
    reconnect_delay: float = float(os.getenv("MESH_RECONNECT_DELAY", "5.0"))
    max_reconnect_attempts: int = int(os.getenv("MESH_MAX_RECONNECT_ATTEMPTS", "10"))
    reconnect_backoff_multiplier: float = float(os.getenv("MESH_RECONNECT_BACKOFF", "1.5"))
    message_timeout: float = float(os.getenv("MESH_MESSAGE_TIMEOUT", "30.0"))


@dataclass
class NomadNetConfig:
    """Configuration for NomadNet/Reticulum connection."""
    identity_path: Optional[str] = os.getenv("NOMADNET_IDENTITY_PATH")
    storage_path: str = os.getenv("NOMADNET_STORAGE_PATH", "/var/lib/aegis/nomadnet")
    announce_interval: int = int(os.getenv("NOMADNET_ANNOUNCE_INTERVAL", "300"))
    enable_propagation: bool = os.getenv("NOMADNET_ENABLE_PROPAGATION", "true").lower() == "true"


@dataclass
class AlertConfig:
    """Configuration for alert routing."""
    critical_priority_threshold: int = int(os.getenv("ALERT_CRITICAL_THRESHOLD", "1"))
    high_priority_threshold: int = int(os.getenv("ALERT_HIGH_THRESHOLD", "2"))
    escalation_timeout: float = float(os.getenv("ALERT_ESCALATION_TIMEOUT", "300.0"))
    max_retries: int = int(os.getenv("ALERT_MAX_RETRIES", "3"))
    isp_check_interval: float = float(os.getenv("ISP_CHECK_INTERVAL", "60.0"))
    isp_check_hosts: list = None

    def __post_init__(self):
        hosts_str = os.getenv("ISP_CHECK_HOSTS", "8.8.8.8,1.1.1.1")
        self.isp_check_hosts = hosts_str.split(",")


@dataclass
class QueueConfig:
    """Configuration for message queue."""
    max_queue_size: int = int(os.getenv("QUEUE_MAX_SIZE", "1000"))
    batch_size: int = int(os.getenv("QUEUE_BATCH_SIZE", "10"))
    flush_interval: float = float(os.getenv("QUEUE_FLUSH_INTERVAL", "1.0"))
    persistence_path: str = os.getenv("QUEUE_PERSISTENCE_PATH", "/var/lib/aegis/queue")


class Config:
    """Main configuration container."""
    meshtastic: MeshtasticConfig = MeshtasticConfig()
    nomadnet: NomadNetConfig = NomadNetConfig()
    alerts: AlertConfig = AlertConfig()
    queue: QueueConfig = QueueConfig()


config = Config()
