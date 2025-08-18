from pydantic import BaseModel
from typing import Optional


class StopRecord(BaseModel):
	id: Optional[int] = None
	name: Optional[str] = None
	location: Optional[str] = None
	eta: Optional[str] = None
	cross_street: Optional[str] = None
	nearest_highway: Optional[str] = None
	is_delayed: Optional[bool] = None
	delay_reason: Optional[str] = None
	expected_location: Optional[str] = None
	reported_location: Optional[str] = None
	is_origin: Optional[bool] = None
	is_destination: Optional[bool] = None


