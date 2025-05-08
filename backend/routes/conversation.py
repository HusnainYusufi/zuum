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

router = APIRouter(
    prefix="/conversation",
    tags=["conversation"],
    responses={404: {"description": "Not found"}},
)

db = next(get_db())

class ChatRequest(BaseModel):
    message: str = None
    audio_file: str = None
    thread_id: str

@router.get("/initialize")
async def initialize_chat(stop_id: Optional[int] = None, is_audio: Optional[bool] = False):
    try:
        thread_id = random.randint(1, 1000000)
        
        langraph_service = check_langraph_service(stop_id)
        
        # Initialize state with required parameters
        state = {"messages": [], 'running': True}
        if stop_id is not None:
            state['stop_id'] = stop_id
            
        query = langraph_service.run(state, str(thread_id))
        if is_audio:
            # Store the query for later audio streaming
            # We'll return just the text response and client can request audio separately
            return {'response': query, 'thread_id': thread_id, 'user': None, 'AI': query}
        else:
            return {'response': query, 'thread_id': thread_id}
    except Exception as e:
        logger.error(f"Error in initialize_chat: {str(e)}")
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
    try:
        # Log received parameters
        logger.debug(f"Received chat request - File: {audio is not None}, Query params: thread_id={thread_id}, message={message}, stop_id={stop_id}")
        
        # If we have a JSON request body
        if request:
            logger.debug(f"JSON body: {request}")
            thread_id = request.thread_id
            message = request.message
            audio_data = request.audio_file
        
        # If we're missing thread_id, that's an error
        if not thread_id:
            raise HTTPException(status_code=400, detail="Missing thread_id parameter")
        
        langraph_service = check_langraph_service(stop_id)
        
        # Handle audio file upload
        if audio and audio.filename:
            # Read the audio file content
            audio_content = await audio.read()
            
            # Convert to base64 for internal processing if needed
            audio_b64 = base64.b64encode(audio_content).decode('utf-8')
            
            # Get transcribed text from the whisper service
            text = whisper_service.transcribe_audio(audio_b64)
            
            # Check for None or empty text
            if not text:
                logger.warning("Received empty transcription from whisper service")
                text = "I couldn't understand the audio clearly."
            
            logger.debug(f"Transcribed text: {text}")
            query = langraph_service.run(Command(resume={'data': text}), str(thread_id))
            return {'response': query, 'thread_id': thread_id, 'user': text, 'AI': query}
            
        # Handle base64 encoded audio from JSON request
        elif request and request.audio_file:
            # Get transcribed text from the whisper service
            text = whisper_service.transcribe_audio(request.audio_file)
            
            # Check for None or empty text
            if not text:
                logger.warning("Received empty transcription from whisper service")
                text = "I couldn't understand the audio clearly."
            
            logger.debug(f"Transcribed text: {text}")
            query = langraph_service.run(Command(resume={'data': text}), str(thread_id))
            return {'response': query, 'thread_id': thread_id, 'user': text, 'AI': query}
            
        # Handle text message
        elif message:
            logger.debug(f"Processing text message: {message}")
            # Run the message directly through langgraph
            query = langraph_service.run(Command(resume={'data': message}), str(thread_id))
            logger.debug(f"Langgraph response: {query}")
            # Return a consistent response format
            return {'response': query, 'thread_id': thread_id, 'user': message, 'AI': query}
            
        else:
            raise HTTPException(status_code=400, detail="No audio or message provided")
            
    except Exception as e:
        logger.error(f"Error in chat: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


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
