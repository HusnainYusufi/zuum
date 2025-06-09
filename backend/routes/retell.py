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
from db_models import CheckIn
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
import json
from db_models import RetellCall
from services.notification_service import notify_stop_update, notify_check_in_update, notify_journey_state_update, send_notification

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
    """Change the transit state for the journey."""
    try:
        # Extract state from request - handle different formats
        state = None
        
        if isinstance(request, dict):
            # Handle direct state in request
            if 'state' in request:
                state = request['state']
            # Handle args format
            elif 'args' in request and isinstance(request['args'], dict) and 'state' in request['args']:
                state = request['args']['state']
            # Handle name/args format
            elif 'name' in request and request['name'] == 'change_transit_state' and 'args' in request and 'state' in request['args']:
                state = request['args']['state']
        
        if state is None:
            logger.error(f"Invalid request format: {request}")
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid request format. 'state' field is required.")
        
        # Update the journey state
        journey = db.query(Journey).filter(Journey.id == 1).update({'current_state': state})
        
        if not journey:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Journey not found")
        
        db.commit()
        
        # Send notification about journey state update
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(notify_journey_state_update(state))
            loop.close()
        except Exception as e:
            logger.warning(f"Could not send notification: {e}")
        
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
        
        # Get the updated stop data for notification
        updated_stop = db.query(Stop).filter(Stop.id == stop_id).first()
        if updated_stop:
            stop_data = {
                'id': updated_stop.id,
                'name': updated_stop.name,
                'location': updated_stop.location,
                'eta': updated_stop.eta,
                'is_delayed': updated_stop.is_delayed,
                'delay_reason': updated_stop.delay_reason,
                'expected_location': updated_stop.expected_location,
                'reported_location': updated_stop.reported_location,
                'nearest_highway': updated_stop.nearest_highway,
                'is_origin': updated_stop.is_origin,
                'is_destination': updated_stop.is_destination
            }
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(notify_stop_update(stop_data))
                loop.close()
            except Exception as e:
                logger.warning(f"Could not send notification: {e}")
        
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
        
        # Get the updated stop data for notification
        updated_stop = db.query(Stop).filter(Stop.id == stop_id).first()
        if updated_stop:
            stop_data = {
                'id': updated_stop.id,
                'name': updated_stop.name,
                'location': updated_stop.location,
                'eta': updated_stop.eta,
                'is_delayed': updated_stop.is_delayed,
                'delay_reason': updated_stop.delay_reason,
                'expected_location': updated_stop.expected_location,
                'reported_location': updated_stop.reported_location,
                'nearest_highway': updated_stop.nearest_highway,
                'is_origin': updated_stop.is_origin,
                'is_destination': updated_stop.is_destination
            }
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(notify_stop_update(stop_data))
                loop.close()
            except Exception as e:
                logger.warning(f"Could not send notification: {e}")
        
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

