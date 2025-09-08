from fastapi import APIRouter, HTTPException, Body
from loguru import logger
from datetime import datetime, timedelta
import os
import json
from services.notification_service import notify_check_in_update
from services.supabase import supabase_service
import traceback

router = APIRouter(
    prefix="/retell",
    tags=["retell"],
    responses={404: {"description": "Not found"}},
)

INBOUND_CALL_AGENT_ID = os.getenv("INBOUND_CALL_AGENT_ID")

# Local DB removed; all persistence via Supabase

# In-memory storage for call resumption context
call_resumption_storage = {}


async def store_call_resumption_context(call_id: str, call_data: dict):
    """Store call context data for resumption when purpose_fulfilled is pending"""
    try:

        # Extract the caller's phone number from call data
        from_number = call_data.get("to_number", "")

        # Fetch call details from Supabase to get dynamic variables and metadata
        call_result = await supabase_service.get_retell_call_by_id(call_id)

        if not call_result["success"]:
            logger.warning(f"Could not fetch call details from Supabase for {call_id}: {call_result['error']}")
            # Fallback to using data from webhook
            dynamic_variables = call_data.get("retell_llm_dynamic_variables", {})
            metadata = call_data.get("metadata", {})
        else:
            # Extract dynamic variables and metadata from Supabase
            supabase_call_data = call_result["data"]
            output_data = supabase_call_data.get("output_data", {})

            # Get dynamic variables from output_data
            dynamic_variables = output_data.get("retell_llm_dynamic_variables", {})

            # Create metadata from dynamic variables (similar to retell_check_in.py)
            metadata = {
                "form_number": dynamic_variables.get("form_number"),
                "form_title": dynamic_variables.get("form_title"),
                "purpose": dynamic_variables.get("purpose"),
                "form": dynamic_variables.get("form"),
                "output_schema": dynamic_variables.get("output_schema")
            }

            logger.info(f"Fetched call details from Supabase for {call_id}: form_title={dynamic_variables.get('form_title')}")

        # Create resumption context
        resumption_context = {
            "call_id": call_id,
            "from_number": from_number,
            "dynamic_variables": dynamic_variables,
            "metadata": metadata,
            "timestamp": datetime.now().isoformat(),
            "status": "pending"
        }

        # Store in memory (keyed by normalized phone number)
        normalized_phone = normalize_phone_number(from_number)
        call_resumption_storage[normalized_phone] = resumption_context

        logger.info(f"Stored call resumption context for call {call_id} (phone: {normalized_phone})")
        logger.info(f"Resumption context stored: {json.dumps(resumption_context, indent=2)}")

    except Exception as e:
        logger.error(f"Error storing call resumption context: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")


async def cleanup_call_resumption_context(call_id: str):
    """Clean up stored call context when purpose_fulfilled is done"""
    try:
        # Find and remove from memory storage
        for phone_number, context in list(call_resumption_storage.items()):
            if context.get("call_id") == call_id:
                del call_resumption_storage[phone_number]
                logger.info(f"Cleaned up call resumption context for call {call_id} (phone: {phone_number})")
                break

    except Exception as e:
        logger.error(f"Error cleaning up call resumption context: {e}")


def normalize_phone_number(phone_number: str) -> str:
    """Normalize phone number for consistent matching"""
    if not phone_number:
        return ""

    # Remove all non-digit characters
    digits_only = ''.join(filter(str.isdigit, phone_number))

    # If it starts with 1 and has 11 digits, it's likely a US number with country code
    if len(digits_only) == 11 and digits_only.startswith('1'):
        return f"+{digits_only}"
    # If it has 10 digits, assume US number and add +1
    elif len(digits_only) == 10:
        return f"+1{digits_only}"
    # Otherwise, add + if not present
    elif digits_only and not phone_number.startswith('+'):
        return f"+{digits_only}"

    return phone_number


