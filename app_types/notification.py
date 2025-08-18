from pydantic import BaseModel
from typing import Optional, Dict, Any


class NotificationRecord(BaseModel):
	id: Optional[int] = None
	message: str
	timestamp: Optional[str] = None
	stop_id: Optional[int] = None
	severity: str = "info"
	read: Optional[bool] = None
	notification_type: Optional[str] = None
	check_in_id: Optional[int] = None
	metadata: Optional[Dict[str, Any]] = None


