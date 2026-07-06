from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class FavoriteToggle(BaseModel):
    tender_id: str  # Может быть числовым ID или EIS ID

class CRMStatusUpdate(BaseModel):
    status: str
    notes: Optional[str] = None

class CRMItem(BaseModel):
    id: int
    tender_id: int
    status: str
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
