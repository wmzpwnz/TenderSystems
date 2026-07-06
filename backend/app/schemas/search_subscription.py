from pydantic import BaseModel
from typing import Optional, Dict, List
from datetime import datetime

class SearchSubscriptionBase(BaseModel):
    name: str
    filters: Dict
    notify_email: bool = True
    notify_telegram: bool = True
    is_active: bool = True

class SearchSubscriptionCreate(SearchSubscriptionBase):
    pass

class SearchSubscriptionUpdate(BaseModel):
    name: Optional[str] = None
    filters: Optional[Dict] = None
    notify_email: Optional[bool] = None
    notify_telegram: Optional[bool] = None
    is_active: Optional[bool] = None

class SearchSubscriptionResponse(SearchSubscriptionBase):
    id: int
    user_id: int
    last_checked_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
