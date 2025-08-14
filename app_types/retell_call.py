from pydantic import BaseModel
from typing import Optional, Dict, Any


class RetellCallRecord(BaseModel):
	call_id: str
	check_in_id: Optional[int] = None
	call_transcript: Optional[str] = None
	recording_url: Optional[str] = None
	output_data: Optional[Dict[str, Any]] = None


