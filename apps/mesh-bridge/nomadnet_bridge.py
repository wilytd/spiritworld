"""
NomadNet/Reticulum integration for encrypted mesh communications.

NomadNet is built on Reticulum - a cryptographic networking protocol
designed for resilient, delay-tolerant communications.
"""

import asyncio
import logging
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Callable, List, Any
import threading
import hashlib

try:
    import RNS
    import LXMF
    RETICULUM_AVAILABLE = True
except ImportError:
    RETICULUM_AVAILABLE = False
    RNS = None
    LXMF = None

from .config import config
from .models import Protocol

logger = logging.getLogger(__name__)


class NomadNetBridge:
    """
    NomadNet/Reticulum bridge for encrypted mesh communications.

    Features:
    - Encrypted end-to-end messaging via LXMF
    - File sharing with encryption
    - Message relay between Meshtastic and NomadNet
    - Persistent message storage
    - Automatic announce and discovery
    """

    def __init__(self):
        self.reticulum: Optional[Any] = None
        self.identity: Optional[Any] = None
        self.lxmf_router: Optional[Any] = None
        self.lxmf_destination: Optional[Any] = None
        self._running = False
        self._announce_task: Optional[asyncio.Task] = None
        self._lock = threading.Lock()

        # Storage paths
        self._storage_path = Path(config.nomadnet.storage_path)
        self._messages_path = self._storage_path / "messages"
        self._files_path = self._storage_path / "files"

        # Callbacks
        self.message_callbacks: List[Callable] = []
        self.file_callbacks: List[Callable] = []

        # Known destinations
        self.known_destinations: Dict[str, Dict] = {}

        # Statistics
        self.stats = {
            "messages_sent": 0,
            "messages_received": 0,
            "files_shared": 0,
            "files_received": 0,
            "announces_sent": 0
        }

        # Message storage
        self.stored_messages: List[Dict] = []

    async def start(self) -> bool:
        """Initialize and start the NomadNet bridge."""
        if not RETICULUM_AVAILABLE:
            logger.warning("Reticulum/LXMF libraries not installed")
            return False

        self._running = True

        # Ensure storage directories exist
        self._storage_path.mkdir(parents=True, exist_ok=True)
        self._messages_path.mkdir(exist_ok=True)
        self._files_path.mkdir(exist_ok=True)

        try:
            # Initialize Reticulum
            self.reticulum = RNS.Reticulum()

            # Load or create identity
            await self._init_identity()

            # Initialize LXMF router
            await self._init_lxmf()

            # Start announcement loop
            self._announce_task = asyncio.create_task(self._announce_loop())

            # Load stored messages
            await self._load_stored_messages()

            logger.info("NomadNet bridge started successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to start NomadNet bridge: {e}")
            self._running = False
            return False

    async def stop(self):
        """Stop the NomadNet bridge."""
        self._running = False

        if self._announce_task:
            self._announce_task.cancel()
            try:
                await self._announce_task
            except asyncio.CancelledError:
                pass

        # Save stored messages
        await self._save_stored_messages()

        logger.info("NomadNet bridge stopped")

    async def _init_identity(self):
        """Initialize or load the LXMF identity."""
        identity_path = config.nomadnet.identity_path
        if identity_path and Path(identity_path).exists():
            self.identity = RNS.Identity.from_file(identity_path)
            logger.info("Loaded existing identity")
        else:
            self.identity = RNS.Identity()
            if identity_path:
                self.identity.to_file(identity_path)
                logger.info("Created new identity")

    async def _init_lxmf(self):
        """Initialize LXMF router and destination."""
        # Create LXMF destination
        self.lxmf_destination = RNS.Destination(
            self.identity,
            RNS.Destination.IN,
            RNS.Destination.SINGLE,
            "aegis",
            "mesh"
        )

        # Set up message handler
        self.lxmf_destination.set_packet_callback(self._handle_lxmf_packet)

        # Create LXMF router for message delivery
        self.lxmf_router = LXMF.LXMRouter(
            identity=self.identity,
            storagepath=str(self._storage_path / "lxmf")
        )

        # Register delivery callback
        self.lxmf_router.register_delivery_callback(self._on_message_received)

        # Enable propagation if configured
        if config.nomadnet.enable_propagation:
            self.lxmf_router.enable_propagation()

        logger.info(f"LXMF initialized with address: {RNS.prettyhexrep(self.lxmf_destination.hash)}")

    def _handle_lxmf_packet(self, data, packet):
        """Handle incoming LXMF packets."""
        try:
            logger.debug(f"Received LXMF packet from {RNS.prettyhexrep(packet.source_hash)}")
        except Exception as e:
            logger.error(f"Error handling LXMF packet: {e}")

    def _on_message_received(self, message):
        """Handle received LXMF messages."""
        try:
            self.stats["messages_received"] += 1

            msg_data = {
                "id": RNS.prettyhexrep(message.hash),
                "source": RNS.prettyhexrep(message.source_hash),
                "destination": RNS.prettyhexrep(message.destination_hash),
                "title": message.title.decode() if message.title else "",
                "content": message.content.decode() if message.content else "",
                "timestamp": datetime.utcnow().isoformat(),
                "fields": message.fields
            }

            # Store message
            self.stored_messages.append(msg_data)

            logger.info(f"Received LXMF message from {msg_data['source']}")

            # Notify callbacks
            for callback in self.message_callbacks:
                try:
                    callback(msg_data)
                except Exception as e:
                    logger.error(f"Message callback error: {e}")

        except Exception as e:
            logger.error(f"Error processing received message: {e}")

    async def _announce_loop(self):
        """Periodically announce presence on the network."""
        while self._running:
            try:
                self.lxmf_destination.announce()
                self.stats["announces_sent"] += 1
                logger.debug("Sent network announce")
            except Exception as e:
                logger.error(f"Error sending announce: {e}")

            await asyncio.sleep(config.nomadnet.announce_interval)

    async def send_message(
        self,
        destination_hash: str,
        content: str,
        title: str = "",
        fields: Optional[Dict] = None
    ) -> bool:
        """
        Send an encrypted LXMF message.

        Args:
            destination_hash: Hex string of destination hash
            content: Message content
            title: Message title
            fields: Optional additional fields

        Returns:
            True if message was queued for delivery
        """
        if not self.lxmf_router:
            logger.error("LXMF router not initialized")
            return False

        try:
            # Convert hex string to bytes
            dest_bytes = bytes.fromhex(destination_hash.replace(":", ""))

            # Create LXMF message
            message = LXMF.LXMessage(
                destination_hash=dest_bytes,
                source_hash=self.lxmf_destination.hash,
                content=content.encode(),
                title=title.encode() if title else b"",
                fields=fields or {}
            )

            # Queue for delivery
            self.lxmf_router.handle_outbound(message)
            self.stats["messages_sent"] += 1

            logger.info(f"Queued LXMF message for {destination_hash}")
            return True

        except Exception as e:
            logger.error(f"Error sending LXMF message: {e}")
            return False

    async def share_file(
        self,
        destination_hash: str,
        file_path: str,
        description: str = ""
    ) -> bool:
        """
        Share a file via encrypted transfer.

        Args:
            destination_hash: Target destination
            file_path: Path to file to share
            description: Optional file description

        Returns:
            True if file was queued for transfer
        """
        if not self.lxmf_router:
            return False

        try:
            path = Path(file_path)
            if not path.exists():
                logger.error(f"File not found: {file_path}")
                return False

            # Read file and compute hash
            with open(path, "rb") as f:
                file_data = f.read()

            file_hash = hashlib.sha256(file_data).hexdigest()

            # Create message with file attachment
            fields = {
                "file_name": path.name,
                "file_size": len(file_data),
                "file_hash": file_hash,
                "file_data": file_data,
                "description": description
            }

            dest_bytes = bytes.fromhex(destination_hash.replace(":", ""))

            message = LXMF.LXMessage(
                destination_hash=dest_bytes,
                source_hash=self.lxmf_destination.hash,
                content=f"File: {path.name}".encode(),
                title=b"File Transfer",
                fields=fields
            )

            self.lxmf_router.handle_outbound(message)
            self.stats["files_shared"] += 1

            logger.info(f"Queued file transfer: {path.name}")
            return True

        except Exception as e:
            logger.error(f"Error sharing file: {e}")
            return False

    def get_address(self) -> Optional[str]:
        """Get our LXMF address as hex string."""
        if self.lxmf_destination:
            return RNS.prettyhexrep(self.lxmf_destination.hash)
        return None

    def get_known_destinations(self) -> Dict[str, Dict]:
        """Get dictionary of known destinations."""
        return self.known_destinations.copy()

    def add_known_destination(self, hash_str: str, name: str = "", metadata: Dict = None):
        """Add a known destination for easier messaging."""
        self.known_destinations[hash_str] = {
            "name": name,
            "added": datetime.utcnow().isoformat(),
            "metadata": metadata or {}
        }

    async def _load_stored_messages(self):
        """Load stored messages from disk."""
        msg_file = self._messages_path / "messages.json"
        if msg_file.exists():
            try:
                import json
                with open(msg_file, "r") as f:
                    self.stored_messages = json.load(f)
                logger.info(f"Loaded {len(self.stored_messages)} stored messages")
            except Exception as e:
                logger.error(f"Error loading stored messages: {e}")

    async def _save_stored_messages(self):
        """Save stored messages to disk."""
        msg_file = self._messages_path / "messages.json"
        try:
            import json
            with open(msg_file, "w") as f:
                json.dump(self.stored_messages, f, indent=2)
            logger.info(f"Saved {len(self.stored_messages)} messages")
        except Exception as e:
            logger.error(f"Error saving messages: {e}")

    def get_stored_messages(self, limit: int = 100) -> List[Dict]:
        """Get stored messages, most recent first."""
        return list(reversed(self.stored_messages[-limit:]))

    def register_message_callback(self, callback: Callable):
        """Register callback for incoming messages."""
        self.message_callbacks.append(callback)

    def register_file_callback(self, callback: Callable):
        """Register callback for incoming files."""
        self.file_callbacks.append(callback)

    def is_connected(self) -> bool:
        """Check if Reticulum is initialized."""
        return self.reticulum is not None and self._running

    def get_stats(self) -> Dict[str, Any]:
        """Get bridge statistics."""
        return {
            **self.stats,
            "address": self.get_address(),
            "known_destinations": len(self.known_destinations),
            "stored_messages": len(self.stored_messages)
        }


