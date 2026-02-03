"""
API clients for network service integrations.
"""

from .base import BaseClient
from .opnsense import OPNsenseClient
from .unifi import UnifiClient
from .pihole import PiholeClient
from .adguard import AdGuardClient

__all__ = [
    "BaseClient",
    "OPNsenseClient",
    "UnifiClient",
    "PiholeClient",
    "AdGuardClient",
]
