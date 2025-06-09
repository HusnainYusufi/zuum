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
    """Update the checkIn by extracting chat_summary and other fields from the request."""
    try:
        logger.info(f"Received in update_checkIn: {request}")
        
        # Initialize variables with defaults
        check_in_data = {
            'stop_id': 1,  # Default to first stop
            'chat_summary': None,
            'query': None,
            'issue_flagged': False,
            'exception_type': None,
            'call_confidence_score': None,
            'requires_human_review': False,
            'tags': None,
            'load_id': None,
            'miles': None,
            'call_id': None
        }
        
        # Extract call_id from the call object if present
        if 'call' in request and 'call_id' in request['call']:
            check_in_data['call_id'] = request['call']['call_id']
            
            # Extract dynamic variables if present
            if 'retell_llm_dynamic_variables' in request['call']:
                dynamic_vars = request['call']['retell_llm_dynamic_variables']
                
                # Extract stop_id
                if 'stop_id' in dynamic_vars:
                    check_in_data['stop_id'] = int(dynamic_vars['stop_id'])
                elif 'id' in dynamic_vars:
                    check_in_data['stop_id'] = int(dynamic_vars['id'])
                
                # Extract other fields
                if 'query' in dynamic_vars:
                    check_in_data['query'] = dynamic_vars['query']
                if 'load_number' in dynamic_vars:
                    check_in_data['load_id'] = dynamic_vars['load_number']
                elif 'load_id' in dynamic_vars:
                    check_in_data['load_id'] = dynamic_vars['load_id']
                if 'miles' in dynamic_vars:
                    check_in_data['miles'] = dynamic_vars['miles']
        
        # Extract args - this is the main source of check-in data
        if 'args' in request and isinstance(request['args'], dict):
            args = request['args']
            
            # Map the args to our check_in_data
            check_in_data['chat_summary'] = args.get('chat_summary') or args.get('AI_Response_Summary')
            check_in_data['query'] = args.get('query', check_in_data['query'])
            check_in_data['stop_id'] = args.get('stop_id', check_in_data['stop_id'])
            check_in_data['issue_flagged'] = args.get('issue_flagged', False)
            check_in_data['exception_type'] = args.get('exception_type')
            check_in_data['call_confidence_score'] = args.get('call_confidence_score')
            check_in_data['requires_human_review'] = args.get('requires_human_review', False)
            check_in_data['tags'] = args.get('tags')
            check_in_data['load_id'] = args.get('load_id') or args.get('load_number', check_in_data['load_id'])
            check_in_data['miles'] = args.get('miles', check_in_data['miles'])
        
        # Create timestamp
        timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        
        # Create new CheckIn record
        check_in_record = CheckIn(
            stop_id=check_in_data['stop_id'],
            load_id=check_in_data['load_id'],
            query=check_in_data['query'],
            AI_Response_Summary=check_in_data['chat_summary'],
            AI_Timestamp=timestamp,
            Issue_Flagged=check_in_data['issue_flagged'],
            Exception_Type=check_in_data['exception_type'],
            Call_confidence_score=check_in_data['call_confidence_score'],
            Requires_Human_Review=check_in_data['requires_human_review'],
            Tags=check_in_data['tags'],
            miles=check_in_data['miles']
        )
        
        db.add(check_in_record)
        db.commit()
        db.refresh(check_in_record)
        
        # Link with RetellCall if call_id exists
        if check_in_data['call_id']:
            link_checkin_to_retell_call(check_in_record.id, check_in_data['call_id'])
        
        # Send notification
        send_checkin_notification(check_in_record, check_in_data['stop_id'])
        
        logger.info(f"Stored check-in #{check_in_record.id} for stop {check_in_data['stop_id']}")
        
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


def link_checkin_to_retell_call(check_in_id: int, call_id: str):
    """Link a check-in to a RetellCall record"""
    try:
        existing_retell_call = db.query(RetellCall).filter(RetellCall.call_id == call_id).first()
        
        if existing_retell_call:
            existing_retell_call.check_in_id = check_in_id
            db.commit()
            logger.info(f"Updated RetellCall with check_in_id: {check_in_id}")
        else:
            # Create new RetellCall record
            retell_call_record = RetellCall(
                check_in_id=check_in_id,
                call_id=call_id
            )
            db.add(retell_call_record)
            db.commit()
            logger.info(f"Created new RetellCall for check_in_id: {check_in_id}, call_id: {call_id}")
    except Exception as e:
        logger.error(f"Error linking check-in to RetellCall: {e}")


def send_checkin_notification(check_in_record: CheckIn, stop_id: int):
    """Send notification about new check-in"""
    try:
        # Get stop information
        stop = db.query(Stop).filter(Stop.id == stop_id).first()
        
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
            'Requires_Human_Review': check_in_record.Requires_Human_Review,
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

@router.post("/webhook/call-ended")
async def retell_recording_webhook(request: dict = Body(...)):
    """Handle Retell webhook events, specifically call_ended events."""
    try:
        logger.info(f"Received Retell webhook: {request}")
        
        # Check if this is a call_ended event
        if request.get("event") == "call_ended":
            call_data = request.get("call", {})
            
            # Extract call_id, recording_url, and transcript
            call_id = call_data.get("call_id")
            recording_url = call_data.get("recording_url")
            transcript = call_data.get("transcript")
            
            logger.info(f"Call ended - Call ID: {call_id}, Recording URL: {recording_url}")
            
            # Find the RetellCall record with this call_id and update it
            if call_id:
                retell_call = db.query(RetellCall).filter(RetellCall.call_id == call_id).first()
                if retell_call:
                    # Update with recording URL and transcript
                    retell_call.recording_url = recording_url
                    if transcript:
                        retell_call.call_transcript = transcript
                    db.commit()
                    logger.info(f"Updated RetellCall with recording_url and transcript")
                else:
                    # Create new RetellCall record if it doesn't exist
                    new_retell_call = RetellCall(
                        call_id=call_id,
                        recording_url=recording_url,
                        call_transcript=transcript
                    )
                    db.add(new_retell_call)
                    db.commit()
                    logger.info(f"Created new RetellCall with call_id: {call_id}")
            
            return {"status": "success", "message": "Webhook processed successfully"}
        
        # Check if this is a call_analyzed event
        elif request.get("event") == "call_analyzed":
            call_data = request.get("call", {})
            
            # Extract call_id, recording_url, and transcript
            call_id = call_data.get("call_id")
            recording_url = call_data.get("recording_url")
            transcript = call_data.get("transcript")
            
            logger.info(f"Call analyzed - Call ID: {call_id}, Recording URL: {recording_url}")
            
            # Find the RetellCall record with this call_id and update it
            if call_id:
                retell_call = db.query(RetellCall).filter(RetellCall.call_id == call_id).first()
                if retell_call:
                    # Update with recording URL and transcript
                    if recording_url:
                        retell_call.recording_url = recording_url
                    if transcript:
                        retell_call.call_transcript = transcript
                    db.commit()
                    logger.info(f"Updated RetellCall with recording_url and transcript from call_analyzed")
                else:
                    # Create new RetellCall record if it doesn't exist
                    new_retell_call = RetellCall(
                        call_id=call_id,
                        recording_url=recording_url,
                        call_transcript=transcript
                    )
                    db.add(new_retell_call)
                    db.commit()
                    logger.info(f"Created new RetellCall from call_analyzed with call_id: {call_id}")
            
            return {"status": "success", "message": "Call analyzed webhook processed successfully"}
        
        return {"status": "ignored", "message": "Not a call_ended or call_analyzed event"}
        
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