@router.post("/update_checkIn")
def check_in(request: dict = Body(...)):
    """Update the checkIn by extracting chat_summary, query, and stop_id and storing in database."""
    try:
        logger.info(f"Received in update_checkIn: {request}")
        
        # Extract values from request - handle different formats
        stop_id = None
        chat_summary = None
        query = None
        issue_flagged = False
        exception_type = None
        call_confidence_score = None
        requires_human_review = False
        tags = None
        load_id = None
        call_id = None
        transcript = None
        miles = None
        
        if isinstance(request, dict):
            # Extract call_id and transcript from the call object
            if 'call' in request:
                if 'call_id' in request['call']:
                    call_id = request['call']['call_id']
                if 'transcript' in request['call']:
                    transcript = request['call']['transcript']
                    
            # Try to get stop_id, query, and load_number from call.retell_llm_dynamic_variables if it exists
            if 'call' in request and 'retell_llm_dynamic_variables' in request['call']:
                if 'stop_id' in request['call']['retell_llm_dynamic_variables']:
                    stop_id = int(request['call']['retell_llm_dynamic_variables']['stop_id'])
                elif 'id' in request['call']['retell_llm_dynamic_variables']:
                    stop_id = int(request['call']['retell_llm_dynamic_variables']['id'])
                
                # Extract query from retell_llm_dynamic_variables
                if 'query' in request['call']['retell_llm_dynamic_variables']:
                    query = request['call']['retell_llm_dynamic_variables']['query']
                
                # Extract load_number as load_id if available
                if 'load_number' in request['call']['retell_llm_dynamic_variables']:
                    load_id = request['call']['retell_llm_dynamic_variables']['load_number']
                elif 'load_id' in request['call']['retell_llm_dynamic_variables']:
                    load_id = request['call']['retell_llm_dynamic_variables']['load_id']
                
                # Extract miles if available
                if 'miles' in request['call']['retell_llm_dynamic_variables']:
                    miles = request['call']['retell_llm_dynamic_variables']['miles']
            
            # Handle args format (most common in tool call invocations)
            if 'args' in request and isinstance(request['args'], dict):
                args = request['args']
                if 'chat_summary' in args:
                    chat_summary = args['chat_summary']
                elif 'AI_Response_Summary' in args:
                    chat_summary = args['AI_Response_Summary']
                if 'query' in args:
                    query = args['query']
                if 'stop_id' in args:
                    stop_id = args['stop_id']
                if 'issue_flagged' in args:
                    issue_flagged = args['issue_flagged']
                if 'exception_type' in args:
                    exception_type = args['exception_type']
                if 'call_confidence_score' in args:
                    call_confidence_score = args['call_confidence_score']
                if 'requires_human_review' in args:
                    requires_human_review = args['requires_human_review']
                if 'tags' in args:
                    tags = args['tags']
                if 'load_id' in args:
                    load_id = args['load_id']
                elif 'load_number' in args:
                    load_id = args['load_number']
                if 'miles' in args:
                    miles = args['miles']
            
            # Handle name/args format for tool calls
            elif 'name' in request and request['name'] == 'update_checkIn' and 'args' in request:
                args = request['args']
                if 'chat_summary' in args:
                    chat_summary = args['chat_summary']
                elif 'AI_Response_Summary' in args:
                    chat_summary = args['AI_Response_Summary']
                if 'query' in args:
                    query = args['query']
                if 'stop_id' in args:
                    stop_id = args['stop_id']
                if 'issue_flagged' in args:
                    issue_flagged = args['issue_flagged']
                if 'exception_type' in args:
                    exception_type = args['exception_type']
                if 'call_confidence_score' in args:
                    call_confidence_score = args['call_confidence_score']
                if 'requires_human_review' in args:
                    requires_human_review = args['requires_human_review']
                if 'tags' in args:
                    tags = args['tags']
                if 'load_id' in args:
                    load_id = args['load_id']
                elif 'load_number' in args:
                    load_id = args['load_number']
                if 'miles' in args:
                    miles = args['miles']
            
            # Handle direct format
            elif 'chat_summary' in request:
                chat_summary = request['chat_summary']
                if 'query' in request:
                    query = request['query']
                if 'stop_id' in request:
                    stop_id = request['stop_id']
                if 'issue_flagged' in request:
                    issue_flagged = request['issue_flagged']
                if 'exception_type' in request:
                    exception_type = request['exception_type']
                if 'call_confidence_score' in request:
                    call_confidence_score = request['call_confidence_score']
                if 'requires_human_review' in request:
                    requires_human_review = request['requires_human_review']
                if 'tags' in request:
                    tags = request['tags']
                if 'load_id' in request:
                    load_id = request['load_id']
                elif 'load_number' in request:
                    load_id = request['load_number']
                if 'miles' in request:
                    miles = request['miles']
        
        # Default stop_id if not provided
        if stop_id is None:
            stop_id = 1  # Default to first stop
        
        # Create timestamp
        timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        
        # Create new CheckIn record with correct field names
        check_in_record = CheckIn(
            stop_id=stop_id,
            load_id=load_id,
            query=query,
            AI_Response_Summary=chat_summary,  # Correct field name
            AI_Timestamp=timestamp,  # Correct field name
            Issue_Flagged=issue_flagged,
            Exception_Type=exception_type,
            Call_confidence_score=call_confidence_score,
            Requires_Human_Review=requires_human_review,
            Tags=tags,
            miles=miles
        )
        
        db.add(check_in_record)
        db.commit()
        
        # Refresh the check_in_record to get the generated ID
        db.refresh(check_in_record)
        
        # Store or update the RetellCall record if we have call_id and transcript
        if call_id and transcript:
            # Check if a RetellCall with this call_id already exists
            existing_retell_call = db.query(RetellCall).filter(RetellCall.call_id == call_id).first()
            
            if existing_retell_call:
                # Update existing RetellCall record
                existing_retell_call.check_in_id = check_in_record.id
                existing_retell_call.call_transcript = transcript
                db.commit()
                logger.info(f"Updated existing RetellCall: check_in_id={check_in_record.id}, call_id={call_id}")
            else:
                # Create new RetellCall record
                retell_call_record = RetellCall(
                    check_in_id=check_in_record.id,
                    call_id=call_id,
                    call_transcript=transcript
                )
                db.add(retell_call_record)
                db.commit()
                logger.info(f"Created new RetellCall: check_in_id={check_in_record.id}, call_id={call_id}")
        
        # Get stop information for the check-in
        stop = db.query(Stop).filter(Stop.id == stop_id).first()
        
        # Prepare check-in data for notification
        check_in_data = {
            'id': check_in_record.id,
            'stop_id': check_in_record.stop_id,
            'load_id': check_in_record.load_id,
            'query': check_in_record.query,
            'AI_Response_Summary': check_in_record.AI_Response_Summary,
            'AI_Timestamp': check_in_record.AI_Timestamp,
            'Issue_Flagged': check_in_record.Issue_Flagged,
            'Exception_Type': check_in_record.Exception_Type,
            'Call_confidence_score': check_in_record.Call_confidence_score,
            'Requires_Human_Review': check_in_record.Requires_Human_Review,
            'Tags': check_in_record.Tags,
            'stop_name': stop.name if stop else None,
            'stop_location': stop.location if stop else None,
            'stop_eta': stop.eta if stop else None,
            'call_id': call_id,
            'call_transcript': transcript
        }
        
        # Send notification about new check-in
        # Use asyncio.run to create a new event loop for the async operation
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(notify_check_in_update(check_in_data))
            loop.close()
        except Exception as e:
            logger.warning(f"Could not send notification: {e}")
            # Don't fail the request if notification fails
        
        logger.info(f"Stored check-in: stop_id={stop_id}, load_id={load_id}, summary='{chat_summary}', query='{query}', timestamp='{timestamp}', issue_flagged={issue_flagged}, exception_type='{exception_type}', confidence_score='{call_confidence_score}', requires_review={requires_human_review}, tags='{tags}', miles='{miles}'")
        
        return {
            'message': 'Check-in stored successfully',
            'check_in_id': check_in_record.id
        }
    
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Database error in update_checkIn: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Database error: {str(e)}")
    
    except Exception as e:
        logger.error(f"Unexpected error in update_checkIn: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Internal server error: {str(e)}")