def cleanup_old_resumption_contexts():
    """Remove call resumption contexts older than 24 hours"""
    try:
        current_time = datetime.now()
        expired_phones = []

        for phone_number, context in call_resumption_storage.items():
            try:
                # Parse the stored timestamp
                context_timestamp = datetime.fromisoformat(context.get("timestamp", ""))

                # Calculate age of the context
                age = current_time - context_timestamp

                # If older than 24 hours, mark for removal
                if age > timedelta(hours=24):
                    expired_phones.append(phone_number)
                    logger.info(f"Context for {phone_number} is {age} old - marking for cleanup")

            except (ValueError, TypeError) as e:
                # If timestamp parsing fails, remove the context as it's invalid
                expired_phones.append(phone_number)
                logger.warning(f"Invalid timestamp for {phone_number}: {e} - marking for cleanup")

        # Remove expired contexts
        for phone_number in expired_phones:
            context = call_resumption_storage.pop(phone_number, {})
            call_id = context.get("call_id", "unknown")
            logger.info(f"Removed expired call resumption context for {phone_number} (call_id: {call_id})")

        if expired_phones:
            logger.info(f"Cleaned up {len(expired_phones)} expired call resumption contexts")

    except Exception as e:
        logger.error(f"Error during call resumption context cleanup: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")


