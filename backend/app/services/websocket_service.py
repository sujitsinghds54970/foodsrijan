"""
WebSocket Service for Real-time Notifications

Provides real-time communication for:
- Staff report alerts
- Appointment notifications
- System announcements
- Live updates across all connected clients
"""

import json
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, field, asdict
from enum import Enum
import asyncio
from collections import defaultdict
import redis.asyncio as redis
from fastapi import WebSocket, WebSocketDisconnect

# Connection Manager for handling multiple WebSocket connections


class NotificationType(str, Enum):
    """Types of notifications"""
    REPORT_READY = "report_ready"
    REPORT_URGENT = "report_urgent"
    APPOINTMENT_REMINDER = "appointment_reminder"
    APPOINTMENT_CANCELLED = "appointment_cancelled"
    APPOINTMENT_CONFIRMED = "appointment_confirmed"
    NEW_PATIENT = "new_patient"
    LOW_STOCK_ALERT = "low_stock_alert"
    PAYMENT_RECEIVED = "payment_received"
    SYSTEM_ANNOUNCEMENT = "system_announcement"
    DOCTOR_ASSIGNED = "doctor_assigned"
    LAB_RESULT = "lab_result"


class Priority(str, Enum):
    """Notification priority levels"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


@dataclass
class Notification:
    """Notification data structure"""
    id: str
    type: str
    title: str
    message: str
    priority: str = Priority.NORMAL.value
    data: Dict = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    read: bool = False
    action_url: Optional[str] = None
    reference_id: Optional[str] = None
    reference_type: Optional[str] = None

    def to_json(self):
        return asdict(self)


@dataclass
class UserConnection:
    """User connection information"""
    user_id: int
    user_type: str  # doctor, staff, admin
    username: str
    connected_at: str = field(default_factory=lambda: datetime.now().isoformat())
    last_active: str = field(default_factory=lambda: datetime.now().isoformat())
    subscribed_channels: List[str] = field(default_factory=list)

    def to_json(self):
        return asdict(self)


@dataclass
class ThemeSubscriber:
    """A scoped theme socket subscription.

    A single user may hold several theme sockets (tabs or devices), each with
    the profile type and company scope derived from the authenticated session.
    """
    user_id: int
    profile_type_id: Optional[int] = None
    company_id: Optional[int] = None
    profile_type_key: Optional[str] = None
    connected_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_json(self):
        return asdict(self)


@dataclass
class DomainSubscriber:
    """A tenant-scoped domain event subscription derived by the server.

    Company CEOs subscribe to ``company:{company_id}``; outlet managers
    subscribe only to ``outlet:{outlet_id}`` inside their company.
    """
    user_id: int
    role: str
    company_id: int
    outlet_id: Optional[int] = None
    connected_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @property
    def channels(self) -> List[str]:
        if self.outlet_id is not None:
            return [f"outlet:{self.outlet_id}"]
        return [f"company:{self.company_id}"]

    def to_json(self):
        return {**asdict(self), "channels": self.channels}


class ConnectionManager:
    """
    Manages WebSocket connections for real-time communication.
    Supports multiple users, channels, and notification broadcasting.
    """

    def __init__(self):
        # A user may have several tabs or devices connected simultaneously.
        self.active_connections: Dict[int, Set[WebSocket]] = defaultdict(set)
        
        # User connection info: user_id -> UserConnection
        self.user_info: Dict[int, UserConnection] = {}
        
        # Channel subscriptions: channel_name -> Set[user_id]
        self.channels: Dict[str, Set[int]] = defaultdict(set)
        
        # Notification queue per user (for offline delivery)
        self.notification_queues: Dict[int, List[Notification]] = defaultdict(list)
        
        # Redis connection for distributed systems
        self.redis: Optional[redis.Redis] = None
        
        # Scoped theme sockets: websocket -> ThemeSubscriber
        self.theme_connections: Dict[WebSocket, ThemeSubscriber] = {}

        # Event loop that owns the theme sockets, used to dispatch events
        # emitted from synchronous request handlers.
        self.theme_event_loop: Optional[asyncio.AbstractEventLoop] = None

        # Scoped outlet/company domain sockets: websocket -> DomainSubscriber
        self.domain_connections: Dict[WebSocket, DomainSubscriber] = {}
        self.domain_event_loop: Optional[asyncio.AbstractEventLoop] = None

        # Lock for thread-safe operations
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, user_id: int, user_type: str, username: str):
        """Accept and register a new WebSocket connection"""
        await websocket.accept()
        
        async with self._lock:
            self.active_connections[user_id].add(websocket)
            self.user_info[user_id] = UserConnection(
                user_id=user_id,
                user_type=user_type,
                username=username
            )
            
            # Subscribe to user's private channel
            private_channel = f"user:{user_id}"
            self.channels[private_channel].add(user_id)
            self.user_info[user_id].subscribed_channels.append(private_channel)
            
            # Subscribe to role-based channel
            role_channel = f"role:{user_type}"
            if user_id not in self.channels[role_channel]:
                self.channels[role_channel].add(user_id)
                self.user_info[user_id].subscribed_channels.append(role_channel)

        # Send pending notifications
        await self._send_pending_notifications(user_id)

        # Log connection
        print(f"WebSocket connected: User {user_id} ({username}) - Type: {user_type}")

        return private_channel

    async def disconnect(self, user_id: int, websocket: Optional[WebSocket] = None):
        """Remove a WebSocket connection"""
        async with self._lock:
            if user_id in self.active_connections:
                if websocket is None:
                    self.active_connections.pop(user_id, None)
                else:
                    self.active_connections[user_id].discard(websocket)
                    if not self.active_connections[user_id]:
                        del self.active_connections[user_id]
            
            if user_id in self.user_info and user_id not in self.active_connections:
                user_conn = self.user_info[user_id]
                # Remove from all channels
                for channel in user_conn.subscribed_channels:
                    if user_id in self.channels[channel]:
                        self.channels[channel].discard(user_id)
                        if not self.channels[channel]:
                            del self.channels[channel]
                del self.user_info[user_id]

        print(f"WebSocket disconnected: User {user_id}")

    async def send_personal_notification(self, user_id: int, notification: Notification):
        """Send notification to a specific user"""
        sockets = list(self.active_connections.get(user_id, ()))
        if sockets:
            sent = False
            for websocket in sockets:
                try:
                    await websocket.send_json(notification.to_json())
                    sent = True
                except Exception:
                    await self.disconnect(user_id, websocket)
            return sent
        async with self._lock:
            if user_id not in self.active_connections:
                # Queue only when the user has no active client.
                self.notification_queues[user_id].append(notification)
                return False

    async def send_channel_notification(self, channel: str, notification: Notification):
        """Send notification to all users subscribed to a channel"""
        if channel not in self.channels:
            return 0

        user_ids = list(self.channels[channel])
        sent_count = 0

        for user_id in user_ids:
            success = await self.send_personal_notification(user_id, notification)
            if success:
                sent_count += 1

        return sent_count

    async def broadcast_notification(self, notification: Notification):
        """Broadcast notification to all connected users"""
        user_ids = list(self.active_connections.keys())
        sent_count = 0

        for user_id in user_ids:
            success = await self.send_personal_notification(user_id, notification)
            if success:
                sent_count += 1

        return sent_count

    async def broadcast_event(self, event: Dict):
        """Broadcast a structured domain event to every connected client."""
        sent_count = 0
        for user_id, sockets in list(self.active_connections.items()):
            for websocket in list(sockets):
                try:
                    await websocket.send_json(event)
                    sent_count += 1
                except Exception:
                    await self.disconnect(user_id, websocket)
        return sent_count

    async def connect_theme_socket(
        self,
        websocket: WebSocket,
        user_id: int,
        profile_type_id: Optional[int] = None,
        company_id: Optional[int] = None,
        profile_type_key: Optional[str] = None,
    ) -> ThemeSubscriber:
        """Accept and register a scoped theme socket."""
        await websocket.accept()
        subscriber = ThemeSubscriber(
            user_id=user_id,
            profile_type_id=profile_type_id,
            company_id=company_id,
            profile_type_key=profile_type_key,
        )
        async with self._lock:
            self.theme_connections[websocket] = subscriber
            try:
                self.theme_event_loop = asyncio.get_running_loop()
            except RuntimeError:
                self.theme_event_loop = None
        return subscriber

    async def disconnect_theme_socket(self, websocket: WebSocket) -> None:
        """Remove a theme socket registration."""
        async with self._lock:
            self.theme_connections.pop(websocket, None)

    def theme_subscribers(self) -> List[Dict]:
        """Inspect currently registered theme subscriptions."""
        return [subscriber.to_json() for subscriber in self.theme_connections.values()]

    def theme_connection_count(self) -> int:
        return len(self.theme_connections)

    @staticmethod
    def theme_event_matches(subscriber: ThemeSubscriber, profile_type_id, company_id) -> bool:
        """Scope matching for theme events.

        A subscriber receives an event when the profile type matches. A
        company-scoped event (``company_id`` present) is limited to subscribers
        inside that company; a platform event (``company_id`` is ``None``)
        reaches every subscriber of the profile type.
        """
        if profile_type_id is not None and subscriber.profile_type_id != profile_type_id:
            return False
        if company_id is not None and subscriber.company_id != company_id:
            return False
        return True

    async def broadcast_theme_event(self, event: Dict) -> int:
        """Send a theme event to every theme socket matching its scope."""
        profile_type_id = event.get("profile_type_id")
        company_id = event.get("company_id")
        sent_count = 0
        for websocket, subscriber in list(self.theme_connections.items()):
            if not self.theme_event_matches(subscriber, profile_type_id, company_id):
                continue
            try:
                await websocket.send_json(event)
                sent_count += 1
            except Exception:
                await self.disconnect_theme_socket(websocket)
        return sent_count

    async def connect_domain_socket(self, websocket: WebSocket, subscriber: DomainSubscriber) -> DomainSubscriber:
        await websocket.accept()
        self.domain_connections[websocket] = subscriber
        try:
            self.domain_event_loop = asyncio.get_running_loop()
        except RuntimeError:
            self.domain_event_loop = None
        return subscriber

    async def disconnect_domain_socket(self, websocket: WebSocket) -> None:
        self.domain_connections.pop(websocket, None)

    def domain_subscribers(self) -> List[Dict]:
        return [subscriber.to_json() for subscriber in self.domain_connections.values()]

    @staticmethod
    def domain_event_matches(subscriber: DomainSubscriber, event: Dict) -> bool:
        """Company events reach that company's CEOs; outlet events also reach that outlet's manager."""
        scope = event.get("scope") or {}
        company_id = scope.get("company_id")
        outlet_id = scope.get("outlet_id")
        if company_id is None or subscriber.company_id != company_id:
            return False
        if subscriber.outlet_id is not None:
            return outlet_id is not None and subscriber.outlet_id == outlet_id
        return True

    async def broadcast_domain_event(self, event: Dict) -> int:
        revoke_user_ids = set(event.pop("_revoke_user_ids", ()) or ())
        sent_count = 0
        for websocket, subscriber in list(self.domain_connections.items()):
            if not self.domain_event_matches(subscriber, event):
                continue
            try:
                await websocket.send_json(event)
                sent_count += 1
            except Exception:
                await self.disconnect_domain_socket(websocket)
                continue
            if subscriber.user_id in revoke_user_ids:
                try:
                    await websocket.close(code=4403, reason="Session invalidated")
                except Exception:
                    pass
                await self.disconnect_domain_socket(websocket)
        return sent_count

    async def broadcast_to_role(self, role: str, notification: Notification):
        """Send notification to all users with a specific role"""
        channel = f"role:{role}"
        return await self.send_channel_notification(channel, notification)

    async def broadcast_to_branch(self, branch_id: int, notification: Notification):
        """Send notification to all users in a specific branch"""
        channel = f"branch:{branch_id}"
        return await self.send_channel_notification(channel, notification)

    async def subscribe_to_channel(self, user_id: int, channel: str):
        """Subscribe a user to a channel"""
        async with self._lock:
            self.channels[channel].add(user_id)
            if user_id in self.user_info:
                if channel not in self.user_info[user_id].subscribed_channels:
                    self.user_info[user_id].subscribed_channels.append(channel)

    async def unsubscribe_from_channel(self, user_id: int, channel: str):
        """Unsubscribe a user from a channel"""
        async with self._lock:
            if channel in self.channels:
                self.channels[channel].discard(user_id)

    async def _send_pending_notifications(self, user_id: int):
        """Send queued notifications when user reconnects"""
        async with self._lock:
            if user_id in self.notification_queues:
                notifications = self.notification_queues[user_id]
                if user_id in self.active_connections:
                    websocket = next(iter(self.active_connections[user_id]))
                    for notification in notifications:
                        await websocket.send_json(notification.to_json())
                    notifications.clear()

    def get_connected_users(self) -> List[Dict]:
        """Get list of all connected users"""
        return [conn.to_json() for conn in self.user_info.values()]

    def get_connection_count(self) -> int:
        """Get total number of connections"""
        return sum(len(sockets) for sockets in self.active_connections.values())

    def get_channel_subscribers(self, channel: str) -> List[int]:
        """Get list of user IDs subscribed to a channel"""
        return list(self.channels.get(channel, set()))

    async def send_typing_indicator(self, user_id: int, channel: str, is_typing: bool):
        """Send typing indicator to a channel"""
        indicator = {
            "type": "typing",
            "user_id": user_id,
            "channel": channel,
            "is_typing": is_typing
        }

        if channel not in self.channels:
            return 0

        sent_count = 0
        for uid in self.channels[channel]:
            if uid in self.active_connections and uid != user_id:
                for websocket in list(self.active_connections[uid]):
                    await websocket.send_json(indicator)
                    sent_count += 1

        return sent_count


# Global connection manager instance
connection_manager = ConnectionManager()


# Notification Factory for creating different types of notifications


class NotificationFactory:
    """Factory for creating common notification types"""

    @staticmethod
    def create_report_ready_notification(
        patient_name: str,
        report_id: str,
        report_type: str,
        branch_id: int,
        doctor_id: Optional[int] = None
    ) -> Notification:
        """Create a report ready notification"""
        return Notification(
            id=f"NR-{uuid.uuid4().hex[:8].upper()}",
            type=NotificationType.REPORT_READY.value,
            title="Order Ready",
            message=f"New {report_type} report ready for patient {patient_name}",
            priority=Priority.NORMAL.value,
            data={
                "report_id": report_id,
                "report_type": report_type,
                "patient_name": patient_name,
                "branch_id": branch_id
            },
            action_url=f"/orders/{report_id}",
            reference_id=report_id,
            reference_type="lab_result"
        )

    @staticmethod
    def create_urgent_report_notification(
        patient_name: str,
        report_id: str,
        report_type: str,
        urgency_reason: str
    ) -> Notification:
        """Create an urgent report notification"""
        return Notification(
            id=f"NU-{uuid.uuid4().hex[:8].upper()}",
            type=NotificationType.REPORT_URGENT.value,
            title="🔴 URGENT: Order Ready",
            message=f"URGENT {report_type} report for {patient_name} - {urgency_reason}",
            priority=Priority.URGENT.value,
            data={
                "report_id": report_id,
                "report_type": report_type,
                "patient_name": patient_name,
                "urgency_reason": urgency_reason
            },
            action_url=f"/orders/{report_id}",
            reference_id=report_id,
            reference_type="lab_result"
        )

    @staticmethod
    def create_appointment_reminder(
        patient_name: str,
        appointment_id: str,
        appointment_date: str,
        appointment_time: str,
        doctor_name: str
    ) -> Notification:
        """Create an appointment reminder notification"""
        return Notification(
            id=f"NA-{uuid.uuid4().hex[:8].upper()}",
            type=NotificationType.APPOINTMENT_REMINDER.value,
            title="Appointment Reminder",
            message=f"Reminder: Appointment for {patient_name} with {doctor_name} on {appointment_date} at {appointment_time}",
            priority=Priority.NORMAL.value,
            data={
                "appointment_id": appointment_id,
                "patient_name": patient_name,
                "doctor_name": doctor_name,
                "appointment_date": appointment_date,
                "appointment_time": appointment_time
            },
            action_url=f"/appointments/{appointment_id}",
            reference_id=appointment_id,
            reference_type="appointment"
        )

    @staticmethod
    def create_low_stock_alert(
        item_name: str,
        item_id: str,
        current_stock: int,
        minimum_stock: int,
        branch_id: int
    ) -> Notification:
        """Create a low stock alert notification"""
        status = "Out of Stock" if current_stock == 0 else "Low Stock"
        return Notification(
            id=f"NS-{uuid.uuid4().hex[:8].upper()}",
            type=NotificationType.LOW_STOCK_ALERT.value,
            title=f"⚠️ {status}: {item_name}",
            message=f"{item_name} is running low (Current: {current_stock}, Min: {minimum_stock})",
            priority=Priority.HIGH.value if current_stock == 0 else Priority.NORMAL.value,
            data={
                "item_id": item_id,
                "item_name": item_name,
                "current_stock": current_stock,
                "minimum_stock": minimum_stock,
                "branch_id": branch_id
            },
            action_url=f"/inventory/{item_id}",
            reference_id=item_id,
            reference_type="inventory_item"
        )

    @staticmethod
    def create_payment_received_notification(
        patient_name: str,
        invoice_id: str,
        amount: float,
        branch_id: int
    ) -> Notification:
        """Create a payment received notification"""
        return Notification(
            id=f"NP-{uuid.uuid4().hex[:8].upper()}",
            type=NotificationType.PAYMENT_RECEIVED.value,
            title="Payment Received",
            message=f"Payment of ₹{amount:.2f} received from {patient_name}",
            priority=Priority.NORMAL.value,
            data={
                "invoice_id": invoice_id,
                "patient_name": patient_name,
                "amount": amount,
                "branch_id": branch_id
            },
            action_url=f"/invoices/{invoice_id}",
            reference_id=invoice_id,
            reference_type="invoice"
        )

    @staticmethod
    def create_system_announcement(
        title: str,
        message: str,
        priority: str = Priority.NORMAL.value
    ) -> Notification:
        """Create a system announcement"""
        return Notification(
            id=f"NS-{uuid.uuid4().hex[:8].upper()}",
            type=NotificationType.SYSTEM_ANNOUNCEMENT.value,
            title=title,
            message=message,
            priority=priority,
            data={}
        )

    @staticmethod
    def create_doctor_assigned_notification(
        doctor_name: str,
        patient_name: str,
        appointment_id: str,
        branch_id: int
    ) -> Notification:
        """Create notification when doctor is assigned to a patient"""
        return Notification(
            id=f"ND-{uuid.uuid4().hex[:8].upper()}",
            type=NotificationType.DOCTOR_ASSIGNED.value,
            title="New Customer Assignment",
            message=f"You have been assigned to patient {patient_name}",
            priority=Priority.NORMAL.value,
            data={
                "doctor_name": doctor_name,
                "patient_name": patient_name,
                "appointment_id": appointment_id,
                "branch_id": branch_id
            },
            action_url=f"/customers/{appointment_id}",
            reference_id=appointment_id,
            reference_type="appointment"
        )


# Helper functions for common operations

async def notify_staff_new_report(
    report_id: str,
    report_type: str,
    patient_name: str,
    doctor_ids: List[int],
    is_urgent: bool = False
):
    """Notify staff about a new report"""
    notification_class = NotificationFactory.create_urgent_report_notification if is_urgent else NotificationFactory.create_report_ready_notification
    
    notification = notification_class(
        patient_name=patient_name,
        report_id=report_id,
        report_type=report_type,
        urgency_reason="Critical values detected" if is_urgent else ""
    )

    for doctor_id in doctor_ids:
        await connection_manager.send_personal_notification(doctor_id, notification)


async def notify_branch_staff(
    branch_id: int,
    notification: Notification
):
    """Notify all staff in a branch"""
    await connection_manager.broadcast_to_branch(branch_id, notification)


async def notify_role(
    role: str,
    notification: Notification
):
    """Notify all users with a specific role"""
    await connection_manager.broadcast_to_role(role, notification)


# WebSocket endpoint handlers

async def websocket_endpoint(websocket: WebSocket, user_id: int, user_type: str, username: str):
    """Main WebSocket endpoint handler"""
    channel = await connection_manager.connect(websocket, user_id, user_type, username)
    
    try:
        while True:
            # Wait for messages from client
            data = await websocket.receive_text()
            
            try:
                message = json.loads(data)
                
                # Handle different message types
                message_type = message.get("type")
                
                if message_type == "ping":
                    # Keep-alive ping
                    await websocket.send_json({"type": "pong", "timestamp": datetime.now().isoformat()})
                    
                elif message_type == "subscribe":
                    # Subscribe to a channel
                    target_channel = message.get("channel")
                    if target_channel:
                        await connection_manager.subscribe_to_channel(user_id, target_channel)
                        await websocket.send_json({
                            "type": "subscribed",
                            "channel": target_channel
                        })
                        
                elif message_type == "unsubscribe":
                    # Unsubscribe from a channel
                    target_channel = message.get("channel")
                    if target_channel:
                        await connection_manager.unsubscribe_from_channel(user_id, target_channel)
                        await websocket.send_json({
                            "type": "unsubscribed",
                            "channel": target_channel
                        })
                        
                elif message_type == "mark_read":
                    # Mark notification as read
                    notification_id = message.get("notification_id")
                    # Could integrate with database here
                    await websocket.send_json({
                        "type": "marked_read",
                        "notification_id": notification_id
                    })
                    
                elif message_type == "typing":
                    # Send typing indicator to channel
                    target_channel = message.get("channel")
                    is_typing = message.get("is_typing", True)
                    if target_channel:
                        await connection_manager.send_typing_indicator(
                            user_id, target_channel, is_typing
                        )
                        
                else:
                    # Echo back unknown messages
                    await websocket.send_json({
                        "type": "echo",
                        "original": message
                    })
                    
            except json.JSONDecodeError:
                await websocket.send_json({
                    "type": "error",
                    "message": "Invalid JSON format"
                })
                
    except WebSocketDisconnect:
        await connection_manager.disconnect(user_id, websocket)


async def theme_updates_endpoint(
    websocket: WebSocket,
    user_id: int,
    profile_type_id: Optional[int] = None,
    company_id: Optional[int] = None,
    profile_type_key: Optional[str] = None,
):
    """Theme update socket handler for /api/ws/theme-updates."""
    await connection_manager.connect_theme_socket(
        websocket,
        user_id,
        profile_type_id=profile_type_id,
        company_id=company_id,
        profile_type_key=profile_type_key,
    )
    try:
        while True:
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
            except json.JSONDecodeError:
                await websocket.send_json({"type": "error", "message": "Invalid JSON format"})
                continue
            if message.get("type") == "ping":
                await websocket.send_json({
                    "type": "pong",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })
            else:
                await websocket.send_json({"type": "ack", "received": message.get("type")})
    except WebSocketDisconnect:
        pass
    finally:
        await connection_manager.disconnect_theme_socket(websocket)


def publish_theme_event(event: Dict, timeout: float = 2.0) -> int:
    """Broadcast a theme event from either a sync or async caller.

    Realtime delivery is best effort: transport failures never propagate to the
    request that produced the event.
    """
    try:
        running_loop = asyncio.get_running_loop()
    except RuntimeError:
        running_loop = None

    if running_loop is not None:
        running_loop.create_task(connection_manager.broadcast_theme_event(event))
        return 0

    loop = connection_manager.theme_event_loop
    try:
        if loop is not None and loop.is_running():
            future = asyncio.run_coroutine_threadsafe(
                connection_manager.broadcast_theme_event(event), loop
            )
            return future.result(timeout=timeout)
        return asyncio.run(connection_manager.broadcast_theme_event(event))
    except Exception as error:
        print(f"Warning: theme event broadcast failed - {error}")
        return 0


async def domain_events_endpoint(websocket: WebSocket, subscriber: DomainSubscriber):
    """Scoped outlet/company event socket for /api/ws/outlet-events."""
    await connection_manager.connect_domain_socket(websocket, subscriber)
    try:
        await websocket.send_json({"type": "subscribed", "channels": subscriber.channels})
        while True:
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
            except json.JSONDecodeError:
                await websocket.send_json({"type": "error", "message": "Invalid JSON format"})
                continue
            if message.get("type") == "ping":
                await websocket.send_json({"type": "pong", "timestamp": datetime.now(timezone.utc).isoformat()})
            else:
                # Subscriptions are fixed by the server; clients cannot choose tenant channels.
                await websocket.send_json({"type": "ack", "received": message.get("type")})
    except WebSocketDisconnect:
        pass
    finally:
        await connection_manager.disconnect_domain_socket(websocket)


def build_domain_event(
    event_type: str,
    *,
    company_id: int,
    outlet_id: Optional[int],
    actor_id: Optional[int],
    actor_role: Optional[str],
    resource_type: str,
    resource_id: Optional[int],
    data: Optional[Dict] = None,
) -> Dict:
    return {
        "event_id": str(uuid.uuid4()),
        "event_version": 1,
        "type": event_type,
        "occurred_at": datetime.now(timezone.utc).isoformat(),
        "actor": {"id": actor_id, "role": actor_role},
        "scope": {"company_id": company_id, "outlet_id": outlet_id},
        "resource": {"type": resource_type, "id": resource_id},
        "data": data or {},
    }


def publish_domain_event(event: Dict, *, revoke_user_ids: Optional[List[int]] = None, timeout: float = 2.0) -> int:
    """Best-effort delivery of a scoped domain event from sync or async callers."""
    if revoke_user_ids:
        event = {**event, "_revoke_user_ids": list(revoke_user_ids)}
    if not connection_manager.domain_connections:
        return 0
    try:
        running_loop = asyncio.get_running_loop()
    except RuntimeError:
        running_loop = None

    if running_loop is not None:
        running_loop.create_task(connection_manager.broadcast_domain_event(event))
        return 0

    loop = connection_manager.domain_event_loop
    try:
        if loop is not None and loop.is_running():
            future = asyncio.run_coroutine_threadsafe(connection_manager.broadcast_domain_event(event), loop)
            return future.result(timeout=timeout)
        return asyncio.run(connection_manager.broadcast_domain_event(event))
    except Exception as error:
        print(f"Warning: domain event broadcast failed - {error}")
        return 0


# Redis integration for distributed systems

async def init_redis():
    """Initialize Redis connection for distributed WebSocket"""
    try:
        connection_manager.redis = redis.Redis(
            host="localhost",
            port=6379,
            db=0,
            decode_responses=True
        )
        print("Redis connected for WebSocket service")
    except Exception as e:
        print(f"Warning: Redis not available - {e}")


async def publish_to_redis(channel: str, message: str):
    """Publish message to Redis channel"""
    if connection_manager.redis:
        await connection_manager.redis.publish(channel, message)


async def subscribe_to_redis(channel: str):
    """Subscribe to Redis channel and broadcast to WebSocket clients"""
    if connection_manager.redis:
        pubsub = connection_manager.redis.pubsub()
        await pubsub.subscribe(channel)
        
        async for message in pubsub.listen():
            if message["type"] == "message":
                try:
                    data = json.loads(message["data"])
                    notification = Notification(**data)
                    await connection_manager.send_channel_notification(channel, notification)
                except Exception as e:
                    print(f"Error processing Redis message: {e}")
