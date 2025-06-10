"""
Notification routes for WebSocket connections and notification management
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from loguru import logger

from db_models import get_db
from services.notification_service import manager, notification_service

router = APIRouter(prefix="", tags=["notifications"])


@router.websocket("/ws/notifications")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time notifications"""
    await manager.connect(websocket)
    try:
        # Keep the connection alive
        while True:
            # Wait for any message from client (like ping/pong)
            data = await websocket.receive_text()
            # Echo back to confirm connection is alive
            await websocket.send_text(f"echo: {data}")
    except WebSocketDisconnect:
        await manager.disconnect(websocket)
        logger.info("Client disconnected from WebSocket")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await manager.disconnect(websocket)


@router.post("/api/notifications/test")
async def test_notification(
    message: str = "Test notification",
    stop_id: int = None,
    severity: str = "info"
):
    """Test endpoint to send a notification to all connected clients"""
    try:
        await notification_service.send_notification(message, stop_id, severity)
        return {"status": "success", "message": "Notification sent"}
    except Exception as e:
        logger.error(f"Error sending test notification: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/notifications/stop-update")
async def test_stop_update(stop_data: Dict[str, Any]):
    """Test endpoint to send a stop update notification"""
    try:
        await notification_service.notify_stop_update(stop_data)
        return {"status": "success", "message": "Stop update notification sent"}
    except Exception as e:
        logger.error(f"Error sending stop update notification: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/notifications/check-in-update")
async def test_check_in_update(check_in_data: Dict[str, Any]):
    """Test endpoint to send a check-in update notification"""
    try:
        await notification_service.notify_check_in_update(check_in_data)
        return {"status": "success", "message": "Check-in update notification sent"}
    except Exception as e:
        logger.error(f"Error sending check-in update notification: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/notifications/journey-state-update")
async def test_journey_state_update(state: int):
    """Test endpoint to send a journey state update notification"""
    try:
        await notification_service.notify_journey_state_update(state)
        return {"status": "success", "message": "Journey state update notification sent"}
    except Exception as e:
        logger.error(f"Error sending journey state update notification: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/notifications/connections")
async def get_active_connections():
    """Get the number of active WebSocket connections"""
    return {
        "active_connections": len(manager.active_connections),
        "status": "active"
    } 