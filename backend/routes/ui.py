from fastapi import APIRouter, HTTPException, Body, File, UploadFile, Form, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
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

# Set up Jinja2 templates
templates = Jinja2Templates(directory="templates")

db = next(get_db())

@router.get("/journey_state")
async def get_journey_state():
    journey = db.query(Journey).filter(Journey.id == 1).first()
    return journey.current_state

@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(request: Request):
    """Serve the stakeholder dashboard page"""
    return templates.TemplateResponse("dashboard.html", {"request": request})

@router.get("/transcript/{check_in_id}", response_class=HTMLResponse)
async def transcript_page(request: Request, check_in_id: int):
    """Serve the transcript page for a specific check-in"""
    # For now, just redirect back to dashboard
    # In a full implementation, you would create a transcript.html template
    return templates.TemplateResponse("dashboard.html", {"request": request})



