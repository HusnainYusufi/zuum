from fastapi import APIRouter, HTTPException, Body, File, UploadFile, Form, Query
from typing import List, Dict, Optional
from pydantic import BaseModel
from loguru import logger
from services.langrapghs.transit_langrapgh_service import transit_langgraph_service
from langgraph.types import Command
import random
from services.whisper_service import whisper_service
from services.orpheus_service import orpheus_service
import base64
from io import BytesIO
from db_models import get_db
from db_models import Stop
from services.langrapghs.origin_langraph import origin_langgraph_service
from services.langrapghs.destination_langrapgh_service import destination_langgraph_service
import time
import asyncio
from datetime import datetime, timedelta

router = APIRouter(
    prefix="/conversation",
    tags=["conversation"],
    responses={404: {"description": "Not found"}},
)

db = next(get_db())


RESPONSE_TIMEOUT = timedelta(seconds=4)
MAX_INIT_ATTEMPTS = 3

# Track chat initialization attempts for each driver/stop
chat_init_tracking = {}

# Store active notifications that should be shown in the dashboard
active_notifications = []

class ChatRequest(BaseModel):
    message: str = None
    audio_file: str = None

class NotificationRequest(BaseModel):
    message: str
    stop_id: Optional[int] = None
    severity: str = "info"  # info, warning, error

# Internal function for sending notifications programmatically
async def send_notification_internal(message: str, stop_id: Optional[int] = None, severity: str = "info"):
    """
    Internal function to send a notification to the stakeholder dashboard.
    This function is used when notifications are triggered programmatically.
    """
    try:
        # Log the notification
        logger.info(f"New notification: {message} (severity: {severity}, stop_id: {stop_id})")
        
        # In a production environment, this would:
        # 1. Save the notification to a database
        # 2. Broadcast it via WebSockets or Server-Sent Events to the frontend

        # Add this notification to our active notifications list so the dashboard can fetch it
        notification = {
            "id": int(time.time() * 1000),  # Use timestamp as ID
            "message": message,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "stop_id": stop_id,
            "severity": severity
        }
        
        # Add to active notifications
        active_notifications.append(notification)
        
        # Limit to most recent 50 notifications
        if len(active_notifications) > 50:
            active_notifications.pop(0)
        
        # Just return success for now
        return {"status": "success", "message": "Notification sent", "notification": notification}
    except Exception as e:
        logger.error(f"Error sending notification internally: {str(e)}")
        return {"status": "error", "message": str(e)}

@router.get("/initialize")
async def initialize_chat(stop_id: Optional[int] = None, is_audio: Optional[bool] = False, thread_id: Optional[str] = None):
    global chat_init_tracking
    try:
        if not thread_id:
            thread_id = random.randint(1, 1000000)
        
        # Skip inactivity tracking for audio chats
        if not is_audio and stop_id is not None:
            current_time = datetime.now()
            
            # Initialize tracking for this stop if it doesn't exist
            if stop_id not in chat_init_tracking and not is_audio:
                chat_init_tracking[stop_id] = {
                    "attempts": 1,
                    "last_init": current_time,

                }
            else:
                # Check if last initialization was more than 5 minutes ago
                last_init = chat_init_tracking[stop_id]["last_init"]
                if current_time - last_init > RESPONSE_TIMEOUT:
                    # Increment attempts counter
                    chat_init_tracking[stop_id]["attempts"] += 1
                    chat_init_tracking[stop_id]["last_init"] = current_time
                    
                    # If this is the 4th attempt (3 timeouts), send notification
                    if chat_init_tracking[stop_id]["attempts"] >= MAX_INIT_ATTEMPTS:
                        # Get the stop name for better notification
                        stop = db.query(Stop).filter(Stop.id == stop_id).first()
                        stop_name = stop.name if stop else f"Stop #{stop_id}"
                        
                        # Send notification about driver unresponsiveness
                        notification_result = await send_notification_internal(
                            message=f"Driver at {stop_name} is not responding to text chat after multiple attempts",
                            stop_id=stop_id,
                            severity="warning"
                        )
                        
                        # Save the stop_id to remove it from tracking
                        stop_id_to_remove = stop_id
                        
                        # Reset tracking for this stop
                        if stop_id_to_remove in chat_init_tracking:
                            del chat_init_tracking[stop_id_to_remove]
                            
                        return {
                            'response': 'Respond to me when you are free.', 
                            'thread_id': thread_id, 
                            'repeat': False,
                            'notification': notification_result.get('notification')
                        }
                    else:
                        return {'response': 'Hello, you there?', 'thread_id': thread_id, 'repeat': True}
        
        langraph_service = check_langraph_service(stop_id)
        
        # Initialize state with required parameters
        state = {"messages": [], 'running': True}
        if stop_id is not None:
            state['stop_id'] = stop_id
            
        query = langraph_service.run(state, str(thread_id))
        if is_audio:
            # Store the query for later audio streaming
            # We'll return just the text response and client can request audio separately
            return {'response': query, 'thread_id': thread_id, 'user': None, 'AI': query, 'repeat': False}
        else:
            return {'response': query, 'thread_id': thread_id, 'repeat': True}
    except Exception as e:
        logger.error(f"Error in initialize_chat: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/active_notifications")
