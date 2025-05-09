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
from db_models import Journey

router = APIRouter(
    prefix="/ui",
    tags=["ui"],
    responses={404: {"description": "Not found"}},
)

db = next(get_db())

@router.get("/journey_state")
async def get_journey_state():
    journey = db.query(Journey).filter(Journey.id == 1).first()
    return journey.current_state



