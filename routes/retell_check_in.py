from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from typing import Optional
from datetime import datetime
import os
import httpx
from dotenv import load_dotenv
import json
from services.prompt_config.prompt_config import (
    prompt_config,
    FORM_TYPE_DEFAULT,
    FORM_TYPE_AT_PICKUP,
    FORM_TYPE_PICKUP_COMPLETE,
    FORM_TYPE_IN_TRANSIT,
    FORM_TYPE_AT_DROP,
    FORM_TYPE_DELIVERED,
    FORM_TYPE_REQUEST_POD
)
import logging

# Replace old database imports with new Supabase service
from services.supabase import supabase_service
from services.notification_service import notify_check_in_update

# Load environment variables
load_dotenv()

router = APIRouter(
    prefix="/API",
    tags=["API"]
)

# Initialize templates
templates = Jinja2Templates(directory="templates")

# Get environment variables
RETELL_API_KEY = os.getenv("RETELL_API_KEY")
FROM_PHONE_NUMBER = os.getenv("RETELL_FROM_NUMBER")
AGENT_ID = os.getenv("CheckIn_RETELL_AGENT_ID")
BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")

# Retell API endpoint
RETELL_API_URL = "https://api.retellai.com/v2/create-phone-call"

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Silence noisy HTTP libraries if you want to use DEBUG level
# Uncomment these lines if you change back to DEBUG level:
logging.getLogger('httpx').setLevel(logging.WARNING)
logging.getLogger('httpcore').setLevel(logging.WARNING)
logging.getLogger('h11').setLevel(logging.WARNING)
logging.getLogger('h2').setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

def normalize_phone_number(country_code: str, contact_phone: str) -> str:
    """
    Normalize phone number by combining country code and cleaning the phone number.

    Args:
        country_code: The country code (e.g., "+1")
        contact_phone: The phone number to normalize

    Returns:
        Normalized phone number in E.164 format
    """
    return country_code + contact_phone.lstrip('0').replace('-', '').replace(' ', '').replace('(', '').replace(')', '')


async def make_retell_call(contact_phone: str, form_type: str, form_data: dict):
    """
    Reusable function to make Retell API calls

    Args:
        contact_phone: Phone number to call
        form_type: Type of form (at_pickup, pickup_complete, etc.)
        form_data: Dictionary containing all form field values

    Returns:
        Dictionary with status and response data
    """
    # Validate environment variables
    if not all([RETELL_API_KEY, FROM_PHONE_NUMBER, AGENT_ID]):
        return {
            "status": "error",
            "message": "Missing configuration. Please check environment variables."
        }

    # Format phone number to E.164 format if needed
    to_number = contact_phone

    # Get all form configuration data in one efficient call
    form_config = prompt_config.get_form_config(form_type)
    form_number = prompt_config.FORM_TYPE_MAPPING.get(form_type, 0)

    # Extract transfer call number from form data (simplified)
    transfer_call = form_data.get("transfer_call_to")

    # Prepare call data (no duplication, no unnecessary JSON conversion)
    call_data = {
        "form_number": str(form_number),
        "form_title": form_config.get("title", ""),
        "purpose": json.dumps(form_config.get("voice_questions", [])),  # Stringify voice questions array
        "form": json.dumps(form_data),  # Stringify form data dictionary
        "output_schema": json.dumps(form_config.get("output_schema", {}))  # Stringify output schema dictionary
    }

    # Add transfer call if present
    if transfer_call:
        call_data["transfer_call_to"] = transfer_call
        logger.info(f"Transfer call number included: {transfer_call}")

    logger.info(f"Retell call data: {json.dumps(call_data, indent=2, default=str)}")

    # Make the Retell API call
    headers = {
        "Authorization": f"Bearer {RETELL_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "from_number": FROM_PHONE_NUMBER,
        "to_number": to_number,
        "override_agent_id": AGENT_ID,
        "metadata": call_data,
        "retell_llm_dynamic_variables": call_data  # Same data, no duplication
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                RETELL_API_URL,
                headers=headers,
                json=payload
            )
            if response.status_code == 201:
                call_data = response.json()
                call_id = call_data.get("call_id")

                # Extract load_id from form_data - handle different field names
                load_id = (form_data.get("load_id") or
                    form_data.get("pickup_load_id") or
                    form_data.get("pc_load_id") or
                    form_data.get("it_load_id") or
                    form_data.get("ad_load_id") or
                    form_data.get("del_load_id") or
                    form_data.get("pod_load_id")
                        )

                # Create check-in entry
                checkin_result = await create_checkin_entry(call_id, load_id, form_type, form_data)

                return {
                    "status": "success",
                    "call_id": call_id,
                    "message": f"Call initiated successfully to {contact_phone}",
                    "form_type": form_type,
                    "load_id": load_id,
                    "transfer_call": transfer_call,
                    "output_schema_properties": len(form_config.get('output_schema', {}).get('properties', {})) if form_config.get('output_schema') else 0,
                    "checkin_link": checkin_result.get("checkin_page_link") if checkin_result.get("status") == "success" else None,
                    "checkin_id": checkin_result.get("checkin_id") if checkin_result.get("status") == "success" else None,
                    "form_data_stored": checkin_result.get("form_data_stored", False) if checkin_result.get("status") == "success" else False
                }
            else:
                error_detail = response.json() if response.content else "Unknown error"
                return {
                    "status": "error",
                    "message": f"Failed to initiate call: {response.status_code} - {error_detail}"
                }

    except Exception as e:
        return {
            "status": "error",
            "message": f"Error making API call: {str(e)}"
        }


