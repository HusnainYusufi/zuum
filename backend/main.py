import traceback
from typing import List, Dict, Optional
import os
import ssl
import certifi
import subprocess
import sys
from loguru import logger
from pydantic import BaseModel
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware

# SSL Certificate setup - must be done before any SSL connections
def setup_ssl_certificates():
    """Setup SSL certificates for Windows systems"""
    try:
        # Method 1: Install pip-system-certs if not already installed
        try:
            import pip_system_certs
            logger.info("pip-system-certs already installed")
        except ImportError:
            logger.info("Installing pip-system-certs...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", "pip-system-certs"])
            logger.info("Successfully installed pip-system-certs")

        # Method 2: Update certifi
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", "certifi"])
            logger.info("Successfully updated certifi")
        except subprocess.CalledProcessError as e:
            logger.warning(f"Failed to update certifi: {e}")

        # Method 3: Set SSL context to use certifi certificates
        ssl_context = ssl.create_default_context(cafile=certifi.where())
        ssl._create_default_https_context = lambda: ssl_context
        logger.info("SSL context configured with certifi certificates")
        
        # Method 4: Set environment variables for SSL
        os.environ['SSL_CERT_FILE'] = certifi.where()
        os.environ['REQUESTS_CA_BUNDLE'] = certifi.where()
        os.environ['CURL_CA_BUNDLE'] = certifi.where()
        logger.info("SSL environment variables set")
        
        return True
        
    except Exception as e:
        logger.error(f"Error setting up SSL certificates: {e}")
        # Try to continue anyway
        return False

# Setup SSL certificates before any other operations
setup_ssl_certificates()

from dotenv import load_dotenv
load_dotenv()

from origin import initialize_chat, process_chat_sequence
from transit import initialize_transit_chat, process_transit_chat_sequence, get_all_stops, get_chat_history, get_all_stops_with_details
from init_db import init_db
from routes import conversation_router, ui_router, retell_router

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
    
state_dict = {}
    
@app.post("/transit-chat", response_model=ChatResponse)
async def transit_chat(request: ChatRequest):
    try:
        # Get the stop_id from the request
        stop_id = request.stop_id

        if not stop_id:
            raise HTTPException(status_code=400, detail="Stop ID is required")
        
        # Initialize state with stop_id if provided
        if stop_id not in state_dict:
            # current_state = state_dict[stop_id]
            state_dict[stop_id] = initialize_transit_chat(stop_id)

        current_state = state_dict[stop_id]
        response = process_transit_chat_sequence(current_state, request.message)

        state_dict[stop_id] = response["state"] # update the state

        return response

    except Exception as e:
        logger.error(f"Error in transit chat endpoint: {str(e)}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

# @app.post("/transit-chat", response_model=ChatResponse)
# async def transit_chat(request: ChatRequest):
#     try:
#         # Get the stop_id from the request
#         stop_id = request.stop_id

#         if not stop_id:
#             raise HTTPException(status_code=400, detail="Stop ID is required")
        
#         # Initialize state with stop_id if provided
#         current_state = initialize_transit_chat(stop_id)
        
#         # Process the transit chat sequence with the user's message
#         response = process_transit_chat_sequence(current_state, request.message)
        
#         # Log the response for debugging
#         logger.debug(f"Transit API Response before sending: {response}")
        
#         # Ensure response is properly formatted
#         if isinstance(response, dict) and 'message' in response and 'state' in response:
#             return response
#         else:
#             # Handle legacy format or unexpected response
#             formatted_response = ChatResponse(
#                 message=str(response),
#                 state={
#                     "bool3": current_state.get("bool3", False),
#                     "bool2": current_state.get("bool2", False),
#                     "bool1": current_state.get("bool1", False),
#                     "bool0": current_state.get("bool0", False),
#                     "stop_id": stop_id,
#                     "current_step": "scheduled" if not current_state.get("is_scheduled") else "location" if not current_state.get("location_provided") else "eta"
#                 }
#             )
#             logger.debug(f"Formatted transit response: {formatted_response}")
#             return formatted_response

#     except Exception as e:
#         logger.error(f"Error in transit chat endpoint: {str(e)}")
#         traceback.print_exc()
#         raise HTTPException(status_code=500, detail=str(e))

@app.get("/transit-chat", response_model=ChatResponse)
async def get_transit_chat(stop_id: Optional[int] = None):
    try:
        # Initialize state with stop_id if provided
        current_state = initialize_transit_chat(stop_id) if stop_id else transit_state
        
        # Get the initial state and message
        response = process_transit_chat_sequence(current_state)
        
        # Log the response for debugging
        logger.debug(f"Transit API Response before sending: {response}")
        
        # Ensure response is properly formatted
        if isinstance(response, dict) and 'message' in response and 'state' in response:
            return response
        else:
            # Handle legacy format or unexpected response
            formatted_response = ChatResponse(
                message=str(response),
                state={
                    "bool3": current_state.get("bool3", False),
                    "bool2": current_state.get("bool2", False),
                    "bool1": current_state.get("bool1", False),
                    "bool0": current_state.get("bool0", False),
                    "stop_id": stop_id,
                    "current_step": "scheduled" if not current_state.get("is_scheduled") else "location" if not current_state.get("location_provided") else "eta"
                }
            )
            logger.debug(f"Formatted transit response: {formatted_response}")
            return formatted_response

    except Exception as e:
        logger.error(f"Error in transit chat endpoint: {str(e)}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))



if __name__ == "__main__":
    import uvicorn
    
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
                    logger.info("Ngrok authtoken configured")
                except PyngrokNgrokInstallError as e:
                    logger.error(f"Failed to install/configure ngrok due to SSL issues: {e}")
                    logger.info("Attempting to run server without ngrok tunnel...")
                    return None, port
                except Exception as e:
                    logger.error(f"Unexpected error configuring ngrok: {e}")
                    logger.info("Attempting to run server without ngrok tunnel...")
                    return None, port
            else:
                logger.warning("NGROK_AUTH_TOKEN not found in environment variables. Running without tunnel.")
                return None, port
            
            # Start ngrok tunnel with static domain
            try:
                ngrok_domain = "trusting-dolphin-internally.ngrok-free.app"
                public_url = ngrok.connect(port, hostname=ngrok_domain).public_url
                logger.info(f"ngrok tunnel established at {public_url}")
                return public_url, port
            except Exception as e:
                logger.error(f"Failed to create ngrok tunnel: {e}")
                logger.info("Running server without tunnel...")
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
    
    # Start FastAPI application
    uvicorn.run("main:app", host="localhost", port=port, reload=True)



