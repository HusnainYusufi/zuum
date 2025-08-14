from pydantic import BaseModel
from typing import Optional


class FeedbackRecord(BaseModel):
	id: Optional[int] = None
	feedback_type: str
	user_name: str
	user_email: str
	description: str
	created_at: Optional[str] = None
	resolved: Optional[bool] = None


class FeedbackImageRecord(BaseModel):
	id: Optional[int] = None
	feedback_id: int
	filename: str
	original_filename: Optional[str] = None
	file_path: Optional[str] = None
	uploaded_at: Optional[str] = None
	image_url: Optional[str] = None


