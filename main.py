import traceback
from typing import List, Dict, Optional
import os
from loguru import logger
from pydantic import BaseModel
from fastapi import FastAPI, HTTPException, Depends, Form, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from init_db import init_db
from routes import conversation_router, ui_router, retell_router, notifications_router, checkin_router
from routes.test_froms import router as test_forms_router
from dotenv import load_dotenv
from db_models import CheckIn, Stop as StopModel, get_db, RetellCall, Feedback, FeedbackImage
from sqlalchemy.orm import Session
from services.db_service import get_all_stops, get_all_stops_with_details
from twilio.rest import Client
from datetime import datetime
import shutil
from pathlib import Path

load_dotenv()

# Create feedback images directory if it doesn't exist
FEEDBACK_IMAGES_DIR = Path("static/feedback-images")
FEEDBACK_IMAGES_DIR.mkdir(parents=True, exist_ok=True)

# Initialize the database only if it's empty
def init_db_if_empty():
    """Initialize database only if it doesn't have data already"""
    # First create tables
    from db_models import create_tables
    create_tables()
    
    db = next(get_db())
    try:
        # Check if we have any stops
        existing_stops = db.query(StopModel).first()
        if not existing_stops:
            print("Database is empty, initializing with dummy data...")
            init_db()
        else:
            print(f"Database already has data, skipping initialization. Found {db.query(StopModel).count()} stops.")
    finally:
        db.close()

# Initialize the database only if empty
init_db_if_empty()

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
app.include_router(conversation_router)
app.include_router(ui_router)
app.include_router(retell_router)
# app.include_router(tests_router)
app.include_router(notifications_router)
app.include_router(test_forms_router)
app.include_router(checkin_router)

# Initialize Twilio client
twilio_client = Client(
    os.getenv('TWILIO_ACCOUNT_SID', ''),
    os.getenv('TWILIO_AUTH_TOKEN', '')
)
TWILIO_FROM_NUMBER = os.getenv('TWILIO_FROM_NUMBER', '')

# Get recipient phone numbers from environment variable
FEEDBACK_RECIPIENT_PHONES = os.getenv('FEEDBACK_RECIPIENT_PHONES', '').split(',')

class ChatRequest(BaseModel):
    message: str
    stop_id: Optional[int] = None

class ChatResponse(BaseModel):
    message: str
    state: dict

class Stop(BaseModel):
    id: int
    name: str
    location: str
    eta: str
    is_delayed: bool
    is_origin: bool
    is_destination: bool


class StopDetail(BaseModel):
    id: int
    name: str
    location: str
    eta: str
    cross_street: Optional[str] = None
    nearest_highway: Optional[str] = None
    is_delayed: bool
    delay_reason: Optional[str] = None
    expected_location: Optional[str] = None
    reported_location: Optional[str] = None
    is_origin: bool
    is_destination: bool


class CheckInResponse(BaseModel):
    id: int
    stop_id: Optional[int] = None
    load_id: Optional[str] = None
    query: Optional[str] = None
    AI_Response_Summary: Optional[str] = None
    AI_Timestamp: Optional[str] = None
    Issue_Flagged: bool = False
    Exception_Type: Optional[str] = None
    Call_confidence_score: Optional[str] = None
    call_trasfered: bool = False
    Tags: Optional[str] = None
    stop_name: Optional[str] = None
    stop_location: Optional[str] = None
    stop_eta: Optional[str] = None
    call_id: Optional[str] = None
    call_transcript: Optional[str] = None
    recording_url: Optional[str] = None
    check_in_metadata: Optional[str] = None
    is_active: Optional[bool] = None

class FeedbackRequest(BaseModel):
    feedbackType: str
    userName: str
    userEmail: str
    feedbackDescription: str

class FeedbackImageResponse(BaseModel):
    id: int
    filename: str
    original_filename: Optional[str]
    url: str
    uploaded_at: str

class FeedbackResponse(BaseModel):
    id: int
    feedback_type: str
    user_name: str
    user_email: str
    description: str
    created_at: str
    images: List[FeedbackImageResponse]