@router.post("/webhook/call-ended")
async def retell_recording_webhook(request: dict = Body(...)):
    """Handle Retell webhook events, specifically call_ended events."""
    try:
        # logger.info(f"Received Retell webhook: {request}")
        
        # Check if this is a call_ended event
        if request.get("event") == "call_ended":
            call_data = request.get("call", {})
            
            # Extract call_id and recording_url
            call_id = call_data.get("call_id")
            recording_url = call_data.get("recording_url")
            
            logger.info(f"Call ended - Call ID: {call_id}, Recording URL: {recording_url}")
            
            # Find the RetellCall record with this call_id and update it
            if call_id:
                retell_call = db.query(RetellCall).filter(RetellCall.call_id == call_id).first()
                if retell_call:
                    retell_call.recording_url = recording_url
                    db.commit()
                    logger.info(f"Updated RetellCall with recording_url: {recording_url}")
                else:
                    logger.warning(f"No RetellCall found with call_id: {call_id}")
            
            return {"status": "success", "message": "Webhook processed successfully"}
        
        return {"status": "ignored", "message": "Not a call_ended event"}
        
    except Exception as e:
        logger.error(f"Error processing Retell webhook: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post('/check_in/set_metadata')
def set_metadata(request: dict = Body(...)):
    """Set the metadata for the check-in."""
    try:
        logger.info(f"Received in set_metadata: \n {request}")
        
        # Extract call_id and args from the request
        call_id = None
        args = None
        
        if isinstance(request, dict):
            # Extract call_id from the call object
            if 'call' in request and 'call_id' in request['call']:
                call_id = request['call']['call_id']
            
            # Extract args
            if 'args' in request:
                args = request['args']
        
        # If we have both call_id and args, update or create RetellCall record
        if call_id and args:
            retell_call = db.query(RetellCall).filter(RetellCall.call_id == call_id).first()
            if retell_call:
                # Update existing RetellCall with metadata
                retell_call.check_in_metadata = json.dumps(args)
                db.commit()
                logger.info(f"Updated existing RetellCall with metadata for call_id: {call_id}")
                return {"status": "success", "message": "Metadata updated in existing RetellCall record"}
            else:
                # Create new RetellCall record with metadata
                new_retell_call = RetellCall(
                    call_id=call_id,
                    check_in_metadata=json.dumps(args)
                )
                db.add(new_retell_call)
                db.commit()
                logger.info(f"Created new RetellCall with metadata for call_id: {call_id}")
                return {"status": "success", "message": "Metadata stored in new RetellCall record"}
        else:
            logger.warning(f"Missing call_id or args in request")
            return {"status": "warning", "message": "Missing call_id or args in request"}
            
    except Exception as e:
        logger.error(f"Error in set_metadata: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