class MessageRelay:
    """
    Relay messages between Meshtastic and NomadNet.

    Routes messages based on prefix/destination and maintains
    mapping between the two networks.
    """

    def __init__(
        self,
        meshtastic_send: Callable,
        nomadnet_send: Callable
    ):
        self.meshtastic_send = meshtastic_send
        self.nomadnet_send = nomadnet_send

        # Mapping between mesh nodes and NomadNet destinations
        self.node_mapping: Dict[str, str] = {}

        # Message history for deduplication
        self.message_history: List[str] = []
        self.history_max = 1000

        self.stats = {
            "mesh_to_nomad": 0,
            "nomad_to_mesh": 0,
            "duplicates_dropped": 0
        }

    def add_node_mapping(self, mesh_node_id: str, nomadnet_hash: str):
        """Map a Meshtastic node to a NomadNet destination."""
        self.node_mapping[mesh_node_id] = nomadnet_hash

    def get_nomadnet_for_node(self, mesh_node_id: str) -> Optional[str]:
        """Get NomadNet destination for a mesh node."""
        return self.node_mapping.get(mesh_node_id)

    def _hash_message(self, source: str, text: str) -> str:
        """Create hash for deduplication."""
        return hashlib.sha256(f"{source}:{text}".encode()).hexdigest()[:16]

    def _is_duplicate(self, msg_hash: str) -> bool:
        """Check if message is a duplicate."""
        if msg_hash in self.message_history:
            return True

        self.message_history.append(msg_hash)
        if len(self.message_history) > self.history_max:
            self.message_history = self.message_history[-self.history_max:]

        return False

    async def relay_from_mesh(
        self,
        source_node: str,
        message: str,
        target_nomadnet: Optional[str] = None
    ) -> bool:
        """
        Relay a message from Meshtastic to NomadNet.

        Messages prefixed with 'N:' or with a mapped target will be relayed.
        """
        msg_hash = self._hash_message(source_node, message)
        if self._is_duplicate(msg_hash):
            self.stats["duplicates_dropped"] += 1
            return False

        # Check for explicit NomadNet prefix
        if message.startswith("N:"):
            message = message[2:].strip()

        # Determine target
        target = target_nomadnet or self.node_mapping.get(source_node)
        if not target:
            logger.debug("No NomadNet target for mesh relay")
            return False

        try:
            await self.nomadnet_send(
                destination_hash=target,
                content=message,
                title=f"From Mesh: {source_node}"
            )
            self.stats["mesh_to_nomad"] += 1
            logger.info(f"Relayed mesh message to NomadNet: {target}")
            return True
        except Exception as e:
            logger.error(f"Error relaying to NomadNet: {e}")
            return False

    async def relay_from_nomadnet(
        self,
        source_hash: str,
        message: str,
        target_mesh: Optional[str] = None
    ) -> bool:
        """
        Relay a message from NomadNet to Meshtastic.

        Messages prefixed with 'M:' or with a mapped target will be relayed.
        """
        msg_hash = self._hash_message(source_hash, message)
        if self._is_duplicate(msg_hash):
            self.stats["duplicates_dropped"] += 1
            return False

        # Check for explicit Meshtastic prefix
        if message.startswith("M:"):
            message = message[2:].strip()

        # Find mesh target from mapping (reverse lookup)
        target = target_mesh
        if not target:
            for mesh_id, nomad_hash in self.node_mapping.items():
                if nomad_hash == source_hash:
                    # Broadcast to mesh if no specific target
                    target = None
                    break

        try:
            await self.meshtastic_send(
                text=f"[NomadNet] {message}",
                destination=target
            )
            self.stats["nomad_to_mesh"] += 1
            logger.info("Relayed NomadNet message to mesh")
            return True
        except Exception as e:
            logger.error(f"Error relaying to mesh: {e}")
            return False

    def get_stats(self) -> Dict[str, Any]:
        """Get relay statistics."""
        return {
            **self.stats,
            "active_mappings": len(self.node_mapping)
        }