@app.post("/send-feedback")
async def send_feedback(
    feedbackType: str = Form(...),
    userName: str = Form(...),
    userEmail: str = Form(...),
    feedbackDescription: str = Form(...),
    feedbackImages: List[UploadFile] = File(None),
    db: Session = Depends(get_db)
):
    try:
        logger.info(f"Received feedback from {userName} ({userEmail}) - Type: {feedbackType}")
        
        # Check required environment variables for Twilio
        required_env_vars = {
            'TWILIO_ACCOUNT_SID': os.getenv('TWILIO_ACCOUNT_SID'),
            'TWILIO_AUTH_TOKEN': os.getenv('TWILIO_AUTH_TOKEN'),
            'TWILIO_FROM_NUMBER': os.getenv('TWILIO_FROM_NUMBER'),
            'FEEDBACK_RECIPIENT_PHONES': os.getenv('FEEDBACK_RECIPIENT_PHONES'),
        }
        
        missing_vars = [var for var, val in required_env_vars.items() if not val]
        if missing_vars:
            error_msg = f"Missing required environment variables: {', '.join(missing_vars)}"
            logger.error(error_msg)
            raise HTTPException(status_code=500, detail=error_msg)
        
        logger.info("All required environment variables are present")
        
        # Create feedback record in database
        feedback = Feedback(
            feedback_type=feedbackType,
            user_name=userName,
            user_email=userEmail,
            description=feedbackDescription
        )
        db.add(feedback)
        db.flush()  # Flush to get the feedback ID
        
        image_links = []
        
        # Process and save images locally
        if feedbackImages:
            logger.info(f"Processing {len(feedbackImages)} image files")
            for i, file in enumerate(feedbackImages):
                if file.filename:
                    logger.info(f"Processing image {i+1}: {file.filename}")
                    # Generate unique filename
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    file_extension = os.path.splitext(file.filename)[1]
                    unique_filename = f"feedback_{feedback.id}_{userName}_{timestamp}_{i}{file_extension}"
                    
                    # Read file contents
                    contents = await file.read()
                    logger.info(f"Read {len(contents)} bytes from {file.filename}")
                    
                    # Save to local storage
                    try:
                        file_path = FEEDBACK_IMAGES_DIR / unique_filename
                        logger.info(f"Saving to local storage: {file_path}")
                        
                        with open(file_path, "wb") as f:
                            f.write(contents)
                        
                        # Create relative URL for accessing the image
                        relative_url = f"/static/feedback-images/{unique_filename}"
                        image_links.append(relative_url)
                        
                        # Save image record to database
                        feedback_image = FeedbackImage(
                            feedback_id=feedback.id,
                            filename=unique_filename,
                            original_filename=file.filename,
                            file_path=str(file_path)
                        )
                        db.add(feedback_image)
                        
                        logger.info(f"Generated local URL: {relative_url}")
                    except Exception as save_error:
                        logger.error(f"Failed to save image {file.filename}: {str(save_error)}")
                        logger.error(f"Save error type: {type(save_error).__name__}")
                        continue
        
        # Commit all database changes
        db.commit()
        logger.info(f"Successfully saved feedback {feedback.id} with {len(image_links)} images")
        
        # Create SMS body with image links
        sms_body = f"""[Freight Broker Project]
New Feedback from {userName}
Email: {userEmail}
Type: {feedbackType}

Message:
{feedbackDescription[:200]}{"..." if len(feedbackDescription) > 200 else ""}"""

        # Add image links if any (using the host URL if available)
        if image_links:
            sms_body += "\n\nImage/s:"
            # Get the base URL from request or environment
            base_url = os.getenv('BASE_URL', 'http://localhost:8000')
            for link in image_links:
                full_url = f"{base_url}{link}"
                sms_body += f"\n{full_url}"

        logger.info(f"SMS body length: {len(sms_body)} characters")
        
        # Check if recipient phones are configured
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
                
                # Validate phone number format
                clean_from_number = TWILIO_FROM_NUMBER.replace(' ', '').replace('(', '').replace(')', '').replace('-', '')
                clean_to_number = phone_number.strip().replace(' ', '').replace('(', '').replace(')', '').replace('-', '')
                
                logger.info(f"Cleaned numbers - From: {clean_from_number}, To: {clean_to_number}")
                
                message = twilio_client.messages.create(
                    body=sms_body,
                    from_=clean_from_number,
                    to=clean_to_number
                )
                logger.info(f"SMS sent successfully to {phone_number}. Message SID: {message.sid}")
            except Exception as sms_error:
                error_msg = f"Failed to send SMS to {phone_number}: {str(sms_error)}"
                logger.error(error_msg)
                logger.error(f"SMS error type: {type(sms_error).__name__}")
                logger.error(f"SMS error details: {sms_error}")
                sms_errors.append(error_msg)
        
        # Handle SMS sending results
        if sms_errors and len(sms_errors) < len(recipient_phones):
            logger.warning(f"Some SMS notifications failed: {', '.join(sms_errors)}")
        elif sms_errors and len(sms_errors) == len(recipient_phones):
            logger.error("All SMS notifications failed to send")
            raise HTTPException(status_code=500, detail=f"Failed to send SMS notifications: {'; '.join(sms_errors)}")
        
        logger.info("Feedback processed successfully")
        return {
            "success": True, 
            "message": "Feedback sent successfully",
            "feedback_id": feedback.id,
            "images_saved": len(image_links)
        }
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(f"Unexpected error in send_feedback: {str(e)}")
        logger.error(f"Error type: {type(e).__name__}")
        logger.error(f"Error traceback: {traceback.format_exc()}")
        db.rollback()  # Rollback database changes on error
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

