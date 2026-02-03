import meshtastic
import meshtastic.serial_interface
from fastapi import FastAPI
import asyncio

app = FastAPI()

# Initialize Meshtastic connection
# This allows your home lab to "hear" the mesh network
try:
    interface = meshtastic.serial_interface.SerialInterface()
except Exception as e:
    print(f"Mesh Hardware not found: {e}")
    interface = None

def on_receive(packet, interface):
    """Callback for when a message arrives via LoRa"""
    if 'decoded' in packet and packet['decoded']['portnum'] == 'TEXT_MESSAGE_APP':
        message_text = packet['decoded']['text']
        print(f"Mesh Message Received: {message_text}")
        # Logic to route to NomadNet or trigger Maintenance Tasks goes here

if interface:
    meshtastic.pub.subscribe(on_receive, "meshtastic.receive")

@app.get("/status")
async def get_system_status():
    return {"status": "Aegis Core Online", "mesh_connected": interface is not None}

@app.post("/alert/mesh")
async def send_to_mesh(message: str):
    """Send a lab alert out to the handheld mesh nodes"""
    if interface:
        interface.sendText(message)
        return {"sent": True}
    return {"sent": False, "error": "Hardware disconnected"}
