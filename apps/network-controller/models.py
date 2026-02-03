"""
Data models and enums for the network-controller service.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class ConnectionState(str, Enum):
    """Connection state for API clients."""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    FAILED = "failed"


class Provider(str, Enum):
    """Service provider identifiers."""
    OPNSENSE = "opnsense"
    UNIFI = "unifi"
    PIHOLE = "pihole"
    ADGUARD = "adguard"
    NONE = "none"


@dataclass
class BandwidthStats:
    """Bandwidth statistics for a network interface."""
    interface: str
    rx_bytes: int = 0
    tx_bytes: int = 0
    rx_rate: float = 0.0
    tx_rate: float = 0.0
    provider: Provider = Provider.NONE

    def to_dict(self) -> dict:
        return {
            "interface": self.interface,
            "rx_bytes": self.rx_bytes,
            "tx_bytes": self.tx_bytes,
            "rx_rate": self.rx_rate,
            "tx_rate": self.tx_rate,
            "provider": self.provider.value,
        }


@dataclass
class NetworkClient:
    """A client connected to the network."""
    mac: str
    ip: Optional[str] = None
    hostname: Optional[str] = None
    vendor: Optional[str] = None
    interface: Optional[str] = None
    vlan: Optional[int] = None
    rx_bytes: int = 0
    tx_bytes: int = 0
    last_seen: Optional[datetime] = None
    is_wired: bool = False
    provider: Provider = Provider.NONE

    def to_dict(self) -> dict:
        return {
            "mac": self.mac,
            "ip": self.ip,
            "hostname": self.hostname,
            "vendor": self.vendor,
            "interface": self.interface,
            "vlan": self.vlan,
            "rx_bytes": self.rx_bytes,
            "tx_bytes": self.tx_bytes,
            "last_seen": self.last_seen.isoformat() if self.last_seen else None,
            "is_wired": self.is_wired,
            "provider": self.provider.value,
        }


@dataclass
class DNSStats:
    """DNS query statistics."""
    queries_today: int = 0
    blocked_today: int = 0
    percent_blocked: float = 0.0
    domains_blocked: int = 0
    top_queries: list = field(default_factory=list)
    top_blocked: list = field(default_factory=list)
    provider: Provider = Provider.NONE

    def to_dict(self) -> dict:
        return {
            "queries_today": self.queries_today,
            "blocked_today": self.blocked_today,
            "percent_blocked": self.percent_blocked,
            "domains_blocked": self.domains_blocked,
            "top_queries": self.top_queries,
            "top_blocked": self.top_blocked,
            "provider": self.provider.value,
        }


@dataclass
class VPNPeer:
    """WireGuard VPN peer."""
    name: str
    public_key: str
    allowed_ips: list = field(default_factory=list)
    endpoint: Optional[str] = None
    last_handshake: Optional[datetime] = None
    transfer_rx: int = 0
    transfer_tx: int = 0
    enabled: bool = True

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "public_key": self.public_key,
            "allowed_ips": self.allowed_ips,
            "endpoint": self.endpoint,
            "last_handshake": self.last_handshake.isoformat() if self.last_handshake else None,
            "transfer_rx": self.transfer_rx,
            "transfer_tx": self.transfer_tx,
            "enabled": self.enabled,
        }


@dataclass
class ClientHealth:
    """Health status for an API client."""
    name: str
    configured: bool = False
    connected: bool = False
    state: ConnectionState = ConnectionState.DISCONNECTED
    last_error: Optional[str] = None
    request_count: int = 0
    error_count: int = 0

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "configured": self.configured,
            "connected": self.connected,
            "state": self.state.value,
            "last_error": self.last_error,
            "request_count": self.request_count,
            "error_count": self.error_count,
        }