# Get all stops (basic info)
@app.get("/stops", response_model=List[Stop])
async def stops():
    try:
        return get_all_stops()
    except Exception as e:
        logger.error(f"Error in stops endpoint: {str(e)}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

# Get all stops with detailed information
@app.get("/stops/details", response_model=List[StopDetail])
async def stops_details():
    try:
        return get_all_stops_with_details()
    except Exception as e:
        logger.error(f"Error in stops details endpoint: {str(e)}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# Get all check-ins
@app.get("/check-ins", response_model=List[CheckInResponse])
async def get_check_ins(db: Session = Depends(get_db)):
    try:
        # Query all check-ins ordered by newest first (no stop dependency)
        check_ins = db.query(CheckIn).order_by(CheckIn.AI_Timestamp.desc()).all()
        
        # Transform to response model
        result = []
        for check_in in check_ins:
            # Get the first retell call for this check-in (if any)
            retell_call = db.query(RetellCall).filter(RetellCall.check_in_id == check_in.id).first()
            
            # Get stop information if stop_id exists
            stop_name = None
            stop_location = None
            stop_eta = None
            if check_in.stop_id:
                stop = db.query(StopModel).filter(StopModel.id == check_in.stop_id).first()
                if stop:
                    stop_name = stop.name
                    stop_location = stop.location
                    stop_eta = stop.eta
            
            result.append(CheckInResponse(
                id=check_in.id,
                stop_id=check_in.stop_id,
                load_id=check_in.load_id,
                query=check_in.query,
                AI_Response_Summary=check_in.AI_Response_Summary,
                AI_Timestamp=check_in.AI_Timestamp,
                Issue_Flagged=check_in.Issue_Flagged,
                Exception_Type=check_in.Exception_Type,
                Call_confidence_score=check_in.Call_confidence_score,
                call_trasfered=check_in.call_trasfered,
                Tags=check_in.Tags,
                stop_name=stop_name,
                stop_location=stop_location,
                stop_eta=stop_eta,
                call_id=retell_call.call_id if retell_call else None,
                call_transcript=retell_call.call_transcript if retell_call else None,
                recording_url=retell_call.recording_url if retell_call else None,
                check_in_metadata=retell_call.check_in_metadata if retell_call else None,
                is_active=check_in.is_active
            ))
        print(result)
        return result
    except Exception as e:
        logger.error(f"Error in check-ins endpoint: {str(e)}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

state_dict = {}

# Root route redirects to dashboard
@app.get("/")
async def root():
    """Redirect root to dashboard"""
    return RedirectResponse(url="/checkin-dashboard")

@app.get("/health-check")
async def health_check():
    """Health check endpoint to verify all services are working"""
    health_status = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "services": {},
        "environment": {}
    }
    
    # Check environment variables
    env_vars_to_check = [
        'TWILIO_ACCOUNT_SID', 'TWILIO_AUTH_TOKEN', 'TWILIO_FROM_NUMBER',
        'FEEDBACK_RECIPIENT_PHONES',
    ]
    
    for var in env_vars_to_check:
        value = os.getenv(var)
        health_status["environment"][var] = {
            "configured": bool(value),
            "length": len(value) if value else 0
        }
    
    # Test Twilio connection
    try:
        # Simple test to verify Twilio client works
        twilio_client.api.accounts(os.getenv('TWILIO_ACCOUNT_SID')).fetch()
        health_status["services"]["twilio"] = {"status": "connected", "error": None}
    except Exception as e:
        health_status["services"]["twilio"] = {"status": "failed", "error": str(e)}
        health_status["status"] = "degraded"
    
    return health_status

# Get all feedback entries
@app.get("/feedback", response_model=List[FeedbackResponse])
async def get_feedback(db: Session = Depends(get_db)):
    """Retrieve all feedback entries with their associated images"""
    try:
        feedbacks = db.query(Feedback).order_by(Feedback.created_at.desc()).all()
        
        result = []
        base_url = os.getenv('BASE_URL', 'http://localhost:8000')
        
        for feedback in feedbacks:
            images = []
            for img in feedback.images:
                images.append(FeedbackImageResponse(
                    id=img.id,
                    filename=img.filename,
                    original_filename=img.original_filename,
                    url=f"{base_url}/static/feedback-images/{img.filename}",
                    uploaded_at=img.uploaded_at
                ))
            
            result.append(FeedbackResponse(
                id=feedback.id,
                feedback_type=feedback.feedback_type,
                user_name=feedback.user_name,
                user_email=feedback.user_email,
                description=feedback.description,
                created_at=feedback.created_at,
                images=images
            ))
        
        return result
    except Exception as e:
        logger.error(f"Error retrieving feedback: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Get specific feedback by ID
@app.get("/feedback/{feedback_id}", response_model=FeedbackResponse)
async def get_feedback_by_id(feedback_id: int, db: Session = Depends(get_db)):
    """Retrieve a specific feedback entry by ID"""
    try:
        feedback = db.query(Feedback).filter(Feedback.id == feedback_id).first()
        if not feedback:
            raise HTTPException(status_code=404, detail="Feedback not found")
        
        base_url = os.getenv('BASE_URL', 'http://localhost:8000')
        images = []
        for img in feedback.images:
            images.append(FeedbackImageResponse(
                id=img.id,
                filename=img.filename,
                original_filename=img.original_filename,
                url=f"{base_url}/static/feedback-images/{img.filename}",
                uploaded_at=img.uploaded_at
            ))
        
        return FeedbackResponse(
            id=feedback.id,
            feedback_type=feedback.feedback_type,
            user_name=feedback.user_name,
            user_email=feedback.user_email,
            description=feedback.description,
            created_at=feedback.created_at,
            images=images
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving feedback {feedback_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    import time
    
    def test_ssl_connection():
        """Test SSL connection before proceeding with ngrok"""
        try:
            import urllib.request
            import urllib.error
            
            # Test a simple HTTPS connection
            urllib.request.urlopen('https://www.google.com', timeout=10)
            logger.info("SSL connection test successful")
            return True
        except Exception as e:
            logger.warning(f"SSL connection test failed: {e}")
            return False
    
    def setup_ngrok_with_retry():
        """Setup ngrok with SSL error handling and retry logic"""
        try:
            from pyngrok import ngrok
            from pyngrok.exception import PyngrokNgrokInstallError
            
            # Test SSL connection first
            if not test_ssl_connection():
                logger.warning("SSL connection test failed, but continuing with ngrok setup...")
            
            port = 8000
            
            # Set ngrok auth token from environment variable
            ngrok_auth_token = os.getenv("NGROK_AUTH_TOKEN")
            if ngrok_auth_token:
                try:
                    ngrok.set_auth_token(ngrok_auth_token)
                    logger.info("Ngrok authtoken configured successfully")
                    
                    # Give ngrok a moment to initialize
                    time.sleep(2)
                    
                except PyngrokNgrokInstallError as e:
                    logger.error(f"Failed to install/configure ngrok due to SSL issues: {e}")
                    logger.info("Attempting to run server without ngrok tunnel...")
                    return None, port
                except Exception as e:
                    logger.error(f"Unexpected error configuring ngrok: {e}")
                    logger.info("Attempting to run server without ngrok tunnel...")
                    return None, port
            else:
                logger.warning("⚠️  NGROK_AUTH_TOKEN not found in environment variables")
                logger.info("🔧 To enable ngrok tunneling, set NGROK_AUTH_TOKEN in your .env file")
                logger.info("🚀 Continuing without ngrok tunnel - application will be available locally only")
                return None, port
            
            # Start ngrok tunnel with static domain
            try:

                ngrok_domain = os.getenv("BACKEND_ngrok_LINK")

                logger.info(f"Attempting to establish ngrok tunnel with domain: {ngrok_domain}")
                
                public_url = ngrok.connect(port, hostname=ngrok_domain).public_url
                # public_url = ngrok.connect(port).public_url
                logger.info(f"✅ Ngrok tunnel established successfully at {public_url}")
                
                # Log ngrok admin interface
                logger.info(f"🔧 Ngrok admin interface available at: http://localhost:4040")
                
                return public_url, port
            except Exception as e:
                logger.error(f"❌ Failed to establish ngrok tunnel: {str(e)}")
                logger.error(f"Error details: {type(e).__name__}")
                logger.info("🚀 Continuing without ngrok tunnel - application will be available locally only")
                return None, port
                
        except ImportError as e:
            logger.error(f"Failed to import pyngrok: {e}")
            logger.info("Running server without ngrok...")
            return None, 8000
    
    # Setup ngrok (if possible)
    public_url, port = setup_ngrok_with_retry()
    
    if public_url:
        logger.info(f"Server will be accessible at: {public_url}")
    else:
        logger.info(f"Server will be accessible at: http://localhost:{port}")
    
    # Start FastAPI application - use 0.0.0.0 for Docker compatibility
    logger.info(f"🚀 Starting FastAPI server on http://0.0.0.0:{port}")
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
