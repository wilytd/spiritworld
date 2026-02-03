"""
Unifi Controller API client for network monitoring.
"""

import logging
from datetime import datetime
from typing import List, Optional

import httpx

from config import UnifiConfig
from models import BandwidthStats, NetworkClient, Provider
from .base import BaseClient


logger = logging.getLogger(__name__)


class UnifiClient(BaseClient):
    """
    Client for Unifi Controller API.

    Authentication: Cookie-based session after POST /api/login
    """

    def __init__(self, config: UnifiConfig):
        super().__init__("Unifi")
        self.config = config
        self._cookies: Optional[httpx.Cookies] = None

    @property
    def is_configured(self) -> bool:
        return self.config.is_configured

    async def _create_client(self) -> httpx.AsyncClient:
        client = httpx.AsyncClient(
            base_url=self.config.url,
            verify=self.config.verify_ssl,
            timeout=self.timeout,
        )
        # Authenticate
        await self._authenticate(client)
        return client

    async def _authenticate(self, client: httpx.AsyncClient) -> bool:
        """Authenticate with Unifi Controller."""
        try:
            response = await client.post(
                "/api/login",
                json={
                    "username": self.config.username,
                    "password": self.config.password,
                },
            )
            if response.status_code == 200:
                self._cookies = response.cookies
                client.cookies = self._cookies
                return True
            logger.error(f"Unifi auth failed: {response.status_code}")
            return False
        except Exception as e:
            logger.error(f"Unifi auth error: {e}")
            return False

    async def _test_connection(self) -> bool:
        """Test connection by fetching site info."""
        try:
            response = await self._client.get("/api/self/sites")
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Unifi connection test failed: {e}")
            return False

    # --- Client / Device Methods ---

    async def get_clients(self) -> List[NetworkClient]:
        """Get all connected clients."""
        data = await self.get(f"/api/s/{self.config.site}/stat/sta")
        if not data or "data" not in data:
            return []

        clients = []
        for client_data in data.get("data", []):
            last_seen = None
            if client_data.get("last_seen"):
                try:
                    last_seen = datetime.fromtimestamp(client_data["last_seen"])
                except (ValueError, TypeError):
                    pass

            clients.append(NetworkClient(
                mac=client_data.get("mac", ""),
                ip=client_data.get("ip"),
                hostname=client_data.get("hostname") or client_data.get("name"),
                vendor=client_data.get("oui"),
                interface=client_data.get("network"),
                vlan=client_data.get("vlan"),
                rx_bytes=int(client_data.get("rx_bytes", 0)),
                tx_bytes=int(client_data.get("tx_bytes", 0)),
                last_seen=last_seen,
                is_wired=client_data.get("is_wired", False),
                provider=Provider.UNIFI,
            ))
        return clients

    async def get_client_by_mac(self, mac: str) -> Optional[NetworkClient]:
        """Get a specific client by MAC address."""
        clients = await self.get_clients()
        mac_lower = mac.lower().replace("-", ":")
        for client in clients:
            if client.mac.lower() == mac_lower:
                return client
        return None

    # --- Traffic / Health Methods ---

    async def get_health(self) -> Optional[dict]:
        """Get network health information."""
        data = await self.get(f"/api/s/{self.config.site}/stat/health")
        if data and "data" in data:
            return data["data"]
        return None

    async def get_bandwidth_stats(self) -> List[BandwidthStats]:
        """
        Get bandwidth statistics from Unifi.

        Note: Unifi doesn't provide per-interface bandwidth the same way
        OPNsense does, so we aggregate from network health data.
        """
        health = await self.get_health()
        if not health:
            return []

        stats = []
        for subsystem in health:
            if subsystem.get("subsystem") in ("wlan", "lan", "wan"):
                stats.append(BandwidthStats(
                    interface=subsystem.get("subsystem", "unknown"),
                    rx_bytes=int(subsystem.get("rx_bytes-r", 0)),
                    tx_bytes=int(subsystem.get("tx_bytes-r", 0)),
                    rx_rate=float(subsystem.get("rx_bytes-r", 0)),
                    tx_rate=float(subsystem.get("tx_bytes-r", 0)),
                    provider=Provider.UNIFI,
                ))
        return stats

    async def get_devices(self) -> List[dict]:
        """Get all Unifi devices (APs, switches, etc.)."""
        data = await self.get(f"/api/s/{self.config.site}/stat/device")
        if data and "data" in data:
            return data["data"]
        return []

    async def get_networks(self) -> List[dict]:
        """Get configured networks."""
        data = await self.get(f"/api/s/{self.config.site}/rest/networkconf")
        if data and "data" in data:
            return data["data"]
        return []
