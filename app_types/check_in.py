from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List


class CheckInRecord(BaseModel):
	id: Optional[int] = None
	load_id: Optional[str] = None
	AI_Response_Summary: Optional[str] = Field(default=None, alias="ai_response_summary")
	AI_Timestamp: Optional[str] = Field(default=None, alias="ai_timestamp")
	Issue_Flagged: bool = Field(default=False, alias="issue_flagged")
	Exception_Type: Optional[str] = Field(default=None, alias="exception_type")
	Call_confidence_score: Optional[str] = Field(default=None, alias="confidence_score")
	call_trasfered: Optional[bool] = None
	call_status: Optional[str] = None
	user_picked_up: Optional[bool] = None
	Tags: Optional[List[str]] = Field(default=None, alias="tags")
	miles: Optional[str] = None
	is_active: Optional[bool] = None
	forms: Optional[Dict[str, Any]] = None
	created_at: Optional[str] = None
	updated_at: Optional[str] = None
	# Related retell call data
	call_id: Optional[str] = None
	call_transcript: Optional[str] = None
	recording_url: Optional[str] = None
	check_in_metadata: Optional[Dict[str, Any]] = None

	class Config:
		populate_by_name = True