async def get_active_notifications():
    """Return all active notifications that should be displayed in the dashboard"""
    try:
        return {"notifications": active_notifications}
    except Exception as e:
        logger.error(f"Error retrieving notifications: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/check_driver_activity")
async def check_driver_activity():
    """Check for inactive drivers and return information about them"""
    try:
        inactive_drivers = []
        
        # Look for drivers who have had inactivity notifications
        for notification in active_notifications:
            if "not responding" in notification["message"] and notification["stop_id"] is not None:
                # Get stop information
                stop = db.query(Stop).filter(Stop.id == notification["stop_id"]).first()
                if stop:
                    inactive_drivers.append({
                        "stop_id": notification["stop_id"],
                        "stop_name": stop.name,
                        "notification_id": notification["id"],
                        "timestamp": notification["timestamp"]
                    })
        
        return {"inactive_drivers": inactive_drivers}
    except Exception as e:
        logger.error(f"Error checking driver activity: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/audio")
async def get_audio(text: str = Query(...)):
    """Stream audio for the provided text"""
    try:
        return orpheus_service.stream_audio_response(text)
    except Exception as e:
        logger.error(f"Error in audio streaming: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    
# Support both JSON and form uploads
@router.post("/chat")
async def chat(
    audio: UploadFile = File(None),
    thread_id: str = Query(None),
    message: str = Query(None),
    request: ChatRequest = Body(None),
    stop_id: Optional[int] = Query(None)
):
    global chat_init_tracking
    try:
        # Log received parameters
        logger.debug(f"Received chat request - File: {audio is not None}, Query params: thread_id={thread_id}, message={message}, stop_id={stop_id}")
        
        # If we have a JSON request body
        if request:
            logger.debug(f"JSON body: {request}")
            thread_id = thread_id or request.thread_id
            message = message or request.message
        
        # If we're missing thread_id, that's an error
        if not thread_id:
            raise HTTPException(status_code=400, detail="Missing thread_id parameter")
        
        langraph_service = check_langraph_service(stop_id)
        
        # Reset initialization counter if the driver responds to text chat
        if stop_id is not None and message and stop_id in chat_init_tracking:
            chat_init_tracking[stop_id] = {
                "attempts": 0,
                "last_init": datetime.now(),
                "thread_id": thread_id
            }
        
        # Handle base64 encoded audio from JSON request
        logger.debug(f"Request: {request}")
        if request and request.audio_file:
            logger.debug("Processing base64 audio from JSON request")
            # Pass the base64 string directly to whisper service
            text = whisper_service.transcribe_audio(request.audio_file)
            
            # Check for None or empty text
            if not text:
                logger.warning("Received empty transcription from whisper service")
                text = "I couldn't understand the audio clearly."
            
            logger.debug(f"Transcribed text: {text}")
            query = langraph_service.run(Command(resume={'data': text}), str(thread_id))
            return {'response': query, 'thread_id': thread_id, 'user': text, 'AI': query, 'repeat': False}
        
        # Handle file upload audio (multipart/form-data)
        elif audio:
            logger.debug("Processing audio file from form upload")
            # Read the audio file content
            audio_content = await audio.read()
            
            # Send the binary data directly to whisper service
            text = whisper_service.transcribe_audio(audio_content)
            
            # Check for None or empty text
            if not text:
                logger.warning("Received empty transcription from whisper service")
                text = "I couldn't understand the audio clearly."
                
            logger.debug(f"Transcribed text from uploaded file: {text}")
            query = langraph_service.run(Command(resume={'data': text}), str(thread_id))
            return {'response': query, 'thread_id': thread_id, 'user': text, 'AI': query, 'repeat': False}
            
        # Handle text message
        elif message:
            logger.debug(f"Processing text message: {message}")
            # Run the message directly through langgraph
            query = langraph_service.run(Command(resume={'data': message}), str(thread_id))
            logger.debug(f"Langgraph response: {query}")
            # Return a consistent response format
            return {'response': query, 'thread_id': thread_id, 'user': message, 'AI': query, 'repeat': False}
            
        else:
            raise HTTPException(status_code=400, detail="No audio or message provided")
            
    except Exception as e:
        logger.error(f"Error in chat: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/notification")
async def send_notification(
    request: NotificationRequest = Body(...)
):
    """
    Send a notification to the stakeholder dashboard via API.
    This endpoint is for external services to send notifications.
    """
    try:
        message = request.message
        stop_id = request.stop_id
        severity = request.severity
            
        # Use the internal notification function
        result = await send_notification_internal(message, stop_id, severity)
        return result
    except Exception as e:
        logger.error(f"Error sending notification via API: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/retell-token")
async def get_retell_token():
    """
    Generate an access token for Retell API by creating a web call.
    
    This endpoint calls Retell's create-web-call API to start a new call session
    and returns the access token to the frontend.
    """
    logger.info("Received request for Retell token")
    
    try:
        import os
        import requests
        from dotenv import load_dotenv
        
        # Load environment variables from .env file
        load_dotenv()
        
        # Get your Retell API key from environment variables
        RETELL_API_KEY = os.getenv("RETELL_API_KEY")
        RETELL_AGENT_ID = os.getenv("RETELL_AGENT_ID")
        
        logger.debug(f"RETELL_API_KEY available: {RETELL_API_KEY is not None}")
        logger.debug(f"RETELL_AGENT_ID available: {RETELL_AGENT_ID is not None}")
        
        if not RETELL_API_KEY:
            logger.warning("RETELL_API_KEY not found in environment variables")
            # Fall back to a testing/demo response for development
            return {
                "access_token": "mock_access_token",
                "message": "Using mock token. Set RETELL_API_KEY in .env file for production."
            }
            
        if not RETELL_AGENT_ID:
            logger.warning("RETELL_AGENT_ID not found in environment variables")
            # Fall back to a testing/demo response for development
            return {
                "access_token": "mock_access_token",
                "message": "Using mock token. Set RETELL_AGENT_ID in .env file for production."
            }
        
        # Make the API call to Retell to create a web call
        logger.info(f"Calling Retell API to create web call with agent ID: {RETELL_AGENT_ID}")
        response = requests.post(
            "https://api.retellai.com/v2/create-web-call",
            headers={"Authorization": f"Bearer {RETELL_API_KEY}"},
            json={
                "agent_id": RETELL_AGENT_ID,
                "metadata": {
                    "user_id": "freight_broker_user",
                    "app": "voice_freight_broker"
                }
            }
        )
        
        # Check if the request was successful
        if response.status_code != 201:
            error_msg = f"Retell API returned non-success status code: {response.status_code}"
            logger.error(error_msg)
            logger.error(f"Response content: {response.text}")
            return {
                "access_token": "mock_access_token",
                "message": f"Error from Retell API: {response.status_code} - Using mock token instead",
                "error": response.text
            }
        
        # Parse the response
        data = response.json()
        logger.info(f"Successfully created Retell web call with ID: {data.get('call_id')}")
        
        # Return the access token to the frontend
        return {
            "access_token": data.get("access_token"),
            "call_id": data.get("call_id"),
            "call_status": data.get("call_status")
        }
    except requests.RequestException as e:
        logger.error(f"Error calling Retell API: {str(e)}")
        if hasattr(e, 'response') and e.response is not None:
            logger.error(f"Response status: {e.response.status_code}")
            logger.error(f"Response body: {e.response.text}")
        # Return a mock token with error information for development
        return {
            "access_token": "mock_access_token",
            "message": f"Error from Retell API: {str(e)} - Using mock token instead",
            "error": str(e)
        }
    except Exception as e:
        logger.error(f"Error generating Retell token: {str(e)}")
        # Return a mock token with error information for development
        return {
            "access_token": "mock_access_token",
            "message": f"Error generating token: {str(e)} - Using mock token instead",
            "error": str(e)
        }

@router.get("/retell-token-test")
async def test_retell_token():
    """
    Test endpoint for Retell token (GET method).
    This makes it easier to debug in a browser.
    """
    logger.info("Received GET request for testing Retell token")
    
    # Just call the same function as the POST endpoint
    return await get_retell_token()

def check_langraph_service(stop_id: Optional[int] = None):
    if stop_id is None:
        # If no stop_id is provided, default to transit service
        return transit_langgraph_service
        
    try:
        stop = db.query(Stop).filter(Stop.id == stop_id).first()
        if stop is None:
            # If stop doesn't exist, default to transit service
            return transit_langgraph_service
            
        if stop.is_origin:
            return origin_langgraph_service
        elif stop.is_destination:
            return destination_langgraph_service
        else:
            return transit_langgraph_service
    except Exception as e:
        logger.error(f"Error in check_langraph_service: {str(e)}")
        return transit_langgraph_service
