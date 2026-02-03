"""
Aegis Mesh - Network Controller Service
Integration with OPNsense, Unifi, Pi-hole, and WireGuard.
Phase 1: Placeholder with API structure defined.
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, List
import os

app = FastAPI(
    title="Aegis Network Controller",
    description="Network infrastructure management for home lab",
    version="0.1.0"
)

# Configuration - to be set via environment variables
OPNSENSE_URL = os.getenv("OPNSENSE_URL")
OPNSENSE_KEY = os.getenv("OPNSENSE_KEY")
OPNSENSE_SECRET = os.getenv("OPNSENSE_SECRET")

UNIFI_URL = os.getenv("UNIFI_URL")
UNIFI_USER = os.getenv("UNIFI_USER")
UNIFI_PASS = os.getenv("UNIFI_PASS")

PIHOLE_URL = os.getenv("PIHOLE_URL")
PIHOLE_TOKEN = os.getenv("PIHOLE_TOKEN")

class BandwidthStats(BaseModel):
    interface: str
    rx_bytes: int
    tx_bytes: int
    rx_rate: float
    tx_rate: float

class DNSStats(BaseModel):
    queries_today: int
    blocked_today: int
    percent_blocked: float
    domains_blocked: int

class VPNPeer(BaseModel):
    name: str
    public_key: str
    allowed_ips: List[str]
    last_handshake: Optional[str]
    transfer_rx: int
    transfer_tx: int

@app.get("/")
async def root():
    return {
        "service": "Aegis Network Controller",
        "version": "0.1.0",
        "status": "placeholder",
        "message": "Network integrations to be implemented in Phase 2"
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

# --- Traffic Management (OPNsense/Unifi) ---

@app.get("/traffic/bandwidth")
async def get_bandwidth() -> List[BandwidthStats]:
    """Get current bandwidth usage by interface"""
    # TODO: Implement OPNsense/Unifi API integration
    raise HTTPException(
        status_code=501,
        detail="Bandwidth monitoring not yet implemented. Configure OPNSENSE_URL or UNIFI_URL."
    )

@app.get("/traffic/clients")
async def get_clients():
    """Get list of connected clients"""
    # TODO: Implement client listing
    raise HTTPException(
        status_code=501,
        detail="Client listing not yet implemented."
    )

# --- DNS/Ad-blocking (Pi-hole/AdGuard) ---

@app.get("/dns/stats")
async def get_dns_stats() -> DNSStats:
    """Get DNS query statistics"""
    # TODO: Implement Pi-hole API integration
    raise HTTPException(
        status_code=501,
        detail="DNS stats not yet implemented. Configure PIHOLE_URL and PIHOLE_TOKEN."
    )

@app.post("/dns/block")
async def block_domain(domain: str):
    """Add domain to blocklist"""
    # TODO: Implement domain blocking
    raise HTTPException(
        status_code=501,
        detail="Domain blocking not yet implemented."
    )

@app.post("/dns/allow")
async def allow_domain(domain: str):
    """Add domain to allowlist"""
    # TODO: Implement domain allowing
    raise HTTPException(
        status_code=501,
        detail="Domain allowing not yet implemented."
    )

# --- VPN Management (WireGuard) ---

@app.get("/vpn/peers")
async def get_vpn_peers() -> List[VPNPeer]:
    """Get WireGuard peer status"""
    # TODO: Implement WireGuard status
    raise HTTPException(
        status_code=501,
        detail="VPN peer listing not yet implemented."
    )

@app.post("/vpn/peers")
async def add_vpn_peer(name: str):
    """Generate new WireGuard peer configuration"""
    # TODO: Implement peer generation
    raise HTTPException(
        status_code=501,
        detail="VPN peer creation not yet implemented."
    )

@app.delete("/vpn/peers/{peer_name}")
async def remove_vpn_peer(peer_name: str):
    """Remove a WireGuard peer"""
    # TODO: Implement peer removal
    raise HTTPException(
        status_code=501,
        detail="VPN peer removal not yet implemented."
    )

# --- VLAN Management ---

@app.get("/vlans")
async def get_vlans():
    """Get VLAN configuration"""
    # TODO: Implement VLAN listing
    raise HTTPException(
        status_code=501,
        detail="VLAN management not yet implemented."
    )
