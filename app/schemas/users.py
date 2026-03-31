from pydantic import BaseModel
from datetime import datetime
from typing import Optional
class UserBase(BaseModel):
    Name: str
    Role: str
    BadgeNumber: str
    Contact: str | None = None
    Status: str = "ACTIVE"


class UserCreate(UserBase):
    Password: str


class UserUpdate(BaseModel):
    Name: Optional[str] = None
    Role: Optional[str] = None
    Contact: Optional[str] = None
    Status: Optional[str] = None
    Password: Optional[str] = None


class UserResponse(UserBase):
    UserID: int
    LastLogin: datetime | None = None

    model_config = {
        "from_attributes": True
    }
class UserResponseCreate(BaseModel):
    UserID: int
    BadgeNumber: str

    model_config = {
        "from_attributes": True
    }

