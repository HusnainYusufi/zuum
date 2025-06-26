from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from typing import Optional
from datetime import datetime
import os
import httpx
from dotenv import load_dotenv
import json
from services.prompt_config.prompt_config import prompt_config
import logging

# Replace old database imports with new Supabase service
from services.supabase import supabase_service
from services.notification_service import notify_check_in_update
import asyncio

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
    # Get form configuration and voice questions
    form_config = prompt_config.get_form_config(form_type)
    voice_questions = prompt_config.get_voice_questions(form_type)
    form_number = prompt_config.FORM_TYPE_MAPPING.get(form_type, 0)
    
    # Get output schema from form configuration
    output_schema = form_config.get("output_schema", {})
    
    # Extract transfer call number from form data if present
    transfer_call = None
    # Look for the transfer_call_to field name that matches the form.html
    for field_name in ["transfer_call_to"]:
        if field_name in form_data and form_data[field_name]:
            transfer_call = form_data[field_name]
            break
    
    # Convert data to JSON strings
    form_data_json = json.dumps(form_data)
    voice_questions_json = json.dumps(voice_questions)
    form_number_json = json.dumps(form_number)
    output_schema_json = json.dumps(output_schema)
    
    logger.info(f"Form config: {form_config}")
    logger.info(f"Voice questions: {voice_questions}")
    logger.info(f"Form number: {form_number}")
    logger.info(f"Output schema: {output_schema}")
    
    # Prepare metadata for the call
    metadata = {
        "form_number": form_number_json,
        "form_title": form_config.get("title", ""),
        "purpose": voice_questions_json,
        "form": form_data_json,
        "output_schema": output_schema_json
    }
    
    # Prepare dynamic variables for the agent
    dynamic_variables = {
        "form_number": form_number_json,
        "form_title": form_config.get("title", ""),
        "purpose": voice_questions_json,
        "form": form_data_json,
        "output_schema": output_schema_json
    }
    
    # Add transfer call if present
    if transfer_call:
        dynamic_variables["transfer_call_to"] = json.dumps(transfer_call)
        logger.info(f"Transfer call number included: {transfer_call}")
    
    # Log output schema inclusion
    if output_schema:
        logger.info(f"Output schema included for form type '{form_type}': {len(output_schema.get('properties', {}))} properties")
    
    # Make the Retell API call
    headers = {
        "Authorization": f"Bearer {RETELL_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "from_number": FROM_PHONE_NUMBER,
        "to_number": to_number,
        "override_agent_id": AGENT_ID,
        "metadata": metadata,
        "retell_llm_dynamic_variables": dynamic_variables
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
                          form_data.get("pod_load_id"))
                
                # Create check-in entry
                checkin_result = await create_checkin_entry(call_id, load_id, form_type, form_data)
                
                return {
                    "status": "success",
                    "call_id": call_id,
                    "message": f"Call initiated successfully to {contact_phone}",
                    "form_type": form_type,
                    "load_id": load_id,
                    "transfer_call": transfer_call,
                    "output_schema_properties": len(output_schema.get('properties', {})) if output_schema else 0,
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
        form_data: The form data dictionary to store as JSON
    
    Returns:
        Dictionary with check-in creation result
    """
    try:
        # Determine stop_id based on form_type (keeping for backward compatibility)
        stop_id_mapping = {
            "default": 0,
            "at_pickup": 1,
            "pickup_complete": 2,
            "in_transit": 3,
            "at_drop": 4,
            "delivered": 5,
            "request_pod": 6
        }
        stop_id = stop_id_mapping.get(form_type, 0)
        
        # Prepare check-in data for Supabase
        check_in_data = {
            "load_id": load_id,
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
        
        # Log form data storage
        if form_data:
            logger.info(f"Storing form data for check-in {new_checkin['id']}: {json.dumps(form_data, indent=2)}")
        
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
            logger.info(f"Form data successfully stored for check-in {new_checkin['id']}")
        
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
    print("=== DEFAULT FORM SUBMISSION ===")
    print(f"Load ID: {load_id}")
    print(f"Carrier Name: {carrier_name}")
    print(f"Purpose: {purpose}")
    print(f"Contact Name: {contact_name}")
    print(f"Contact Phone: {contact_phone}")
    print(f"Country Code: {country_code}")
    print(f"Scheduled Pickup Time: {scheduled_pickup_time}")
    print(f"Scheduled Delivery Time: {scheduled_delivery_time}")
    print(f"Origin Address: {origin_address}")
    print(f"Destination Address: {destination_address}")
    print(f"Last Known Status: {last_known_status}")
    print(f"Last Check Call Time: {last_check_call_time}")
    print(f"Transfer Call To: {transfer_call_to}")
    print(f"Transfer Country Code: {transfer_country_code}")
    print(f"Notes: {notes}")
    print("==============================\n")
    
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
    
    # Make Retell API call - combine country code and phone for the actual call
    full_phone_number = country_code + contact_phone.lstrip('0').replace('-', '').replace(' ', '').replace('(', '').replace(')', '')
    print(f"Full Phone Number: {full_phone_number}")
    result = await make_retell_call(full_phone_number, "default", form_data)
    
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
                "active_tab": "default",
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
                "active_tab": "default",
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
    print("=== AT PICKUP FORM SUBMISSION ===")
    print(f"Load ID: {load_id}")
    print(f"Contact Phone: {contact_phone}")
    print(f"Country Code: {country_code}")
    print(f"Trucker Name: {trucker_name}")
    print(f"Pickup Address: {pickup_address}")
    print(f"Driver Type: {driver_type}")
    print(f"Tractor Number: {tractor_number}")
    print(f"Trailer Number: {trailer_number}")
    print(f"Required Equipment: {required_equipment}")
    print(f"Preferred Communications: {preferred_comms}")
    print(f"Tracking On: {tracking_on}")
    print(f"Transfer Call To: {transfer_call_to}")
    print(f"Transfer Country Code: {transfer_country_code}")
    print("==============================\n")
    
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
    
    # Make Retell API call - combine country code and phone for the actual call
    full_phone_number = country_code + contact_phone.lstrip('0').replace('-', '').replace(' ', '').replace('(', '').replace(')', '')
    result = await make_retell_call(full_phone_number, "at_pickup", form_data)
    
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
                "active_tab": "at-pickup",
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
                "active_tab": "at-pickup",
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
    print("=== PICKUP COMPLETE FORM SUBMISSION ===")
    print(f"Load ID: {load_id}")
    print(f"Contact Phone: {contact_phone}")
    print(f"Country Code: {country_code}")
    print(f"Trucker Name: {trucker_name}")
    print(f"Actual Pickup Time: {actual_pickup_time}")
    print(f"BOL/PO Verified: {bol_verified}")
    print(f"Commodity Description: {commodity_description}")
    print(f"Next Stop Location: {next_stop_location}")
    print(f"Scheduled ETA: {scheduled_eta}")
    print(f"Accessorials Needed: {accessorials_needed}")
    print(f"Transfer Call To: {transfer_call_to}")
    print(f"Transfer Country Code: {transfer_country_code}")
    print("==============================\n")
    
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
    
    # Make Retell API call - combine country code and phone for the actual call
    full_phone_number = country_code + contact_phone.lstrip('0').replace('-', '').replace(' ', '').replace('(', '').replace(')', '')
    result = await make_retell_call(full_phone_number, "pickup_complete", form_data)
    
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
                "active_tab": "pickup-complete",
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
                "active_tab": "pickup-complete",
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
    print("=== IN TRANSIT FORM SUBMISSION ===")
    print(f"Load ID: {load_id}")
    print(f"Contact Phone: {contact_phone}")
    print(f"Country Code: {country_code}")
    print(f"Trucker Name: {trucker_name}")
    print(f"Current Location: {current_location}")
    print(f"Remaining Miles: {remaining_miles}")
    print(f"Driver Tracking: {driver_tracking}")
    print(f"Delay Reason: {delay_reason}")
    print(f"Transfer Call To: {transfer_call_to}")
    print(f"Transfer Country Code: {transfer_country_code}")
    print("==============================\n")
    
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
    
    # Make Retell API call - combine country code and phone for the actual call
    full_phone_number = country_code + contact_phone.lstrip('0').replace('-', '').replace(' ', '').replace('(', '').replace(')', '')
    result = await make_retell_call(full_phone_number, "in_transit", form_data)
    
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
                "active_tab": "in-transit",
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
                "active_tab": "in-transit",
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
    print("=== AT DROP FORM SUBMISSION ===")
    print(f"Load ID: {load_id}")
    print(f"Contact Phone: {contact_phone}")
    print(f"Country Code: {country_code}")
    print(f"Trucker Name: {trucker_name}")
    print(f"Receiver Name: {receiver_name}")
    print(f"Receiver Address: {receiver_address}")
    print(f"Arrival Time: {arrival_time}")
    print(f"Dock Number: {dock_number}")
    print(f"Lumper Needed: {lumper_needed}")
    print(f"Lumper Amount: {lumper_amount}")
    print(f"Payment Method: {payment_method}")
    print(f"Transfer Call To: {transfer_call_to}")
    print(f"Transfer Country Code: {transfer_country_code}")
    print("==============================\n")
    
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
    
    # Make Retell API call - combine country code and phone for the actual call
    full_phone_number = country_code + contact_phone.lstrip('0').replace('-', '').replace(' ', '').replace('(', '').replace(')', '')
    result = await make_retell_call(full_phone_number, "at_drop", form_data)
    
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
                "active_tab": "at-drop",
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
                "active_tab": "at-drop",
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
    print("=== DELIVERED FORM SUBMISSION ===")
    print(f"Load ID: {load_id}")
    print(f"Contact Phone: {contact_phone}")
    print(f"Country Code: {country_code}")
    print(f"Trucker Name: {trucker_name}")
    print(f"Empty Time: {empty_time}")
    print(f"POD Uploaded: {pod_uploaded}")
    print(f"Lumper Receipt: {lumper_receipt}")
    print(f"Final OS&D: {final_osd}")
    print(f"OS&D Notes: {osd_notes}")
    print(f"Transfer Call To: {transfer_call_to}")
    print(f"Transfer Country Code: {transfer_country_code}")
    print("==============================\n")
    
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
    
    # Make Retell API call - combine country code and phone for the actual call
    full_phone_number = country_code + contact_phone.lstrip('0').replace('-', '').replace(' ', '').replace('(', '').replace(')', '')
    result = await make_retell_call(full_phone_number, "delivered", form_data)
    
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
                "active_tab": "delivered",
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
                "active_tab": "delivered",
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
    print("=== REQUEST POD FORM SUBMISSION ===")
    print(f"Load ID: {load_id}")
    print(f"Contact Phone: {contact_phone}")
    print(f"Country Code: {country_code}")
    print(f"Trucker Name: {trucker_name}")
    print(f"Delivery Date: {delivery_date}")
    print(f"Upload Method: {upload_method}")
    print(f"Reminder Attempt: {reminder_attempt}")
    print(f"Transfer Call To: {transfer_call_to}")
    print(f"Transfer Country Code: {transfer_country_code}")
    print("==============================\n")
    
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
    
    # Make Retell API call - combine country code and phone for the actual call
    full_phone_number = country_code + contact_phone.lstrip('0').replace('-', '').replace(' ', '').replace('(', '').replace(')', '')
    result = await make_retell_call(full_phone_number, "request_pod", form_data)
    
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
                "active_tab": "request-pod",
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
                "active_tab": "request-pod",
                "tab_name": "Request POD"
            }
        )
