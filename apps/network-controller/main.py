"""
Aegis Mesh - Network Controller Service
Integration with OPNsense, Unifi, Pi-hole, AdGuard, and WireGuard.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from clients import OPNsenseClient, UnifiClient, PiholeClient, AdGuardClient
from routers import traffic, dns, vpn
from schemas import HealthResponse, ClientHealthResponse


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Initialize clients
opnsense_client = OPNsenseClient(settings.opnsense)
unifi_client = UnifiClient(settings.unifi)
pihole_client = PiholeClient(settings.pihole)
adguard_client = AdGuardClient(settings.adguard)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manage client connections during application lifecycle.
    """
    logger.info("Network Controller starting up...")

    # Connect to configured services
    if opnsense_client.is_configured:
        logger.info("Connecting to OPNsense...")
        await opnsense_client.connect()
    else:
        logger.info("OPNsense not configured, skipping")

    if unifi_client.is_configured:
        logger.info("Connecting to Unifi Controller...")
        await unifi_client.connect()
    else:
        logger.info("Unifi not configured, skipping")

    if pihole_client.is_configured:
        logger.info("Connecting to Pi-hole...")
        await pihole_client.connect()
    else:
        logger.info("Pi-hole not configured, skipping")

    if adguard_client.is_configured:
        logger.info("Connecting to AdGuard Home...")
        await adguard_client.connect()
    else:
        logger.info("AdGuard not configured, skipping")

    # Set client references in routers
    traffic.set_clients(opnsense_client, unifi_client)
    dns.set_clients(pihole_client, adguard_client)
    vpn.set_clients(opnsense_client)

    logger.info("Network Controller ready")
    yield

    # Cleanup on shutdown
    logger.info("Network Controller shutting down...")
    await opnsense_client.disconnect()
    await unifi_client.disconnect()
    await pihole_client.disconnect()
    await adguard_client.disconnect()
    logger.info("Network Controller stopped")


app = FastAPI(
    title="Aegis Network Controller",
    description="Network infrastructure management for home lab - OPNsense, Unifi, Pi-hole, AdGuard, WireGuard",
    version="0.2.0",
    lifespan=lifespan,
)

# CORS for dashboard communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://dashboard:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(traffic.router)
app.include_router(dns.router)
app.include_router(vpn.router)


@app.get("/")
async def root():
    """Service information."""
    return {
        "service": "Aegis Network Controller",
        "version": "0.2.0",
        "status": "operational",
        "integrations": {
            "opnsense": {
                "configured": opnsense_client.is_configured,
                "connected": opnsense_client.is_connected,
            },
            "unifi": {
                "configured": unifi_client.is_configured,
                "connected": unifi_client.is_connected,
            },
            "pihole": {
                "configured": pihole_client.is_configured,
                "connected": pihole_client.is_connected,
            },
            "adguard": {
                "configured": adguard_client.is_configured,
                "connected": adguard_client.is_connected,
            },
        },
    }


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Detailed health check for all integrations.
    """
    clients = [
        ClientHealthResponse(**opnsense_client.get_health().to_dict()),
        ClientHealthResponse(**unifi_client.get_health().to_dict()),
        ClientHealthResponse(**pihole_client.get_health().to_dict()),
        ClientHealthResponse(**adguard_client.get_health().to_dict()),
    ]

    # Overall status: healthy if at least one configured service is connected
    configured_clients = [c for c in clients if c.configured]
    connected_clients = [c for c in configured_clients if c.connected]

    if not configured_clients:
        status = "degraded"  # Nothing configured
    elif connected_clients:
        status = "healthy"
    else:
        status = "unhealthy"  # Configured but none connected

    return HealthResponse(status=status, clients=clients)
