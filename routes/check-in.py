"""
Check-in routes for creating and managing check-ins
"""
from fastapi import APIRouter, Depends, HTTPException
from loguru import logger
from datetime import datetime
from typing import Optional
from pydantic import BaseModel
import asyncio

# Replace old imports with new Supabase service
from services.supabase import supabase_service
from services.notification_service import notify_check_in_update

router = APIRouter(prefix="/api/checkin", tags=["checkin"])


class CreateCheckInRequest(BaseModel):
    stop_id: Optional[int] = None
    load_id: Optional[str] = None
    call_id: str  # Required call_id


@router.post("/create")
async def create_checkin(request: CreateCheckInRequest):
    """
    Create an empty check-in entry in the database with associated RetellCall.
    
    Args:
        request: Request body containing stop_id, load_id, and call_id
        
    Returns:
        The created check-in object with its ID and link to the checkin page
    """
    try:
        # Create a new empty check-in instance
        check_in_data = {
            "load_id": request.load_id,
            "AI_Response_Summary": None,
            "AI_Timestamp": datetime.now().isoformat(),
            "Issue_Flagged": False,
            "Exception_Type": None,
            "Confidence_score": None,
            "forms": {},
            "call_status": "in_progress"
        }
        
        # Create check-in using Supabase service
        checkin_result = await supabase_service.create_check_in(check_in_data)
        
        if not checkin_result["success"]:
            raise HTTPException(status_code=500, detail=f"Failed to create check-in: {checkin_result['error']}")
        
        new_checkin = checkin_result["data"]
        
        # Create RetellCall row associated with this check-in
        retell_call_data = {
            "check_in_id": new_checkin["id"],
            "call_id": request.call_id,
            "call_transcript": None,
            "recording_url": None,
            "output_data": {}
        }
        
        call_result = await supabase_service.create_retell_call(retell_call_data)
        
        if not call_result["success"]:
            logger.error(f"Failed to create retell call: {call_result['error']}")
            # Don't fail the request, just log the error
        
        logger.info(f"Created new check-in with ID: {new_checkin['id']} and RetellCall with call_id: {request.call_id}")
        
        # Generate the link to the checkin page
        checkin_page_link = f"/checkin/{new_checkin['id']}"
        
        # Send notification
        await send_checkin_notification(new_checkin, request.stop_id)
        
        return {
            "status": "success",
            "message": "Check-in created successfully",
            "checkin_id": new_checkin["id"],
            "call_id": request.call_id,
            "checkin_page_link": checkin_page_link,
            "data": {
                "id": new_checkin["id"],
                "stop_id": request.stop_id,
                "load_id": new_checkin["load_id"],
                "AI_Timestamp": new_checkin["ai_timestamp"],
                "Issue_Flagged": new_checkin["issue_flagged"],
                "call_trasfered": False,
                "is_active": True,
                "forms": new_checkin["forms"]
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating check-in: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create check-in: {str(e)}")


@router.get("/statistics")
async def get_checkin_statistics():
    """
    Get dashboard statistics for check-ins.
    
    Returns:
        Statistics including total check-ins, issues, human reviews, and today's check-ins
    """
    try:
        stats_result = await supabase_service.get_dashboard_stats()
        
        if not stats_result["success"]:
            raise HTTPException(status_code=500, detail=f"Failed to get statistics: {stats_result['error']}")
        
        return {
            "status": "success",
            "total_checkins": stats_result["total_checkins"],
            "total_issues": stats_result["total_issues"],
            "call_transfers": stats_result["call_transfers"],
            "today_checkins": stats_result["today_checkins"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting statistics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get statistics: {str(e)}")


@router.get("/chart-data")
async def get_chart_data():
    """
    Get chart data for the dashboard.
    
    Returns:
        Chart data for various visualizations
    """
    try:
        # Get stats for basic chart data
        stats_result = await supabase_service.get_dashboard_stats()
        
        if not stats_result["success"]:
            raise HTTPException(status_code=500, detail=f"Failed to get chart data: {stats_result['error']}")
        
        # Get daily chart data
        chart_result = await supabase_service.get_checkins_per_day_chart()
        
        if not chart_result["success"]:
            raise HTTPException(status_code=500, detail=f"Failed to get daily chart data: {chart_result['error']}")
        
        total_checkins = stats_result["total_checkins"]
        issues_count = stats_result["total_issues"]
        no_issues_count = total_checkins - issues_count
        
        transfer_count = stats_result["call_transfers"]
        no_transfer_count = total_checkins - transfer_count
        
        return {
            "status": "success",
            "checkins_per_day": {
                "labels": chart_result["labels"],
                "datasets": chart_result["datasets"],
                "data": chart_result["data"]  # Full data for tooltips
            },
            "issue_distribution": {
                "no_issues": no_issues_count,
                "issues": issues_count
            },
            "transfer_status": {
                "no_transfer": no_transfer_count,
                "transfers": transfer_count
            },
            "weekly_trends": {
                "labels": ["This Week"],
                "issues": [issues_count],
                "transfers": [transfer_count]
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting chart data: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get chart data: {str(e)}")


@router.get("/latest")
async def get_latest_checkin():
    """
    Get the latest check-in.
    
    Returns:
        The most recent check-in data
    """
    try:
        # Get the first check-in from paginated results
        result = await supabase_service.get_check_ins_paginated(page=1, per_page=1)
        
        if not result["success"]:
            raise HTTPException(status_code=500, detail=f"Failed to get latest check-in: {result['error']}")
        
        checkins = result["data"]["checkins"]
        
        if not checkins:
            return {
                "status": "success",
                "data": None,
                "message": "No check-ins found"
            }
        
        latest_checkin = checkins[0]
        
        return {
            "status": "success",
            "data": latest_checkin
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting latest check-in: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get latest check-in: {str(e)}")


@router.get("/list")
async def get_checkins_list(
    page: int = 1,
    per_page: int = 10,
    issue_flagged: Optional[str] = None,
    requires_review: Optional[str] = None,
    tags: Optional[str] = None
):
    """
    Get paginated list of check-ins with filtering.
    
    Args:
        page: Page number (1-based)
        per_page: Number of items per page
        issue_flagged: Filter by issue status ('true', 'false', or None for all)
        requires_review: Filter by review status ('true', 'false', or None for all)
        tags: Filter by tag name (partial match)
        
    Returns:
        Paginated list of check-ins
    """
    try:
        # Build filters
        filters = {}
        
        if issue_flagged is not None:
            filters["issue_flagged"] = issue_flagged.lower() == 'true'
        
        if requires_review is not None:
            if requires_review.lower() == 'true':
                filters["call_status"] = "transferred"
            elif requires_review.lower() == 'false':
                filters["call_status"] = "in_progress"
        
        if tags:
            filters["tags"] = tags
        
        # Get paginated results using Supabase service
        result = await supabase_service.get_check_ins_paginated(
            page=page,
            per_page=per_page,
            filters=filters
        )
        
        if not result["success"]:
            raise HTTPException(status_code=500, detail=f"Failed to get checkins list: {result['error']}")
        
        return {
            "status": "success",
            "data": result["data"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting checkins list: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get checkins list: {str(e)}")


@router.get("/{checkin_id}")
async def get_checkin(checkin_id: int):
    """
    Retrieve a check-in by its ID.
    
    Args:
        checkin_id: The ID of the check-in to retrieve
        
    Returns:
        The check-in object if found
    """
    try:
        result = await supabase_service.get_check_in(checkin_id)
        
        if not result["success"]:
            if "not found" in result["error"].lower():
                raise HTTPException(status_code=404, detail=f"Check-in with ID {checkin_id} not found")
            else:
                raise HTTPException(status_code=500, detail=f"Failed to retrieve check-in: {result['error']}")
        
        return {
            "status": "success",
            "data": result["data"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving check-in: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve check-in: {str(e)}")


async def send_checkin_notification(check_in_record: dict, stop_id: int = None):
    """Send notification about new or updated check-in"""
    try:
        # Prepare notification data
        check_in_data = {
            'id': check_in_record['id'],
            'stop_id': stop_id,
            'load_id': check_in_record.get('load_id'),
            'query': None,
            'AI_Response_Summary': check_in_record.get('ai_response_summary'),
            'AI_Timestamp': check_in_record.get('ai_timestamp'),
            'Issue_Flagged': check_in_record.get('issue_flagged', False),
            'Exception_Type': check_in_record.get('exception_type'),
            'Call_confidence_score': check_in_record.get('confidence_score'),
            'call_trasfered': check_in_record.get('call_status') == 'transferred',
            'is_active': True,
            'Tags': check_in_record.get('tags', []),
            'stop_name': None,  # TODO: Get from stop service if needed
            'stop_location': None,
            'stop_eta': None
        }
        
        # Send notification
        await notify_check_in_update(check_in_data)
        
        # Also create a notification record in the database
        notification_data = {
            "message": f"New check-in created for load {check_in_record.get('load_id', 'Unknown')}",
            "notification_type": "check_in_created",
            "severity": "info",
            "check_in_id": check_in_record['id'],
            "metadata": {"load_id": check_in_record.get('load_id')}
        }
        
        await supabase_service.create_notification(notification_data)
        
    except Exception as e:
        logger.warning(f"Could not send notification: {e}")
        # Don't fail the request if notification fails
