from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
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
    # Load configurations for all form types
    form_types = prompt_config.get_all_form_types()
    form_config = {}

    for form_type in form_types:
        try:
            form_config[form_type] = prompt_config.get_form_config(form_type)
        except FileNotFoundError:
            # Skip missing scenario files
            continue

    # Reconstruct the format expected by the template
    config_data = {
        "FORM_CONFIG": form_config,
        "FORM_TYPE_MAPPING": prompt_config.FORM_TYPE_MAPPING
    }

    return templates.TemplateResponse(
        "prompt-config.html",
        {
            "request": request,
            "config_data": config_data,
            "form_types": list(form_config.keys()),
            "form_config": form_config
        }
    )


@router.post("/save", response_class=JSONResponse)
async def save_config(request: Request):
    """Save the updated configuration to individual scenario files"""
    try:
        # Get the JSON data from the request
        data = await request.json()

        # Validate the structure
        if "FORM_CONFIG" not in data:
            return JSONResponse(
                status_code=400,
                content={"error": "Invalid configuration structure"}
            )

        # Save each form configuration to its individual file
        for form_type, config in data["FORM_CONFIG"].items():
            prompt_config.update_form_config(form_type, config)

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

        # Update questions for the specific form type
        prompt_config.update_voice_questions(form_type, questions)

        return JSONResponse(
            status_code=200,
            content={"message": "Questions updated successfully"}
        )
    except FileNotFoundError:
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

        # Update output schema for the specific form type
        prompt_config.update_output_schema(form_type, output_schema)

        return JSONResponse(
            status_code=200,
            content={"message": "Output schema updated successfully"}
        )
    except FileNotFoundError:
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
    try:
        form_config = prompt_config.get_form_config(form_type)
        return JSONResponse(
            status_code=200,
            content=form_config
        )
    except FileNotFoundError:
        return JSONResponse(
            status_code=404,
            content={"error": f"Form type '{form_type}' not found"}
        )


@router.post("/form-config/{form_type}", response_class=JSONResponse)
async def update_form_config(form_type: str, request: Request):
    """Update configuration for a specific form type"""
    try:
        # Get the JSON data from the request
        config = await request.json()

        # Update the specific form configuration
        prompt_config.update_form_config(form_type, config)

        return JSONResponse(
            status_code=200,
            content={"message": "Form configuration updated successfully"}
        )
    except FileNotFoundError:
        return JSONResponse(
            status_code=404,
            content={"error": f"Form type '{form_type}' not found"}
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": f"Failed to update form configuration: {str(e)}"}
        )
