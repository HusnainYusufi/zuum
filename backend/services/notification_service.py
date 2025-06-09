"""
Notification Service for real-time updates via WebSocket
"""
import json
from typing import Dict, Set, Optional, Any
from fastapi import WebSocket
from loguru import logger
import asyncio
from datetime import datetime


class ConnectionManager:
    """Manages WebSocket connections for real-time notifications"""
    
    def __init__(self):
        # Store active connections
        self.active_connections: Set[WebSocket] = set()
        self._lock = asyncio.Lock()
    
    async def connect(self, websocket: WebSocket):
        """Accept and store a new WebSocket connection"""
        await websocket.accept()
        async with self._lock:
            self.active_connections.add(websocket)
        logger.info(f"New WebSocket connection. Total connections: {len(self.active_connections)}")
    
    async def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket connection"""
        async with self._lock:
            self.active_connections.discard(websocket)
        logger.info(f"WebSocket disconnected. Total connections: {len(self.active_connections)}")
    
    async def send_personal_message(self, message: str, websocket: WebSocket):
        """Send a message to a specific WebSocket connection"""
        try:
            await websocket.send_text(message)
        except Exception as e:
            logger.error(f"Error sending personal message: {e}")
            await self.disconnect(websocket)
    
    async def broadcast(self, message: str):
        """Send a message to all connected clients"""
        if not self.active_connections:
            return
            
        # Create a copy of connections to avoid modification during iteration
        async with self._lock:
            connections = list(self.active_connections)
        
        # Send to all connections concurrently
        disconnected = []
        for connection in connections:
            try:
                await connection.send_text(message)
            except Exception as e:
                logger.error(f"Error broadcasting to connection: {e}")
                disconnected.append(connection)
        
        # Remove disconnected clients
        for connection in disconnected:
            await self.disconnect(connection)
    
    async def broadcast_json(self, data: Dict[str, Any]):
        """Send JSON data to all connected clients"""
        message = json.dumps(data)
        await self.broadcast(message)


# Global connection manager instance
manager = ConnectionManager()


class NotificationService:
    """Service for sending different types of notifications"""
    
    def __init__(self, connection_manager: ConnectionManager):
        self.manager = connection_manager
    
    async def notify_stop_update(self, stop_data: Dict[str, Any]):
        """Notify clients about a stop update"""
        notification = {
            "type": "stop_update",
            "data": stop_data,
            "timestamp": datetime.utcnow().isoformat()
        }
        await self.manager.broadcast_json(notification)
        logger.info(f"Broadcasted stop update for stop {stop_data.get('id')}")
    
    async def notify_check_in_update(self, check_in_data: Dict[str, Any]):
        """Notify clients about a new or updated check-in"""
        notification = {
            "type": "check_in_update",
            "data": check_in_data,
            "timestamp": datetime.utcnow().isoformat()
        }
        await self.manager.broadcast_json(notification)
        logger.info(f"Broadcasted check-in update for check-in {check_in_data.get('id')}")
    
    async def notify_journey_state_update(self, state: int):
        """Notify clients about journey state changes"""
        notification = {
            "type": "journey_state_update",
            "data": {"state": state},
            "timestamp": datetime.utcnow().isoformat()
        }
        await self.manager.broadcast_json(notification)
        logger.info(f"Broadcasted journey state update: {state}")
    
    async def send_notification(self, message: str, stop_id: Optional[int] = None, 
                               severity: str = "info"):
        """Send a general notification message"""
        notification = {
            "type": "notification",
            "data": {
                "message": message,
                "stop_id": stop_id,
                "severity": severity
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        await self.manager.broadcast_json(notification)
        logger.info(f"Broadcasted notification: {message}")


# Global notification service instance
notification_service = NotificationService(manager)


# Helper functions for easy access
async def notify_stop_update(stop_data: Dict[str, Any]):
    """Helper function to notify about stop updates"""
    await notification_service.notify_stop_update(stop_data)


async def notify_check_in_update(check_in_data: Dict[str, Any]):
    """Helper function to notify about check-in updates"""
    await notification_service.notify_check_in_update(check_in_data)


async def notify_journey_state_update(state: int):
    """Helper function to notify about journey state updates"""
    await notification_service.notify_journey_state_update(state)


async def send_notification(message: str, stop_id: Optional[int] = None, 
                           severity: str = "info"):
    """Helper function to send general notifications"""
    await notification_service.send_notification(message, stop_id, severity) 