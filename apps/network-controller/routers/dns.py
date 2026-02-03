"""
DNS statistics and blocking endpoints.
"""

from typing import Optional

from fastapi import APIRouter, Query, HTTPException

from models import Provider
from schemas import (
    DNSStatsResponse,
    DomainBlockRequest,
    DomainAllowRequest,
    SuccessResponse,
)


router = APIRouter(prefix="/dns", tags=["dns"])

# Client instances will be set by main.py
pihole_client = None
adguard_client = None


def set_clients(pihole, adguard):
    """Set client instances (called from main.py)."""
    global pihole_client, adguard_client
    pihole_client = pihole
    adguard_client = adguard


def _get_active_client():
    """Get the first available DNS client."""
    if pihole_client and pihole_client.is_connected:
        return pihole_client, Provider.PIHOLE
    if adguard_client and adguard_client.is_connected:
        return adguard_client, Provider.ADGUARD
    return None, Provider.NONE


@router.get("/stats", response_model=DNSStatsResponse)
async def get_dns_stats(
    provider: Optional[str] = Query(
        None, description="Force specific provider: pihole, adguard"
    ),
    include_top: bool = Query(True, description="Include top queries/blocked"),
    top_count: int = Query(10, ge=1, le=100, description="Number of top items"),
):
    """
    Get DNS query statistics.

    Tries Pi-hole first, falls back to AdGuard if not available.
    Use ?provider= to force a specific source.
    """
    stats = None

    # Try requested provider or fall through
    if provider == "pihole" or (provider is None and pihole_client):
        if pihole_client and pihole_client.is_connected:
            if include_top:
                stats = await pihole_client.get_stats_with_top(top_count)
            else:
                stats = await pihole_client.get_stats()

    if not stats and (provider == "adguard" or provider is None):
        if adguard_client and adguard_client.is_connected:
            if include_top:
                stats = await adguard_client.get_stats_with_top(top_count)
            else:
                stats = await adguard_client.get_stats()

    if stats:
        return DNSStatsResponse(**stats.to_dict())

    # Return empty stats
    return DNSStatsResponse(provider="none")


@router.post("/block", response_model=SuccessResponse)
async def block_domain(
    request: DomainBlockRequest,
    provider: Optional[str] = Query(None, description="Force specific provider"),
):
    """
    Add a domain to the blocklist.

    Uses first available DNS provider (Pi-hole or AdGuard).
    """
    client, used_provider = _get_active_client()

    if provider == "pihole" and pihole_client and pihole_client.is_connected:
        client, used_provider = pihole_client, Provider.PIHOLE
    elif provider == "adguard" and adguard_client and adguard_client.is_connected:
        client, used_provider = adguard_client, Provider.ADGUARD

    if not client:
        raise HTTPException(
            status_code=503,
            detail="No DNS provider available. Configure Pi-hole or AdGuard."
        )

    success = await client.add_to_blacklist(request.domain)
    return SuccessResponse(
        success=success,
        message=f"Domain {request.domain} {'added to' if success else 'failed to add to'} blocklist via {used_provider.value}",
    )


@router.post("/allow", response_model=SuccessResponse)
async def allow_domain(
    request: DomainAllowRequest,
    provider: Optional[str] = Query(None, description="Force specific provider"),
):
    """
    Add a domain to the allowlist (whitelist).

    Uses first available DNS provider (Pi-hole or AdGuard).
    """
    client, used_provider = _get_active_client()

    if provider == "pihole" and pihole_client and pihole_client.is_connected:
        client, used_provider = pihole_client, Provider.PIHOLE
    elif provider == "adguard" and adguard_client and adguard_client.is_connected:
        client, used_provider = adguard_client, Provider.ADGUARD

    if not client:
        raise HTTPException(
            status_code=503,
            detail="No DNS provider available. Configure Pi-hole or AdGuard."
        )

    success = await client.add_to_whitelist(request.domain)
    return SuccessResponse(
        success=success,
        message=f"Domain {request.domain} {'added to' if success else 'failed to add to'} allowlist via {used_provider.value}",
    )


@router.delete("/block/{domain}", response_model=SuccessResponse)
async def unblock_domain(
    domain: str,
    provider: Optional[str] = Query(None, description="Force specific provider"),
):
    """
    Remove a domain from the blocklist.

    Uses first available DNS provider (Pi-hole or AdGuard).
    """
    client, used_provider = _get_active_client()

    if provider == "pihole" and pihole_client and pihole_client.is_connected:
        client, used_provider = pihole_client, Provider.PIHOLE
    elif provider == "adguard" and adguard_client and adguard_client.is_connected:
        client, used_provider = adguard_client, Provider.ADGUARD

    if not client:
        raise HTTPException(
            status_code=503,
            detail="No DNS provider available. Configure Pi-hole or AdGuard."
        )

    success = await client.remove_from_blacklist(domain)
    return SuccessResponse(
        success=success,
        message=f"Domain {domain} {'removed from' if success else 'failed to remove from'} blocklist via {used_provider.value}",
    )
