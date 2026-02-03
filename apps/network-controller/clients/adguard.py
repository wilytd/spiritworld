"""
AdGuard Home API client for DNS statistics and blocking.
"""

import logging
from typing import Optional

import httpx

from config import AdGuardConfig
from models import DNSStats, Provider
from .base import BaseClient


logger = logging.getLogger(__name__)


class AdGuardClient(BaseClient):
    """
    Client for AdGuard Home API.

    API Documentation: https://github.com/AdguardTeam/AdGuardHome/tree/master/openapi

    Authentication: HTTP Basic Auth
    """

    def __init__(self, config: AdGuardConfig):
        super().__init__("AdGuard")
        self.config = config

    @property
    def is_configured(self) -> bool:
        return self.config.is_configured

    async def _create_client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            base_url=self.config.url,
            auth=(self.config.username, self.config.password),
            timeout=self.timeout,
        )

    async def _test_connection(self) -> bool:
        """Test connection by fetching status."""
        try:
            response = await self._client.get("/control/status")
            return response.status_code == 200
        except Exception as e:
            logger.error(f"AdGuard connection test failed: {e}")
            return False

    # --- Statistics Methods ---

    async def get_stats(self) -> Optional[DNSStats]:
        """Get DNS query statistics."""
        data = await self.get("/control/stats")
        if not data:
            return None

        queries_today = sum(data.get("dns_queries", []))
        blocked_today = sum(data.get("blocked_filtering", []))
        percent = (blocked_today / queries_today * 100) if queries_today > 0 else 0

        # Get blocklist count
        status = await self.get("/control/filtering/status")
        domains_blocked = 0
        if status:
            for filter_list in status.get("filters", []):
                if filter_list.get("enabled"):
                    domains_blocked += filter_list.get("rules_count", 0)

        return DNSStats(
            queries_today=queries_today,
            blocked_today=blocked_today,
            percent_blocked=round(percent, 2),
            domains_blocked=domains_blocked,
            provider=Provider.ADGUARD,
        )

    async def get_top_queries(self, count: int = 10) -> list:
        """Get top DNS queries."""
        data = await self.get("/control/stats")
        if not data:
            return []

        queries = []
        for domain, hits in list(data.get("top_queried_domains", {}).items())[:count]:
            queries.append({"domain": domain, "hits": hits})
        return queries

    async def get_top_blocked(self, count: int = 10) -> list:
        """Get top blocked domains."""
        data = await self.get("/control/stats")
        if not data:
            return []

        blocked = []
        for domain, hits in list(data.get("top_blocked_domains", {}).items())[:count]:
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
        """Add a domain to the custom blocklist."""
        # Get current rules
        status = await self.get("/control/filtering/status")
        if not status:
            return False

        current_rules = status.get("user_rules", [])
        rule = f"||{domain}^"

        if rule in current_rules:
            logger.info(f"AdGuard: {domain} already in blocklist")
            return True

        current_rules.append(rule)

        result = await self.post(
            "/control/filtering/set_rules",
            json={"rules": current_rules},
        )
        if result is not None:
            logger.info(f"AdGuard: Added {domain} to blocklist")
            return True
        return False

    async def add_to_whitelist(self, domain: str) -> bool:
        """Add a domain to the whitelist (exception rule)."""
        status = await self.get("/control/filtering/status")
        if not status:
            return False

        current_rules = status.get("user_rules", [])
        rule = f"@@||{domain}^"

        if rule in current_rules:
            logger.info(f"AdGuard: {domain} already in whitelist")
            return True

        current_rules.append(rule)

        result = await self.post(
            "/control/filtering/set_rules",
            json={"rules": current_rules},
        )
        if result is not None:
            logger.info(f"AdGuard: Added {domain} to whitelist")
            return True
        return False

    async def remove_from_blacklist(self, domain: str) -> bool:
        """Remove a domain from the custom blocklist."""
        status = await self.get("/control/filtering/status")
        if not status:
            return False

        current_rules = status.get("user_rules", [])
        rule = f"||{domain}^"

        if rule not in current_rules:
            logger.info(f"AdGuard: {domain} not in blocklist")
            return True

        current_rules.remove(rule)

        result = await self.post(
            "/control/filtering/set_rules",
            json={"rules": current_rules},
        )
        if result is not None:
            logger.info(f"AdGuard: Removed {domain} from blocklist")
            return True
        return False

    async def remove_from_whitelist(self, domain: str) -> bool:
        """Remove a domain from the whitelist."""
        status = await self.get("/control/filtering/status")
        if not status:
            return False

        current_rules = status.get("user_rules", [])
        rule = f"@@||{domain}^"

        if rule not in current_rules:
            logger.info(f"AdGuard: {domain} not in whitelist")
            return True

        current_rules.remove(rule)

        result = await self.post(
            "/control/filtering/set_rules",
            json={"rules": current_rules},
        )
        if result is not None:
            logger.info(f"AdGuard: Removed {domain} from whitelist")
            return True
        return False

    # --- Control Methods ---

    async def enable(self) -> bool:
        """Enable AdGuard filtering."""
        result = await self.post(
            "/control/dns_config",
            json={"protection_enabled": True},
        )
        return result is not None

    async def disable(self) -> bool:
        """Disable AdGuard filtering."""
        result = await self.post(
            "/control/dns_config",
            json={"protection_enabled": False},
        )
        return result is not None
