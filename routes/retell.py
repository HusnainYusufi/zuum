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



def send_checkin_notification(check_in_record: CheckIn, stop_id: int, db_session: Session = None):
    """Send notification about new check-in"""
    try:
        # Get stop information
        stop = None
        if db_session:
            stop = db_session.query(Stop).filter(Stop.id == stop_id).first()
        
        # Prepare notification data
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
            'call_trasfered': check_in_record.call_trasfered,
            'is_active': check_in_record.is_active,
            'Tags': check_in_record.Tags,
            'stop_name': stop.name if stop else None,
            'stop_location': stop.location if stop else None,
            'stop_eta': stop.eta if stop else None
        }
        
        # Send notification
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(notify_check_in_update(check_in_data))
        loop.close()
    except Exception as e:
        logger.warning(f"Could not send notification: {e}")
        # Don't fail the request if notification fails



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





@router.post("/webhook/call-ended")
async def retell_recording_webhook(request: dict = Body(...)):
    """Handle Retell webhook events, specifically call_ended and call_transferred events."""
    try:
        logger.info(f"Received Retell webhook: {request}")
        
        # Check if this is a call_ended event
        if request.get("event") == "call_ended":
            call_data = request.get("call", {})
            
            # Extract call_id, recording_url, transcript, and disconnection_reason
            call_id = call_data.get("call_id")
            recording_url = call_data.get("recording_url")
            transcript = call_data.get("transcript")
            disconnection_reason = call_data.get("disconnection_reason")
            
            logger.info(f"Call ended - Call ID: {call_id}, Recording URL: {recording_url}, Disconnection Reason: {disconnection_reason}")
            
            # Find the RetellCall record with this call_id and update it
            retell_call = None
            check_in = None
            
            if call_id:
                retell_call = db.query(RetellCall).filter(RetellCall.call_id == call_id).first()
                if retell_call:
                    # Update with recording URL and transcript
                    retell_call.recording_url = recording_url
                    if transcript:
                        retell_call.call_transcript = transcript
                    retell_call.call_status = "completed"
                    
                    # Get associated check-in if it exists
                    if retell_call.check_in_id:
                        check_in = db.query(CheckIn).filter(CheckIn.id == retell_call.check_in_id).first()
                    
                    logger.info(f"Updated RetellCall with recording_url and transcript")
                else:
                    # Create new RetellCall record if it doesn't exist
                    retell_call = RetellCall(
                        call_id=call_id,
                        recording_url=recording_url,
                        call_transcript=transcript,
                        call_status="completed"
                    )
                    db.add(retell_call)
                    logger.info(f"Created new RetellCall with call_id: {call_id}")
                
                # Check if call was transferred and update check-in accordingly
                if disconnection_reason == "call_transfer" and check_in:
                    check_in.call_trasfered = True
                    logger.info(f"Marked check-in {check_in.id} as transferred due to call_transfer disconnection")
                    
                    # Don't send notification here - wait for call_analyzed event
                
                # Mark check-in as inactive since call has ended
                if check_in:
                    check_in.is_active = False
                    logger.info(f"Marked check-in {check_in.id} as inactive since call ended")
                    
                    # Don't send notification here - wait for call_analyzed event
                
                db.commit()
            
            return {"status": "success", "message": "Webhook processed successfully"}
        
        # Check if this is a call_transferred event
        elif request.get("event") == "call_transferred":
            call_data = request.get("call", {})
            call_id = call_data.get("call_id")
            
            logger.info(f"Call transferred - Call ID: {call_id}")
            
            # Find the RetellCall and associated CheckIn
            if call_id:
                retell_call = db.query(RetellCall).filter(RetellCall.call_id == call_id).first()
                if retell_call and retell_call.check_in_id:
                    check_in = db.query(CheckIn).filter(CheckIn.id == retell_call.check_in_id).first()
                    if check_in:
                        # Mark the check-in as transferred
                        check_in.call_trasfered = True
                        db.commit()
                        logger.info(f"Marked check-in {check_in.id} as transferred")
                        
                        # Don't send notification here - wait for call_analyzed event
            
            return {"status": "success", "message": "Call transfer webhook processed successfully"}
        
        # Check if this is a call_analyzed event
        elif request.get("event") == "call_analyzed":
            call_data = request.get("call", {})
            
            # Extract call_id, recording_url, transcript, and call_analysis
            call_id = call_data.get("call_id")
            recording_url = call_data.get("recording_url")
            transcript = call_data.get("transcript")
            call_analysis = call_data.get("call_analysis", {})
            
            logger.info(f"Call analyzed - Call ID: {call_id}, Recording URL: {recording_url}")
            
            # Find the RetellCall record with this call_id and update it
            retell_call = None
            check_in = None
            
            if call_id:
                retell_call = db.query(RetellCall).filter(RetellCall.call_id == call_id).first()
                
                if retell_call:
                    # Update with recording URL and transcript
                    if recording_url:
                        retell_call.recording_url = recording_url
                    if transcript:
                        retell_call.call_transcript = transcript
                    retell_call.call_status = "completed"
                    
                    # Get associated check-in if it exists
                    if retell_call.check_in_id:
                        check_in = db.query(CheckIn).filter(CheckIn.id == retell_call.check_in_id).first()
                    
                    logger.info(f"Updated RetellCall with recording_url and transcript from call_analyzed")
                else:
                    # Create new RetellCall record if it doesn't exist
                    retell_call = RetellCall(
                        call_id=call_id,
                        recording_url=recording_url,
                        call_transcript=transcript,
                        call_status="completed"
                    )
                    db.add(retell_call)
                    db.flush()  # Get the ID
                    logger.info(f"Created new RetellCall from call_analyzed with call_id: {call_id}")
                
                # Extract and store custom_analysis_data
                custom_analysis_data = call_analysis.get("custom_analysis_data", {})
                logger.info(f"Call analysis data: {call_analysis}")
                if custom_analysis_data:
                    logger.info(f"Processing custom_analysis_data: {custom_analysis_data}")
                    
                                        # If no check-in exists, create one
                    if not check_in:
                        check_in = CheckIn(
                            AI_Timestamp=datetime.now().isoformat(),
                            Issue_Flagged=False,
                            call_trasfered=False,
                            is_active=False  # Set to False since call is analyzed and complete
                        )
                        db.add(check_in)
                        db.flush()  # Get the check_in ID
                        
                        # Link the RetellCall to the CheckIn
                        retell_call.check_in_id = check_in.id
                    
                    # Extract load_id and stop_id from retell_llm_dynamic_variables if available (for both new and existing check-ins)
                    if 'retell_llm_dynamic_variables' in call_data:
                        try:
                            # Extract from form field if it's a JSON string
                            form_str = call_data['retell_llm_dynamic_variables'].get('form', '{}')
                            if isinstance(form_str, str):
                                form_data = json.loads(form_str)
                            else:
                                form_data = form_str or {}
                            
                            if 'load_id' in form_data and not check_in.load_id:
                                check_in.load_id = form_data['load_id']
                            
                            # Also check for stop_id directly in retell_llm_dynamic_variables
                            dynamic_vars = call_data['retell_llm_dynamic_variables']
                            if 'stop_id' in dynamic_vars and not check_in.stop_id:
                                check_in.stop_id = int(dynamic_vars['stop_id'])
                            elif 'id' in dynamic_vars and not check_in.stop_id:
                                check_in.stop_id = int(dynamic_vars['id'])
                        except Exception as e:
                            logger.warning(f"Could not parse form data from metadata: {e}")
                    
                    # Update CheckIn fields from custom_analysis_data
                    if 'issue_flagged' in custom_analysis_data:
                        check_in.Issue_Flagged = custom_analysis_data['issue_flagged']
                    
                    if 'call_confidence_score' in custom_analysis_data:
                        check_in.Call_confidence_score = custom_analysis_data['call_confidence_score']
                    
                    if 'exception_type' in custom_analysis_data:
                        exception_type = custom_analysis_data['exception_type']
                        # Only store if it's not "N/A" or empty
                        if exception_type and exception_type != "N/A":
                            check_in.Exception_Type = exception_type
                    
                    if 'tags' in custom_analysis_data:
                        tags = custom_analysis_data['tags']
                        # Only store if it's not "N/A" or empty
                        if tags and tags != "N/A":
                            check_in.Tags = tags
                    
                    if '_a_i__response__summary' in custom_analysis_data:
                        check_in.AI_Response_Summary = custom_analysis_data['_a_i__response__summary']
                        check_in.AI_Timestamp = datetime.now().isoformat()
                    
                    # Store the output field and other custom data in metadata
                    check_in_metadata = {}
                    if retell_call.check_in_metadata:
                        try:
                            check_in_metadata = json.loads(retell_call.check_in_metadata)
                        except json.JSONDecodeError:
                            pass
                    
                    # Store the entire custom_analysis_data in metadata
                    check_in_metadata['custom_analysis_data'] = custom_analysis_data
                    
                    # If there's an output field, validate and store it separately for easier access
                    if 'output' in custom_analysis_data:
                        output_data = custom_analysis_data['output']
                        
                        # Try to parse the output to validate it's actual data, not schema
                        try:
                            if isinstance(output_data, str):
                                parsed_output = json.loads(output_data)
                            else:
                                parsed_output = output_data
                            
                            # Check if this is a schema definition (has 'type', 'properties', etc.)
                            if isinstance(parsed_output, dict) and 'type' in parsed_output and 'properties' in parsed_output:
                                logger.warning(f"Output field contains schema definition instead of extracted data for call {call_id}")
                                # Store it anyway for debugging, but mark it as schema
                                check_in_metadata['output_schema_received'] = output_data
                            else:
                                # This appears to be actual extracted data
                                check_in_metadata['output'] = output_data
                                logger.info(f"Stored extracted output data for call {call_id}: {parsed_output}")
                        except json.JSONDecodeError as e:
                            # If we can't parse it, store it as-is but log the issue
                            logger.warning(f"Could not parse output data for call {call_id}: {e}")
                            check_in_metadata['output'] = output_data
                    
                    retell_call.check_in_metadata = json.dumps(check_in_metadata)
                    
                    # Mark check-in as inactive since analysis is complete
                    check_in.is_active = False
                    
                    logger.info(f"Updated check-in {check_in.id} with custom_analysis_data")
                
                # Store retell_llm_dynamic_variables in metadata if not already stored
                if 'retell_llm_dynamic_variables' in call_data:
                    existing_metadata = {}
                    if retell_call.check_in_metadata:
                        try:
                            existing_metadata = json.loads(retell_call.check_in_metadata)
                        except json.JSONDecodeError:
                            pass
                    
                    if 'retell_llm_dynamic_variables' not in existing_metadata:
                        existing_metadata['retell_llm_dynamic_variables'] = call_data['retell_llm_dynamic_variables']
                        retell_call.check_in_metadata = json.dumps(existing_metadata)
                
                db.commit()
                
                # Send notification about the check-in update only after analysis is complete with meaningful data
                if check_in and check_in.stop_id and custom_analysis_data:
                    # Only send notification if we have substantial analysis data
                    has_meaningful_data = (
                        custom_analysis_data.get('_a_i__response__summary') or 
                        custom_analysis_data.get('output') or
                        custom_analysis_data.get('call_confidence_score')
                    )
                    
                    if has_meaningful_data:
                        send_checkin_notification(check_in, check_in.stop_id, db)
                        logger.info(f"Sent check-in notification for analyzed call {call_id} with meaningful data")
                    else:
                        logger.info(f"Skipped notification for call {call_id} - no meaningful analysis data")
            
            return {"status": "success", "message": "Call analyzed webhook processed successfully"}
        
        return {"status": "ignored", "message": "Not a supported webhook event"}
        
    except Exception as e:
        logger.error(f"Error processing Retell webhook: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/check-in/{check_in_id}/status")
