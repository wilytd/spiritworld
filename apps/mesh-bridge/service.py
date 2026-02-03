"""
Mesh Bridge FastAPI Service

Main entry point that orchestrates all mesh bridge components.
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Optional, List
from datetime import datetime

from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field

from .meshtastic_bridge import MeshtasticBridge
from .nomadnet_bridge import NomadNetBridge, MessageRelay
from .message_queue import MessageQueue
from .alerts import AlertManager
from .models import AlertPriority, Protocol
from .config import config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# Global instances
meshtastic_bridge: Optional[MeshtasticBridge] = None
nomadnet_bridge: Optional[NomadNetBridge] = None
alert_manager: Optional[AlertManager] = None
message_relay: Optional[MessageRelay] = None


# Pydantic models for API
class StatusResponse(BaseModel):
    status: str
    mesh_connected: bool
    nomadnet_connected: bool
    isp_online: bool
    timestamp: str


class SendMessageRequest(BaseModel):
    message: str
    destination: Optional[str] = None
    priority: str = "MEDIUM"
    protocol: str = "MESHTASTIC"


class SendMessageResponse(BaseModel):
    sent: bool
    message_id: Optional[str] = None
    error: Optional[str] = None


class AlertRequest(BaseModel):
    title: str
    message: str
    priority: str = "MEDIUM"
    source: str = "api"
    category: str = "general"
    target_nodes: List[str] = Field(default_factory=list)


class AlertResponse(BaseModel):
    alert_id: str
    status: str


class AcknowledgeRequest(BaseModel):
    alert_id: str
    acknowledged_by: str = "api"


class NodeInfo(BaseModel):
    node_id: str
    long_name: Optional[str] = None
    short_name: Optional[str] = None
    snr: Optional[float] = None
    rssi: Optional[int] = None
    battery_level: Optional[int] = None
    last_heard: Optional[str] = None


class StatsResponse(BaseModel):
    meshtastic: dict
    nomadnet: dict
    alerts: dict
    uptime_seconds: float


# Startup/shutdown lifecycle
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage startup and shutdown of services."""
    global meshtastic_bridge, nomadnet_bridge, alert_manager, message_relay

    logger.info("Starting Aegis Mesh Bridge services...")

    # Initialize Meshtastic bridge
    meshtastic_bridge = MeshtasticBridge()
    mesh_connected = await meshtastic_bridge.start()

    # Initialize NomadNet bridge
    nomadnet_bridge = NomadNetBridge()
    nomadnet_connected = await nomadnet_bridge.start()

    # Initialize alert manager
    alert_manager = AlertManager()
    if mesh_connected:
        alert_manager.set_meshtastic_send(meshtastic_bridge.send_message)
    if nomadnet_connected:
        alert_manager.set_nomadnet_send(nomadnet_bridge.send_message)
    await alert_manager.start()

    # Initialize message relay if both protocols are available
    if mesh_connected and nomadnet_connected:
        message_relay = MessageRelay(
            meshtastic_send=meshtastic_bridge.send_message,
            nomadnet_send=nomadnet_bridge.send_message
        )

        # Register relay callbacks
        meshtastic_bridge.register_message_callback(
            lambda src, dst, msg, pkt: asyncio.create_task(
                message_relay.relay_from_mesh(src, msg)
            )
        )
        nomadnet_bridge.register_message_callback(
            lambda msg_data: asyncio.create_task(
                message_relay.relay_from_nomadnet(
                    msg_data["source"],
                    msg_data["content"]
                )
            )
        )

    logger.info("All services started successfully")

    yield

    # Shutdown
    logger.info("Shutting down services...")
    await alert_manager.stop()
    await nomadnet_bridge.stop()
    await meshtastic_bridge.stop()
    logger.info("All services stopped")


# Create FastAPI app
app = FastAPI(
    title="Aegis Mesh Bridge",
    description="Unified mesh communication service for Meshtastic and NomadNet",
    version="0.1.0",
    lifespan=lifespan
)


