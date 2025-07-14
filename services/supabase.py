"""
Supabase Service Module
Handles all database operations using Supabase instead of SQLAlchemy
"""

import os
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
SUPABASE_KEY = os.getenv("SUPABASE_ANON_KEY")

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
                    "search_load_id": filters.get("search_load_id")
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
        """Create feedback with optional S3 image upload"""
        try:
            if not self.client:
                return {"success": False, "error": "Supabase client not initialized"}

            # Upload images to S3 if provided
            s3_image_urls = []
            if image_files and self.s3_client:
                for image_file in image_files:
                    try:
                        # Generate unique filename
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        filename = f"feedback/{timestamp}_{image_file.get('filename', 'image.jpg')}"
                        
                        # Upload to S3
                        self.s3_client.put_object(
                            Bucket=S3_BUCKET_NAME,
                            Key=filename,
                            Body=image_file['content'],
                            ContentType=image_file.get('content_type', 'image/jpeg')
                        )
                        
                        # Generate URL
                        s3_url = f"https://{S3_BUCKET_NAME}.s3.{AWS_REGION}.amazonaws.com/{filename}"
                        s3_image_urls.append(s3_url)
                        
                    except Exception as s3_error:
                        logger.error(f"Error uploading image to S3: {s3_error}")

            # Create feedback record
            feedback_data = {
                "feedback_type": data.get("feedback_type"),
                "user_name": data.get("user_name"),
                "user_email": data.get("user_email"),
                "description": data.get("description"),
                "s3_image_urls": s3_image_urls
            }

            result = self.client.table("feedback").insert(feedback_data).execute()
            
            if result.data:
                logger.info(f"Created feedback with ID: {result.data[0]['id']}")
                return {"success": True, "data": result.data[0]}
            else:
                return {"success": False, "error": "No data returned from database"}

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
