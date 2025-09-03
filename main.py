import traceback
from typing import List, Optional
import os
from loguru import logger
from fastapi import FastAPI, HTTPException, Form, File, UploadFile, Request, Cookie
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
import re
from urllib.parse import urlparse, parse_qs
import json

from routes import (
    ui_router,
    retell_router,
    notifications_router,
    checkin_router,
    retell_check_in_router,
    forms_router,
    auth_router,
    prompt_config_router,
    webhook_router,
    shipments_router,
)

from dotenv import load_dotenv
from twilio.rest import Client
from datetime import datetime
from pathlib import Path
from services.github_service import github_service
from services.grafana_logger import grafana_logger, LogEntry, sanitize_json, sanitize_headers
import time
import asyncio
from starlette.middleware.base import BaseHTTPMiddleware

load_dotenv()

# Create feedback images directory if it doesn't exist
FEEDBACK_IMAGES_DIR = Path("static/feedback-images")
FEEDBACK_IMAGES_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI()

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Set up Jinja2 templates
templates = Jinja2Templates(directory="templates")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Include routers
app.include_router(auth_router)
app.include_router(ui_router)
app.include_router(retell_router)
app.include_router(notifications_router)
app.include_router(checkin_router)
app.include_router(retell_check_in_router)
app.include_router(forms_router)
app.include_router(prompt_config_router)
app.include_router(webhook_router)
app.include_router(shipments_router)

# Initialize Twilio client
twilio_client = Client(os.getenv("TWILIO_ACCOUNT_SID", ""), os.getenv("TWILIO_AUTH_TOKEN", ""))
TWILIO_FROM_NUMBER = os.getenv("TWILIO_FROM_NUMBER", "")

# Get recipient phone numbers from environment variable
FEEDBACK_RECIPIENT_PHONES = os.getenv("FEEDBACK_RECIPIENT_PHONES", "").split(",")


def normalize_body_to_json(body_bytes: bytes, content_type: str) -> str:
    """Convert different body formats to JSON for consistent logging"""
    if not body_bytes:
        return ""

    try:
        body_str = body_bytes.decode("utf-8")
    except UnicodeDecodeError:
        return "[BINARY_DATA]"

    # If it's already JSON, sanitize and return
    if "application/json" in content_type:
        return sanitize_json(body_str)

    # If it's form data, convert to JSON
    if "application/x-www-form-urlencoded" in content_type:
        try:
            # Parse form data into a dictionary
            parsed_data = parse_qs(body_str, keep_blank_values=True)

            # Convert lists with single values to just the value for cleaner JSON
            normalized_data = {}
            for key, values in parsed_data.items():
                if len(values) == 1:
                    normalized_data[key] = values[0]
                else:
                    normalized_data[key] = values

            # Convert to JSON and sanitize
            json_str = json.dumps(normalized_data, separators=(",", ":"))
            return sanitize_json(json_str)
        except Exception:
            # If parsing fails, sanitize as regular text
            return sanitize_json(f'{{"raw_body": "{body_str}"}}')

    # For other content types, wrap in JSON structure
    return sanitize_json(f'{{"raw_body": "{body_str}", "content_type": "{content_type}"}}')


class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()

        body_bytes = await request.body()

        async def receive():
            return {"type": "http.request", "body": body_bytes, "more_body": False}

        request = Request(request.scope, receive=receive)

        response = await call_next(request)
        processing_time = time.time() - start_time

        content_type = request.headers.get("content-type", "")
        sanitized_body_str = normalize_body_to_json(body_bytes, content_type)
        sanitized_headers = sanitize_headers(dict(request.headers))

        job_id = LogEntry.extract_job_id(request, sanitized_body_str)

        log_entry = LogEntry(
            timestamp=str(int(start_time * 1000)),
            method=request.method,
            path=request.url.path,
            headers=sanitized_headers,
            body=sanitized_body_str,
            status_code=response.status_code,
            processing_time=processing_time,
            client_ip=request.client.host,
            log_level=grafana_logger.get_log_level(response.status_code),
            environment=grafana_logger.environment,
            job_id=job_id,
        )

        asyncio.create_task(grafana_logger.add_log(log_entry))

        return response


app.add_middleware(LoggingMiddleware)


# Add this shutdown event to ensure all logs are sent before the app closes
@app.on_event("shutdown")
async def shutdown_event():
    await grafana_logger.close()


def _extract_checkin_id_from_referer(request: Request) -> Optional[int]:
    """
    Best-effort extraction of check-in ID from the Referer header URL
    (e.g., http://localhost:8000/checkin/127). Never raises; returns None on failure.
    """
    try:
        referer = request.headers.get("referer") or ""
        if not referer:
            return None
        path = urlparse(referer).path
        match = re.search(r"/checkin/(\d+)(?:/|$)", path)
        if not match:
            return None
        return int(match.group(1))
    except Exception as e:
        logger.warning(f"Failed to parse check-in ID from Referer: {e}")
        return None


