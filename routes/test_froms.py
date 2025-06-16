from fastapi import APIRouter, HTTPException, Body, File, UploadFile, Form, Query
from dotenv import load_dotenv
from services.langrapghs.forms.forms_langraph import forms_langraph_from_service
import random
from langgraph.types import Command

# Load environment variables from .env file
load_dotenv()

# Form state mapping dictionary
FORM_STATE_MAPPING = {
    "at_pickup": {
        "purpose": [
            "I'm calling on Zuum load ###—are you the driver assigned?",
            "which city and state are you in currently?",
            "Are you empty now?",
            "Have you reached the shipper",
            "Please confirm tractor, trailer and that you have the right equipment for this load.",
            "I've sent the Zuum tracking link—can you open it so tracking starts?",
            "Ask if they have door number.",
            "If they have door number then ask what it is?"
        ],
        "form_data": {
            "load_id": "L123456 / CUST7890",
            "trucker_name": "John Doe",
            "contact_phone": "+1-555-123-4567",
            "pickup_address": "1234 Warehouse Ave, Dallas, TX 75201, Appointment: 2025-06-07T10:00:00",
            "driver_type": "OTR",
            "tractor_number": "TX9821",
            "trailer_number": "TRL4567",
            "required_equipment": "Reefer, Temperature: 34F, Straps, Load Bars",
            "preferred_comms": "Text",
            "tracking_on": "Y"
        },
        "output_schema": {
            "type": "object",
            "properties": {
                "Driver_empty": {
                    "type": "boolean",
                    "description": "Whether the driver is currently empty"
                },
                "ETA_to_shipper": {
                    "type": "string",
                    "description": "Estimated time of arrival to the shipper, stated by the driver"
                },
                "Current_location": {
                    "type": "string",
                    "description": "The driver's current location (city and state)"
                },
                "Confirmed_equipment": {
                    "type": "boolean",
                    "description": "Whether the driver confirmed they have the correct tractor, trailer, and required equipment"
                },
                "Is_assigned_driver": {
                    "type": "boolean",
                    "description": "Whether the person on the call is the driver assigned to the load"
                },
                "Tracking_started": {
                    "type": "boolean",
                    "description": "Whether the driver confirmed they opened the tracking link and tracking has started"
                },
                "door number": {
                    "type": "string",
                    "description": "The door number provided by the trucker."
                }
            },
            "required": [
                "Is_assigned_driver",
                "Driver_empty",
                "Current_location",
                "ETA_to_shipper",
                "Confirmed_equipment",
                "Tracking_started",
                "door number"
            ]
        }
    },
    "pickup_complete": {
        "purpose": [
            "Have you been loaded and left the dock?",
            "If they have left the dock, then ask what time did they pull out?",
            "Does the PO or BOL on your paperwork match the rate-con?",
            "Where are you headed next and when do you expect to arrive?",
            "Any problems at the shipper or accessorial costs we need to know about?"
        ],
        "form_data": {
            "load_id": "L123456",
            "actual_pickup_time": "2025-06-06T14:35:00",
            "bol_verified": "Y",
            "commodity_description": "Frozen chicken – palletized",
            "next_stop_location": "Atlanta, GA",
            "scheduled_eta": "2025-06-07T09:00:00",
            "accessorials_needed": "Lumper, Temp Check"
        },
        "output_schema": {
            "type": "object",
            "properties": {
                "Accessorial_notes": {
                    "type": "string",
                    "nullable": True,
                    "description": "Optional notes provided by the driver about the issue or extra costs (if any)"
                },
                "Loaded_and_left_dock": {
                    "type": "boolean",
                    "description": "Whether the driver has been loaded and left the dock"
                },
                "ETA_to_next": {
                    "type": "string",
                    "description": "Estimated time of arrival to the next destination"
                },
                "Shipper_issues_reported": {
                    "type": "boolean",
                    "description": "Whether the driver reported any problems at the shipper"
                },
                "Departure_time": {
                    "type": "string",
                    "description": "Time the driver pulled out from the shipper, as stated by the driver"
                },
                "Next_destination": {
                    "type": "string",
                    "description": "Where the driver is headed next (typically delivery location or stop)"
                },
                "Accessorial_costs_reported": {
                    "type": "boolean",
                    "description": "Whether the driver mentioned any extra charges (e.g., detention, lumper, layover)"
                },
                "PO_BOL_matches_rate_con": {
                    "type": "boolean",
                    "description": "Whether the PO or BOL on the paperwork matches the rate confirmation"
                }
            },
            "required": [
                "Loaded_and_left_dock",
                "Departure_time",
                "PO_BOL_matches_rate_con",
                "Next_destination",
                "ETA_to_next",
                "Shipper_issues_reported",
                "Accessorial_costs_reported"
            ]
        }
    },
    "in_transit": {
        "purpose": [
            "Which city and state you right now",
            "What's your updated ETA to the receiver?",
            "Do you foresee anything that could make you late—weather, HOS, equipment?",
            "If you're not on the tracking app, can you open it now so we don't have to keep calling?"
        ],
        "form_data": {
            "load_id": "L123456",
            "current_location": "Birmingham, AL",
            "remaining_miles": 210,
            "delay_reason": "Traffic"
        },
        "output_schema": {
            "type": "object",
            "properties": {
                "Risk_of_delay": {
                    "type": "boolean",
                    "description": "Whether the driver foresees any risk of delay (e.g., weather, HOS, equipment issues)"
                },
                "Delay_reason": {
                    "type": "string",
                    "nullable": True,
                    "description": "Optional details about potential delay if risk is present"
                },
                "Current_location_manual": {
                    "type": "string",
                    "description": "Driver's current location (city and state), manually confirmed if tracking is not available"
                },
                "Updated_ETA_to_receiver": {
                    "type": "string",
                    "description": "Driver's updated estimated time of arrival to the receiver"
                },
                "Tracking_restarted": {
                    "type": "boolean",
                    "description": "Whether the driver reopened the tracking app during the call"
                }
            },
            "required": [
                "Updated_ETA_to_receiver",
                "Risk_of_delay",
                "Tracking_restarted"
            ]
        }
    },
    "at_drop": {
        "purpose": [
            "Have you checked in and what dock number did they assign?",
            "Has unloading started, and how long did they quote you?",
            "Do you need a lumper code?",
            "If they need lumper code, then ask how much and what payment type do they accept?",
            "Any overages, shortages or damages noted by the warehouse?"
        ],
        "form_data": {
            "load_id": "L123456",
            "receiver_name": "FreshMart Distribution Center",
            "receiver_address": "5678 Logistics Way, Atlanta, GA 30303",
            "arrival_time": "2025-06-07T09:15:00",
            "dock_number": "12B",
            "lumper_needed": "Y",
            "lumper_amount": 150.00,
            "payment_method": "Comchek",
            "osd_observed": "N"
        },
        "output_schema": {
            "type": "object",
            "properties": {
                "Dock_number": {
                    "type": "string",
                    "nullable": True,
                    "description": "The dock number assigned to the driver"
                },
                "Unloading_duration_estimate": {
                    "type": "string",
                    "nullable": True,
                    "description": "Estimated time to complete unloading as quoted to the driver"
                },
                "Needs_lumper_code": {
                    "type": "boolean",
                    "description": "Whether the driver is requesting a lumper code"
                },
                "Checked_in": {
                    "type": "boolean",
                    "description": "Whether the driver has checked in at the receiver"
                },
                "Lumper_payment_method": {
                    "type": "string",
                    "nullable": True,
                    "description": "Accepted payment method for lumper (e.g., Comchek, EFS, T-Check)"
                },
                "OSD_reported": {
                    "type": "boolean",
                    "description": "Whether any overages, shortages, or damages were reported by the warehouse"
                },
                "Lumper_fee_amount": {
                    "type": "string",
                    "nullable": True,
                    "description": "Amount requested for lumper (e.g., '$95')"
                },
                "OSD_details": {
                    "type": "string",
                    "nullable": True,
                    "description": "Details about any overages, shortages, or damages"
                },
                "Unloading_started": {
                    "type": "boolean",
                    "description": "Whether unloading has started"
                }
            },
            "required": [
                "Checked_in",
                "Unloading_started",
                "Needs_lumper_code",
                "OSD_reported"
            ]
        }
    },
    "delivered": {
        "purpose": [
            "What time were you released from the dock?",
            "Have you already uploaded the signed POD to the Zuum app or can you text a photo now?",
            "Any lumper receipts or scale tickets we still need?"
        ],
        "form_data": {
            "load_id": "L123456",
            "empty_time": "2025-06-07T10:20:00",
            "pod_uploaded": "Y",
            "lumper_receipt": "Y",
            "final_osd": "Y",
            "osd_notes": "2 cases crushed on rear pallet, noted on BOL"
        },
        "output_schema": {
            "type": "object",
            "properties": {
                "Final_OSD_confirmed_clean": {
                    "type": "boolean",
                    "description": "Whether the driver confirmed no overages, shortages, or damages occurred during delivery"
                },
                "Receipts_pending": {
                    "type": "boolean",
                    "description": "Whether any lumper receipts or scale tickets are still pending submission"
                },
                "Dock_release_time": {
                    "type": "string",
                    "description": "The time the driver was released from the dock (e.g., '15:45' or '2025-06-06T15:45:00')"
                },
                "POD_uploaded": {
                    "type": "boolean",
                    "description": "Whether the signed POD has been uploaded to the Zuum app"
                },
                "POD_texted": {
                    "type": "boolean",
                    "nullable": True,
                    "description": "Whether the driver texted a photo of the signed POD (if not uploaded via app)"
                }
            },
            "required": [
                "Dock_release_time",
                "POD_uploaded",
                "Receipts_pending",
                "Final_OSD_confirmed_clean"
            ],
            "dependencies": {
                "_p_o_d_uploaded": {
                    "one_of": [
                        {
                            "properties": {
                                "POD_uploaded": {
                                    "const": True
                                }
                            }
                        },
                        {
                            "properties": {
                                "POD_uploaded": {
                                    "const": False
                                },
                                "POD_texted": {
                                    "type": "boolean"
                                }
                            },
                            "required": [
                                "POD_texted"
                            ]
                        }
                    ]
                }
            }
        }
    },
    "request_pod": {
        "purpose": [
            "could you upload it to the app or text me a clear photo right now?",
            "Were there any OS&D issues we should note before we close the load?"
        ],
        "form_data": {
            "load_id": "L123456",
            "delivery_date": "2025-06-07T10:20:00",
            "upload_method": "App",
            "reminder_attempt": "1"
        },
        "output_schema": {
            "type": "object",
            "properties": {
                "POD_followup_received": {
                    "type": "boolean",
                    "description": "Whether the POD was successfully received during the follow-up call (via app upload or photo text)"
                },
                "OSD_reported_at_closure": {
                    "type": "boolean",
                    "description": "Whether the driver reported any OS&D issues before load closure"
                },
                "OSD_closure_notes": {
                    "type": "string",
                    "nullable": True,
                    "description": "Optional notes about OS&D issues if reported during the closure follow-up"
                }
            },
            "required": [
                "POD_followup_received",
                "OSD_reported_at_closure"
            ]
        }
    },
    "default": {
        "purpose": [],
        "form_data": {
            "load_id": "",
            "carrier_name": "",
            "purpose": "",
            "contact_name": "",
            "contact_phone": "",
            "scheduled_pickup_time": "",
            "scheduled_delivery_time": "",
            "origin_address": "",
            "destination_address": "",
            "last_known_status": "",
            "last_check_call_time": "",
            "notes": ""
        },
        "output_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    }
}

router = APIRouter(
    prefix="/test-forms",
    tags=["test-forms"],
    responses={404: {"description": "Not found"}},
)

# Dictionary to store chat states
chat_states = {}

@router.get("/initialize")
def initialize_chat(formName: str):
    thread_id = str(random.randint(1, 1000000))
    
    # Get the form state configuration
    if formName not in FORM_STATE_MAPPING:
        raise HTTPException(status_code=400, detail=f"Form '{formName}' not found")
    
    form_config = FORM_STATE_MAPPING[formName]
    
    # Create the state with purpose, form_data, and output_schema
    state = {
        "messages": [],
        "purpose": form_config["purpose"],
        "form_data": form_config["form_data"],
        "output_schema": form_config.get("output_schema", {}),
        "result": None
    }
    
    # Store the state with the thread ID
    chat_states[thread_id] = state
    # Run the service with the configured state
    result = forms_langraph_from_service.run(state, thread_id)
    
    return {
        "thread_id": thread_id,
        "result": result
    }

@router.get("/conversate")
def conversate(query: str, thread_id: str):
    # Check if thread exists
    if thread_id not in chat_states:
        raise HTTPException(status_code=404, detail={"type": "error", "message": "Chat session not found"})
    
    try:
        # Get the state for this thread
        state = chat_states[thread_id]
        
        # Run the service with the user query and thread ID
        result = forms_langraph_from_service.run(Command(resume={'data': query}), thread_id)
        
        # Update the state with the result
        chat_states[thread_id] = state
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail={"type": "error", "message": str(e)})