async def create_checkin_entry(call_id: str, load_id: str, form_type: str, form_data: dict = None):
    """
    Create a check-in entry using Supabase service with associated RetellCall.

    Args:
        call_id: The Retell call ID
        load_id: The load ID from the form
        form_type: The type of form being submitted
        form_data: Optional form data dictionary
    """
    try:
        # Use the shared mapping from prompt_config instead of duplicating it
        stop_id = prompt_config.FORM_TYPE_MAPPING.get(form_type, 0)

        # Prepare check-in data for Supabase
        check_in_data = {
            "load_id": load_id,
            "form_type": form_type,
            "AI_Response_Summary": None,
            "AI_Timestamp": datetime.now().isoformat(),
            "Issue_Flagged": False,
            "Exception_Type": None,
            "Confidence_score": None,
            "forms": form_data or {},
            "call_status": "in_progress",
            "tags": [form_type] if form_type else [],
            "user_picked_up": False
        }

        # Create check-in using Supabase service
        checkin_result = await supabase_service.create_check_in(check_in_data)

        if not checkin_result["success"]:
            logger.error(f"Failed to create check-in: {checkin_result['error']}")
            return {
                "status": "error",
                "message": f"Error creating check-in: {checkin_result['error']}"
            }

        new_checkin = checkin_result["data"]

        # Create RetellCall record associated with this check-in
        retell_call_data = {
            "check_in_id": new_checkin["id"],
            "call_id": call_id,
            "call_transcript": None,
            "recording_url": None,
            "output_data": {"form_type": form_type}
        }

        call_result = await supabase_service.create_retell_call(retell_call_data)

        if not call_result["success"]:
            logger.error(f"Failed to create retell call: {call_result['error']}")
            # Don't fail the request, just log the error

        logger.info(f"Created new check-in with ID: {new_checkin['id']} and RetellCall with call_id: {call_id}")
        if form_data:
            logger.info(f"Form data successfully stored for check-in {new_checkin['id']} : {json.dumps(form_data, indent=2)}")

        # Prepare notification data for backward compatibility
        check_in_data_notification = {
            'id': new_checkin['id'],
            'stop_id': stop_id,  # Use mapped stop_id for notification
            'load_id': new_checkin['load_id'],
            'query': None,
            'AI_Response_Summary': new_checkin.get('ai_response_summary'),
            'AI_Timestamp': new_checkin.get('ai_timestamp'),
            'Issue_Flagged': new_checkin.get('issue_flagged', False),
            'Exception_Type': new_checkin.get('exception_type'),
            'Call_confidence_score': new_checkin.get('confidence_score'),
            'call_trasfered': new_checkin.get('call_status') == 'transferred',
            'is_active': True,  # Mark as active since call was just initiated
            'Tags': new_checkin.get('tags', []),
            'stop_name': None,  # TODO: Add stop service if needed
            'stop_location': None,
            'stop_eta': None
        }

        # Send notification asynchronously - call initiated
        try:
            await notify_check_in_update(check_in_data_notification)
            logger.info(f"Sent call-initiated notification for check-in {new_checkin['id']}")
        except Exception as e:
            logger.warning(f"Could not send notification: {e}")
            # Don't fail the request if notification fails

        # Also create a notification record in the database
        notification_data = {
            "message": f"New {form_type.replace('_', ' ').title()} check-in created for load {load_id}",
            "notification_type": "check_in_created",
            "severity": "info",
            "check_in_id": new_checkin['id'],
            "metadata": {
                "load_id": load_id,
                "form_type": form_type,
                "stop_id": stop_id
            }
        }

        try:
            await supabase_service.create_notification(notification_data)
        except Exception as e:
            logger.warning(f"Could not create notification record: {e}")

        # Generate the link to the checkin page
        checkin_page_link = f"/checkin/{new_checkin['id']}"

        return {
            "status": "success",
            "checkin_id": new_checkin['id'],
            "checkin_page_link": checkin_page_link,
            "message": "Check-in created successfully",
            "form_data_stored": bool(form_data)
        }

    except Exception as e:
        logger.error(f"Error creating check-in entry: {str(e)}")
        return {
            "status": "error",
            "message": f"Error creating check-in entry: {str(e)}"
        }


