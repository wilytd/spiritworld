"""
Traffic monitoring endpoints.
"""

from typing import Optional

from fastapi import APIRouter, Query

from models import Provider
from schemas import (
    BandwidthStatsResponse,
    NetworkClientResponse,
    TrafficResponse,
    ClientsResponse,
)


router = APIRouter(prefix="/traffic", tags=["traffic"])

# Client instances will be set by main.py
opnsense_client = None
unifi_client = None


def set_clients(opnsense, unifi):
    """Set client instances (called from main.py)."""
    global opnsense_client, unifi_client
    opnsense_client = opnsense
    unifi_client = unifi


@router.get("/bandwidth", response_model=TrafficResponse)
async def get_bandwidth(
    provider: Optional[str] = Query(
        None, description="Force specific provider: opnsense, unifi"
    ),
):
    """
    Get bandwidth statistics for all interfaces.

    Tries OPNsense first, falls back to Unifi if not available.
    Use ?provider= to force a specific source.
    """
    bandwidth = []
    used_provider = Provider.NONE

    # Try requested provider or fall through
    if provider == "opnsense" or (provider is None and opnsense_client):
        if opnsense_client and opnsense_client.is_connected:
            stats = await opnsense_client.get_interface_statistics()
            if stats:
                bandwidth = [BandwidthStatsResponse(**s.to_dict()) for s in stats]
                used_provider = Provider.OPNSENSE

    if not bandwidth and (provider == "unifi" or provider is None):
        if unifi_client and unifi_client.is_connected:
            stats = await unifi_client.get_bandwidth_stats()
            if stats:
                bandwidth = [BandwidthStatsResponse(**s.to_dict()) for s in stats]
                used_provider = Provider.UNIFI

    return TrafficResponse(
        bandwidth=bandwidth,
        provider=used_provider.value,
    )


@router.get("/bandwidth/{interface}", response_model=BandwidthStatsResponse)
async def get_interface_bandwidth(
    interface: str,
    provider: Optional[str] = Query(None, description="Force specific provider"),
):
    """
    Get bandwidth statistics for a specific interface.

    Currently only supported via OPNsense.
    """
    if opnsense_client and opnsense_client.is_connected:
        stats = await opnsense_client.get_top_traffic(interface)
        if stats:
            return BandwidthStatsResponse(**stats.to_dict())

    # Return empty stats with none provider
    return BandwidthStatsResponse(
        interface=interface,
        rx_bytes=0,
        tx_bytes=0,
        rx_rate=0.0,
        tx_rate=0.0,
        provider="none",
    )


@router.get("/clients", response_model=ClientsResponse)
async def get_clients(
    provider: Optional[str] = Query(
        None, description="Force specific provider: opnsense, unifi"
    ),
):
    """
    Get all connected network clients.

    Tries Unifi first (richer data), falls back to OPNsense ARP table.
    Use ?provider= to force a specific source.
    """
    clients = []
    used_provider = Provider.NONE

    # Prefer Unifi for client data (has more info)
    if provider == "unifi" or (provider is None and unifi_client):
        if unifi_client and unifi_client.is_connected:
            client_list = await unifi_client.get_clients()
            if client_list:
                clients = [NetworkClientResponse(**c.to_dict()) for c in client_list]
                used_provider = Provider.UNIFI

    if not clients and (provider == "opnsense" or provider is None):
        if opnsense_client and opnsense_client.is_connected:
            client_list = await opnsense_client.get_arp_table()
            if client_list:
                clients = [NetworkClientResponse(**c.to_dict()) for c in client_list]
                used_provider = Provider.OPNSENSE

    return ClientsResponse(
        clients=clients,
        total=len(clients),
        provider=used_provider.value,
    )


@router.get("/clients/{mac}", response_model=NetworkClientResponse)
async def get_client_by_mac(mac: str):
    """
    Get a specific client by MAC address.

    Currently only supported via Unifi.
    """
    if unifi_client and unifi_client.is_connected:
        client = await unifi_client.get_client_by_mac(mac)
        if client:
            return NetworkClientResponse(**client.to_dict())

    # Return minimal response
    return NetworkClientResponse(
        mac=mac,
        provider="none",
    )
