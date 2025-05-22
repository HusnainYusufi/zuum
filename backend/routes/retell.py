from fastapi import APIRouter, HTTPException, Body, File, UploadFile, Form, Query, status
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
from db_models import Journey
from db_models import JourneyState
import asyncio
from datetime import datetime, timedelta
from db_models import Journey
from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.exc import SQLAlchemyError
from pathlib import Path
import os

class ChangeStateRequest(BaseModel):
    state: int

class DelayReasonRequest(BaseModel):
    stop_id: int
    reason: str

class ReportedLocationRequest(BaseModel):
    stop_id: int
    reported_location: str

router = APIRouter(
    prefix="/retell",
    tags=["retell"],
    responses={404: {"description": "Not found"}},
)

# Get a database session from the generator
db = next(get_db())

@router.post("/change_transit_state")
def change_transit_state(request: dict = Body(...)):
    """Change the current state of the journey."""
    try:
        # Extract state value from request - handle both direct format and Retell format
        state = None
        if isinstance(request, dict):
            if 'state' in request:
                # Standard request format: {"state": 1}
                state = request['state']
            elif 'args' in request and isinstance(request['args'], dict) and 'state' in request['args']:
                # Retell format: {"args": {"state": 1}, ...}
                state = request['args']['state']
            elif 'name' in request and request['name'] == 'change_transit_state' and 'args' in request:
                # Alternative Retell format: {"name": "change_transit_state", "args": {...}}
                if 'state' in request['args']:
                    state = request['args']['state']
        
        if state is None:
            logger.error(f"Invalid request format: {request}")
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, 
                               detail="Invalid request format. 'state' field is required.")
        
        # Update the journey state
        journey = db.query(Journey).filter(Journey.id == 1).update({'current_state': state})
        
        if not journey:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Journey not found")
        
        db.commit()
        return {'message': True}
    
    except HTTPException:
        # Re-raise HTTPExceptions so they are handled correctly by FastAPI
        raise
    
    except SQLAlchemyError as e:
        db.rollback()  # rollback on DB error
        logger.error(f"Database error in change_transit_state: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Database error: {str(e)}")
    
    except Exception as e:
        # Generic catch-all for unexpected errors
        logger.error(f"Unexpected error in change_transit_state: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Internal server error: {str(e)}")

@router.post("/add_delay_reason")
def add_delay_reason(request: dict = Body(...)):
    """Update the delay reason for a specific stop."""
    try:
        # Log the incoming request
        print(f"Received in add_delay_reason: {request}")
        
        # Extract values from request - handle both direct format and Retell format
        stop_id = None
        reason = None
        
        if isinstance(request, dict):
            # Handle new Retell format with 'call' and 'args' at root level
            if 'name' in request and request['name'] == 'add_delay_reason' and 'args' in request and 'delay_reason' in request['args']:
                reason = request['args']['delay_reason']
                
                # Try to get stop_id from call.retell_llm_dynamic_variables if it exists
                if 'call' in request and 'retell_llm_dynamic_variables' in request['call']:
                    if 'stop_id' in request['call']['retell_llm_dynamic_variables']:
                        stop_id = int(request['call']['retell_llm_dynamic_variables']['stop_id'])
                    elif 'id' in request['call']['retell_llm_dynamic_variables']:
                        stop_id = int(request['call']['retell_llm_dynamic_variables']['id'])
            
            # Standard request format: {"stop_id": 1, "reason": "Traffic"}
            elif 'stop_id' in request and 'reason' in request:
                stop_id = request['stop_id']
                reason = request['reason']
                
            # Retell format: {"args": {"stop_id": 1, "reason": "Traffic"}, ...}
            elif 'args' in request and isinstance(request['args'], dict):
                args = request['args']
                if 'stop_id' in args and 'reason' in args:
                    stop_id = args['stop_id']
                    reason = args['reason']
                elif 'reason' in args:
                    # Handle simplified Retell format with just reason
                    reason = args['reason']
                elif 'delay_reason' in args:
                    # Handle simplified Retell format with delay_reason
                    reason = args['delay_reason']
                    
            # Alternative Retell format: {"name": "add_delay_reason", "args": {...}}
            elif 'name' in request and request['name'] == 'add_delay_reason' and 'args' in request:
                args = request['args']
                if 'stop_id' in args and 'reason' in args:
                    stop_id = args['stop_id']
                    reason = args['reason']
                elif 'reason' in args:
                    # Handle simplified Retell format with just reason
                    reason = args['reason']
                elif 'delay_reason' in args:
                    # Handle simplified Retell format with delay_reason
                    reason = args['delay_reason']
        
        if reason is None:
            logger.error(f"Invalid request format: {request}")
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, 
                               detail="Invalid request format. 'reason' or 'delay_reason' field is required.")
        
        if stop_id is None:
            # Default to first stop if stop_id not provided
            stop_id = 1
        
        # Update the stop with delay information
        stop = db.query(Stop).filter(Stop.id == stop_id).update({
            'delay_reason': reason,
            'is_delayed': True
        })

        if not stop:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stop not found")

        db.commit()
        return {'message': True}
    
    except HTTPException:
        # Re-raise HTTPExceptions
        raise
    
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Database error in add_delay_reason: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Database error: {str(e)}")
    
    except Exception as e:
        logger.error(f"Unexpected error in add_delay_reason: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Internal server error: {str(e)}")

