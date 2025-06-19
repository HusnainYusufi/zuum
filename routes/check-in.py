"""
Check-in routes for creating and managing check-ins
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from loguru import logger
from datetime import datetime
from typing import Optional
from pydantic import BaseModel

from db_models import get_db, CheckIn, RetellCall

router = APIRouter(prefix="/api/checkin", tags=["checkin"])


class CreateCheckInRequest(BaseModel):
    stop_id: Optional[int] = None
    load_id: Optional[str] = None
    call_id: str  # Required call_id


@router.post("/create")
async def create_checkin(
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
            Requires_Human_Review=False,
            Tags=None,
            miles=None
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
                "Requires_Human_Review": new_checkin.Requires_Human_Review
            }
        }
        
    except Exception as e:
        logger.error(f"Error creating check-in: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create check-in: {str(e)}")


@router.get("/{checkin_id}")
async def get_checkin(checkin_id: int, db: Session = Depends(get_db)):
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
                "Requires_Human_Review": checkin.Requires_Human_Review,
                "Tags": checkin.Tags,
                "miles": checkin.miles,
                "call_id": retell_call.call_id if retell_call else None,
                "call_transcript": retell_call.call_transcript if retell_call else None,
                "recording_url": retell_call.recording_url if retell_call else None
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving check-in: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve check-in: {str(e)}")
