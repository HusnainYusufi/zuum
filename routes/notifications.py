"""
Notification routes for WebSocket connections and notification management
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException
from typing import Dict, Any
from loguru import logger

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


@router.post("/api/notifications/check-in-update")
async def test_check_in_update(check_in_data: Dict[str, Any]):
    """Test endpoint to send a check-in update notification"""
    try:
        await notification_service.notify_check_in_update(check_in_data)
        return {"status": "success", "message": "Check-in update notification sent"}
    except Exception as e:
        logger.error(f"Error sending check-in update notification: {e}")
        raise HTTPException(status_code=500, detail=str(e))



@router.get("/api/notifications/connections")
async def get_active_connections():
    """Get the number of active WebSocket connections"""
    return {
        "active_connections": len(manager.active_connections),
        "status": "active"
    } 