# Health and Status Endpoints
@app.get("/status", response_model=StatusResponse)
async def get_status():
    """Get overall system status."""
    return StatusResponse(
        status="Aegis Mesh Bridge Online",
        mesh_connected=meshtastic_bridge.is_connected() if meshtastic_bridge else False,
        nomadnet_connected=nomadnet_bridge.is_connected() if nomadnet_bridge else False,
        isp_online=alert_manager.isp_monitor.status.is_online if alert_manager else True,
        timestamp=datetime.utcnow().isoformat()
    )


@app.get("/health")
async def health_check():
    """Simple health check endpoint."""
    return {"healthy": True}


@app.get("/stats", response_model=StatsResponse)
async def get_stats():
    """Get detailed statistics for all services."""
    start_time = getattr(app.state, "start_time", datetime.utcnow())
    uptime = (datetime.utcnow() - start_time).total_seconds()

    return StatsResponse(
        meshtastic=meshtastic_bridge.get_stats() if meshtastic_bridge else {},
        nomadnet=nomadnet_bridge.get_stats() if nomadnet_bridge else {},
        alerts=alert_manager.get_stats() if alert_manager else {},
        uptime_seconds=uptime
    )


# Messaging Endpoints
@app.post("/message/send", response_model=SendMessageResponse)
async def send_message(request: SendMessageRequest):
    """Send a message via the mesh network."""
    if not meshtastic_bridge or not meshtastic_bridge.is_connected():
        return SendMessageResponse(sent=False, error="Mesh not connected")

    try:
        priority = AlertPriority[request.priority.upper()]
        protocol = Protocol[request.protocol.upper()]

        if protocol == Protocol.MESHTASTIC:
            msg_id = await meshtastic_bridge.send_message(
                text=request.message,
                destination=request.destination
            )
        elif protocol == Protocol.NOMADNET:
            if not nomadnet_bridge or not nomadnet_bridge.is_connected():
                return SendMessageResponse(sent=False, error="NomadNet not connected")
            if not request.destination:
                return SendMessageResponse(sent=False, error="NomadNet requires destination")
            success = await nomadnet_bridge.send_message(
                destination_hash=request.destination,
                content=request.message
            )
            msg_id = "nomadnet" if success else None
        else:
            # Send via both
            msg_id = await meshtastic_bridge.send_message(
                text=request.message,
                destination=request.destination
            )
            if nomadnet_bridge and request.destination:
                await nomadnet_bridge.send_message(
                    destination_hash=request.destination,
                    content=request.message
                )

        if msg_id:
            return SendMessageResponse(sent=True, message_id=msg_id)
        return SendMessageResponse(sent=False, error="Send failed")

    except KeyError as e:
        raise HTTPException(status_code=400, detail=f"Invalid priority or protocol: {e}")
    except Exception as e:
        logger.error(f"Error sending message: {e}")
        return SendMessageResponse(sent=False, error=str(e))


@app.post("/alert/send", response_model=AlertResponse)
async def send_alert(request: AlertRequest):
    """Send an alert through the alert system."""
    if not alert_manager:
        raise HTTPException(status_code=503, detail="Alert manager not available")

    try:
        priority = AlertPriority[request.priority.upper()]

        alert_id = await alert_manager.send_alert(
            title=request.title,
            message=request.message,
            priority=priority,
            source=request.source,
            category=request.category,
            target_nodes=request.target_nodes
        )

        return AlertResponse(alert_id=alert_id, status="queued")

    except KeyError:
        raise HTTPException(status_code=400, detail="Invalid priority level")
    except Exception as e:
        logger.error(f"Error sending alert: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/alert/mesh")
async def send_to_mesh(message: dict):
    """Legacy endpoint: Send a lab alert to mesh nodes."""
    if not meshtastic_bridge or not meshtastic_bridge.is_connected():
        return {"sent": False, "error": "Hardware disconnected"}

    text = message.get("message", "")
    if not text:
        raise HTTPException(status_code=400, detail="Message required")

    msg_id = await meshtastic_bridge.send_message(text=text)
    return {"sent": msg_id is not None, "message_id": msg_id}


