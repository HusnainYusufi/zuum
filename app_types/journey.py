from pydantic import BaseModel
from typing import Optional, List


class JourneyRecord(BaseModel):
	id: Optional[int] = None
	stop_ids: Optional[List[int]] = None
	current_state: Optional[int] = None


