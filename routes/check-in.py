"""
Check-in routes for creating and managing check-ins
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from loguru import logger
from datetime import datetime
from typing import Optional
from pydantic import BaseModel
import asyncio

from db_models import get_db, CheckIn, RetellCall, Stop
from services.notification_service import notify_check_in_update

router = APIRouter(prefix="/api/checkin", tags=["checkin"])


class CreateCheckInRequest(BaseModel):
    stop_id: Optional[int] = None
    load_id: Optional[str] = None
    call_id: str  # Required call_id


@router.post("/create")
def create_checkin(
    request: CreateCheckInRequest,
    db: Session = Depends(get_db)
):
    """
    Create an empty check-in entry in the database with associated RetellCall.
    
    Args:
        request: Request body containing stop_id, load_id, and call_id
        db: Database session dependency
        
    Returns:
        The created check-in object with its ID and link to the checkin page
    """
    try:
        # Create a new empty check-in instance
        new_checkin = CheckIn(
            stop_id=request.stop_id,
            load_id=request.load_id,
            query=None,
            AI_Response_Summary=None,
            AI_Timestamp=datetime.now().isoformat(),
            Issue_Flagged=False,
            Exception_Type=None,
            Call_confidence_score=None,
            call_trasfered=False,
            Tags=None,
            miles=None,
            is_active=True  # Set to True when check-in is created
        )
        
        # Add to database session and commit to get the ID
        db.add(new_checkin)
        db.flush()  # Flush to get the check-in ID without committing yet
        
        # Create RetellCall row associated with this check-in
        new_retell_call = RetellCall(
            check_in_id=new_checkin.id,
            call_id=request.call_id,
            call_transcript=None,
            recording_url=None,
            check_in_metadata=None
        )
        
        db.add(new_retell_call)
        db.commit()
        db.refresh(new_checkin)
        db.refresh(new_retell_call)
        
        logger.info(f"Created new check-in with ID: {new_checkin.id} and RetellCall with call_id: {request.call_id}")
        
        # Generate the link to the checkin page
        checkin_page_link = f"/checkin/{new_checkin.id}"
        
        # Send notification
        send_checkin_notification(new_checkin, request.stop_id, db)
        
        return {
            "status": "success",
            "message": "Check-in created successfully",
            "checkin_id": new_checkin.id,
            "call_id": request.call_id,
            "checkin_page_link": checkin_page_link,
            "data": {
                "id": new_checkin.id,
                "stop_id": new_checkin.stop_id,
                "load_id": new_checkin.load_id,
                "AI_Timestamp": new_checkin.AI_Timestamp,
                "Issue_Flagged": new_checkin.Issue_Flagged,
                "call_trasfered": new_checkin.call_trasfered,
                "is_active": new_checkin.is_active,
                "forms": new_checkin.forms
            }
        }
        
    except Exception as e:
        logger.error(f"Error creating check-in: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create check-in: {str(e)}")


@router.get("/statistics")
def get_checkin_statistics(db: Session = Depends(get_db)):
    """
    Get dashboard statistics for check-ins.
    
    Returns:
        Statistics including total check-ins, issues, human reviews, and today's check-ins
    """
    try:
        from datetime import datetime, timedelta
        
        # Total check-ins
        total_checkins = db.query(CheckIn).count()
        
        # Total issues flagged
        total_issues = db.query(CheckIn).filter(CheckIn.Issue_Flagged == True).count()
        
        # Total call transfers
        call_transfers = db.query(CheckIn).filter(CheckIn.call_trasfered == True).count()
        
        # Today's check-ins
        today = datetime.now().date()
        today_str = today.isoformat()
        today_checkins = db.query(CheckIn).filter(
            CheckIn.AI_Timestamp.like(f"{today_str}%")
        ).count()
        
        return {
            "status": "success",
            "total_checkins": total_checkins,
            "total_issues": total_issues,
            "call_transfers": call_transfers,
            "today_checkins": today_checkins
        }
        
    except Exception as e:
        logger.error(f"Error getting statistics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get statistics: {str(e)}")


@router.get("/chart-data")
def get_chart_data(db: Session = Depends(get_db)):
    """
    Get chart data for the dashboard.
    
    Returns:
        Chart data for various visualizations
    """
    try:
        from datetime import datetime, timedelta
        from collections import defaultdict
        import json
        
        # Get all check-ins (since AI_Timestamp is a string, we'll filter in Python)
        checkins = db.query(CheckIn).all()
        
        # Check-ins per day (last 30 days)
        thirty_days_ago = datetime.now() - timedelta(days=30)
        daily_counts = defaultdict(int)
        for checkin in checkins:
            try:
                checkin_date = datetime.fromisoformat(checkin.AI_Timestamp)
                if checkin_date >= thirty_days_ago:
                    daily_counts[checkin_date.date()] += 1
            except:
                continue
        
        # Fill missing days with 0
        current_date = thirty_days_ago.date()
        end_date = datetime.now().date()
        labels = []
        values = []
        
        while current_date <= end_date:
            labels.append(current_date.strftime("%m/%d"))
            values.append(daily_counts.get(current_date, 0))
            current_date += timedelta(days=1)
        
        # Issue distribution
        total_checkins = db.query(CheckIn).count()
        issues_count = db.query(CheckIn).filter(CheckIn.Issue_Flagged == True).count()
        no_issues_count = total_checkins - issues_count
        
        # Transfer status
        transfer_count = db.query(CheckIn).filter(CheckIn.call_trasfered == True).count()
        no_transfer_count = total_checkins - transfer_count
        
        # Weekly trends (last 4 weeks) - we'll use the same checkins data
        weekly_data = defaultdict(lambda: {"issues": 0, "transfers": 0})
        four_weeks_ago = datetime.now() - timedelta(weeks=4)
        
        for checkin in checkins:
            try:
                checkin_date = datetime.fromisoformat(checkin.AI_Timestamp)
                if checkin_date >= four_weeks_ago:
                    week_start = checkin_date - timedelta(days=checkin_date.weekday())
                    week_key = week_start.strftime("Week of %m/%d")
                    
                    if checkin.Issue_Flagged:
                        weekly_data[week_key]["issues"] += 1
                    if checkin.call_trasfered:
                        weekly_data[week_key]["transfers"] += 1
            except:
                continue
        
        # Sort weekly data by date
        sorted_weeks = sorted(weekly_data.keys(), key=lambda x: datetime.strptime(x.replace("Week of ", ""), "%m/%d"))
        
        return {
            "status": "success",
            "checkins_per_day": {
                "labels": labels,
                "values": values
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
                "labels": sorted_weeks,
                "issues": [weekly_data[week]["issues"] for week in sorted_weeks],
                "transfers": [weekly_data[week]["transfers"] for week in sorted_weeks]
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting chart data: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get chart data: {str(e)}")


@router.get("/latest")
def get_latest_checkin(db: Session = Depends(get_db)):
    """
    Get the latest check-in.
    
    Returns:
        The most recent check-in data
    """
    try:
        latest_checkin = db.query(CheckIn).order_by(CheckIn.id.desc()).first()
        
        if not latest_checkin:
            return {
                "status": "success",
                "data": None,
                "message": "No check-ins found"
            }
        
        return {
            "status": "success",
            "data": {
                "id": latest_checkin.id,
                "stop_id": latest_checkin.stop_id,
                "load_id": latest_checkin.load_id,
                "query": latest_checkin.query,
                "AI_Response_Summary": latest_checkin.AI_Response_Summary,
                "AI_Timestamp": latest_checkin.AI_Timestamp,
                "Issue_Flagged": latest_checkin.Issue_Flagged,
                "Exception_Type": latest_checkin.Exception_Type,
                "Call_confidence_score": latest_checkin.Call_confidence_score,
                "call_trasfered": latest_checkin.call_trasfered,
                "Tags": latest_checkin.Tags,
                "miles": latest_checkin.miles,
                "is_active": latest_checkin.is_active,
                "forms": latest_checkin.forms
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting latest check-in: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get latest check-in: {str(e)}")


@router.get("/list")
def get_checkins_list(
    page: int = 1,
    per_page: int = 10,
    issue_flagged: Optional[str] = None,
    requires_review: Optional[str] = None,
    tags: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Get paginated list of check-ins with filtering.
    
    Args:
        page: Page number (1-based)
        per_page: Number of items per page
        issue_flagged: Filter by issue status ('true', 'false', or None for all)
        requires_review: Filter by review status ('true', 'false', or None for all)
        tags: Filter by tag name (partial match)
        db: Database session dependency
        
    Returns:
        Paginated list of check-ins
    """
    try:
        # Build query with filters
        query = db.query(CheckIn)
        
        if issue_flagged is not None:
            if issue_flagged.lower() == 'true':
                query = query.filter(CheckIn.Issue_Flagged == True)
            elif issue_flagged.lower() == 'false':
                query = query.filter(CheckIn.Issue_Flagged == False)
        
        if requires_review is not None:
            if requires_review.lower() == 'true':
                query = query.filter(CheckIn.call_trasfered == True)
            elif requires_review.lower() == 'false':
                query = query.filter(CheckIn.call_trasfered == False)
        
        if tags:
            query = query.filter(CheckIn.Tags.like(f"%{tags}%"))
        
        # Get total count
        total_count = query.count()
        
        # Calculate pagination
        total_pages = (total_count + per_page - 1) // per_page
        offset = (page - 1) * per_page
        
        # Get paginated results, ordered by most recent first
        checkins = query.order_by(CheckIn.id.desc()).offset(offset).limit(per_page).all()
        
        # Format results
        checkins_data = []
        for checkin in checkins:
            checkins_data.append({
                "id": checkin.id,
                "stop_id": checkin.stop_id,
                "load_id": checkin.load_id,
                "query": checkin.query,
                "AI_Response_Summary": checkin.AI_Response_Summary,
                "AI_Timestamp": checkin.AI_Timestamp,
                "Issue_Flagged": checkin.Issue_Flagged,
                "Exception_Type": checkin.Exception_Type,
                "Call_confidence_score": checkin.Call_confidence_score,
                "call_trasfered": checkin.call_trasfered,
                "Tags": checkin.Tags,
                "miles": checkin.miles,
                "is_active": checkin.is_active,
                "forms": checkin.forms
            })
        
        return {
            "status": "success",
            "data": {
                "checkins": checkins_data,
                "current_page": page,
                "per_page": per_page,
                "total_count": total_count,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_prev": page > 1
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting checkins list: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get checkins list: {str(e)}")


@router.get("/{checkin_id}")
def get_checkin(checkin_id: int, db: Session = Depends(get_db)):
    """
    Retrieve a check-in by its ID.
    
    Args:
        checkin_id: The ID of the check-in to retrieve
        db: Database session dependency
        
    Returns:
        The check-in object if found
    """
    try:
        checkin = db.query(CheckIn).filter(CheckIn.id == checkin_id).first()
        
        if not checkin:
            raise HTTPException(status_code=404, detail=f"Check-in with ID {checkin_id} not found")
        
        # Get associated RetellCall if exists
        retell_call = db.query(RetellCall).filter(RetellCall.check_in_id == checkin_id).first()
        
        return {
            "status": "success",
            "data": {
                "id": checkin.id,
                "stop_id": checkin.stop_id,
                "load_id": checkin.load_id,
                "query": checkin.query,
                "AI_Response_Summary": checkin.AI_Response_Summary,
                "AI_Timestamp": checkin.AI_Timestamp,
                "Issue_Flagged": checkin.Issue_Flagged,
                "Exception_Type": checkin.Exception_Type,
                "Call_confidence_score": checkin.Call_confidence_score,
                "call_trasfered": checkin.call_trasfered,
                "Tags": checkin.Tags,
                "miles": checkin.miles,
                "is_active": checkin.is_active,
                "forms": checkin.forms,  # Include the forms JSON data
                "call_id": retell_call.call_id if retell_call else None,
                "call_transcript": retell_call.call_transcript if retell_call else None,
                "recording_url": retell_call.recording_url if retell_call else None,
                "check_in_metadata": retell_call.check_in_metadata if retell_call else None
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving check-in: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve check-in: {str(e)}")


def send_checkin_notification(check_in_record: CheckIn, stop_id: int = None, db_session: Session = None):
    """Send notification about new or updated check-in"""
    try:
        # Get stop information if stop_id is provided
        stop = None
        if stop_id and db_session:
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
