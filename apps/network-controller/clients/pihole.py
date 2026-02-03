"""
Pi-hole API client for DNS statistics and blocking.
"""

import logging
from typing import Optional

import httpx

from config import PiholeConfig
from models import DNSStats, Provider
from .base import BaseClient


logger = logging.getLogger(__name__)


class PiholeClient(BaseClient):
    """
    Client for Pi-hole Admin API.

    API Documentation: https://discourse.pi-hole.net/t/pi-hole-api/1863

    Authentication: Token passed as query parameter
    """

    def __init__(self, config: PiholeConfig):
        super().__init__("Pi-hole")
        self.config = config

    @property
    def is_configured(self) -> bool:
        return self.config.is_configured

    async def _create_client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            base_url=self.config.url,
            timeout=self.timeout,
        )

    async def _test_connection(self) -> bool:
        """Test connection by fetching summary."""
        try:
            response = await self._client.get(
                "/admin/api.php",
                params={"summary": "", "auth": self.config.token},
            )
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Pi-hole connection test failed: {e}")
            return False

    def _auth_params(self, params: Optional[dict] = None) -> dict:
        """Add auth token to params."""
        result = params or {}
        result["auth"] = self.config.token
        return result

    # --- Statistics Methods ---

    async def get_stats(self) -> Optional[DNSStats]:
        """Get DNS query statistics."""
        data = await self.get(
            "/admin/api.php",
            params=self._auth_params({"summary": ""}),
        )
        if not data:
            return None

        return DNSStats(
            queries_today=int(data.get("dns_queries_today", 0)),
            blocked_today=int(data.get("ads_blocked_today", 0)),
            percent_blocked=float(data.get("ads_percentage_today", 0)),
            domains_blocked=int(data.get("domains_being_blocked", 0)),
            provider=Provider.PIHOLE,
        )

    async def get_top_queries(self, count: int = 10) -> list:
        """Get top DNS queries."""
        data = await self.get(
            "/admin/api.php",
            params=self._auth_params({"topItems": str(count)}),
        )
        if not data:
            return []

        queries = []
        for domain, hits in data.get("top_queries", {}).items():
            queries.append({"domain": domain, "hits": hits})
        return queries

    async def get_top_blocked(self, count: int = 10) -> list:
        """Get top blocked domains."""
        data = await self.get(
            "/admin/api.php",
            params=self._auth_params({"topItems": str(count)}),
        )
        if not data:
            return []

        blocked = []
        for domain, hits in data.get("top_ads", {}).items():
            blocked.append({"domain": domain, "hits": hits})
        return blocked

    async def get_stats_with_top(self, top_count: int = 10) -> Optional[DNSStats]:
        """Get stats including top queries and blocked domains."""
        stats = await self.get_stats()
        if not stats:
            return None

        stats.top_queries = await self.get_top_queries(top_count)
        stats.top_blocked = await self.get_top_blocked(top_count)
        return stats

    # --- Blocking Methods ---

    async def add_to_blacklist(self, domain: str) -> bool:
        """Add a domain to the blacklist."""
        data = await self.get(
            "/admin/api.php",
            params=self._auth_params({"list": "black", "add": domain}),
        )
        if data and data.get("success"):
            logger.info(f"Pi-hole: Added {domain} to blacklist")
            return True
        return False

    async def add_to_whitelist(self, domain: str) -> bool:
        """Add a domain to the whitelist."""
        data = await self.get(
            "/admin/api.php",
            params=self._auth_params({"list": "white", "add": domain}),
        )
        if data and data.get("success"):
            logger.info(f"Pi-hole: Added {domain} to whitelist")
            return True
        return False

    async def remove_from_blacklist(self, domain: str) -> bool:
        """Remove a domain from the blacklist."""
        data = await self.get(
            "/admin/api.php",
            params=self._auth_params({"list": "black", "sub": domain}),
        )
        if data and data.get("success"):
            logger.info(f"Pi-hole: Removed {domain} from blacklist")
            return True
        return False

    async def remove_from_whitelist(self, domain: str) -> bool:
        """Remove a domain from the whitelist."""
        data = await self.get(
            "/admin/api.php",
            params=self._auth_params({"list": "white", "sub": domain}),
        )
        if data and data.get("success"):
            logger.info(f"Pi-hole: Removed {domain} from whitelist")
            return True
        return False

    # --- Control Methods ---

    async def enable(self) -> bool:
        """Enable Pi-hole blocking."""
        data = await self.get(
            "/admin/api.php",
            params=self._auth_params({"enable": ""}),
        )
        return data and data.get("status") == "enabled"

    async def disable(self, seconds: int = 0) -> bool:
        """
        Disable Pi-hole blocking.

        Args:
            seconds: Duration to disable. 0 = indefinitely.
        """
        params = {"disable": str(seconds) if seconds > 0 else ""}
        data = await self.get(
            "/admin/api.php",
            params=self._auth_params(params),
        )
        return data and data.get("status") == "disabled"