def get_check_in_status(check_in_id: int):
    """Get the status of a check-in call."""
    try:
        # Get the check-in
        check_in = db.query(CheckIn).filter(CheckIn.id == check_in_id).first()
        if not check_in:
            raise HTTPException(status_code=404, detail="Check-in not found")
        
        # Get the associated retell call
        retell_call = db.query(RetellCall).filter(RetellCall.check_in_id == check_in_id).first()
        
        if not retell_call:
            return {
                "status": "no_call",
                "message": "No call associated with this check-in"
            }
        
        # Check if call has data (transcript, recording, metadata)
        has_data = bool(
            retell_call.call_transcript or 
            retell_call.recording_url or 
            retell_call.check_in_metadata or
            check_in.AI_Response_Summary
        )
        
        if retell_call.call_status == "completed" or has_data:
            return {
                "status": "completed",
                "message": "Call completed and data available",
                "has_transcript": bool(retell_call.call_transcript),
                "has_recording": bool(retell_call.recording_url),
                "has_summary": bool(check_in.AI_Response_Summary),
                "has_metadata": bool(retell_call.check_in_metadata)
            }
        else:
            return {
                "status": "in_progress",
                "message": "Call in progress, waiting for data"
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting check-in status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# @router.post("/update_checkIn")
# def check_in(request: dict = Body(...)):
#     """Update an existing checkIn by extracting chat_summary and other fields from the request."""
#     try:
#         logger.info(f"Received in update_checkIn: {request}")
        
#         # Initialize variables with defaults
#         check_in_data = {
#             'chat_summary': None,
#             'query': None,
#             'issue_flagged': False,
#             'exception_type': None,
#             'call_confidence_score': None,
#             'requires_human_review': False,
#             'tags': None,
#             'miles': None,
#             'call_id': None
#         }
        
#         # Extract call_id from the call object if present
#         if 'call' in request and 'call_id' in request['call']:
#             check_in_data['call_id'] = request['call']['call_id']
            
#             # Extract dynamic variables if present
#             if 'retell_llm_dynamic_variables' in request['call']:
#                 dynamic_vars = request['call']['retell_llm_dynamic_variables']
                
#                 # Extract other fields
#                 if 'query' in dynamic_vars:
#                     check_in_data['query'] = dynamic_vars['query']
#                 if 'miles' in dynamic_vars:
#                     check_in_data['miles'] = dynamic_vars['miles']
        
#         # Extract args - this is the main source of check-in data
#         if 'args' in request and isinstance(request['args'], dict):
#             args = request['args']
            
#             # Map the args to our check_in_data
#             check_in_data['chat_summary'] = args.get('chat_summary') or args.get('AI_Response_Summary')
#             check_in_data['query'] = args.get('query', check_in_data['query'])
#             check_in_data['issue_flagged'] = args.get('issue_flagged', False)
#             check_in_data['exception_type'] = args.get('exception_type')
#             check_in_data['call_confidence_score'] = args.get('call_confidence_score')
#             check_in_data['requires_human_review'] = args.get('requires_human_review', False)
#             check_in_data['tags'] = args.get('tags')
#             check_in_data['miles'] = args.get('miles', check_in_data['miles'])
        
#         # Find existing CheckIn record by call_id
#         if not check_in_data['call_id']:
#             raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="call_id is required to update check-in")
        
#         # Find the RetellCall record to get the check_in_id
#         retell_call = db.query(RetellCall).filter(RetellCall.call_id == check_in_data['call_id']).first()
#         if not retell_call or not retell_call.check_in_id:
#             raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No existing check-in found for this call_id")
        
#         # Find and update the existing CheckIn record
#         check_in_record = db.query(CheckIn).filter(CheckIn.id == retell_call.check_in_id).first()
#         if not check_in_record:
#             raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Check-in record not found")
        
#         # Create timestamp for AI response
#         timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        
#         # Update the existing CheckIn record with non-null values
#         if check_in_data['query'] is not None:
#             check_in_record.query = check_in_data['query']
#         if check_in_data['chat_summary'] is not None:
#             check_in_record.AI_Response_Summary = check_in_data['chat_summary']
#             check_in_record.AI_Timestamp = timestamp  # Update timestamp when AI response is provided
#         if check_in_data['exception_type'] is not None:
#             check_in_record.Exception_Type = check_in_data['exception_type']
#         if check_in_data['call_confidence_score'] is not None:
#             check_in_record.Call_confidence_score = check_in_data['call_confidence_score']
#         if check_in_data['tags'] is not None:
#             check_in_record.Tags = check_in_data['tags']
#         if check_in_data['miles'] is not None:
#             check_in_record.miles = check_in_data['miles']
        
#         # Always update these boolean fields
#         check_in_record.Issue_Flagged = check_in_data['issue_flagged']
#         check_in_record.Requires_Human_Review = check_in_data['requires_human_review']
        
#         db.commit()
#         db.refresh(check_in_record)
        
#         # Send notification
#         send_checkin_notification(check_in_record, check_in_record.stop_id)
        
#         logger.info(f"Updated check-in #{check_in_record.id} for call_id {check_in_data['call_id']}")
        
#         return {
#             'message': 'Check-in updated successfully',
#             'check_in_id': check_in_record.id
#         }
    
#     except HTTPException:
#         # Re-raise HTTPExceptions
#         raise
    
#     except SQLAlchemyError as e:
#         db.rollback()
#         logger.error(f"Database error in update_checkIn: {str(e)}")
#         raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Database error: {str(e)}")
    
#     except Exception as e:
#         logger.error(f"Unexpected error in update_checkIn: {str(e)}")
#         raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Internal server error: {str(e)}")



# @router.post('/check_in/set_metadata')
# def set_metadata(request: dict = Body(...)):
#     """Set the metadata for the check-in."""
#     try:
#         logger.info(f"Received in set_metadata: \n {request}")
        
#         # Extract call_id and args from the request
#         call_id = None
#         args = None
        
#         if isinstance(request, dict):
#             # Extract call_id from the call object
#             if 'call' in request and 'call_id' in request['call']:
#                 call_id = request['call']['call_id']
            
#             # Extract args
#             if 'args' in request:
#                 args = request['args']
        
#         # If we have both call_id and args, update or create RetellCall record
#         if call_id and args:
#             retell_call = db.query(RetellCall).filter(RetellCall.call_id == call_id).first()
#             if retell_call:
#                 # Update existing RetellCall with metadata
#                 retell_call.check_in_metadata = json.dumps(args)
#                 db.commit()
#                 logger.info(f"Updated existing RetellCall with metadata for call_id: {call_id}")
#                 return {"status": "success", "message": "Metadata updated in existing RetellCall record"}
#             else:
#                 # Create new RetellCall record with metadata
#                 new_retell_call = RetellCall(
#                     call_id=call_id,
#                     check_in_metadata=json.dumps(args)
#                 )
#                 db.add(new_retell_call)
#                 db.commit()
#                 logger.info(f"Created new RetellCall with metadata for call_id: {call_id}")
#                 return {"status": "success", "message": "Metadata stored in new RetellCall record"}
#         else:
#             logger.warning(f"Missing call_id or args in request")
#             return {"status": "warning", "message": "Missing call_id or args in request"}
            
#     except Exception as e:
#         logger.error(f"Error in set_metadata: {str(e)}")
#         raise HTTPException(status_code=500, detail=str(e))