@router.post("/webhook/call-ended")
async def retell_recording_webhook(request: dict = Body(...)):
    """Handle Retell webhook events, specifically call_ended and call_transferred events."""
    try:
        logger.info(f"Received Retell webhook: {request}")

        # Check if this is a call_started event (when user picks up the phone)
        if request.get("event") == "call_started":
            call_data = request.get("call", {})
            call_id = call_data.get("call_id")
            direction = call_data.get("direction")
            to_number = call_data.get("to_number", "")

            logger.info(f"Call started - Call ID: {call_id}, Direction: {direction}, To Number: {to_number}")

            # If this is an outbound call, remove any existing call resumption context for the number
            if direction == "outbound" and to_number:
                normalized_phone = normalize_phone_number(to_number)
                if normalized_phone in call_resumption_storage:
                    del call_resumption_storage[normalized_phone]
                    logger.info(f"Removed call resumption context for outbound call to {normalized_phone}")

            if call_id:
                # Find the retell call and get check_in_id
                try:
                    call_result = supabase_service.client.table("retell_calls").select("check_in_id").eq("call_id", call_id).execute()
                    if call_result.data:
                        check_in_id = call_result.data[0]["check_in_id"]

                        # Update check-in to mark user as picked up and set call status to in_progress
                        update_data = {
                            "user_picked_up": True,
                            "call_status": "in_progress"
                        }
                        await supabase_service.update_check_in(check_in_id, update_data)
                        logger.info(f"Marked check-in {check_in_id} as user picked up for call {call_id}")

                        # Get updated check-in data for WebSocket notification
                        updated_checkin_result = await supabase_service.get_check_in(check_in_id)
                        if updated_checkin_result["success"]:
                            updated_check_in_data = updated_checkin_result["data"]

                            # Send WebSocket notification for call start with updated data
                            websocket_check_in_data = {
                                'id': updated_check_in_data['id'],
                                'stop_id': updated_check_in_data.get('stop_id'),
                                'load_id': updated_check_in_data.get('load_id'),
                                'query': None,
                                'AI_Response_Summary': updated_check_in_data.get('ai_response_summary'),
                                'AI_Timestamp': updated_check_in_data.get('ai_timestamp'),
                                'Issue_Flagged': updated_check_in_data.get('issue_flagged', False),
                                'Exception_Type': updated_check_in_data.get('exception_type'),
                                'Call_confidence_score': updated_check_in_data.get('confidence_score'),
                                'call_trasfered': updated_check_in_data.get('call_status') == 'transferred',
                                'is_active': True,  # Call is now active
                                'Tags': updated_check_in_data.get('tags'),
                                'stop_name': None,
                                'stop_location': None,
                                'stop_eta': None,
                                'call_status': 'in_progress',
                                'user_picked_up': True  # Include this explicitly for dashboard
                            }
                            await notify_check_in_update(websocket_check_in_data)

                        # Create notification for call start/answered
                        notification_data = {
                            "message": f"Call started for check-in {check_in_id}",
                            "notification_type": "call_started",
                            "severity": "info",
                            "check_in_id": check_in_id,
                            "metadata": {"call_id": call_id}
                        }
                        await supabase_service.create_notification(notification_data)
                        logger.info(f"Sent call start notification for check-in {check_in_id}")
                except Exception as e:
                    logger.error(f"Error handling call start: {e}")

            return {"status": "success", "message": "Call start webhook processed successfully"}

        # Check if this is a call_ended event
        elif request.get("event") == "call_ended":
            call_data = request.get("call", {})

            # Extract call_id, recording_url, transcript, and disconnection_reason
            call_id = call_data.get("call_id")
            recording_url = call_data.get("recording_url")
            transcript = call_data.get("transcript")
            disconnection_reason = call_data.get("disconnection_reason")

            logger.info(f"Call ended - Call ID: {call_id}, Recording URL: {recording_url}, Disconnection Reason: {disconnection_reason}")

            if call_id:
                # Try to get existing retell call from Supabase
                try:
                    existing_call_result = supabase_service.client.table("retell_calls").select("*").eq("call_id", call_id).execute()
                    retell_call_data = existing_call_result.data[0] if existing_call_result.data else None
                except Exception:
                    retell_call_data = None

                check_in_id = None
                if retell_call_data:
                    # Update existing retell call
                    update_data = {}
                    if recording_url:
                        update_data["recording_url"] = recording_url
                    if transcript:
                        update_data["call_transcript"] = transcript

                    await supabase_service.update_retell_call(call_id, update_data)
                    check_in_id = retell_call_data.get("check_in_id")
                    logger.info(f"Updated existing retell call: {call_id}")
                else:
                    # Create new retell call
                    retell_call_data = {
                        "call_id": call_id,
                        "recording_url": recording_url,
                        "call_transcript": transcript
                    }
                    result = await supabase_service.create_retell_call(retell_call_data)
                    if result["success"]:
                        check_in_id = result["data"].get("check_in_id")
                        logger.info(f"Created new retell call: {call_id}")

                # Handle check-in updates if we have a check_in_id
                if check_in_id:
                    check_in_update = {}

                    # Check if call was transferred
                    if disconnection_reason == "call_transfer":
                        check_in_update["call_status"] = "transferred"
                        logger.info(f"Marked check-in {check_in_id} as transferred due to call_transfer disconnection")

                        # Update check-in and send notification
                        await supabase_service.update_check_in(check_in_id, check_in_update)

                        # Create notification for transfer
                        notification_data = {
                            "message": f"Call transferred for check-in {check_in_id}",
                            "notification_type": "call_transfer",
                            "severity": "info",
                            "check_in_id": check_in_id,
                            "metadata": {"call_id": call_id, "disconnection_reason": disconnection_reason}
                        }
                        await supabase_service.create_notification(notification_data)

                        # Send WebSocket notification for transfer
                        updated_checkin_result = await supabase_service.get_check_in(check_in_id)
                        if updated_checkin_result["success"]:
                            updated_check_in_data = updated_checkin_result["data"]
                            websocket_check_in_data = {
                                'id': updated_check_in_data['id'],
                                'stop_id': updated_check_in_data.get('stop_id'),
                                'load_id': updated_check_in_data.get('load_id'),
                                'query': None,
                                'AI_Response_Summary': updated_check_in_data.get('ai_response_summary'),
                                'AI_Timestamp': updated_check_in_data.get('ai_timestamp'),
                                'Issue_Flagged': updated_check_in_data.get('issue_flagged', False),
                                'Exception_Type': updated_check_in_data.get('exception_type'),
                                'Call_confidence_score': updated_check_in_data.get('confidence_score'),
                                'call_trasfered': True,  # Call was transferred
                                'is_active': False,
                                'Tags': updated_check_in_data.get('tags'),
                                'stop_name': None,
                                'stop_location': None,
                                'stop_eta': None,
                                'call_status': 'transferred'
                            }
                            await notify_check_in_update(websocket_check_in_data)
                            logger.info(f"Sent WebSocket check-in transfer notification for check-in {check_in_id}")

                        logger.info(f"Sent transfer notification for check-in {check_in_id}")
                        return {"status": "success", "message": "Call transfer webhook processed successfully"}

                    # Check if call reached voicemail
                    elif disconnection_reason == "voicemail_reached":
                        check_in_update["call_status"] = "voicemail"
                        check_in_update["user_picked_up"] = False
                        logger.info(f"Marked check-in {check_in_id} as voicemail - user did not pick up")

                        # Update check-in and send notification
                        await supabase_service.update_check_in(check_in_id, check_in_update)

                        # Create notification for voicemail
                        notification_data = {
                            "message": f"Call reached voicemail for check-in {check_in_id}",
                            "notification_type": "voicemail_reached",
                            "severity": "warning",
                            "check_in_id": check_in_id,
                            "metadata": {"call_id": call_id, "disconnection_reason": disconnection_reason}
                        }
                        await supabase_service.create_notification(notification_data)

                        # Send WebSocket notification for voicemail
                        updated_checkin_result = await supabase_service.get_check_in(check_in_id)
                        if updated_checkin_result["success"]:
                            updated_check_in_data = updated_checkin_result["data"]
                            websocket_check_in_data = {
                                'id': updated_check_in_data['id'],
                                'stop_id': updated_check_in_data.get('stop_id'),
                                'load_id': updated_check_in_data.get('load_id'),
                                'query': None,
                                'AI_Response_Summary': updated_check_in_data.get('ai_response_summary'),
                                'AI_Timestamp': updated_check_in_data.get('ai_timestamp'),
                                'Issue_Flagged': updated_check_in_data.get('issue_flagged', False),
                                'Exception_Type': updated_check_in_data.get('exception_type'),
                                'Call_confidence_score': updated_check_in_data.get('confidence_score'),
                                'call_trasfered': False,
                                'is_active': False,
                                'Tags': updated_check_in_data.get('tags'),
                                'stop_name': None,
                                'stop_location': None,
                                'stop_eta': None,
                                'call_status': 'voicemail',
                                'user_picked_up': False  # Explicitly show user didn't pick up
                            }
                            await notify_check_in_update(websocket_check_in_data)
                            logger.info(f"Sent WebSocket voicemail notification for check-in {check_in_id}")

                        logger.info(f"Sent voicemail notification for check-in {check_in_id}")
                        return {"status": "success", "message": "Voicemail webhook processed successfully"}
                    else:
                        # Mark as completed but wait for analysis
                        check_in_update["call_status"] = "completed"
                        await supabase_service.update_check_in(check_in_id, check_in_update)
                        logger.info(f"Marked check-in {check_in_id} as completed, waiting for analysis")

            return {"status": "success", "message": "Webhook processed successfully"}

        # Check if this is a call_transferred event
        elif request.get("event") == "call_transferred":
            call_data = request.get("call", {})
            call_id = call_data.get("call_id")

            logger.info(f"Call transferred - Call ID: {call_id}")

            if call_id:
                # Find the retell call and get check_in_id
                try:
                    call_result = supabase_service.client.table("retell_calls").select("check_in_id").eq("call_id", call_id).execute()
                    if call_result.data:
                        check_in_id = call_result.data[0]["check_in_id"]

                        # Update check-in as transferred
                        await supabase_service.update_check_in(check_in_id, {"call_status": "transferred"})
                        logger.info(f"Marked check-in {check_in_id} as transferred")

                        # Create notification for transfer
                        notification_data = {
                            "message": f"Call transferred for check-in {check_in_id}",
                            "notification_type": "call_transfer",
                            "severity": "info",
                            "check_in_id": check_in_id,
                            "metadata": {"call_id": call_id}
                        }
                        await supabase_service.create_notification(notification_data)

                        # Send WebSocket notification for transfer
                        updated_checkin_result = await supabase_service.get_check_in(check_in_id)
                        if updated_checkin_result["success"]:
                            updated_check_in_data = updated_checkin_result["data"]
                            websocket_check_in_data = {
                                'id': updated_check_in_data['id'],
                                'stop_id': updated_check_in_data.get('stop_id'),
                                'load_id': updated_check_in_data.get('load_id'),
                                'query': None,
                                'AI_Response_Summary': updated_check_in_data.get('ai_response_summary'),
                                'AI_Timestamp': updated_check_in_data.get('ai_timestamp'),
                                'Issue_Flagged': updated_check_in_data.get('issue_flagged', False),
                                'Exception_Type': updated_check_in_data.get('exception_type'),
                                'Call_confidence_score': updated_check_in_data.get('confidence_score'),
                                'call_trasfered': True,  # Call was transferred
                                'is_active': False,
                                'Tags': updated_check_in_data.get('tags'),
                                'stop_name': None,
                                'stop_location': None,
                                'stop_eta': None,
                                'call_status': 'transferred'
                            }
                            await notify_check_in_update(websocket_check_in_data)
                            logger.info(f"Sent WebSocket check-in transfer notification for check-in {check_in_id}")

                        logger.info(f"Sent transfer notification for check-in {check_in_id}")
                except Exception as e:
                    logger.error(f"Error handling call transfer: {e}")

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

            if call_id:
                # Extract custom_analysis_data
                custom_analysis_data = call_analysis.get("custom_analysis_data", {})

                check_in_id = None
                check_in_data = None

                # Try to find existing retell call and check-in
                try:
                    call_result = supabase_service.client.table("retell_calls").select("check_in_id").eq("call_id", call_id).execute()
                    if call_result.data:
                        check_in_id = call_result.data[0]["check_in_id"]

                        # Get the check-in data
                        if check_in_id:
                            checkin_result = await supabase_service.get_check_in(check_in_id)
                            if checkin_result["success"]:
                                check_in_data = checkin_result["data"]
                except Exception:
                    pass

                # If no check-in exists, create one from the form data
                if not check_in_id:
                    logger.info(f"Creating new check-in for call {call_id}")

                    # Extract metadata from retell_llm_dynamic_variables
                    load_id = None
                    forms_data = {}

                    if 'retell_llm_dynamic_variables' in call_data:
                        try:
                            dynamic_vars = call_data['retell_llm_dynamic_variables']

                            # Extract from form field if it's a JSON string
                            form_str = dynamic_vars.get('form', '{}')
                            if isinstance(form_str, str):
                                form_data = json.loads(form_str)
                            else:
                                form_data = form_str or {}

                            load_id = form_data.get('load_id')
                            forms_data = form_data

                        except Exception as e:
                            logger.warning(f"Could not parse form data from metadata: {e}")

                    # Create new check-in
                    new_check_in = {
                        "load_id": load_id,
                        "ai_timestamp": datetime.now().isoformat(),
                        "issue_flagged": False,
                        "call_status": "analyzed",
                        "forms": forms_data
                    }

                    result = await supabase_service.create_check_in(new_check_in)
                    if result["success"]:
                        check_in_id = result["data"]["id"]
                        check_in_data = result["data"]
                        logger.info(f"Created new check-in {check_in_id} for call {call_id}")

                        # Link the retell call to the check-in
                        retell_call_data = {
                            "call_id": call_id,
                            "check_in_id": check_in_id,
                            "recording_url": recording_url,
                            "call_transcript": transcript
                        }
                        await supabase_service.create_retell_call(retell_call_data)

                # Update check-in with analysis data
                if check_in_id and custom_analysis_data:
                    logger.info(f"Processing custom_analysis_data: {custom_analysis_data}")

                    update_data = {}

                    # Update CheckIn fields from custom_analysis_data
                    if 'issue_flagged' in custom_analysis_data:
                        update_data['issue_flagged'] = custom_analysis_data['issue_flagged']

                    if 'call_confidence_score' in custom_analysis_data:
                        update_data['Confidence_score'] = custom_analysis_data['call_confidence_score']

                    if 'exception_type' in custom_analysis_data:
                        exception_type = custom_analysis_data['exception_type']
                        if exception_type and exception_type != "N/A":
                            update_data['exception_type'] = exception_type

                    if 'tags' in custom_analysis_data:
                        tags = custom_analysis_data['tags']
                        if tags and tags != "N/A":
                            # Convert to list if it's a string
                            if isinstance(tags, str):
                                try:
                                    tags = json.loads(tags)
                                except Exception:
                                    tags = [tags]  # Make it a list
                            update_data['tags'] = tags

                    if '_a_i__response__summary' in custom_analysis_data:
                        update_data['AI_Response_Summary'] = custom_analysis_data['_a_i__response__summary']
                        update_data['ai_timestamp'] = datetime.now().isoformat()

                    # Mark as analyzed
                    update_data['call_status'] = 'analyzed'

                    # Update the check-in
                    result = await supabase_service.update_check_in(check_in_id, update_data)
                    if result["success"]:
                        logger.info(f"Updated check-in {check_in_id} with custom_analysis_data")

                        # Update retell call with output data
                        output_data = {
                            'custom_analysis_data': custom_analysis_data,
                            'retell_llm_dynamic_variables': call_data.get('retell_llm_dynamic_variables', {})
                        }

                        # Store the output field if present
                        if 'output' in custom_analysis_data:
                            output_data['output'] = custom_analysis_data['output']

                        await supabase_service.update_retell_call(call_id, {
                            "recording_url": recording_url,
                            "call_transcript": transcript,
                            "output_data": output_data
                        })

                        # Create notification for the analysis
                        has_meaningful_data = (
                            custom_analysis_data.get('_a_i__response__summary') or
                            custom_analysis_data.get('output') or
                            custom_analysis_data.get('call_confidence_score')
                        )

                        if has_meaningful_data:
                            # Store notification in database
                            notification_data = {
                                "message": f"Check-in {check_in_id} analysis completed",
                                "notification_type": "check_in_analyzed",
                                "severity": "high" if update_data.get('issue_flagged') else "info",
                                "check_in_id": check_in_id,
                                "metadata": {
                                    "call_id": call_id,
                                    "load_id": check_in_data.get('load_id') if check_in_data else None,
                                    "issue_flagged": update_data.get('issue_flagged', False),
                                    "confidence_score": update_data.get('confidence_score'),
                                    "has_recording": bool(recording_url),
                                    "has_transcript": bool(transcript)
                                }
                            }
                            await supabase_service.create_notification(notification_data)

                            # Send WebSocket notification to dashboard clients
                            # Get updated check-in data for the notification
                            updated_checkin_result = await supabase_service.get_check_in(check_in_id)
                            if updated_checkin_result["success"]:
                                updated_check_in_data = updated_checkin_result["data"]

                                # Format check-in data for WebSocket notification (compatible with dashboard)
                                websocket_check_in_data = {
                                    'id': updated_check_in_data['id'],
                                    'stop_id': updated_check_in_data.get('stop_id'),
                                    'load_id': updated_check_in_data.get('load_id'),
                                    'query': None,
                                    'AI_Response_Summary': updated_check_in_data.get('ai_response_summary'),
                                    'AI_Timestamp': updated_check_in_data.get('ai_timestamp'),
                                    'Issue_Flagged': updated_check_in_data.get('issue_flagged', False),
                                    'Exception_Type': updated_check_in_data.get('exception_type'),
                                    'Call_confidence_score': updated_check_in_data.get('confidence_score'),
                                    'call_trasfered': updated_check_in_data.get('call_status') == 'transferred',
                                    'is_active': False,  # Analysis is complete, so not active anymore
                                    'Tags': updated_check_in_data.get('tags'),
                                    'stop_name': None,
                                    'stop_location': None,
                                    'stop_eta': None,
                                    'call_status': updated_check_in_data.get('call_status')
                                }

                                # Send WebSocket broadcast to connected clients
                                await notify_check_in_update(websocket_check_in_data)
                                logger.info(f"Sent WebSocket check-in update notification for check-in {check_in_id}")

                            logger.info(f"Sent check-in analysis notification for call {call_id} with meaningful data")
                        else:
                            logger.info(f"Skipped notification for call {call_id} - no meaningful analysis data")

                # Check if purpose_fulfilled is pending - store call context for resumption
                purpose_fulfilled = custom_analysis_data.get("purpose_fulfilled")
                if purpose_fulfilled == "pending":
                    logger.info(f"Call {call_id} has pending purpose_fulfilled - storing context for call resumption")
                    await store_call_resumption_context(call_id, call_data)
                elif purpose_fulfilled == "done":
                    logger.info(f"Call {call_id} has completed purpose_fulfilled - cleaning up any stored context")
                    await cleanup_call_resumption_context(call_id)

            return {"status": "success", "message": "Call analyzed webhook processed successfully"}

        return {"status": "ignored", "message": "Not a supported webhook event"}
    except Exception as e:
        logger.error(f"Error processing Retell webhook: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/check-in/{check_in_id}/status")
