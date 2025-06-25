import os
import httpx
import time
import json
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from dotenv import load_dotenv
from services.prompt_config.prompt_config import prompt_config

# Load environment variables
load_dotenv()

# Create router
router = APIRouter(prefix="/API/retell", tags=["retell_webcall"])

# Templates
templates = Jinja2Templates(directory="templates")

# Get environment variables
RETELL_API_KEY = os.getenv("RETELL_API_KEY")
AGENT_ID = os.getenv("AGENT_ID")

# Retell API endpoints
RETELL_API_BASE = "https://api.retellai.com/v2"


@router.get("/webcall", response_class=HTMLResponse)
async def show_webcall_page(request: Request):
    """Display the Retell webcall page"""
    return templates.TemplateResponse(
        "retell-webcall.html",
        {"request": request}
    )


@router.post("/get-access-token")
async def get_access_token(request: Request):
    """Get access token for Retell Web SDK"""
    
    if not RETELL_API_KEY or not AGENT_ID:
        raise HTTPException(
            status_code=500,
            detail="Retell API key or Agent ID not configured"
        )
    
    try:
        # Get request body
        body = await request.json()
        metadata = body.get("metadata", {})
        
        # Extract form data and type
        form_data = metadata.get("form_data", {})
        form_type = metadata.get("form_type", "default")
        
        # Get form configuration and voice questions from form_config.json
        form_config = prompt_config.get_form_config(form_type)
        voice_questions = prompt_config.get_voice_questions(form_type)
        form_number = prompt_config.FORM_TYPE_MAPPING.get(form_type, 0)
        
        # Get output schema from form configuration
        output_schema = form_config.get("output_schema", {})
        
        # Convert data to JSON strings for dynamic variables
        form_data_json = json.dumps(form_data)
        voice_questions_json = json.dumps(voice_questions)
        form_number_json = json.dumps(form_number)
        output_schema_json = json.dumps(output_schema)
        
        # Prepare dynamic variables for the agent (same as retell_check_in.py)
        dynamic_variables = {
            "form_number": form_number_json,
            "form_title": form_config.get("title", ""),
            "purpose": voice_questions_json,
            "form": form_data_json,
            "output_schema": output_schema_json
        }
        
        # Add transfer call if present in form data
        transfer_call = None
        for field_name in ["transfer_call_to"]:
            if field_name in form_data and form_data[field_name]:
                transfer_call = form_data[field_name]
                break
        
        if transfer_call:
            dynamic_variables["transfer_call_to"] = json.dumps(transfer_call)
        
        # Update metadata with form information
        metadata.update({
            "form_number": form_number_json,
            "form_title": form_config.get("title", ""),
            "purpose": voice_questions_json,
            "form": form_data_json,
            "output_schema": output_schema_json
        })
        
        # Prepare the API request
        api_request = {
            "agent_id": AGENT_ID,
            "metadata": metadata,
            "retell_llm_dynamic_variables": dynamic_variables
        }
        
        async with httpx.AsyncClient() as client:
            # Create a web call to get access token
            response = await client.post(
                f"{RETELL_API_BASE}/create-web-call",
                headers={
                    "Authorization": f"Bearer {RETELL_API_KEY}",
                    "Content-Type": "application/json"
                },
                json=api_request
            )
            
            if response.status_code != 201:
                error_detail = response.json() if response.content else "Unknown error"
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Failed to create web call: {error_detail}"
                )
            
            data = response.json()
            
            # Return the access token
            return JSONResponse({
                "access_token": data.get("access_token"),
                "call_id": data.get("call_id")
            })
            
    except httpx.RequestError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to connect to Retell API: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred: {str(e)}"
        )


@router.post("/end-call/{call_id}")
async def end_call(call_id: str):
    """End an active Retell call"""
    
    if not RETELL_API_KEY:
        raise HTTPException(
            status_code=500,
            detail="Retell API key not configured"
        )
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{RETELL_API_BASE}/end-call/{call_id}",
                headers={
                    "Authorization": f"Bearer {RETELL_API_KEY}"
                }
            )
            
            if response.status_code != 200:
                error_detail = response.json() if response.content else "Unknown error"
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Failed to end call: {error_detail}"
                )
            
            return JSONResponse({"status": "success", "message": "Call ended"})
            
    except httpx.RequestError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to connect to Retell API: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred: {str(e)}"
        )


@router.get("/call-details/{call_id}")
async def get_call_details(call_id: str):
    """Get details of a specific call"""
    
    if not RETELL_API_KEY:
        raise HTTPException(
            status_code=500,
            detail="Retell API key not configured"
        )
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{RETELL_API_BASE}/get-call/{call_id}",
                headers={
                    "Authorization": f"Bearer {RETELL_API_KEY}"
                }
            )
            
            if response.status_code != 200:
                error_detail = response.json() if response.content else "Unknown error"
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Failed to get call details: {error_detail}"
                )
            
            return JSONResponse(response.json())
            
    except httpx.RequestError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to connect to Retell API: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred: {str(e)}"
        )