@app.post("/alert/acknowledge")
async def acknowledge_alert(request: AcknowledgeRequest):
    """Acknowledge an alert."""
    if not alert_manager:
        raise HTTPException(status_code=503, detail="Alert manager not available")

    success = await alert_manager.acknowledge_alert(
        request.alert_id,
        request.acknowledged_by
    )

    if success:
        return {"acknowledged": True, "alert_id": request.alert_id}
    raise HTTPException(status_code=404, detail="Alert not found")


@app.get("/alerts/active")
async def get_active_alerts():
    """Get all active (unacknowledged) alerts."""
    if not alert_manager:
        return {"alerts": []}
    return {"alerts": alert_manager.get_active_alerts()}


@app.get("/alerts/escalated")
async def get_escalated_alerts():
    """Get all escalated alerts."""
    if not alert_manager:
        return {"alerts": []}
    return {"alerts": alert_manager.get_escalated_alerts()}


@app.get("/alert/{alert_id}")
async def get_alert(alert_id: str):
    """Get a specific alert by ID."""
    if not alert_manager:
        raise HTTPException(status_code=503, detail="Alert manager not available")

    alert = alert_manager.get_alert(alert_id)
    if alert:
        return alert
    raise HTTPException(status_code=404, detail="Alert not found")


# Node Management Endpoints
@app.get("/nodes")
async def get_nodes():
    """Get all discovered mesh nodes."""
    if not meshtastic_bridge:
        return {"nodes": []}

    nodes = meshtastic_bridge.get_nodes()
    return {"nodes": [node.to_dict() for node in nodes]}


@app.get("/nodes/connected")
async def get_connected_nodes():
    """Get recently connected nodes (heard in last hour)."""
    if not meshtastic_bridge:
        return {"nodes": []}

    nodes = meshtastic_bridge.get_connected_nodes()
    return {"nodes": [node.to_dict() for node in nodes]}


@app.get("/node/{node_id}")
async def get_node(node_id: str):
    """Get a specific node by ID."""
    if not meshtastic_bridge:
        raise HTTPException(status_code=503, detail="Mesh bridge not available")

    node = meshtastic_bridge.get_node(node_id)
    if node:
        return node.to_dict()
    raise HTTPException(status_code=404, detail="Node not found")


# NomadNet Endpoints
@app.get("/nomadnet/address")
async def get_nomadnet_address():
    """Get our NomadNet/LXMF address."""
    if not nomadnet_bridge or not nomadnet_bridge.is_connected():
        return {"address": None, "connected": False}
    return {"address": nomadnet_bridge.get_address(), "connected": True}


@app.get("/nomadnet/messages")
async def get_nomadnet_messages(limit: int = 100):
    """Get stored NomadNet messages."""
    if not nomadnet_bridge:
        return {"messages": []}
    return {"messages": nomadnet_bridge.get_stored_messages(limit)}


@app.get("/nomadnet/destinations")
async def get_known_destinations():
    """Get known NomadNet destinations."""
    if not nomadnet_bridge:
        return {"destinations": {}}
    return {"destinations": nomadnet_bridge.get_known_destinations()}


@app.post("/nomadnet/destination")
async def add_destination(hash_str: str, name: str = "", metadata: dict = None):
    """Add a known NomadNet destination."""
    if not nomadnet_bridge:
        raise HTTPException(status_code=503, detail="NomadNet not available")
    nomadnet_bridge.add_known_destination(hash_str, name, metadata or {})
    return {"added": True}


# ISP Status Endpoints
@app.get("/isp/status")
async def get_isp_status():
    """Get ISP connectivity status."""
    if not alert_manager:
        return {"is_online": True, "failover_active": False}
    return alert_manager.isp_monitor.get_status()


# Message Queue Endpoints
@app.get("/queue/status")
async def get_queue_status():
    """Get message queue status."""
    if not alert_manager:
        return {"pending": 0, "failed": 0, "sent": 0}
    return alert_manager.message_queue.get_queue_status()


@app.post("/queue/retry-failed")
async def retry_failed_messages():
    """Retry all failed messages."""
    if not alert_manager:
        raise HTTPException(status_code=503, detail="Alert manager not available")
    count = alert_manager.message_queue.retry_all_failed()
    return {"retried": count}


# Main entry point for direct execution
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
