from fastapi import APIRouter, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from typing import Optional
import json
import os
from services.prompt_config.prompt_config import prompt_config

router = APIRouter(
    prefix="/forms",
    tags=["forms"]
)

# Initialize templates
templates = Jinja2Templates(directory="templates")

@router.get("/", response_class=HTMLResponse)
async def show_form(request: Request, active_tab: str = "default"):
    """Display the load check-in form with specified active tab"""
    # Map URL parameters to actual tab names
    tab_mapping = {
        "default": "Default Form",
        "at-pickup": "At Pickup",
        "pickup-complete": "Pickup Complete",
        "in-transit": "In Transit",
        "at-drop": "At Drop",
        "delivered": "Delivered",
        "request-pod": "Request POD"
    }
    
    # Validate and get the correct tab name, default to "default" if invalid
    active_tab = active_tab.lower()
    if active_tab not in tab_mapping:
        active_tab = "default"
    
    return templates.TemplateResponse(
        "form.html",
        {
            "request": request,
            "active_tab": active_tab,
            "tab_name": tab_mapping[active_tab]
        }
    )

@router.post("/submit-load")
async def submit_load(request: Request):
    """Handle default form submission"""
    try:
        form_data = await request.form()
        data = dict(form_data)
        
        # Prepare metadata for Retell call
        metadata = {
            "form_type": "default",
            "form_data": data
        }
        
        # Return success response with call initiation details
        return templates.TemplateResponse(
            "form.html",
            {
                "request": request,
                "active_tab": "default",
                "success": True,
                "message": "Call initiated successfully",
                "form_data": data
            }
        )
    except Exception as e:
        return templates.TemplateResponse(
            "form.html",
            {
                "request": request,
                "active_tab": "default",
                "error": f"Failed to process form: {str(e)}"
            }
        )

@router.post("/submit-at-pickup")
async def submit_at_pickup(request: Request):
    """Handle at-pickup form submission"""
    try:
        form_data = await request.form()
        data = dict(form_data)
        
        metadata = {
            "form_type": "at-pickup",
            "form_data": data
        }
        
        return templates.TemplateResponse(
            "form.html",
            {
                "request": request,
                "active_tab": "at-pickup",
                "success": True,
                "message": "Call initiated successfully",
                "form_data": data
            }
        )
    except Exception as e:
        return templates.TemplateResponse(
            "form.html",
            {
                "request": request,
                "active_tab": "at-pickup",
                "error": f"Failed to process form: {str(e)}"
            }
        )

@router.post("/submit-pickup-complete")
async def submit_pickup_complete(request: Request):
    """Handle pickup-complete form submission"""
    try:
        form_data = await request.form()
        data = dict(form_data)
        
        metadata = {
            "form_type": "pickup-complete",
            "form_data": data
        }
        
        return templates.TemplateResponse(
            "form.html",
            {
                "request": request,
                "active_tab": "pickup-complete",
                "success": True,
                "message": "Call initiated successfully",
                "form_data": data
            }
        )
    except Exception as e:
        return templates.TemplateResponse(
            "form.html",
            {
                "request": request,
                "active_tab": "pickup-complete",
                "error": f"Failed to process form: {str(e)}"
            }
        )

@router.post("/submit-in-transit")
async def submit_in_transit(request: Request):
    """Handle in-transit form submission"""
    try:
        form_data = await request.form()
        data = dict(form_data)
        
        metadata = {
            "form_type": "in-transit",
            "form_data": data
        }
        
        return templates.TemplateResponse(
            "form.html",
            {
                "request": request,
                "active_tab": "in-transit",
                "success": True,
                "message": "Call initiated successfully",
                "form_data": data
            }
        )
    except Exception as e:
        return templates.TemplateResponse(
            "form.html",
            {
                "request": request,
                "active_tab": "in-transit",
                "error": f"Failed to process form: {str(e)}"
            }
        )

@router.post("/submit-at-drop")
async def submit_at_drop(request: Request):
    """Handle at-drop form submission"""
    try:
        form_data = await request.form()
        data = dict(form_data)
        
        metadata = {
            "form_type": "at-drop",
            "form_data": data
        }
        
        return templates.TemplateResponse(
            "form.html",
            {
                "request": request,
                "active_tab": "at-drop",
                "success": True,
                "message": "Call initiated successfully",
                "form_data": data
            }
        )
    except Exception as e:
        return templates.TemplateResponse(
            "form.html",
            {
                "request": request,
                "active_tab": "at-drop",
                "error": f"Failed to process form: {str(e)}"
            }
        )

@router.post("/submit-delivered")
async def submit_delivered(request: Request):
    """Handle delivered form submission"""
    try:
        form_data = await request.form()
        data = dict(form_data)
        
        metadata = {
            "form_type": "delivered",
            "form_data": data
        }
        
        return templates.TemplateResponse(
            "form.html",
            {
                "request": request,
                "active_tab": "delivered",
                "success": True,
                "message": "Call initiated successfully",
                "form_data": data
            }
        )
    except Exception as e:
        return templates.TemplateResponse(
            "form.html",
            {
                "request": request,
                "active_tab": "delivered",
                "error": f"Failed to process form: {str(e)}"
            }
        )

@router.post("/submit-request-pod")
async def submit_request_pod(request: Request):
    """Handle request-pod form submission"""
    try:
        form_data = await request.form()
        data = dict(form_data)
        
        metadata = {
            "form_type": "request-pod",
            "form_data": data
        }
        
        return templates.TemplateResponse(
            "form.html",
            {
                "request": request,
                "active_tab": "request-pod",
                "success": True,
                "message": "Call initiated successfully",
                "form_data": data
            }
        )
    except Exception as e:
        return templates.TemplateResponse(
            "form.html",
            {
                "request": request,
                "active_tab": "request-pod",
                "error": f"Failed to process form: {str(e)}"
            }
        )
