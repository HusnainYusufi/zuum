import traceback
from typing import List, Dict, Optional
import os
from loguru import logger
from pydantic import BaseModel
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from origin import initialize_chat, process_chat_sequence
from transit import initialize_transit_chat, process_transit_chat_sequence, get_all_stops, get_chat_history, get_all_stops_with_details
from init_db import init_db
from routes import conversation_router, ui_router, retell_router, tests_router
from dotenv import load_dotenv
# Add database imports
from db_models import CheckIn, Stop as StopModel, get_db
from sqlalchemy.orm import Session

load_dotenv()

# Initialize the database
init_db()

app = FastAPI()

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
app.include_router(tests_router)
# Initialize the chat states
state = initialize_chat()
transit_state = initialize_transit_chat(1)
transit_state_2 = initialize_transit_chat(2)
transit_state_3 = initialize_transit_chat(3)

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
    stop_id: int
    query: str
    summary: str
    timestamp: str
    stop_name: Optional[str] = None
    stop_location: Optional[str] = None


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

# Get chat history for a stop
@app.get("/chat-history/{stop_id}", response_model=List[Dict])
async def chat_history(stop_id: int):
    try:
        return get_chat_history(stop_id)
    except Exception as e:
        logger.error(f"Error in chat history endpoint: {str(e)}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

# Get all check-ins
@app.get("/check-ins", response_model=List[CheckInResponse])
async def get_check_ins(db: Session = Depends(get_db)):
    try:
        # Query check-ins with stop information
        check_ins = db.query(CheckIn).join(StopModel, CheckIn.stop_id == StopModel.id).all()
        
        # Transform to response model
        result = []
        for check_in in check_ins:
            result.append(CheckInResponse(
                id=check_in.id,
                stop_id=check_in.stop_id,
                query=check_in.query,
                summary=check_in.summary,
                timestamp=check_in.timestamp,
                stop_name=check_in.stop.name if check_in.stop else None,
                stop_location=check_in.stop.location if check_in.stop else None
            ))
        
        return result
    except Exception as e:
        logger.error(f"Error in check-ins endpoint: {str(e)}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

# Get check-ins for a specific stop
@app.get("/check-ins/{stop_id}", response_model=List[CheckInResponse])
async def get_check_ins_by_stop(stop_id: int, db: Session = Depends(get_db)):
    try:
        # Query check-ins for specific stop with stop information
        check_ins = db.query(CheckIn).join(StopModel, CheckIn.stop_id == StopModel.id).filter(CheckIn.stop_id == stop_id).all()
        
        # Transform to response model
        logger.info(f"Found {len(check_ins)} check-ins for stop {stop_id}")
        result = []
        for check_in in check_ins:
            result.append(CheckInResponse(
                id=check_in.id,
                stop_id=check_in.stop_id,
                query=check_in.query,
                summary=check_in.summary,
                timestamp=check_in.timestamp,
                stop_name=check_in.stop.name if check_in.stop else None,
                stop_location=check_in.stop.location if check_in.stop else None
            ))
        
        return result
    except Exception as e:
        logger.error(f"Error in check-ins by stop endpoint: {str(e)}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

state_dict = {}




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
                ngrok_domain = "legal-bluebird-bright.ngrok-free.app"
                logger.info(f"Attempting to establish ngrok tunnel with domain: {ngrok_domain}")
                
                public_url = ngrok.connect(port, hostname=ngrok_domain).public_url
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



