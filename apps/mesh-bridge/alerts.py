"""
Cross-protocol alert system with ISP failover detection,
priority-based routing, acknowledgment, and escalation.
"""

import asyncio
import logging
import subprocess
from datetime import datetime, timedelta
from typing import Optional, Dict, Callable, List, Any
import threading

from .config import config
from .models import (
    Alert, AlertPriority, Protocol, ISPStatus,
    QueuedMessage, MessageStatus
)
from .message_queue import MessageQueue

logger = logging.getLogger(__name__)


class ISPMonitor:
    """
    Monitor ISP connectivity and trigger failover to mesh.

    Performs periodic connectivity checks and notifies the
    alert system when ISP goes down/up.
    """

    def __init__(self, failover_callback: Optional[Callable] = None):
        self.status = ISPStatus()
        self.failover_callback = failover_callback
        self._running = False
        self._check_task: Optional[asyncio.Task] = None
        self._consecutive_failures = 0
        self._failure_threshold = 3  # Failures before triggering failover

    async def start(self):
        """Start ISP monitoring."""
        self._running = True
        self._check_task = asyncio.create_task(self._monitor_loop())
        logger.info("ISP monitor started")

    async def stop(self):
        """Stop ISP monitoring."""
        self._running = False
        if self._check_task:
            self._check_task.cancel()
            try:
                await self._check_task
            except asyncio.CancelledError:
                pass

    async def _monitor_loop(self):
        """Main monitoring loop."""
        while self._running:
            try:
                await self._check_connectivity()
            except Exception as e:
                logger.error(f"ISP check error: {e}")

            await asyncio.sleep(config.alerts.isp_check_interval)

    async def _check_connectivity(self):
        """Check connectivity to configured hosts."""
        success = False
        latencies = []

        for host in config.alerts.isp_check_hosts:
            try:
                # Use ping to check connectivity
                result = await asyncio.create_subprocess_exec(
                    "ping", "-c", "1", "-W", "3", host,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, _ = await result.communicate()

                if result.returncode == 0:
                    success = True
                    # Parse latency from ping output
                    output = stdout.decode()
                    if "time=" in output:
                        time_str = output.split("time=")[1].split()[0]
                        latencies.append(float(time_str.replace("ms", "")))
                    break

            except Exception as e:
                logger.debug(f"Ping to {host} failed: {e}")
                continue

        # Update status
        self.status.last_check = datetime.utcnow()

        if success:
            if latencies:
                self.status.latency_ms = sum(latencies) / len(latencies)

            self._consecutive_failures = 0
            self.status.failed_checks = 0

            # Check if recovering from failover
            if self.status.failover_active:
                self.status.failover_active = False
                self.status.is_online = True
                logger.info("ISP connection restored")
                if self.failover_callback:
                    await self.failover_callback(False)  # Failover deactivated
        else:
            self._consecutive_failures += 1
            self.status.failed_checks = self._consecutive_failures

            if self._consecutive_failures >= self._failure_threshold:
                if not self.status.failover_active:
                    self.status.is_online = False
                    self.status.failover_active = True
                    self.status.failover_triggered_at = datetime.utcnow()
                    logger.warning("ISP failover triggered - switching to mesh")
                    if self.failover_callback:
                        await self.failover_callback(True)  # Failover activated

    def get_status(self) -> Dict[str, Any]:
        """Get current ISP status."""
        return {
            "is_online": self.status.is_online,
            "latency_ms": self.status.latency_ms,
            "failover_active": self.status.failover_active,
            "failed_checks": self.status.failed_checks,
            "last_check": self.status.last_check.isoformat() if self.status.last_check else None,
            "failover_triggered_at": (
                self.status.failover_triggered_at.isoformat()
                if self.status.failover_triggered_at else None
            )
        }


class AlertManager:
    """
    Manages cross-protocol alert routing, acknowledgment, and escalation.

    Features:
    - Priority-based routing rules
    - ISP failover to mesh
    - Alert acknowledgment tracking
    - Automatic escalation for unacknowledged alerts
    """

    def __init__(
        self,
        meshtastic_send: Optional[Callable] = None,
        nomadnet_send: Optional[Callable] = None
    ):
        self.meshtastic_send = meshtastic_send
        self.nomadnet_send = nomadnet_send

        # Active alerts
        self.active_alerts: Dict[str, Alert] = {}
        self.acknowledged_alerts: Dict[str, Alert] = {}
        self.escalated_alerts: Dict[str, Alert] = {}

        # ISP monitoring
        self.isp_monitor = ISPMonitor(failover_callback=self._on_isp_failover)

        # Message queue for outbound alerts
        self.message_queue = MessageQueue()

        # Escalation tracking
        self._escalation_task: Optional[asyncio.Task] = None
        self._running = False
        self._lock = threading.Lock()

        # Routing rules
        self.routing_rules: List[Dict] = self._default_routing_rules()

        # Statistics
        self.stats = {
            "total_alerts": 0,
            "acknowledged": 0,
            "escalated": 0,
            "sent_via_mesh": 0,
            "sent_via_nomadnet": 0,
            "sent_via_both": 0
        }

    def _default_routing_rules(self) -> List[Dict]:
        """Default alert routing rules based on priority."""
        return [
            {
                "priority": AlertPriority.CRITICAL,
                "protocol": Protocol.BOTH,
                "escalation_timeout": 60,  # 1 minute
                "require_ack": True
            },
            {
                "priority": AlertPriority.HIGH,
                "protocol": Protocol.MESHTASTIC,
                "escalation_timeout": 300,  # 5 minutes
                "require_ack": True
            },
            {
                "priority": AlertPriority.MEDIUM,
                "protocol": Protocol.MESHTASTIC,
                "escalation_timeout": 1800,  # 30 minutes
                "require_ack": False
            },
            {
                "priority": AlertPriority.LOW,
                "protocol": Protocol.NOMADNET,  # Lower priority via NomadNet
                "escalation_timeout": 0,  # No escalation
                "require_ack": False
            },
            {
                "priority": AlertPriority.INFO,
                "protocol": Protocol.NOMADNET,
                "escalation_timeout": 0,
                "require_ack": False
            }
        ]

    async def start(self):
        """Start the alert manager."""
        self._running = True

        # Start ISP monitor
        await self.isp_monitor.start()

        # Start message queue
        self.message_queue.set_send_callback(self._send_queued_message)
        await self.message_queue.start()

        # Start escalation checker
        self._escalation_task = asyncio.create_task(self._escalation_loop())

        logger.info("Alert manager started")

    async def stop(self):
        """Stop the alert manager."""
        self._running = False

        await self.isp_monitor.stop()
        await self.message_queue.stop()

        if self._escalation_task:
            self._escalation_task.cancel()
            try:
                await self._escalation_task
            except asyncio.CancelledError:
                pass

        logger.info("Alert manager stopped")

    def set_meshtastic_send(self, callback: Callable):
        """Set the Meshtastic send callback."""
        self.meshtastic_send = callback

    def set_nomadnet_send(self, callback: Callable):
        """Set the NomadNet send callback."""
        self.nomadnet_send = callback

    async def send_alert(
        self,
        title: str,
        message: str,
        priority: AlertPriority = AlertPriority.MEDIUM,
        source: str = "aegis-core",
        category: str = "general",
        target_nodes: Optional[List[str]] = None,
        metadata: Optional[Dict] = None
    ) -> str:
        """
        Send an alert through the appropriate protocol(s).

        Returns:
            Alert ID
        """
        alert = Alert(
            title=title,
            message=message,
            priority=priority,
            source=source,
            category=category,
            target_nodes=target_nodes or [],
            metadata=metadata or {}
        )

        # Determine routing based on rules and ISP status
        protocol = self._determine_protocol(alert)
        alert.routing_protocol = protocol

        # Store alert
        with self._lock:
            self.active_alerts[alert.id] = alert

        self.stats["total_alerts"] += 1

        # Queue for sending
        await self.message_queue.enqueue(
            text=alert.to_mesh_message(),
            destination=target_nodes[0] if target_nodes else None,
            priority=priority,
            protocol=protocol,
            metadata={"alert_id": alert.id}
        )

        logger.info(f"Alert queued: {alert.id} via {protocol.name}")
        return alert.id

    def _determine_protocol(self, alert: Alert) -> Protocol:
        """Determine which protocol to use based on rules and ISP status."""
        # Find matching rule
        rule = None
        for r in self.routing_rules:
            if r["priority"] == alert.priority:
                rule = r
                break

        if not rule:
            rule = {"protocol": Protocol.MESHTASTIC}

        protocol = rule["protocol"]

        # If ISP is down, force mesh for critical alerts
        if self.isp_monitor.status.failover_active:
            if alert.priority in [AlertPriority.CRITICAL, AlertPriority.HIGH]:
                protocol = Protocol.MESHTASTIC
                logger.info("ISP down - routing via mesh")

        return protocol

    async def _send_queued_message(self, message: QueuedMessage) -> bool:
        """Send a queued message via the appropriate protocol."""
        protocol = message.protocol
        success = False

        try:
            if protocol in [Protocol.MESHTASTIC, Protocol.BOTH]:
                if self.meshtastic_send:
                    result = await self.meshtastic_send(
                        text=message.text,
                        destination=message.destination
                    )
                    if result:
                        success = True
                        self.stats["sent_via_mesh"] += 1

            if protocol in [Protocol.NOMADNET, Protocol.BOTH]:
                if self.nomadnet_send and message.destination:
                    result = await self.nomadnet_send(
                        destination_hash=message.destination,
                        content=message.text,
                        title="Aegis Alert"
                    )
                    if result:
                        success = True
                        self.stats["sent_via_nomadnet"] += 1

            if protocol == Protocol.BOTH and success:
                self.stats["sent_via_both"] += 1

            return success

        except Exception as e:
            logger.error(f"Error sending message: {e}")
            return False

    async def acknowledge_alert(self, alert_id: str, acknowledged_by: str = "unknown") -> bool:
        """
        Acknowledge an alert.

        Returns:
            True if alert was found and acknowledged
        """
        with self._lock:
            if alert_id in self.active_alerts:
                alert = self.active_alerts.pop(alert_id)
                alert.acknowledged = True
                alert.acknowledged_by = acknowledged_by
                alert.acknowledged_at = datetime.utcnow()
                self.acknowledged_alerts[alert_id] = alert
                self.stats["acknowledged"] += 1
                logger.info(f"Alert {alert_id} acknowledged by {acknowledged_by}")
                return True

            # Check if already in escalated
            if alert_id in self.escalated_alerts:
                alert = self.escalated_alerts.pop(alert_id)
                alert.acknowledged = True
                alert.acknowledged_by = acknowledged_by
                alert.acknowledged_at = datetime.utcnow()
                self.acknowledged_alerts[alert_id] = alert
                self.stats["acknowledged"] += 1
                return True

        return False

    async def _escalation_loop(self):
        """Check for alerts that need escalation."""
        while self._running:
            try:
                await self._check_escalations()
            except Exception as e:
                logger.error(f"Escalation check error: {e}")

            await asyncio.sleep(30)  # Check every 30 seconds

    async def _check_escalations(self):
        """Check and process alert escalations."""
        now = datetime.utcnow()
        to_escalate = []

        with self._lock:
            for alert_id, alert in list(self.active_alerts.items()):
                # Find escalation timeout for this priority
                timeout = config.alerts.escalation_timeout
                for rule in self.routing_rules:
                    if rule["priority"] == alert.priority:
                        timeout = rule.get("escalation_timeout", timeout)
                        break

                if timeout <= 0:
                    continue  # No escalation for this priority

                # Check if escalation needed
                age = (now - alert.created_at).total_seconds()
                if age >= timeout and not alert.escalated:
                    to_escalate.append(alert_id)

        # Process escalations
        for alert_id in to_escalate:
            await self._escalate_alert(alert_id)

    async def _escalate_alert(self, alert_id: str):
        """Escalate an unacknowledged alert."""
        with self._lock:
            if alert_id not in self.active_alerts:
                return

            alert = self.active_alerts[alert_id]
            alert.escalated = True
            alert.escalated_at = datetime.utcnow()

            # Move to escalated
            self.escalated_alerts[alert_id] = self.active_alerts.pop(alert_id)

        self.stats["escalated"] += 1
        logger.warning(f"Alert {alert_id} escalated due to no acknowledgment")

        # Send escalation notification via all protocols
        escalation_msg = f"[ESCALATION] {alert.to_mesh_message()}"

        await self.message_queue.enqueue(
            text=escalation_msg,
            priority=AlertPriority.CRITICAL,  # Escalations are critical
            protocol=Protocol.BOTH,
            metadata={"alert_id": alert_id, "escalation": True}
        )

    async def _on_isp_failover(self, failover_active: bool):
        """Handle ISP failover state change."""
        if failover_active:
            # Send alert about ISP failure via mesh
            await self.send_alert(
                title="ISP Failover",
                message="Internet connection lost. Routing via mesh network.",
                priority=AlertPriority.HIGH,
                source="isp-monitor",
                category="network"
            )
        else:
            # Send recovery notification
            await self.send_alert(
                title="ISP Restored",
                message="Internet connection restored. Resuming normal routing.",
                priority=AlertPriority.MEDIUM,
                source="isp-monitor",
                category="network"
            )

    def get_active_alerts(self) -> List[Dict]:
        """Get all active (unacknowledged) alerts."""
        with self._lock:
            return [alert.to_dict() for alert in self.active_alerts.values()]

    def get_escalated_alerts(self) -> List[Dict]:
        """Get all escalated alerts."""
        with self._lock:
            return [alert.to_dict() for alert in self.escalated_alerts.values()]

    def get_alert(self, alert_id: str) -> Optional[Dict]:
        """Get a specific alert by ID."""
        with self._lock:
            alert = (
                self.active_alerts.get(alert_id) or
                self.escalated_alerts.get(alert_id) or
                self.acknowledged_alerts.get(alert_id)
            )
            return alert.to_dict() if alert else None

    def get_stats(self) -> Dict[str, Any]:
        """Get alert manager statistics."""
        return {
            **self.stats,
            "active_alerts": len(self.active_alerts),
            "escalated_alerts": len(self.escalated_alerts),
            "acknowledged_alerts": len(self.acknowledged_alerts),
            "isp_status": self.isp_monitor.get_status(),
            "queue_status": self.message_queue.get_queue_status()
        }

    def update_routing_rule(
        self,
        priority: AlertPriority,
        protocol: Optional[Protocol] = None,
        escalation_timeout: Optional[int] = None,
        require_ack: Optional[bool] = None
    ):
        """Update a routing rule."""
        for rule in self.routing_rules:
            if rule["priority"] == priority:
                if protocol is not None:
                    rule["protocol"] = protocol
                if escalation_timeout is not None:
                    rule["escalation_timeout"] = escalation_timeout
                if require_ack is not None:
                    rule["require_ack"] = require_ack
                return True
        return False
