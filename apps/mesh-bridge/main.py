"""
Aegis Mesh - Mesh Bridge Service
Gateway between Meshtastic LoRa network and the home lab infrastructure.
"""

import meshtastic
import meshtastic.serial_interface
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from contextlib import asynccontextmanager
import asyncio
import os
from typing import Optional
from datetime import datetime

# Message buffer for received messages
message_buffer = []
MAX_BUFFER_SIZE = 100

# Global interface reference
interface: Optional[meshtastic.serial_interface.SerialInterface] = None

def on_receive(packet, iface):
    """Callback for when a message arrives via LoRa"""
    global message_buffer

    if 'decoded' in packet and packet['decoded'].get('portnum') == 'TEXT_MESSAGE_APP':
        message_text = packet['decoded'].get('text', '')
        from_id = packet.get('fromId', 'unknown')

        message = {
            "text": message_text,
            "from": from_id,
            "received_at": datetime.utcnow().isoformat(),
            "raw": packet
        }

        message_buffer.append(message)

        # Keep buffer size limited
        if len(message_buffer) > MAX_BUFFER_SIZE:
            message_buffer = message_buffer[-MAX_BUFFER_SIZE:]

        print(f"Mesh Message Received from {from_id}: {message_text}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    global interface

    # Startup: Initialize Meshtastic connection
    device_path = os.getenv("MESH_DEVICE_PATH", "/dev/ttyUSB0")
    try:
        interface = meshtastic.serial_interface.SerialInterface(devPath=device_path)
        meshtastic.pub.subscribe(on_receive, "meshtastic.receive")
        print(f"Connected to Meshtastic device at {device_path}")
    except Exception as e:
        print(f"Mesh Hardware not found at {device_path}: {e}")
        interface = None

    yield

    # Shutdown: Close connection
    if interface:
        interface.close()

app = FastAPI(
    title="Aegis Mesh Bridge",
    description="Meshtastic/NomadNet gateway for home lab alerts",
    version="0.1.0",
    lifespan=lifespan
)

class SendMessageRequest(BaseModel):
    message: str
    destination: Optional[str] = None  # Node ID or broadcast if None

class MessageResponse(BaseModel):
    text: str
    from_id: str
    received_at: str

@app.get("/")
async def root():
    return {
        "service": "Aegis Mesh Bridge",
        "version": "0.1.0",
        "status": "operational"
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy", "mesh_connected": interface is not None}

@app.get("/status")
async def get_status():
    """Get detailed mesh bridge status"""
    status = {
        "status": "Aegis Mesh Bridge Online",
        "mesh_connected": interface is not None,
        "messages_buffered": len(message_buffer)
    }

    if interface:
        try:
            my_info = interface.getMyNodeInfo()
            status["node_info"] = {
                "id": my_info.get("user", {}).get("id"),
                "long_name": my_info.get("user", {}).get("longName"),
                "short_name": my_info.get("user", {}).get("shortName")
            }
        except Exception:
            pass

    return status

@app.post("/send")
async def send_to_mesh(request: SendMessageRequest):
    """Send a message out to the mesh network"""
    if not interface:
        raise HTTPException(
            status_code=503,
            detail="Mesh hardware not connected"
        )

    try:
        if request.destination:
            interface.sendText(request.message, destinationId=request.destination)
        else:
            interface.sendText(request.message)

        return {"sent": True, "message": request.message}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to send message: {str(e)}"
        )

@app.get("/messages")
async def get_messages(limit: int = 50):
    """Get recently received mesh messages"""
    return {
        "messages": message_buffer[-limit:],
        "total": len(message_buffer)
    }

@app.delete("/messages")
async def clear_messages():
    """Clear the message buffer"""
    global message_buffer
    count = len(message_buffer)
    message_buffer = []
    return {"cleared": count}

@app.get("/nodes")
async def get_nodes():
    """Get known mesh nodes"""
    if not interface:
        raise HTTPException(
            status_code=503,
            detail="Mesh hardware not connected"
        )

    try:
        nodes = interface.nodes
        return {"nodes": nodes}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get nodes: {str(e)}"
        )