async def get_check_in_status(check_in_id: int):
    """Get the status of a check-in call from Supabase."""
    try:
        checkin_result = await supabase_service.get_check_in(check_in_id)
        if not checkin_result["success"]:
            raise HTTPException(status_code=404, detail="Check-in not found")

        check_in = checkin_result["data"]
        call_id = check_in.get("call_id")
        retell_call = None
        if call_id:
            call_result = await supabase_service.get_retell_call_by_id(call_id)
            if call_result["success"]:
                retell_call = call_result["data"]

        has_data = bool(
            (retell_call and (retell_call.get("call_transcript") or retell_call.get("recording_url") or retell_call.get("output_data"))) or
            check_in.get("AI_Response_Summary")
        )

        call_status = check_in.get("call_status")
        if call_status == "completed" or has_data:
            return {
                "status": "completed",
                "message": "Call completed and data available",
                "has_transcript": bool(retell_call and retell_call.get("call_transcript")),
                "has_recording": bool(retell_call and retell_call.get("recording_url")),
                "has_summary": bool(check_in.get("AI_Response_Summary")),
                "has_metadata": bool(retell_call and retell_call.get("output_data")),
            }
        else:
            return {
                "status": "in_progress",
                "message": "Call in progress, waiting for data",
            }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting check-in status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/webhook/inbound")
