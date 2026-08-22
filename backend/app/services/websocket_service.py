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
from datetime import datetime
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


class ConnectionManager:
    """
    Manages WebSocket connections for real-time communication.
    Supports multiple users, channels, and notification broadcasting.
    """

    def __init__(self):
        # Active connections: user_id -> WebSocket
        self.active_connections: Dict[int, WebSocket] = {}
        
        # User connection info: user_id -> UserConnection
        self.user_info: Dict[int, UserConnection] = {}
        
        # Channel subscriptions: channel_name -> Set[user_id]
        self.channels: Dict[str, Set[int]] = defaultdict(set)
        
        # Notification queue per user (for offline delivery)
        self.notification_queues: Dict[int, List[Notification]] = defaultdict(list)
        
        # Redis connection for distributed systems
        self.redis: Optional[redis.Redis] = None
        
        # Lock for thread-safe operations
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, user_id: int, user_type: str, username: str):
        """Accept and register a new WebSocket connection"""
        await websocket.accept()
        
        async with self._lock:
            self.active_connections[user_id] = websocket
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

    async def disconnect(self, user_id: int):
        """Remove a WebSocket connection"""
        async with self._lock:
            if user_id in self.active_connections:
                del self.active_connections[user_id]
            
            if user_id in self.user_info:
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
        async with self._lock:
            if user_id in self.active_connections:
                websocket = self.active_connections[user_id]
                await websocket.send_json(notification.to_json())
                return True
            else:
                # Queue for later delivery
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
                    websocket = self.active_connections[user_id]
                    for notification in notifications:
                        await websocket.send_json(notification.to_json())
                    notifications.clear()

    def get_connected_users(self) -> List[Dict]:
        """Get list of all connected users"""
        return [conn.to_json() for conn in self.user_info.values()]

    def get_connection_count(self) -> int:
        """Get total number of connections"""
        return len(self.active_connections)

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
                websocket = self.active_connections[uid]
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
        await connection_manager.disconnect(user_id)


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

