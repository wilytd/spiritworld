"""
VPN (WireGuard) management endpoints.
"""

from typing import Optional

from fastapi import APIRouter, HTTPException

from schemas import (
    VPNPeerResponse,
    VPNPeersResponse,
    VPNPeerCreateRequest,
    SuccessResponse,
)


router = APIRouter(prefix="/vpn", tags=["vpn"])

# Client instance will be set by main.py
opnsense_client = None


def set_clients(opnsense):
    """Set client instance (called from main.py)."""
    global opnsense_client
    opnsense_client = opnsense


@router.get("/peers", response_model=VPNPeersResponse)
async def get_vpn_peers():
    """
    Get all WireGuard peers and their status.

    Requires OPNsense to be configured with WireGuard.
    """
    if not opnsense_client or not opnsense_client.is_connected:
        return VPNPeersResponse(peers=[], total=0)

    peers = await opnsense_client.get_wireguard_status()
    peer_responses = [VPNPeerResponse(**p.to_dict()) for p in peers]

    return VPNPeersResponse(
        peers=peer_responses,
        total=len(peer_responses),
    )


@router.get("/peers/{name}", response_model=VPNPeerResponse)
async def get_vpn_peer(name: str):
    """
    Get a specific WireGuard peer by name.

    Requires OPNsense to be configured with WireGuard.
    """
    if not opnsense_client or not opnsense_client.is_connected:
        raise HTTPException(
            status_code=503,
            detail="OPNsense not available. Configure OPNSENSE_URL, KEY, and SECRET."
        )

    peers = await opnsense_client.get_wireguard_status()
    for peer in peers:
        if peer.name.lower() == name.lower():
            return VPNPeerResponse(**peer.to_dict())

    raise HTTPException(status_code=404, detail=f"Peer '{name}' not found")


@router.post("/peers", response_model=SuccessResponse)
async def create_vpn_peer(request: VPNPeerCreateRequest):
    """
    Create a new WireGuard peer.

    Requires OPNsense to be configured with WireGuard.
    """
    if not opnsense_client or not opnsense_client.is_connected:
        raise HTTPException(
            status_code=503,
            detail="OPNsense not available. Configure OPNSENSE_URL, KEY, and SECRET."
        )

    result = await opnsense_client.add_wireguard_peer(
        name=request.name,
        allowed_ips=request.allowed_ips,
    )

    if result:
        return SuccessResponse(
            success=True,
            message=f"WireGuard peer '{request.name}' created successfully",
        )

    return SuccessResponse(
        success=False,
        message=f"Failed to create WireGuard peer '{request.name}'",
    )


@router.delete("/peers/{name}", response_model=SuccessResponse)
async def delete_vpn_peer(name: str):
    """
    Delete a WireGuard peer by name.

    Requires OPNsense to be configured with WireGuard.
    """
    if not opnsense_client or not opnsense_client.is_connected:
        raise HTTPException(
            status_code=503,
            detail="OPNsense not available. Configure OPNSENSE_URL, KEY, and SECRET."
        )

    # First find the peer UUID
    clients = await opnsense_client.get_wireguard_clients()
    peer_uuid = None
    for client in clients:
        if client.get("name", "").lower() == name.lower():
            peer_uuid = client.get("uuid")
            break

    if not peer_uuid:
        raise HTTPException(status_code=404, detail=f"Peer '{name}' not found")

    success = await opnsense_client.delete_wireguard_peer(peer_uuid)

    return SuccessResponse(
        success=success,
        message=f"WireGuard peer '{name}' {'deleted' if success else 'deletion failed'}",
    )


@router.get("/peers/{name}/config")
async def get_vpn_peer_config(name: str):
    """
    Get the WireGuard configuration for a peer.

    Returns the configuration that can be used to set up the peer's device.
    Requires OPNsense to be configured with WireGuard.
    """
    if not opnsense_client or not opnsense_client.is_connected:
        raise HTTPException(
            status_code=503,
            detail="OPNsense not available. Configure OPNSENSE_URL, KEY, and SECRET."
        )

    # Find the peer UUID
    clients = await opnsense_client.get_wireguard_clients()
    peer_uuid = None
    for client in clients:
        if client.get("name", "").lower() == name.lower():
            peer_uuid = client.get("uuid")
            break

    if not peer_uuid:
        raise HTTPException(status_code=404, detail=f"Peer '{name}' not found")

    config = await opnsense_client.get_wireguard_peer_config(peer_uuid)
    if not config:
        raise HTTPException(
            status_code=404,
            detail=f"Configuration not available for peer '{name}'"
        )

    return {"name": name, "config": config}