async def retell_inbound_webhook(request: dict = Body(...)):
    """
    Handle Retell inbound call webhook for call resumption functionality.
    This webhook is called when someone calls your Retell phone number.

    Documentation: https://docs.retellai.com/features/inbound-call-webhook#inbound-call-webhook
    """
    try:
        logger.info(f"Received inbound call webhook payload: {json.dumps(request, indent=2)}")

        if not INBOUND_CALL_AGENT_ID:
            logger.error("INBOUND_CALL_AGENT_ID not found in environment variables")
            raise HTTPException(status_code=500, detail="Missing INBOUND_CALL_AGENT_ID configuration")

        # Extract the event type and call_inbound data according to Retell spec
        event = request.get("event")
        call_inbound_data = request.get("call_inbound", {})

        if event != "call_inbound":
            logger.warning(f"Unexpected event type: {event}")
            return {"error": "Invalid event type"}

        logger.info("Inbound call details:")
        logger.info(f"  - Agent ID: {call_inbound_data.get('agent_id')}")
        logger.info(f"  - From Number: {call_inbound_data.get('from_number', '')}")
        logger.info(f"  - To Number: {call_inbound_data.get('to_number', '')}")
        logger.info(f"  - Timestamp: {datetime.now().isoformat()}")

        # Normalize the incoming phone number for lookup
        normalized_phone = normalize_phone_number(call_inbound_data.get("from_number", ""))

        # Clean up contexts older than 24 hours before searching
        cleanup_old_resumption_contexts()

        # Search for existing call context in resumption storage
        resumption_context = call_resumption_storage.get(normalized_phone)

        if resumption_context:
            # Found existing context - prepare resumption response
            logger.info(f"Found call resumption context for {normalized_phone}")
            logger.info(f"Previous call ID: {resumption_context.get('call_id')}")

            # Extract dynamic variables and metadata from stored context
            dynamic_variables = resumption_context.get("dynamic_variables", {})
            metadata = resumption_context.get("metadata", {})

            # Remove the context from storage since it's being resumed
            del call_resumption_storage[normalized_phone]

            response = {
                "call_inbound": {
                    "override_agent_id": INBOUND_CALL_AGENT_ID,
                    "dynamic_variables": dynamic_variables,
                    "metadata": metadata
                }
            }
            logger.info(f"Resuming call for phone {normalized_phone}")
        else:
            # No existing context found - handle as new call
            logger.info(f"No call resumption context found for {normalized_phone} - processing as new call")

            response = {
                "call_inbound": {
                    "override_agent_id": INBOUND_CALL_AGENT_ID
                }
            }
        return response
    except Exception as e:
        logger.error(f"Error processing inbound call webhook: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")

        # Return a valid response even on error to avoid call rejection
        return {
            "call_inbound": {
                "override_agent_id": INBOUND_CALL_AGENT_ID
            }
        }
