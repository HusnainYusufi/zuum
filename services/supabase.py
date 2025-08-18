"""
Supabase Service Module
Handles all database operations using Supabase instead of SQLAlchemy
"""

import os
import uuid
import json
from typing import List, Dict, Optional, Any, Union
from loguru import logger
from datetime import datetime
import asyncio
import boto3
from botocore.exceptions import ClientError
from supabase import create_client, Client
from dotenv import load_dotenv
import logging

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Supabase client
SUPABASE_URL = os.getenv("SUPABASE_URL")
# Prefer service role key on backend; fallback to anon key
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_ANON_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    logger.warning("Supabase credentials not found in environment variables")
    supabase_client = None
else:
    try:
        supabase_client: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        logger.info("Supabase client initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize Supabase client: {e}")
        supabase_client = None

# Initialize S3 client for feedback images
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME", "voice-freight-broker-feedback")

s3_client = None
if AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY:
    s3_client = boto3.client(
        's3',
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        region_name=AWS_REGION
    )


class SupabaseService:
    """Service class for all Supabase database operations"""

    def __init__(self):
        self.client = supabase_client
        self.s3_client = s3_client

    # Check-in operations
    async def create_check_in(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new check-in record"""
        try:
            if not self.client:
                return {"success": False, "error": "Supabase client not initialized"}

            # Prepare data for insertion
            check_in_data = {
                "load_id": data.get("load_id"),
                "Form_type": data.get("form_type"),
                "ai_response_summary": data.get("AI_Response_Summary"),
                "ai_timestamp": data.get("AI_Timestamp", datetime.now().isoformat()),
                "tags": data.get("tags", []),
                "issue_flagged": data.get("Issue_Flagged", False),
                "confidence_score": data.get("Confidence_score"),
                "forms": data.get("forms", {}),
                "call_status": data.get("call_status", "in_progress"),
                "user_picked_up": data.get("user_picked_up", False)
            }

            # Insert into Supabase
            result = self.client.table("check_ins").insert(check_in_data).execute()
            
            if result.data:
                logger.info(f"Created check-in with ID: {result.data[0]['id']}")
                return {"success": True, "data": result.data[0]}
            else:
                logger.error(f"Failed to create check-in: No data returned")
                return {"success": False, "error": "No data returned from database"}

        except Exception as e:
            logger.error(f"Error creating check-in: {e}")
            return {"success": False, "error": str(e)}

    async def update_check_in(self, check_in_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update an existing check-in record"""
        try:
            if not self.client:
                return {"success": False, "error": "Supabase client not initialized"}

            # Prepare update data
            update_data = {}
            field_mappings = {
                "load_id": "load_id",
                "AI_Response_Summary": "ai_response_summary",
                "AI_Timestamp": "ai_timestamp",
                "tags": "tags",
                "Issue_Flagged": "issue_flagged",
                "Confidence_score": "confidence_score",
                "forms": "forms",
                "call_status": "call_status",
                "user_picked_up": "user_picked_up"
            }

            for old_field, new_field in field_mappings.items():
                if old_field in data:
                    update_data[new_field] = data[old_field]

            if not update_data:
                return {"success": False, "error": "No valid fields to update"}

            # Update in Supabase
            result = self.client.table("check_ins").update(update_data).eq("id", check_in_id).execute()
            
            if result.data:
                logger.info(f"Updated check-in ID: {check_in_id}")
                return {"success": True, "data": result.data[0]}
            else:
                logger.error(f"Failed to update check-in ID: {check_in_id}")
                return {"success": False, "error": "Check-in not found or no changes made"}

        except Exception as e:
            logger.error(f"Error updating check-in {check_in_id}: {e}")
            return {"success": False, "error": str(e)}

    async def get_check_in(self, check_in_id: int) -> Dict[str, Any]:
        """Get a check-in by ID with associated call data"""
        try:
            if not self.client:
                return {"success": False, "error": "Supabase client not initialized"}

            # Get check-in with retell call data
            result = self.client.table("check_ins").select(
                "*, retell_calls(*)"
            ).eq("id", check_in_id).execute()
            
            if result.data and len(result.data) > 0:
                check_in = result.data[0]
                # Convert field names back to old format for compatibility
                formatted_data = self._format_check_in_for_compatibility(check_in)
                return {"success": True, "data": formatted_data}
            else:
                return {"success": False, "error": "Check-in not found"}

        except Exception as e:
            logger.error(f"Error getting check-in {check_in_id}: {e}")
            return {"success": False, "error": str(e)}

    async def get_check_ins_by_load_id(self, load_id: str) -> List[Dict[str, Any]]:
        """Get all check-ins for a specific load_id"""
        try:
            if not self.client:
                logger.warning("Supabase client not initialized")
                return []

            result = self.client.table("check_ins").select("*").eq("load_id", load_id).execute()
            
            if result.data:
                return result.data
            else:
                return []

        except Exception as e:
            logger.error(f"Error getting check-ins by load_id {load_id}: {e}")
            return []

    async def get_check_ins_paginated(self, page: int = 1, per_page: int = 10, 
                                    filters: Optional[Dict] = None) -> Dict[str, Any]:
        """Get paginated list of check-ins using enhanced RPC function"""
        try:
            if not self.client:
                return {"success": False, "error": "Supabase client not initialized"}

            filters = filters or {}
            
            # Call the enhanced RPC function
            result = self.client.rpc(
                "get_check_ins_paginated_enhanced",
                {
                    "page_num": page,
                    "page_size": per_page,
                    "filter_issue_flagged": filters.get("issue_flagged"),
                    "filter_tags": filters.get("tags"),
                    "filter_call_status": filters.get("call_status"),
                    "search_name": filters.get("search_name"),
                    "search_phone": filters.get("search_phone"),
                    "search_load_id": filters.get("search_load_id"),
                    "start_date": filters.get("start_date"),
                    "end_date": filters.get("end_date")
                }
            ).execute()
            
            if result.data:
                # Format data for compatibility
                formatted_checkins = []
                total_count = 0
                
                for item in result.data:
                    total_count = item.get("total_count", 0)
                    formatted_item = self._format_check_in_for_compatibility(item)
                    
                    # Add tags to the formatted item
                    formatted_item["tags"] = item.get("tags", [])
                    
                    formatted_checkins.append(formatted_item)
                
                total_pages = (total_count + per_page - 1) // per_page
                
                return {
                    "success": True,
                    "data": {
                        "checkins": formatted_checkins,
                        "current_page": page,
                        "per_page": per_page,
                        "total_count": total_count,
                        "total_pages": total_pages,
                        "has_next": page < total_pages,
                        "has_prev": page > 1
                    }
                }
            else:
                return {"success": True, "data": {"checkins": [], "total_count": 0}}

        except Exception as e:
            logger.error(f"Error getting paginated check-ins: {e}")
            return {"success": False, "error": str(e)}

    async def get_dashboard_stats(self) -> Dict[str, Any]:
        """Get dashboard statistics using RPC function"""
        try:
            if not self.client:
                return {"success": False, "error": "Supabase client not initialized"}

            result = self.client.rpc("get_dashboard_stats").execute()
            
            if result.data and len(result.data) > 0:
                stats = result.data[0]
                return {
                    "success": True,
                    "total_checkins": stats.get("total_checkins", 0),
                    "total_issues": stats.get("total_issues", 0),
                    "call_transfers": stats.get("call_transfers", 0),
                    "today_checkins": stats.get("today_checkins", 0),
                    "avg_confidence": float(stats.get("avg_confidence", 0)) if stats.get("avg_confidence") else 0
                }
            else:
                return {
                    "success": True,
                    "total_checkins": 0,
                    "total_issues": 0,
                    "call_transfers": 0,
                    "today_checkins": 0,
                    "avg_confidence": 0
                }

        except Exception as e:
            logger.error(f"Error getting dashboard stats: {e}")
            return {"success": False, "error": str(e)}

    async def get_checkins_per_day_chart(self) -> Dict[str, Any]:
        """Get check-ins per day for chart visualization"""
        try:
            if not self.client:
                return {"success": False, "error": "Supabase client not initialized"}

            result = self.client.rpc("get_checkins_per_day_chart").execute()
            
            if result.data:
                labels = []
                checkin_values = []
                issues_values = []
                transfers_values = []
                
                for row in result.data:
                    labels.append(row.get("date_label", ""))
                    checkin_values.append(row.get("checkin_count", 0))
                    issues_values.append(row.get("issues_count", 0))
                    transfers_values.append(row.get("transfers_count", 0))
                
                return {
                    "success": True,
                    "labels": labels,
                    "datasets": {
                        "checkins": checkin_values,
                        "issues": issues_values,
                        "transfers": transfers_values
                    },
                    "data": result.data  # Full data for detailed tooltips
                }
            else:
                return {
                    "success": True,
                    "labels": [],
                    "datasets": {
                        "checkins": [],
                        "issues": [],
                        "transfers": []
                    },
                    "data": []
                }

        except Exception as e:
            logger.error(f"Error getting chart data: {e}")
            return {"success": False, "error": str(e)}

    # Retell call operations
    async def create_retell_call(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new retell call record"""
        try:
            if not self.client:
                return {"success": False, "error": "Supabase client not initialized"}

            call_data = {
                "call_id": data.get("call_id"),
                "check_in_id": data.get("check_in_id"),
                "call_transcript": data.get("call_transcript"),
                "recording_url": data.get("recording_url"),
                "output_data": data.get("output_data", {})
            }

            result = self.client.table("retell_calls").insert(call_data).execute()
            
            if result.data:
                logger.info(f"Created retell call with ID: {result.data[0]['call_id']}")
                return {"success": True, "data": result.data[0]}
            else:
                return {"success": False, "error": "No data returned from database"}

        except Exception as e:
            logger.error(f"Error creating retell call: {e}")
            return {"success": False, "error": str(e)}

    async def update_retell_call(self, call_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update an existing retell call record"""
        try:
            if not self.client:
                return {"success": False, "error": "Supabase client not initialized"}

            update_data = {}
            if "call_transcript" in data:
                update_data["call_transcript"] = data["call_transcript"]
            if "recording_url" in data:
                update_data["recording_url"] = data["recording_url"]
            if "output_data" in data:
                update_data["output_data"] = data["output_data"]

            if not update_data:
                return {"success": False, "error": "No valid fields to update"}

            result = self.client.table("retell_calls").update(update_data).eq("call_id", call_id).execute()
            
            if result.data:
                logger.info(f"Updated retell call ID: {call_id}")
                return {"success": True, "data": result.data[0]}
            else:
                return {"success": False, "error": "Call not found or no changes made"}

        except Exception as e:
            logger.error(f"Error updating retell call {call_id}: {e}")
            return {"success": False, "error": str(e)}

    async def get_retell_call_by_id(self, call_id: str) -> Dict[str, Any]:
        """
        Fetch a RetellCall record by its call_id
        
        Args:
            call_id: The Retell call ID to fetch
            
        Returns:
            Dictionary containing success status and data/error
        """
        try:
            response = self.client.table('retell_calls').select('*').eq('call_id', call_id).execute()
            data = response.data
            
            if not data:
                return {"success": False, "error": f"No call found with ID: {call_id}"}
                
            return {"success": True, "data": data[0]}
            
        except Exception as e:
            logger.error(f"Error fetching RetellCall {call_id}: {str(e)}")
            return {"success": False, "error": str(e)}

    # Shipment ingestion and queries
    async def upsert_shipment(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Ingest shipment payload.

        - Promotes primary identifiers into first-class columns on `public.shipments`
        - Stores full JSON in `public.shipment_data` and references it by `data_id`
        - Keeps writing `payload` into `public.shipments` for backward compatibility
        """
        try:
            if not self.client:
                return {"success": False, "error": "Supabase client not initialized"}

            long_id: Optional[str] = payload.get("longId") or payload.get("long_id")

            tenant_id = (
                payload.get("customerTenantId")
                or ((payload.get("owningCompany") or {}).get("tenantId"))
                or payload.get("parentCompanyId")
            )

            shipment_id = ((payload.get("job") or {}).get("shipment"))
            load_id = payload.get("loadId")
            fleet_phone = (((payload.get("job") or {}).get("fleetManager") or {}).get("phoneNumber"))
            fleet_name = (((payload.get("job") or {}).get("fleetManager") or {}).get("fullName"))
            customer_name = ((payload.get("customer") or {}).get("name"))
            carrier_id = ((payload.get("job") or {}).get("carrierId"))
            job_id = ((payload.get("job") or {}).get("_id"))

            # 1) Write full payload to shipment_data and get data_id
            generated_data_id = str(uuid.uuid4())
            data_insert = self.client.table("shipment_data").insert({
                "data_id": generated_data_id,
                "payload": payload,
            }).execute()

            if not data_insert or not data_insert.data:
                # If RLS blocks insert or table not present, fall back to generated ID and log
                logger.warning(
                    "shipment_data insert returned no data; using generated data_id. Check RLS and table existence."
                )
                data_id = generated_data_id
            else:
                data_id = data_insert.data[0].get("data_id") or generated_data_id

            # 2) Upsert identifiers row into shipments (also write payload for compatibility)
            record = {
                "long_id": long_id,
                "tenant_id": str(tenant_id) if tenant_id is not None else None,
                "shipment_id": shipment_id,
                "load_id": str(load_id) if load_id is not None else None,
                "fleet_phone": fleet_phone,
                "fleet_name": fleet_name,
                "customer_name": customer_name,
                "carrier_id": carrier_id,
                "job_id": job_id,
                "data_id": data_id,
                "payload": payload,
            }

            # Require job_id as the sole upsert key
            if not job_id:
                return {"success": False, "error": "job._id is required for shipment upsert"}
            self.client.table("shipments").upsert(record, on_conflict="job_id").execute()

            return {"success": True, "job_id": job_id, "long_id": long_id, "data_id": data_id}
        except Exception as e:
            logger.error(f"Error upserting shipment: {e}")
            return {"success": False, "error": str(e)}

    async def get_shipment_by_long_id(self, long_id: str) -> Dict[str, Any]:
        """Fetch a raw shipment payload by long_id from `shipments`."""
        try:
            if not self.client:
                return {"success": False, "error": "Supabase client not initialized"}

            shipment_res = self.client.table("shipments").select("*").eq("long_id", long_id).execute()
            if not shipment_res.data:
                return {"success": False, "error": "Shipment not found"}

            return {"success": True, "data": shipment_res.data[0]}

        except Exception as e:
            logger.error(f"Error fetching raw shipment {long_id}: {e}")
            return {"success": False, "error": str(e)}

    async def search_shipments(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Search shipments by first-class identifier columns via RPC.

        If no filters are provided, returns all shipments (paginated).
        """
        try:
            if not self.client:
                return {"success": False, "error": "Supabase client not initialized"}

            limit = min(int(params.get("limit", 10)), 50)
            offset = int(params.get("offset", 0))

            filters = {k: params.get(k) for k in [
                "tenant_id", "shipment_id", "load_id", "fleet_phone",
                "fleet_name", "customer_name", "carrier_id", "job_id"
            ] if params.get(k)}

            # Trim name filters to avoid leading/trailing whitespace mismatches
            for name_key in ("fleet_name", "customer_name"):
                if filters.get(name_key) and isinstance(filters[name_key], str):
                    filters[name_key] = filters[name_key].strip()

            # Allow empty filters to list all shipments

            rpc_args = {
                "p_tenant_id": filters.get("tenant_id"),
                "p_shipment_id": filters.get("shipment_id"),
                "p_load_id": filters.get("load_id"),
                "p_fleet_phone": filters.get("fleet_phone"),
                "p_fleet_name": filters.get("fleet_name"),
                "p_customer_name": filters.get("customer_name"),
                "p_carrier_id": filters.get("carrier_id"),
                "p_job_id": filters.get("job_id"),
                "p_limit": limit,
                "p_offset": offset,
            }

            resp = self.client.rpc("search_shipments_simple", rpc_args).execute()
            rows = resp.data or []
            total_count = rows[0].get("total_count", 0) if rows else 0
            for r in rows:
                r.pop("total_count", None)

            return {
                "success": True,
                "data": rows,
                "pagination": {"limit": limit, "offset": offset, "count": total_count},
            }
        except Exception as e:
            logger.error(f"Error searching shipments: {e}")
            return {"success": False, "error": str(e)}

    async def get_shipment_data(self, data_id: str) -> Dict[str, Any]:
        """Fetch full payload for a given data_id from `shipment_data`."""
        try:
            if not self.client:
                return {"success": False, "error": "Supabase client not initialized"}
            resp = self.client.table("shipment_data").select("data_id,payload").eq("data_id", data_id).single().execute()
            if not resp.data:
                return {"success": False, "error": "Not found"}
            return {"success": True, "data": resp.data}
        except Exception as e:
            logger.error(f"Error fetching shipment data {data_id}: {e}")
            return {"success": False, "error": str(e)}


    # Notification operations
    async def create_notification(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new notification"""
        try:
            if not self.client:
                return {"success": False, "error": "Supabase client not initialized"}

            notification_data = {
                "message": data.get("message"),
                "notification_type": data.get("notification_type", "info"),
                "severity": data.get("severity", "info"),
                "check_in_id": data.get("check_in_id"),
                "metadata": data.get("metadata", {}),
                "read": False
            }

            result = self.client.table("notifications").insert(notification_data).execute()
            
            if result.data:
                logger.info(f"Created notification with ID: {result.data[0]['id']}")
                return {"success": True, "data": result.data[0]}
            else:
                return {"success": False, "error": "No data returned from database"}

        except Exception as e:
            logger.error(f"Error creating notification: {e}")
            return {"success": False, "error": str(e)}

    async def get_notifications_paginated(self, page: int = 1, per_page: int = 20,
                                        filters: Optional[Dict] = None) -> Dict[str, Any]:
        """Get paginated notifications using RPC function"""
        try:
            if not self.client:
                return {"success": False, "error": "Supabase client not initialized"}

            filters = filters or {}
            
            result = self.client.rpc(
                "get_notifications_paginated",
                {
                    "page_num": page,
                    "page_size": per_page,
                    "filter_read": filters.get("read"),
                    "filter_severity": filters.get("severity")
                }
            ).execute()
            
            if result.data:
                total_count = result.data[0].get("total_count", 0) if result.data else 0
                total_pages = (total_count + per_page - 1) // per_page
                
                return {
                    "success": True,
                    "data": {
                        "notifications": result.data,
                        "current_page": page,
                        "per_page": per_page,
                        "total_count": total_count,
                        "total_pages": total_pages,
                        "has_next": page < total_pages,
                        "has_prev": page > 1
                    }
                }
            else:
                return {"success": True, "data": {"notifications": [], "total_count": 0}}

        except Exception as e:
            logger.error(f"Error getting notifications: {e}")
            return {"success": False, "error": str(e)}

    async def mark_notification_read(self, notification_id: int) -> Dict[str, Any]:
        """Mark a notification as read using RPC function"""
        try:
            if not self.client:
                return {"success": False, "error": "Supabase client not initialized"}

            result = self.client.rpc("mark_notification_read", {"notification_id": notification_id}).execute()
            
            return {"success": True, "marked_read": result.data}

        except Exception as e:
            logger.error(f"Error marking notification as read: {e}")
            return {"success": False, "error": str(e)}

    # Feedback operations
    async def create_feedback(self, data: Dict[str, Any], image_files: Optional[List] = None) -> Dict[str, Any]:
        """Create feedback with optional Supabase Storage image upload"""
        try:
            if not self.client:
                return {"success": False, "error": "Supabase client not initialized"}

            # Create feedback record first
            feedback_data = {
                "feedback_type": data.get("feedback_type"),
                "user_name": data.get("user_name"),
                "user_email": data.get("user_email"),
                "description": data.get("description"),
                "resolved": False  # Default to unresolved
            }

            feedback_result = self.client.table("feedback").insert(feedback_data).execute()
            
            if not feedback_result.data:
                return {"success": False, "error": "Failed to create feedback record"}
            
            feedback_id = feedback_result.data[0]['id']
            logger.info(f"Created feedback with ID: {feedback_id}")

            # Upload images to Supabase Storage if provided
            image_records = []
            if image_files:
                bucket_name = os.getenv('SUPABASE_STORAGE_BUCKET', 'feedback-images')
                
                for i, image_file in enumerate(image_files):
                    try:
                        # Generate unique filename
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        file_extension = os.path.splitext(image_file.get('filename', 'image.jpg'))[1]
                        unique_filename = f"feedback_{feedback_id}_{timestamp}_{i}{file_extension}"
                        
                        # Upload to Supabase Storage
                        storage_response = self.client.storage.from_(bucket_name).upload(
                            path=unique_filename,
                            file=image_file['content'],
                            file_options={
                                "content-type": image_file.get('content_type', 'image/jpeg')
                            }
                        )
                        
                        if storage_response:
                            # Generate public URL
                            image_url = self.client.storage.from_(bucket_name).get_public_url(unique_filename)
                            
                            # Create image record in database
                            image_data = {
                                "feedback_id": feedback_id,
                                "filename": unique_filename,
                                "original_filename": image_file.get('filename'),
                                "image_url": image_url
                            }
                            
                            image_result = self.client.table("feedback_images").insert(image_data).execute()
                            if image_result.data:
                                image_records.append(image_result.data[0])
                                logger.info(f"Uploaded image {unique_filename} for feedback {feedback_id}")
                            else:
                                logger.error(f"Failed to save image record for {unique_filename}")
                        
                    except Exception as storage_error:
                        error_msg = str(storage_error)
                        if "row-level security policy" in error_msg:
                            logger.error(f"RLS Policy Error: Storage bucket '{bucket_name}' may have RLS enabled. Please make the bucket public or add appropriate policies.")
                            logger.error(f"To fix: Go to Supabase Dashboard → Storage → {bucket_name} → Settings → Check 'Public bucket'")
                        else:
                            logger.error(f"Error uploading image to Supabase Storage: {storage_error}")
                        continue

            return {
                "success": True, 
                "data": {
                    "feedback": feedback_result.data[0],
                    "images": image_records
                }
            }

        except Exception as e:
            logger.error(f"Error creating feedback: {e}")
            return {"success": False, "error": str(e)}

    # Utility methods
    def _format_check_in_for_compatibility(self, check_in: Dict) -> Dict:
        """Format check-in data for compatibility with existing code"""
        return {
            "id": check_in.get("id"),
            "load_id": check_in.get("load_id"),
            "query": None,  # This field doesn't exist in new schema
            "AI_Response_Summary": check_in.get("ai_response_summary"),
            "AI_Timestamp": check_in.get("ai_timestamp"),
            "Issue_Flagged": check_in.get("issue_flagged", False),
            "Exception_Type": check_in.get("exception_type"),
            "Call_confidence_score": str(check_in.get("confidence_score")) if check_in.get("confidence_score") else None,
            "call_trasfered": check_in.get("call_status") == "transferred",
            "call_status": check_in.get("call_status", "in_progress"),  # Include call_status field
            "user_picked_up": check_in.get("user_picked_up", False),  # Include user_picked_up field
            "Tags": json.dumps(check_in.get("tags", [])) if isinstance(check_in.get("tags"), list) else str(check_in.get("tags", "")),
            "miles": None,  # This field doesn't exist in new schema
            "is_active": check_in.get("call_status") in ["in_progress", "completed"],  # Map based on call_status
            "forms": json.dumps(check_in.get("forms", {})) if isinstance(check_in.get("forms"), dict) else str(check_in.get("forms", "{}")),
            "created_at": check_in.get("created_at"),
            "updated_at": check_in.get("updated_at"),
            # Add retell call data if present
            "call_id": check_in.get("retell_calls", [{}])[0].get("call_id") if check_in.get("retell_calls") else None,
            "call_transcript": check_in.get("retell_calls", [{}])[0].get("call_transcript") if check_in.get("retell_calls") else None,
            "recording_url": check_in.get("retell_calls", [{}])[0].get("recording_url") if check_in.get("retell_calls") else None,
            "check_in_metadata": json.dumps(check_in.get("retell_calls", [{}])[0].get("output_data", {})) if check_in.get("retell_calls") else None
        }

    # Health check
    async def health_check(self) -> bool:
        """Check if Supabase connection is working"""
        try:
            if not self.client:
                return False
            result = self.client.table("check_ins").select("id").limit(1).execute()
            return True
        except Exception as e:
            logger.error(f"Supabase health check failed: {e}")
            return False


# Create singleton instance
supabase_service = SupabaseService()

# Export main functions for easy import
create_check_in = supabase_service.create_check_in
update_check_in = supabase_service.update_check_in
get_check_in = supabase_service.get_check_in
get_check_ins_by_load_id = supabase_service.get_check_ins_by_load_id
get_check_ins_paginated = supabase_service.get_check_ins_paginated
get_dashboard_stats = supabase_service.get_dashboard_stats
create_retell_call = supabase_service.create_retell_call
update_retell_call = supabase_service.update_retell_call
create_notification = supabase_service.create_notification
get_notifications_paginated = supabase_service.get_notifications_paginated
mark_notification_read = supabase_service.mark_notification_read
create_feedback = supabase_service.create_feedback
get_retell_call_by_id = supabase_service.get_retell_call_by_id
upsert_shipment = supabase_service.upsert_shipment
get_shipment_by_long_id = supabase_service.get_shipment_by_long_id
search_shipments = supabase_service.search_shipments
get_shipment_data = supabase_service.get_shipment_data
