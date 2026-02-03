"""
Configuration management for network-controller service.
All configuration is loaded from environment variables.
"""

import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class OPNsenseConfig:
    """OPNsense firewall configuration."""
    url: Optional[str] = None
    key: Optional[str] = None
    secret: Optional[str] = None
    verify_ssl: bool = False

    @classmethod
    def from_env(cls) -> "OPNsenseConfig":
        return cls(
            url=os.getenv("OPNSENSE_URL"),
            key=os.getenv("OPNSENSE_KEY"),
            secret=os.getenv("OPNSENSE_SECRET"),
            verify_ssl=os.getenv("OPNSENSE_VERIFY_SSL", "false").lower() == "true",
        )

    @property
    def is_configured(self) -> bool:
        return all([self.url, self.key, self.secret])


@dataclass
class UnifiConfig:
    """Unifi Controller configuration."""
    url: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    site: str = "default"
    verify_ssl: bool = False

    @classmethod
    def from_env(cls) -> "UnifiConfig":
        return cls(
            url=os.getenv("UNIFI_URL"),
            username=os.getenv("UNIFI_USER"),
            password=os.getenv("UNIFI_PASS"),
            site=os.getenv("UNIFI_SITE", "default"),
            verify_ssl=os.getenv("UNIFI_VERIFY_SSL", "false").lower() == "true",
        )

    @property
    def is_configured(self) -> bool:
        return all([self.url, self.username, self.password])


@dataclass
class PiholeConfig:
    """Pi-hole configuration."""
    url: Optional[str] = None
    token: Optional[str] = None

    @classmethod
    def from_env(cls) -> "PiholeConfig":
        return cls(
            url=os.getenv("PIHOLE_URL"),
            token=os.getenv("PIHOLE_TOKEN"),
        )

    @property
    def is_configured(self) -> bool:
        return all([self.url, self.token])


@dataclass
class AdGuardConfig:
    """AdGuard Home configuration."""
    url: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None

    @classmethod
    def from_env(cls) -> "AdGuardConfig":
        return cls(
            url=os.getenv("ADGUARD_URL"),
            username=os.getenv("ADGUARD_USER"),
            password=os.getenv("ADGUARD_PASS"),
        )

    @property
    def is_configured(self) -> bool:
        return all([self.url, self.username, self.password])


@dataclass
class Settings:
    """Combined settings for all integrations."""
    opnsense: OPNsenseConfig
    unifi: UnifiConfig
    pihole: PiholeConfig
    adguard: AdGuardConfig

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            opnsense=OPNsenseConfig.from_env(),
            unifi=UnifiConfig.from_env(),
            pihole=PiholeConfig.from_env(),
            adguard=AdGuardConfig.from_env(),
        )


# Global settings instance
settings = Settings.from_env()
