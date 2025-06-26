from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
import json
import os
from typing import Dict, Any, List
from services.prompt_config.prompt_config import prompt_config

router = APIRouter(
    prefix="/prompt-config",
    tags=["prompt-config"]
)

# Initialize templates
templates = Jinja2Templates(directory="templates")

@router.get("/", response_class=HTMLResponse)
async def get_prompt_config(request: Request):
    """Display the prompt configuration page"""
    # Load current configuration from file
    config_data = prompt_config.load_config()
    
    return templates.TemplateResponse(
        "prompt-config.html",
        {
            "request": request,
            "config_data": json.dumps(config_data, indent=2),
            "form_types": list(config_data["FORM_CONFIG"].keys()),
            "form_config": config_data["FORM_CONFIG"]
        }
    )

@router.post("/save", response_class=JSONResponse)
async def save_config(request: Request):
    """Save the updated configuration to the JSON file"""
    try:
        # Get the JSON data from the request
        data = await request.json()
        
        # Validate the structure
        if "FORM_CONFIG" not in data or "FORM_TYPE_MAPPING" not in data:
            return JSONResponse(
                status_code=400,
                content={"error": "Invalid configuration structure"}
            )
        
        # Save to file
        config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'services', 'prompt_config', 'prompt_config.json')
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        # Update the prompt_config instance
        prompt_config.config_data = data
        prompt_config.FORM_CONFIG = data["FORM_CONFIG"]
        prompt_config.FORM_TYPE_MAPPING = data["FORM_TYPE_MAPPING"]
        
        return JSONResponse(
            status_code=200,
            content={"message": "Configuration saved successfully"}
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": f"Failed to save configuration: {str(e)}"}
        )

@router.post("/update-questions/{form_type}", response_class=JSONResponse)
async def update_questions(form_type: str, request: Request):
    """Update voice questions for a specific form type"""
    try:
        data = await request.json()
        questions = data.get("questions", [])
        
        # Load current config
        config_data = prompt_config.load_config()
        
        # Update questions
        if form_type in config_data["FORM_CONFIG"]:
            config_data["FORM_CONFIG"][form_type]["voice_questions"] = questions
            
            # Save back to file
            config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'services', 'prompt_config', 'prompt_config.json')
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=2, ensure_ascii=False)
            
            # Update the prompt_config instance
            prompt_config.config_data = config_data
            prompt_config.FORM_CONFIG = config_data["FORM_CONFIG"]
            prompt_config.FORM_TYPE_MAPPING = config_data["FORM_TYPE_MAPPING"]
            
            return JSONResponse(
                status_code=200,
                content={"message": "Questions updated successfully"}
            )
        else:
            return JSONResponse(
                status_code=404,
                content={"error": f"Form type '{form_type}' not found"}
            )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": f"Failed to update questions: {str(e)}"}
        )

@router.post("/update-output-schema/{form_type}", response_class=JSONResponse)
async def update_output_schema(form_type: str, request: Request):
    """Update output schema for a specific form type"""
    try:
        data = await request.json()
        output_schema = data.get("output_schema", {})
        
        # Load current config
        config_data = prompt_config.load_config()
        
        # Update output schema
        if form_type in config_data["FORM_CONFIG"]:
            config_data["FORM_CONFIG"][form_type]["output_schema"] = output_schema
            
            # Save back to file
            config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'services', 'prompt_config', 'prompt_config.json')
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=2, ensure_ascii=False)
            
            # Update the prompt_config instance
            prompt_config.config_data = config_data
            prompt_config.FORM_CONFIG = config_data["FORM_CONFIG"]
            prompt_config.FORM_TYPE_MAPPING = config_data["FORM_TYPE_MAPPING"]
            
            return JSONResponse(
                status_code=200,
                content={"message": "Output schema updated successfully"}
            )
        else:
            return JSONResponse(
                status_code=404,
                content={"error": f"Form type '{form_type}' not found"}
            )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": f"Failed to update output schema: {str(e)}"}
        )

@router.get("/form-config/{form_type}", response_class=JSONResponse)
async def get_form_config(form_type: str):
    """Get configuration for a specific form type"""
    # Get form configuration using prompt_config
    form_config = prompt_config.get_form_config(form_type)
    
    if form_config:
        return JSONResponse(
            status_code=200,
            content=form_config
        )
    else:
        return JSONResponse(
            status_code=404,
            content={"error": f"Form type '{form_type}' not found"}
        )
