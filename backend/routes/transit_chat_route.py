from fastapi import APIRouter, HTTPException, Body
from typing import List, Dict
from pydantic import BaseModel
from loguru import logger
from services.transit_langrapgh_service import transit_langgraph_service
from typing import Optional
from langgraph.types import Command
import random

router = APIRouter(
    prefix="/transit-chat",
    tags=["transit-chat"],
    responses={404: {"description": "Not found"}},
)

class ChatRequest(BaseModel):
    message: str
    thread_id: str

@router.get("/initialize")
async def initialize_transit_chat(stop_id: Optional[int] = None):
    try:
        thread_id = random.randint(1, 1000000)
        return {'response': transit_langgraph_service.run({"messages":[],'running': True, 'stop_id': stop_id}, thread_id), 'thread_id': thread_id}
    except Exception as e:
        logger.error(f"Error in initialize_transit_chat: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    

@router.post("/chat")
async def chat(request: ChatRequest = Body(...)):
    try:
        logger.debug(f"Received chat request: {request}")
        logger.debug(f"Message: {request.message}, Thread ID: {request.thread_id}")
        
        response = transit_langgraph_service.run(Command(resume={'data': request.message}), request.thread_id)
        logger.debug(f"Response from service: {response}")
        
        return response
    except Exception as e:
        logger.error(f"Error in chat: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
