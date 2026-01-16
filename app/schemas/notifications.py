from typing import List, Optional, Dict

from pydantic import BaseModel, EmailStr, Field


class AdminNotificationRequest(BaseModel):
    title: str = Field(..., min_length=1)
    body: str = Field(..., min_length=1)
    audience: str = "all"
    user_ids: Optional[List[int]] = None
    emails: Optional[List[EmailStr]] = None
    data: Optional[Dict[str, str]] = None