# Default form submission
@router.post("/submit-load", response_class=HTMLResponse)
async def submit_default_load(
    request: Request,
    load_id: str = Form(...),
    carrier_name: str = Form(...),
    purpose: str = Form(...),
    contact_name: str = Form(...),
    contact_phone: str = Form(...),
    country_code: str = Form(...),
    scheduled_pickup_time: str = Form(...),
    scheduled_delivery_time: str = Form(...),
    origin_address: str = Form(...),
    destination_address: str = Form(...),
    last_known_status: str = Form(...),
    last_check_call_time: Optional[str] = Form(None),
    transfer_call_to: Optional[str] = Form(None),
    transfer_country_code: Optional[str] = Form(None),
    notes: Optional[str] = Form(None)
):
    # Prepare form data
    form_data = {
        "load_id": load_id,
        "carrier_name": carrier_name,
        "purpose": purpose,
        "contact_name": contact_name,
        "contact_phone": contact_phone,
        "country_code": country_code,
        "scheduled_pickup_time": scheduled_pickup_time,
        "scheduled_delivery_time": scheduled_delivery_time,
        "origin_address": origin_address,
        "destination_address": destination_address,
        "last_known_status": last_known_status,
        "last_check_call_time": last_check_call_time,
        "transfer_call_to": transfer_call_to,
        "transfer_country_code": transfer_country_code,
        "notes": notes
    }

    result = await make_retell_call(normalize_phone_number(country_code, contact_phone), FORM_TYPE_DEFAULT, form_data)

    # Return HTML response
    if result["status"] == "success":
        return templates.TemplateResponse(
            "form.html",
            {
                "request": request,
                "success": True,
                "call_id": result.get("call_id"),
                "message": result.get("message"),
                "checkin_link": result.get("checkin_link"),
                "active_tab": FORM_TYPE_DEFAULT,
                "tab_name": "Default Form"
            }
        )
    else:
        return templates.TemplateResponse(
            "form.html",
            {
                "request": request,
                "error": result.get("message"),
                "form_data": form_data,
                "active_tab": FORM_TYPE_DEFAULT,
                "tab_name": "Default Form"
            }
        )

