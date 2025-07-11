from fastapi import APIRouter, HTTPException, Body, File, UploadFile, Form, Query, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from .auth import get_current_user
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
    prefix="",  # Empty prefix
    tags=["ui"],
    responses={404: {"description": "Not found"}},
)

# Set up Jinja2 templates
templates = Jinja2Templates(directory="templates")

db = next(get_db())

@router.get("/journey_state")
async def get_journey_state(current_user: dict = Depends(get_current_user)):
    if not current_user:
        return RedirectResponse(url="/auth/login", status_code=302)
    journey = db.query(Journey).filter(Journey.id == 1).first()
    if not journey:
        return {"current_state": None}
    return {"current_state": journey.current_state}

@router.get("/transit-dashboard", response_class=HTMLResponse)
async def dashboard_page(request: Request, current_user: dict = Depends(get_current_user)):
    """Serve the stakeholder dashboard page"""
    if not current_user:
        return RedirectResponse(url="/auth/login", status_code=302)
    return templates.TemplateResponse("transit-dashboard.html", {"request": request})

@router.get("/checkin/{check_in_id}", response_class=HTMLResponse)
async def checkin_page(request: Request, check_in_id: int, current_user: dict = Depends(get_current_user)):
    """Serve the check-in page for a specific check-in"""
    if not current_user:
        return RedirectResponse(url="/auth/login", status_code=302)
    return templates.TemplateResponse("checkin.html", {"request": request})

@router.get("/test-forms-chat", response_class=HTMLResponse)
async def test_forms_chat_page(request: Request, current_user: dict = Depends(get_current_user)):
    """Serve the test forms chat interface page"""
    if not current_user:
        return RedirectResponse(url="/auth/login", status_code=302)
    return templates.TemplateResponse("test_forms_chat.html", {"request": request})

@router.get("/dashboard", response_class=HTMLResponse)
async def checkin_dashboard_page(request: Request, current_user: dict = Depends(get_current_user)):
    """Serve the checkin dashboard page"""
    if not current_user:
        return RedirectResponse(url="/auth/login", status_code=302)
    return templates.TemplateResponse("checkin_dashboard.html", {"request": request})