@app.post("/send-feedback")
async def send_feedback(
    request: Request,
    feedbackType: str = Form(...),
    userName: str = Form(...),
    userEmail: str = Form(...),
    feedbackDescription: str = Form(...),
    feedbackImages: List[UploadFile] = File(None),
):
    """
    Handle user feedback submission with image uploads, SMS notifications, and GitHub issue creation
    """
    try:
        # Validate feedback description length
        if len(feedbackDescription) > 1400:
            raise HTTPException(
                status_code=400,
                detail="Feedback description cannot exceed 1400 characters",
            )

        # Derive check-in ID from Referer URL (non-fatal)
        checkin_id = _extract_checkin_id_from_referer(request)
        logger.info(f"Received feedback from {userName} ({userEmail}) - Type: {feedbackType}, Check-in ID: {checkin_id}")

        # Check required environment variables for Twilio
        required_env_vars = {
            "TWILIO_ACCOUNT_SID": os.getenv("TWILIO_ACCOUNT_SID"),
            "TWILIO_AUTH_TOKEN": os.getenv("TWILIO_AUTH_TOKEN"),
            "TWILIO_FROM_NUMBER": os.getenv("TWILIO_FROM_NUMBER"),
            "FEEDBACK_RECIPIENT_PHONES": os.getenv("FEEDBACK_RECIPIENT_PHONES"),
        }
        missing_vars = [var for var, val in required_env_vars.items() if not val]
        if missing_vars:
            error_msg = f"Missing required environment variables: {', '.join(missing_vars)}"
            logger.error(error_msg)
            raise HTTPException(status_code=500, detail=error_msg)

        logger.info("All required environment variables are present")

        # Prepare feedback data for Supabase
        supabase_feedback_data = {
            "feedback_type": feedbackType,
            "user_name": userName,
            "user_email": userEmail,
            "description": feedbackDescription,
        }

        # Prepare image files for Supabase upload
        supabase_image_files = []
        image_urls = []

        if feedbackImages:
            logger.info(f"Processing {len(feedbackImages)} image files for Supabase")
            for i, file in enumerate(feedbackImages):
                if file.filename:
                    logger.info(f"Processing image {i+1}: {file.filename}")
                    contents = await file.read()
                    logger.info(f"Read {len(contents)} bytes from {file.filename}")
                    supabase_image_files.append(
                        {
                            "filename": file.filename,
                            "content": contents,
                            "content_type": file.content_type or "image/jpeg",
                        }
                    )

        # Store in Supabase
        try:
            from services.supabase import supabase_service

            supabase_result = await supabase_service.create_feedback(supabase_feedback_data, supabase_image_files)

            if supabase_result["success"]:
                feedback_id = supabase_result["data"]["feedback"]["id"]
                logger.info(f"Successfully stored feedback in Supabase with ID: {feedback_id}")

                if supabase_result["data"].get("images"):
                    image_urls = [img["image_url"] for img in supabase_result["data"]["images"]]
                    logger.info(f"Uploaded {len(image_urls)} images to Supabase")
            else:
                logger.error(f"Failed to store feedback in Supabase: {supabase_result.get('error')}")
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to store feedback: {supabase_result.get('error')}",
                )

        except Exception as supabase_error:
            logger.error(f"Error storing feedback in Supabase: {supabase_error}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to store feedback: {str(supabase_error)}",
            )

        base_url = f"{request.url.scheme}://{request.url.netloc}"

        if feedbackType.lower() in ["suggestions", "comments"]:
            logger.info(f"Creating GitHub issue for {feedbackType} feedback")

            github_result = await github_service.create_feedback_issue(
                feedback_type=feedbackType,
                user_name=userName,
                user_email=userEmail,
                description=feedbackDescription,
                feedback_id=feedback_id,
                checkin_id=checkin_id,
                base_url=base_url,
                image_urls=image_urls,
            )

            if github_result["success"]:
                logger.info(f"Successfully created GitHub issue: {github_result['issue_url']}")
            else:
                logger.warning(f"Failed to create GitHub issue: {github_result.get('error')}")

        # Build SMS
        lines = [
            "[Freight Broker Project]",
            f"New Feedback from {userName}",
            f"Email: {userEmail}",
            f"Type: {feedbackType}",
        ]
        if checkin_id is not None:
            lines.append(f"Check-in ID: {checkin_id}")
        lines.extend(["", "Message:", f"{feedbackDescription}"])

        if github_result["success"]:
            lines.extend(["", f"GitHub Issue: {github_result['issue_url']}"])

        if image_urls:
            lines.append("\nImage/s:")
            lines.extend(image_urls)

        sms_body = "\n".join(lines)
        logger.info(f"SMS body length: {len(sms_body)} characters")

        # Send SMS
        recipient_phones = [phone.strip() for phone in FEEDBACK_RECIPIENT_PHONES if phone.strip()]
        if not recipient_phones:
            error_msg = "No recipient phone numbers configured in FEEDBACK_RECIPIENT_PHONES"
            logger.error(error_msg)
            raise HTTPException(status_code=500, detail=error_msg)

        logger.info(f"Sending SMS to {len(recipient_phones)} recipients")

        sms_errors = []
        for i, phone_number in enumerate(recipient_phones):
            try:
                logger.info(f"Sending SMS {i+1}/{len(recipient_phones)} to {phone_number}")
                clean_from_number = TWILIO_FROM_NUMBER.replace(" ", "").replace("(", "").replace(")", "").replace("-", "")
                clean_to_number = phone_number.strip().replace(" ", "").replace("(", "").replace(")", "").replace("-", "")
                message = twilio_client.messages.create(body=sms_body, from_=clean_from_number, to=clean_to_number)
                logger.info(f"SMS sent successfully to {phone_number}. Message SID: {message.sid}")
            except Exception as sms_error:
                err = f"Failed to send SMS to {phone_number}: {str(sms_error)}"
                logger.error(err)
                sms_errors.append(err)

        if sms_errors and len(sms_errors) == len(recipient_phones):
            raise HTTPException(
                status_code=500,
                detail=f"Failed to send SMS notifications: {'; '.join(sms_errors)}",
            )
        elif sms_errors:
            logger.warning(f"Some SMS notifications failed: {', '.join(sms_errors)}")

        return {
            "success": True,
            "message": "Feedback sent successfully",
            "feedback_id": feedback_id,
            "images_saved": len(image_urls),
            "checkin_id": checkin_id,  # may be None
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in send_feedback: {str(e)}")
        logger.error(f"Error type: {type(e).__name__}")
        logger.error(f"Error traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


state_dict = {}


# Root route redirects to dashboard if authenticated, login otherwise
@app.get("/")
async def root(request: Request, session_token: str = Cookie(None)):
    """Redirect root to dashboard if authenticated, login otherwise"""
    from routes.auth import verify_session_token

    # Check if user is authenticated
    if session_token and verify_session_token(session_token):
        return RedirectResponse(url="/dashboard")
    else:
        return RedirectResponse(url="/auth/login")


@app.get("/health-check")
async def health_check():
    """Health check endpoint to verify all services are working"""
    health_status = {"status": "healthy", "timestamp": datetime.now().isoformat(), "services": {}, "environment": {}}

    # Check environment variables
    env_vars_to_check = [
        "TWILIO_ACCOUNT_SID",
        "TWILIO_AUTH_TOKEN",
        "TWILIO_FROM_NUMBER",
        "FEEDBACK_RECIPIENT_PHONES",
    ]

    for var in env_vars_to_check:
        value = os.getenv(var)
        health_status["environment"][var] = {"configured": bool(value), "length": len(value) if value else 0}

    # Test Twilio connection
    try:
        # Simple test to verify Twilio client works
        twilio_client.api.accounts(os.getenv("TWILIO_ACCOUNT_SID")).fetch()
        health_status["services"]["twilio"] = {"status": "connected", "error": None}
    except Exception as e:
        health_status["services"]["twilio"] = {"status": "failed", "error": str(e)}
        health_status["status"] = "degraded"

    return health_status


if __name__ == "__main__":
    import uvicorn

    # Determine port
    port_env = os.getenv("PORT") or os.getenv("UVICORN_PORT")
    try:
        port = int(port_env) if port_env else 8000
    except ValueError:
        logger.warning(f"Invalid port '{port_env}', defaulting to 8000")
        port = 8000

    # Start FastAPI application - use 0.0.0.0 for Docker compatibility
    # Disable reload in production to prevent restart loops
    environment = os.getenv("ENVIRONMENT", "development")
    # Force disable reload if we're in a Docker container or production
    in_docker = os.path.exists("/.dockerenv")
    reload_enabled = environment == "development" and not in_docker

    logger.info(f"Server will be accessible at: http://localhost:{port}")
    logger.info(f"🚀 Starting FastAPI server on http://0.0.0.0:{port}")
    logger.info(f"🔧 Environment: {environment}, Docker: {in_docker}, Reload: {reload_enabled}")
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=reload_enabled)
