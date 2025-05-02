from fastapi import APIRouter, HTTPException, Body
from typing import List, Dict
from pydantic import BaseModel
from loguru import logger
from services.transit_langrapgh_service import transit_langgraph_service
from typing import Optional
from langgraph.types import Command
import random
from services.whisper_service import whisper_service
from services.orpheus_service import orpheus_service

router = APIRouter(
    prefix="/conversation",
    tags=["conversation"],
    responses={404: {"description": "Not found"}},
)

class ChatRequest(BaseModel):
    message: str = None
    audio_file: str = None
    thread_id: str

@router.get("/initialize")
async def initialize_transit_chat(stop_id: Optional[int] = None, is_audio: Optional[bool] = False):
    try:
        thread_id = random.randint(1, 1000000)
        if is_audio:
            query = transit_langgraph_service.run({"messages":[],'running': True, 'stop_id': stop_id}, thread_id)
            response = orpheus_service.stream_audio_response(query)
            return {'response': response, 'thread_id': thread_id, 'user': None, 'AI': query}
        else:
            return {'response': transit_langgraph_service.run({"messages":[],'running': True, 'stop_id': stop_id}, thread_id), 'thread_id': thread_id}
    except Exception as e:
        logger.error(f"Error in initialize_transit_chat: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    

@router.post("/chat")
async def chat(request: ChatRequest = Body(...)):
    try:
        logger.debug(f"Received chat request: {request}")
        logger.debug(f"Message: {request.message}, Thread ID: {request.thread_id}")
        if request.audio_file:
            text = whisper_service.transcribe_audio(request.audio_file)
            request.message = text
            query = transit_langgraph_service.run(Command(resume={'data': request.message}), request.thread_id)
            response = orpheus_service.stream_audio_response(query)
            return {'response': response, 'thread_id': request.thread_id,'user': text, 'AI': query}
        else:
            response = transit_langgraph_service.run(Command(resume={'data': request.message}), request.thread_id)
            return {'response': response, 'thread_id': request.thread_id}
    except Exception as e:
        logger.error(f"Error in chat: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
