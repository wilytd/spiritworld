"""
Pydantic schemas for API request/response validation.
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


# --- Response Models ---

class BandwidthStatsResponse(BaseModel):
    """Bandwidth statistics for a network interface."""
    interface: str
    rx_bytes: int = 0
    tx_bytes: int = 0
    rx_rate: float = Field(default=0.0, description="Receive rate in bytes/sec")
    tx_rate: float = Field(default=0.0, description="Transmit rate in bytes/sec")
    provider: str = "none"


class NetworkClientResponse(BaseModel):
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
    provider: str = "none"


class DNSStatsResponse(BaseModel):
    """DNS query statistics."""
    queries_today: int = 0
    blocked_today: int = 0
    percent_blocked: float = 0.0
    domains_blocked: int = 0
    top_queries: List[dict] = Field(default_factory=list)
    top_blocked: List[dict] = Field(default_factory=list)
    provider: str = "none"


class VPNPeerResponse(BaseModel):
    """WireGuard VPN peer."""
    name: str
    public_key: str
    allowed_ips: List[str] = Field(default_factory=list)
    endpoint: Optional[str] = None
    last_handshake: Optional[datetime] = None
    transfer_rx: int = 0
    transfer_tx: int = 0
    enabled: bool = True


class ClientHealthResponse(BaseModel):
    """Health status for an API client."""
    name: str
    configured: bool = False
    connected: bool = False
    state: str = "disconnected"
    last_error: Optional[str] = None
    request_count: int = 0
    error_count: int = 0


class HealthResponse(BaseModel):
    """Overall service health status."""
    status: str = "healthy"
    clients: List[ClientHealthResponse] = Field(default_factory=list)


# --- Request Models ---

class DomainBlockRequest(BaseModel):
    """Request to block a domain."""
    domain: str = Field(..., description="Domain to add to blocklist")


class DomainAllowRequest(BaseModel):
    """Request to allow a domain."""
    domain: str = Field(..., description="Domain to add to allowlist")


class VPNPeerCreateRequest(BaseModel):
    """Request to create a new WireGuard peer."""
    name: str = Field(..., description="Name for the peer")
    allowed_ips: List[str] = Field(
        default_factory=lambda: ["10.0.0.0/24"],
        description="IP ranges allowed for this peer"
    )


# --- Common Response Wrappers ---

class SuccessResponse(BaseModel):
    """Generic success response."""
    success: bool = True
    message: str = ""


class ErrorResponse(BaseModel):
    """Generic error response."""
    success: bool = False
    error: str
    detail: Optional[str] = None


class TrafficResponse(BaseModel):
    """Traffic data response wrapper."""
    bandwidth: List[BandwidthStatsResponse] = Field(default_factory=list)
    provider: str = "none"


class ClientsResponse(BaseModel):
    """Connected clients response wrapper."""
    clients: List[NetworkClientResponse] = Field(default_factory=list)
    total: int = 0
    provider: str = "none"


class VPNPeersResponse(BaseModel):
    """VPN peers response wrapper."""
    peers: List[VPNPeerResponse] = Field(default_factory=list)
    total: int = 0
