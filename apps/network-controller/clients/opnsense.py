"""
OPNsense API client for firewall, traffic, and WireGuard management.
"""

import logging
from datetime import datetime
from typing import List, Optional

import httpx

from config import OPNsenseConfig
from models import BandwidthStats, NetworkClient, VPNPeer, Provider
from .base import BaseClient


logger = logging.getLogger(__name__)


class OPNsenseClient(BaseClient):
    """
    Client for OPNsense REST API.

    API Documentation: https://docs.opnsense.org/development/api.html

    Authentication: HTTP Basic Auth with API key (username) and secret (password)
    """

    def __init__(self, config: OPNsenseConfig):
        super().__init__("OPNsense")
        self.config = config

    @property
    def is_configured(self) -> bool:
        return self.config.is_configured

    async def _create_client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            base_url=self.config.url,
            auth=(self.config.key, self.config.secret),
            verify=self.config.verify_ssl,
            timeout=self.timeout,
        )

    async def _test_connection(self) -> bool:
        """Test connection by fetching system info."""
        try:
            response = await self._client.get("/api/core/system/status")
            return response.status_code == 200
        except Exception as e:
            logger.error(f"OPNsense connection test failed: {e}")
            return False

    # --- Bandwidth / Traffic Methods ---

    async def get_interface_statistics(self) -> List[BandwidthStats]:
        """Get traffic statistics for all interfaces."""
        data = await self.get("/api/diagnostics/interface/getInterfaceStatistics")
        if not data or "statistics" not in data:
            return []

        stats = []
        for iface, iface_data in data.get("statistics", {}).items():
            stats.append(BandwidthStats(
                interface=iface,
                rx_bytes=int(iface_data.get("bytes received", 0)),
                tx_bytes=int(iface_data.get("bytes transmitted", 0)),
                rx_rate=float(iface_data.get("inpkts rate", 0)),
                tx_rate=float(iface_data.get("outpkts rate", 0)),
                provider=Provider.OPNSENSE,
            ))
        return stats

    async def get_top_traffic(self, interface: str = "wan") -> Optional[BandwidthStats]:
        """Get top traffic data for a specific interface."""
        data = await self.get(f"/api/diagnostics/traffic/top/{interface}")
        if not data:
            return None

        # Aggregate totals from top traffic data
        rx_total = 0
        tx_total = 0
        rx_rate = 0.0
        tx_rate = 0.0

        for entry in data.get("records", []):
            rx_total += int(entry.get("bytes_received", 0))
            tx_total += int(entry.get("bytes_sent", 0))
            rx_rate += float(entry.get("rate_received", 0))
            tx_rate += float(entry.get("rate_sent", 0))

        return BandwidthStats(
            interface=interface,
            rx_bytes=rx_total,
            tx_bytes=tx_total,
            rx_rate=rx_rate,
            tx_rate=tx_rate,
            provider=Provider.OPNSENSE,
        )

    # --- Client / Device Methods ---

    async def get_arp_table(self) -> List[NetworkClient]:
        """Get ARP table entries as network clients."""
        data = await self.get("/api/diagnostics/interface/getArp")
        if not data:
            return []

        clients = []
        for entry in data:
            clients.append(NetworkClient(
                mac=entry.get("mac", ""),
                ip=entry.get("ip", ""),
                hostname=entry.get("hostname"),
                interface=entry.get("intf"),
                vendor=entry.get("manufacturer"),
                provider=Provider.OPNSENSE,
            ))
        return clients

    # --- WireGuard VPN Methods ---

    async def get_wireguard_status(self) -> List[VPNPeer]:
        """Get WireGuard peer status."""
        data = await self.get("/api/wireguard/general/status")
        if not data or "peers" not in data:
            return []

        peers = []
        for peer_data in data.get("peers", []):
            last_handshake = None
            if peer_data.get("latest_handshake"):
                try:
                    last_handshake = datetime.fromtimestamp(
                        int(peer_data["latest_handshake"])
                    )
                except (ValueError, TypeError):
                    pass

            peers.append(VPNPeer(
                name=peer_data.get("name", peer_data.get("public_key", "")[:8]),
                public_key=peer_data.get("public_key", ""),
                allowed_ips=peer_data.get("allowed_ips", "").split(","),
                endpoint=peer_data.get("endpoint"),
                last_handshake=last_handshake,
                transfer_rx=int(peer_data.get("transfer_rx", 0)),
                transfer_tx=int(peer_data.get("transfer_tx", 0)),
                enabled=peer_data.get("enabled", "1") == "1",
            ))
        return peers

    async def get_wireguard_clients(self) -> List[dict]:
        """Get configured WireGuard clients."""
        data = await self.get("/api/wireguard/client/searchClient")
        if not data or "rows" not in data:
            return []
        return data.get("rows", [])

    async def add_wireguard_peer(
        self,
        name: str,
        allowed_ips: List[str],
        server_uuid: Optional[str] = None,
    ) -> Optional[dict]:
        """
        Add a new WireGuard peer/client.

        Returns the created peer configuration or None on failure.
        """
        # First get server UUID if not provided
        if not server_uuid:
            servers = await self.get("/api/wireguard/server/searchServer")
            if servers and servers.get("rows"):
                server_uuid = servers["rows"][0].get("uuid")

        if not server_uuid:
            logger.error("No WireGuard server found")
            return None

        # Add the client
        payload = {
            "client": {
                "name": name,
                "tunneladdress": ",".join(allowed_ips),
                "servers": server_uuid,
                "enabled": "1",
            }
        }

        result = await self.post("/api/wireguard/client/addClient", json=payload)
        if result and result.get("uuid"):
            # Apply changes
            await self.post("/api/wireguard/service/reconfigure")
            return result
        return None

    async def delete_wireguard_peer(self, peer_uuid: str) -> bool:
        """Delete a WireGuard peer by UUID."""
        result = await self.post(f"/api/wireguard/client/delClient/{peer_uuid}")
        if result and result.get("result") == "deleted":
            await self.post("/api/wireguard/service/reconfigure")
            return True
        return False

    async def get_wireguard_peer_config(self, peer_uuid: str) -> Optional[str]:
        """Get WireGuard client configuration (for QR code or download)."""
        data = await self.get(f"/api/wireguard/client/getClientConfig/{peer_uuid}")
        if data and "config" in data:
            return data["config"]
        return None