# At Pickup form submission
@router.post("/submit-at-pickup", response_class=HTMLResponse)
async def submit_at_pickup(
    request: Request,
    load_id: str = Form(...),
    contact_phone: str = Form(...),
    country_code: str = Form(...),
    trucker_name: str = Form(...),
    pickup_address: str = Form(...),
    driver_type: str = Form(...),
    tractor_number: Optional[str] = Form(None),
    trailer_number: Optional[str] = Form(None),
    required_equipment: Optional[str] = Form(None),
    preferred_comms: Optional[str] = Form(None),
    tracking_on: Optional[str] = Form(None),
    transfer_call_to: Optional[str] = Form(None),
    transfer_country_code: Optional[str] = Form(None)
):
    # Prepare form data for persistence
    form_data = {
        "pickup_load_id": load_id,  # Note the field name matches the HTML form
        "pickup_contact_phone": contact_phone,  # Match HTML field names
        "pickup_country_code": country_code,
        "pickup_trucker_name": trucker_name,
        "pickup_address": pickup_address,
        "driver_type": driver_type,
        "tractor_number": tractor_number,
        "trailer_number": trailer_number,
        "required_equipment": required_equipment,
        "preferred_comms": preferred_comms,
        "tracking_on": tracking_on,
        "transfer_call_to": transfer_call_to,
        "transfer_country_code": transfer_country_code
    }

    result = await make_retell_call(normalize_phone_number(country_code, contact_phone), FORM_TYPE_AT_PICKUP, form_data)

    # Return HTML response with form data for persistence
    if result["status"] == "success":
        return templates.TemplateResponse(
            "form.html",
            {
                "request": request,
                "success": True,
                "call_id": result.get("call_id"),
                "message": result.get("message"),
                "checkin_link": result.get("checkin_link"),
                "active_tab": FORM_TYPE_AT_PICKUP,
                "tab_name": "At Pickup",
                "form_data": form_data  # Include form data for persistence
            }
        )
    else:
        return templates.TemplateResponse(
            "form.html",
            {
                "request": request,
                "error": result.get("message"),
                "form_data": form_data,  # Include form data for persistence
                "active_tab": FORM_TYPE_AT_PICKUP,
                "tab_name": "At Pickup"
            }
        )

# Pickup Complete form submission
@router.post("/submit-pickup-complete", response_class=HTMLResponse)
async def submit_pickup_complete(
    request: Request,
    load_id: str = Form(...),
    contact_phone: str = Form(...),
    country_code: str = Form(...),
    trucker_name: str = Form(...),
    actual_pickup_time: str = Form(...),
    bol_verified: str = Form(...),
    commodity_description: Optional[str] = Form(None),
    next_stop_location: Optional[str] = Form(None),
    scheduled_eta: Optional[str] = Form(None),
    accessorials_needed: Optional[str] = Form(None),
    transfer_call_to: Optional[str] = Form(None),
    transfer_country_code: Optional[str] = Form(None)
):
    # Prepare form data for persistence
    form_data = {
        "pc_load_id": load_id,  # Match HTML field names
        "pc_contact_phone": contact_phone,
        "pc_country_code": country_code,
        "pc_trucker_name": trucker_name,
        "actual_pickup_time": actual_pickup_time,
        "bol_verified": bol_verified,
        "commodity_description": commodity_description,
        "next_stop_location": next_stop_location,
        "scheduled_eta": scheduled_eta,
        "accessorials_needed": accessorials_needed,
        "transfer_call_to": transfer_call_to,
        "transfer_country_code": transfer_country_code
    }

    result = await make_retell_call(normalize_phone_number(country_code, contact_phone), FORM_TYPE_PICKUP_COMPLETE, form_data)

    # Return HTML response with form data for persistence
    if result["status"] == "success":
        return templates.TemplateResponse(
            "form.html",
            {
                "request": request,
                "success": True,
                "call_id": result.get("call_id"),
                "message": result.get("message"),
                "checkin_link": result.get("checkin_link"),
                "active_tab": FORM_TYPE_PICKUP_COMPLETE,
                "tab_name": "Pickup Complete",
                "form_data": form_data  # Include form data for persistence
            }
        )
    else:
        return templates.TemplateResponse(
            "form.html",
            {
                "request": request,
                "error": result.get("message"),
                "form_data": form_data,  # Include form data for persistence
                "active_tab": FORM_TYPE_PICKUP_COMPLETE,
                "tab_name": "Pickup Complete"
            }
        )

