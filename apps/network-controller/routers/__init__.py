"""
API routers for network-controller endpoints.
"""

from .traffic import router as traffic_router
from .dns import router as dns_router
from .vpn import router as vpn_router

__all__ = ["traffic_router", "dns_router", "vpn_router"]