@router.post("/update_reported_location_eta")
def update_reported_location_eta(request: dict = Body(...)):
    """Update the reported location and ETA for a specific stop."""
    try:
        # Extract values from request - handle all possible formats
        stop_id = None
        reported_location = None
        eta = None
        
        if isinstance(request, dict):
            # Try to get stop_id from call.retell_llm_dynamic_variables if it exists
            if 'call' in request and 'retell_llm_dynamic_variables' in request['call'] and 'id' in request['call']['retell_llm_dynamic_variables']:
                stop_id = int(request['call']['retell_llm_dynamic_variables']['id'])
            
            # Handle direct args at root level (most common format in error logs)
            if 'args' in request and isinstance(request['args'], dict):
                args = request['args']
                if 'reported_location' in args and 'reported_eta' in args:
                    reported_location = args['reported_location']
                    eta = args['reported_eta']
            
            # Handle name/args format (seen in error logs)
            elif 'name' in request and 'args' in request and isinstance(request['args'], dict):
                args = request['args']
                if 'reported_location' in args and 'reported_eta' in args:
                    reported_location = args['reported_location']
                    eta = args['reported_eta']
            
            # Handle additionalProp1 format (original format)
            elif 'additionalProp1' in request and isinstance(request['additionalProp1'], dict):
                if 'args' in request['additionalProp1'] and 'reported_location' in request['additionalProp1']['args'] and 'reported_eta' in request['additionalProp1']['args']:
                    reported_location = request['additionalProp1']['args']['reported_location']
                    eta = request['additionalProp1']['args']['reported_eta']
            
            # Standard request format
            elif 'stop_id' in request and 'reported_location' in request and 'reported_eta' in request:
                stop_id = request['stop_id']
                reported_location = request['reported_location']
                eta = request['reported_eta']
        
        if reported_location is None or eta is None:
            logger.error(f"Invalid request format: {request}")
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, 
                               detail="Invalid request format. Both 'reported_location' and 'reported_eta' fields are required.")
        
        if stop_id is None:
            # Default to first stop if stop_id not provided
            stop_id = 2
        # Remove 'Z' from eta if present
        if eta and eta.endswith('Z'):
            eta = eta[:-1]
        # Get the previous ETA from the database
        previous_stop = db.query(Stop).filter(Stop.id == stop_id).first()
        previous_eta = previous_stop.eta if previous_stop else None

        if previous_eta:
            # Compare new ETA with previous ETA to determine if delayed
            try:
                # Try parsing with microseconds
                new_eta = datetime.strptime(eta, '%Y-%m-%dT%H:%M:%S.%f')
            except ValueError:
                # If that fails, try without microseconds
                new_eta = datetime.strptime(eta, '%Y-%m-%dT%H:%M:%S')
                
            try:
                # Try parsing with microseconds
                prev_eta = datetime.strptime(previous_eta, '%Y-%m-%dT%H:%M:%S.%f')
            except ValueError:
                # If that fails, try without microseconds
                prev_eta = datetime.strptime(previous_eta, '%Y-%m-%dT%H:%M:%S')
            
       
            delay = new_eta > prev_eta
        else:
            # If no previous ETA, default to comparing with current time
            try:
                # Try parsing with microseconds
                new_eta = datetime.strptime(eta, '%Y-%m-%dT%H:%M:%S.%f')
            except ValueError:
                # If that fails, try without microseconds
                new_eta = datetime.strptime(eta, '%Y-%m-%dT%H:%M:%S')
                
            delay = new_eta > datetime.now()
        # Update the stop with the reported location and ETA
        logger.info(f"Delay: {delay}")
        logger.info(f"Stop ID: {stop_id}")
        logger.info(f"Reported Location: {reported_location}")
        logger.info(f"ETA: {new_eta}")
        logger.info(f"Previous ETA: {previous_eta}")
        stop = db.query(Stop).filter(Stop.id == stop_id).update({
            'reported_location': reported_location,
            'eta': eta,
            'is_delayed': delay
        })

        if not stop:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stop not found")

        db.commit()
        return {'delay': delay}
    
    except HTTPException:
        # Re-raise HTTPExceptions
        raise
    
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Database error in update_reported_location_eta: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Database error: {str(e)}")
    
    except Exception as e:
        logger.error(f"Unexpected error in update_reported_location_eta: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Internal server error: {str(e)}")