# In Transit form submission
@router.post("/submit-in-transit", response_class=HTMLResponse)
async def submit_in_transit(
    request: Request,
    load_id: str = Form(...),
    contact_phone: str = Form(...),
    country_code: str = Form(...),
    trucker_name: str = Form(...),
    current_location: str = Form(...),
    remaining_miles: str = Form(...),
    driver_tracking: str = Form(...),
    delay_reason: Optional[str] = Form(None),
    transfer_call_to: Optional[str] = Form(None),
    transfer_country_code: Optional[str] = Form(None)
):
    # Prepare form data for persistence - using the same IDs as fillTestData
    form_data = {
        "it_load_id": load_id,
        "it_contact_phone": contact_phone,
        "it_country_code": country_code,
        "it_trucker_name": trucker_name,
        "current_location": current_location,
        "remaining_miles": remaining_miles,
        "driver_tracking": driver_tracking,
        "delay_reason": delay_reason,
        "transfer_call_to": transfer_call_to,
        "transfer_country_code": transfer_country_code
    }

    result = await make_retell_call(normalize_phone_number(country_code, contact_phone), FORM_TYPE_IN_TRANSIT, form_data)

    # Return HTML response with form data for persistence
    if result["status"] == "success":
        return templates.TemplateResponse(
            "form.html",
            {
                "request": request,
                "success": True,
                "call_id": result.get("call_id"),
                "message": result.get("message"),
                "checkin_link": result.get("checkin_link"),
                "active_tab": FORM_TYPE_IN_TRANSIT,
                "tab_name": "In Transit",
                "form_data": form_data  # Include form data for persistence
            }
        )
    else:
        return templates.TemplateResponse(
            "form.html",
            {
                "request": request,
                "error": result.get("message"),
                "form_data": form_data,  # Include form data for persistence
                "active_tab": FORM_TYPE_IN_TRANSIT,
                "tab_name": "In Transit"
            }
        )

# At Drop form submission
@router.post("/submit-at-drop", response_class=HTMLResponse)
async def submit_at_drop(
    request: Request,
    load_id: str = Form(...),
    contact_phone: str = Form(...),
    country_code: str = Form(...),
    trucker_name: str = Form(...),
    receiver_name: str = Form(...),
    receiver_address: str = Form(...),
    arrival_time: str = Form(...),
    dock_number: str = Form(...),
    lumper_needed: str = Form(...),
    lumper_amount: Optional[str] = Form(None),
    payment_method: Optional[str] = Form(None),
    transfer_call_to: Optional[str] = Form(None),
    transfer_country_code: Optional[str] = Form(None)
):
    # Prepare form data for persistence - using the same IDs as fillTestData
    form_data = {
        "ad_load_id": load_id,
        "ad_contact_phone": contact_phone,
        "ad_country_code": country_code,
        "ad_trucker_name": trucker_name,
        "receiver_name": receiver_name,
        "receiver_address": receiver_address,
        "arrival_time": arrival_time,
        "dock_number": dock_number,
        "lumper_needed": lumper_needed,
        "lumper_amount": lumper_amount,
        "payment_method": payment_method,
        "transfer_call_to": transfer_call_to,
        "transfer_country_code": transfer_country_code
    }

    result = await make_retell_call(normalize_phone_number(country_code, contact_phone), FORM_TYPE_AT_DROP, form_data)

    # Return HTML response with form data for persistence
    if result["status"] == "success":
        return templates.TemplateResponse(
            "form.html",
            {
                "request": request,
                "success": True,
                "call_id": result.get("call_id"),
                "message": result.get("message"),
                "checkin_link": result.get("checkin_link"),
                "active_tab": FORM_TYPE_AT_DROP,
                "tab_name": "At Drop",
                "form_data": form_data  # Include form data for persistence
            }
        )
    else:
        return templates.TemplateResponse(
            "form.html",
            {
                "request": request,
                "error": result.get("message"),
                "form_data": form_data,  # Include form data for persistence
                "active_tab": FORM_TYPE_AT_DROP,
                "tab_name": "At Drop"
            }
        )

