"""
Enhanced Meshtastic Bridge with error handling, reconnection logic,
node discovery, and delivery confirmation tracking.
"""

import asyncio
import logging
import threading
from datetime import datetime
from typing import Optional, Dict, Callable, List, Any
from collections import defaultdict

try:
    import meshtastic
    import meshtastic.serial_interface
    import meshtastic.tcp_interface
    from pubsub import pub
    MESHTASTIC_AVAILABLE = True
except ImportError:
    MESHTASTIC_AVAILABLE = False

from .config import config
from .models import MeshNode, QueuedMessage, MessageStatus, DeliveryConfirmation

logger = logging.getLogger(__name__)


class ConnectionState:
    """Tracks the connection state of the Meshtastic interface."""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    FAILED = "failed"


class MeshtasticBridge:
    """
    Enhanced Meshtastic bridge with:
    - Automatic reconnection with exponential backoff
    - Node discovery and tracking
    - Delivery confirmation
    - Signal strength and battery monitoring
    """

    def __init__(self):
        self.interface: Optional[Any] = None
        self.state: str = ConnectionState.DISCONNECTED
        self.nodes: Dict[str, MeshNode] = {}
        self.pending_confirmations: Dict[str, DeliveryConfirmation] = {}
        self.message_callbacks: List[Callable] = []
        self.node_update_callbacks: List[Callable] = []
        self.connection_callbacks: List[Callable] = []
        self._reconnect_task: Optional[asyncio.Task] = None
        self._reconnect_attempts: int = 0
        self._lock = threading.Lock()
        self._running = False
        self._loop: Optional[asyncio.AbstractEventLoop] = None

        # Statistics
        self.stats = {
            "messages_sent": 0,
            "messages_received": 0,
            "messages_failed": 0,
            "reconnections": 0,
            "last_connected": None,
            "uptime_seconds": 0
        }

    async def start(self) -> bool:
        """Start the Meshtastic bridge and connect to device."""
        if not MESHTASTIC_AVAILABLE:
            logger.error("Meshtastic library not installed")
            self.state = ConnectionState.FAILED
            return False

        self._running = True
        self._loop = asyncio.get_event_loop()
        return await self._connect()

    async def stop(self):
        """Stop the bridge and cleanup resources."""
        self._running = False
        if self._reconnect_task:
            self._reconnect_task.cancel()
            try:
                await self._reconnect_task
            except asyncio.CancelledError:
                pass
        await self._disconnect()

    async def _connect(self) -> bool:
        """Attempt to connect to the Meshtastic device."""
        self.state = ConnectionState.CONNECTING
        logger.info(f"Connecting to Meshtastic device at {config.meshtastic.device_path}")

        try:
            # Try serial connection first
            self.interface = meshtastic.serial_interface.SerialInterface(
                devPath=config.meshtastic.device_path
            )

            # Subscribe to message events
            pub.subscribe(self._on_receive, "meshtastic.receive")
            pub.subscribe(self._on_connection, "meshtastic.connection.established")
            pub.subscribe(self._on_disconnection, "meshtastic.connection.lost")
            pub.subscribe(self._on_node_update, "meshtastic.node.updated")

            self.state = ConnectionState.CONNECTED
            self.stats["last_connected"] = datetime.utcnow()
            self._reconnect_attempts = 0

            # Initial node discovery
            await self._discover_nodes()

            # Notify connection callbacks
            for callback in self.connection_callbacks:
                try:
                    callback(True, self.state)
                except Exception as e:
                    logger.error(f"Connection callback error: {e}")

            logger.info("Meshtastic connection established")
            return True

        except Exception as e:
            logger.error(f"Failed to connect to Meshtastic: {e}")
            self.state = ConnectionState.FAILED
            self.interface = None

            # Start reconnection loop if running
            if self._running:
                asyncio.create_task(self._reconnect_loop())

            return False

    async def _disconnect(self):
        """Disconnect from the Meshtastic device."""
        if self.interface:
            try:
                pub.unsubscribe(self._on_receive, "meshtastic.receive")
                pub.unsubscribe(self._on_connection, "meshtastic.connection.established")
                pub.unsubscribe(self._on_disconnection, "meshtastic.connection.lost")
                pub.unsubscribe(self._on_node_update, "meshtastic.node.updated")
                self.interface.close()
            except Exception as e:
                logger.error(f"Error during disconnect: {e}")
            finally:
                self.interface = None
                self.state = ConnectionState.DISCONNECTED

    async def _reconnect_loop(self):
        """Reconnection loop with exponential backoff."""
        self.state = ConnectionState.RECONNECTING
        delay = config.meshtastic.reconnect_delay

        while self._running and self._reconnect_attempts < config.meshtastic.max_reconnect_attempts:
            self._reconnect_attempts += 1
            self.stats["reconnections"] += 1
            logger.info(f"Reconnection attempt {self._reconnect_attempts}/{config.meshtastic.max_reconnect_attempts}")

            await asyncio.sleep(delay)

            if await self._connect():
                return

            # Exponential backoff
            delay = min(delay * config.meshtastic.reconnect_backoff_multiplier, 300)  # Max 5 minutes

        if self._reconnect_attempts >= config.meshtastic.max_reconnect_attempts:
            logger.error("Max reconnection attempts reached")
            self.state = ConnectionState.FAILED
            for callback in self.connection_callbacks:
                try:
                    callback(False, self.state)
                except Exception as e:
                    logger.error(f"Connection callback error: {e}")

    def _on_receive(self, packet, interface):
        """Handle received messages from the mesh network."""
        try:
            self.stats["messages_received"] += 1

            # Extract message info
            from_id = packet.get("fromId", packet.get("from", "unknown"))
            to_id = packet.get("toId", packet.get("to"))

            # Update node info from packet
            if "snr" in packet or "rssi" in packet:
                self._update_node_signal(from_id, packet.get("snr"), packet.get("rssi"))

            # Handle text messages
            if "decoded" in packet:
                decoded = packet["decoded"]
                portnum = decoded.get("portnum", "")

                if portnum == "TEXT_MESSAGE_APP":
                    message_text = decoded.get("text", "")
                    logger.info(f"Received message from {from_id}: {message_text}")

                    # Check if this is an acknowledgment
                    if message_text.startswith("ACK:"):
                        msg_id = message_text[4:].strip()
                        self._handle_acknowledgment(msg_id, from_id)

                    # Notify message callbacks
                    for callback in self.message_callbacks:
                        try:
                            callback(from_id, to_id, message_text, packet)
                        except Exception as e:
                            logger.error(f"Message callback error: {e}")

                elif portnum == "POSITION_APP":
                    self._handle_position_update(from_id, decoded)

                elif portnum == "TELEMETRY_APP":
                    self._handle_telemetry_update(from_id, decoded)

                elif portnum == "NODEINFO_APP":
                    self._handle_nodeinfo_update(from_id, decoded)

        except Exception as e:
            logger.error(f"Error processing received packet: {e}")

    def _on_connection(self, interface, topic=pub.AUTO_TOPIC):
        """Handle connection established event."""
        logger.info("Meshtastic connection established")
        self.state = ConnectionState.CONNECTED
        self.stats["last_connected"] = datetime.utcnow()

    def _on_disconnection(self, interface, topic=pub.AUTO_TOPIC):
        """Handle connection lost event."""
        logger.warning("Meshtastic connection lost")
        self.state = ConnectionState.DISCONNECTED
        self.interface = None

        if self._running:
            asyncio.run_coroutine_threadsafe(self._reconnect_loop(), self._loop)

    def _on_node_update(self, node, interface, topic=pub.AUTO_TOPIC):
        """Handle node update events."""
        try:
            node_id = node.get("num", str(node.get("user", {}).get("id", "unknown")))
            self._update_node_from_dict(str(node_id), node)
        except Exception as e:
            logger.error(f"Error updating node: {e}")

    async def _discover_nodes(self):
        """Discover and catalog nodes in the mesh network."""
        if not self.interface:
            return

        try:
            node_info = self.interface.nodes
            if node_info:
                for node_id, node_data in node_info.items():
                    self._update_node_from_dict(node_id, node_data)
                logger.info(f"Discovered {len(self.nodes)} nodes")
        except Exception as e:
            logger.error(f"Error during node discovery: {e}")

    def _update_node_from_dict(self, node_id: str, data: Dict):
        """Update or create a node from dictionary data."""
        with self._lock:
            if node_id not in self.nodes:
                self.nodes[node_id] = MeshNode(node_id=node_id)

            node = self.nodes[node_id]

            # Update user info
            user = data.get("user", {})
            if user:
                node.long_name = user.get("longName", node.long_name)
                node.short_name = user.get("shortName", node.short_name)
                node.hw_model = user.get("hwModel", node.hw_model)
                node.is_licensed = user.get("isLicensed", node.is_licensed)
                node.role = user.get("role", node.role)

            # Update position
            position = data.get("position", {})
            if position:
                node.latitude = position.get("latitude", node.latitude)
                node.longitude = position.get("longitude", node.longitude)
                node.altitude = position.get("altitude", node.altitude)

            # Update metrics
            device_metrics = data.get("deviceMetrics", {})
            if device_metrics:
                node.battery_level = device_metrics.get("batteryLevel", node.battery_level)
                node.voltage = device_metrics.get("voltage", node.voltage)

            # Update signal info
            node.snr = data.get("snr", node.snr)
            node.rssi = data.get("rssi", node.rssi)
            node.hops_away = data.get("hopsAway", node.hops_away)
            node.last_heard = datetime.utcnow()

            # Notify callbacks
            for callback in self.node_update_callbacks:
                try:
                    callback(node)
                except Exception as e:
                    logger.error(f"Node update callback error: {e}")

    def _update_node_signal(self, node_id: str, snr: Optional[float], rssi: Optional[int]):
        """Update signal metrics for a node."""
        with self._lock:
            if node_id in self.nodes:
                if snr is not None:
                    self.nodes[node_id].snr = snr
                if rssi is not None:
                    self.nodes[node_id].rssi = rssi
                self.nodes[node_id].last_heard = datetime.utcnow()

    def _handle_position_update(self, node_id: str, decoded: Dict):
        """Handle position telemetry update."""
        position = decoded.get("position", {})
        if position and node_id in self.nodes:
            with self._lock:
                node = self.nodes[node_id]
                node.latitude = position.get("latitude", node.latitude)
                node.longitude = position.get("longitude", node.longitude)
                node.altitude = position.get("altitude", node.altitude)

    def _handle_telemetry_update(self, node_id: str, decoded: Dict):
        """Handle device telemetry update."""
        telemetry = decoded.get("telemetry", {})
        device_metrics = telemetry.get("deviceMetrics", {})

        if device_metrics and node_id in self.nodes:
            with self._lock:
                node = self.nodes[node_id]
                node.battery_level = device_metrics.get("batteryLevel", node.battery_level)
                node.voltage = device_metrics.get("voltage", node.voltage)

    def _handle_nodeinfo_update(self, node_id: str, decoded: Dict):
        """Handle node info update."""
        self._update_node_from_dict(node_id, decoded)

    def _handle_acknowledgment(self, message_id: str, from_node: str):
        """Handle message acknowledgment."""
        if message_id in self.pending_confirmations:
            confirmation = self.pending_confirmations[message_id]
            confirmation.acknowledged = True
            confirmation.acknowledged_at = datetime.utcnow()
            logger.info(f"Message {message_id} acknowledged by {from_node}")

    async def send_message(
        self,
        text: str,
        destination: Optional[str] = None,
        want_ack: bool = True,
        channel_index: int = 0
    ) -> Optional[str]:
        """
        Send a message via the mesh network.

        Args:
            text: Message text to send
            destination: Target node ID (None for broadcast)
            want_ack: Request delivery acknowledgment
            channel_index: Channel to send on

        Returns:
            Message ID if sent successfully, None otherwise
        """
        if not self.interface or self.state != ConnectionState.CONNECTED:
            logger.warning("Cannot send message: not connected")
            return None

        try:
            msg_id = str(id(text) + int(datetime.utcnow().timestamp()))

            if destination:
                self.interface.sendText(
                    text,
                    destinationId=destination,
                    wantAck=want_ack,
                    channelIndex=channel_index
                )
            else:
                self.interface.sendText(
                    text,
                    wantAck=want_ack,
                    channelIndex=channel_index
                )

            self.stats["messages_sent"] += 1

            # Track for confirmation
            if want_ack:
                self.pending_confirmations[msg_id] = DeliveryConfirmation(
                    message_id=msg_id,
                    node_id=destination or "broadcast"
                )

            logger.info(f"Sent message to {destination or 'broadcast'}: {text[:50]}...")
            return msg_id

        except Exception as e:
            logger.error(f"Error sending message: {e}")
            self.stats["messages_failed"] += 1
            return None

    def get_nodes(self) -> List[MeshNode]:
        """Get list of all discovered nodes."""
        with self._lock:
            return list(self.nodes.values())

    def get_node(self, node_id: str) -> Optional[MeshNode]:
        """Get a specific node by ID."""
        with self._lock:
            return self.nodes.get(node_id)

    def get_connected_nodes(self) -> List[MeshNode]:
        """Get nodes heard within the last hour."""
        cutoff = datetime.utcnow()
        with self._lock:
            return [
                node for node in self.nodes.values()
                if node.last_heard and (cutoff - node.last_heard).total_seconds() < 3600
            ]

    def register_message_callback(self, callback: Callable):
        """Register a callback for incoming messages."""
        self.message_callbacks.append(callback)

    def register_node_callback(self, callback: Callable):
        """Register a callback for node updates."""
        self.node_update_callbacks.append(callback)

    def register_connection_callback(self, callback: Callable):
        """Register a callback for connection state changes."""
        self.connection_callbacks.append(callback)

    def is_connected(self) -> bool:
        """Check if connected to mesh network."""
        return self.state == ConnectionState.CONNECTED and self.interface is not None

    def get_stats(self) -> Dict[str, Any]:
        """Get bridge statistics."""
        return {
            **self.stats,
            "state": self.state,
            "node_count": len(self.nodes),
            "pending_confirmations": len(self.pending_confirmations)
        }