# Delivered form submission
@router.post("/submit-delivered", response_class=HTMLResponse)
async def submit_delivered(
    request: Request,
    load_id: str = Form(...),
    contact_phone: str = Form(...),
    country_code: str = Form(...),
    trucker_name: str = Form(...),
    empty_time: str = Form(...),
    pod_uploaded: str = Form(...),
    lumper_receipt: str = Form(...),
    final_osd: str = Form(...),
    osd_notes: Optional[str] = Form(None),
    transfer_call_to: Optional[str] = Form(None),
    transfer_country_code: Optional[str] = Form(None)
):
    # Prepare form data for persistence - using the same IDs as fillTestData
    form_data = {
        "del_load_id": load_id,
        "del_contact_phone": contact_phone,
        "del_country_code": country_code,
        "del_trucker_name": trucker_name,
        "empty_time": empty_time,
        "pod_uploaded": pod_uploaded,
        "lumper_receipt": lumper_receipt,
        "final_osd": final_osd,
        "osd_notes": osd_notes,
        "transfer_call_to": transfer_call_to,
        "transfer_country_code": transfer_country_code
    }

    result = await make_retell_call(normalize_phone_number(country_code, contact_phone), FORM_TYPE_DELIVERED, form_data)

    # Return HTML response with form data for persistence
    if result["status"] == "success":
        return templates.TemplateResponse(
            "form.html",
            {
                "request": request,
                "success": True,
                "call_id": result.get("call_id"),
                "message": result.get("message"),
                "checkin_link": result.get("checkin_link"),
                "active_tab": FORM_TYPE_DELIVERED,
                "tab_name": "Delivered",
                "form_data": form_data  # Include form data for persistence
            }
        )
    else:
        return templates.TemplateResponse(
            "form.html",
            {
                "request": request,
                "error": result.get("message"),
                "form_data": form_data,  # Include form data for persistence
                "active_tab": FORM_TYPE_DELIVERED,
                "tab_name": "Delivered"
            }
        )

# Request POD form submission
@router.post("/submit-request-pod", response_class=HTMLResponse)
async def submit_request_pod(
    request: Request,
    load_id: str = Form(...),
    contact_phone: str = Form(...),
    country_code: str = Form(...),
    trucker_name: str = Form(...),
    delivery_date: str = Form(...),
    upload_method: Optional[str] = Form(None),
    reminder_attempt: Optional[str] = Form("1"),
    transfer_call_to: Optional[str] = Form(None),
    transfer_country_code: Optional[str] = Form(None)
):
    # Prepare form data for persistence - using the same IDs as fillTestData
    form_data = {
        "pod_load_id": load_id,
        "pod_contact_phone": contact_phone,
        "pod_country_code": country_code,
        "pod_trucker_name": trucker_name,
        "delivery_date": delivery_date,
        "upload_method": upload_method,
        "reminder_attempt": reminder_attempt,
        "transfer_call_to": transfer_call_to,
        "transfer_country_code": transfer_country_code
    }

    result = await make_retell_call(normalize_phone_number(country_code, contact_phone), FORM_TYPE_REQUEST_POD, form_data)

    # Return HTML response with form data for persistence
    if result["status"] == "success":
        return templates.TemplateResponse(
            "form.html",
            {
                "request": request,
                "success": True,
                "call_id": result.get("call_id"),
                "message": result.get("message"),
                "checkin_link": result.get("checkin_link"),
                "active_tab": FORM_TYPE_REQUEST_POD,
                "tab_name": "Request POD",
                "form_data": form_data  # Include form data for persistence
            }
        )
    else:
        return templates.TemplateResponse(
            "form.html",
            {
                "request": request,
                "error": result.get("message"),
                "form_data": form_data,  # Include form data for persistence
                "active_tab": FORM_TYPE_REQUEST_POD,
                "tab_name": "Request POD"
            }
        )
