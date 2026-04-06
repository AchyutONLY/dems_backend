from pydantic import BaseModel
from datetime import datetime
from typing import Optional
class UserBase(BaseModel):
    Name: str
    Role: str
    BadgeNumber: str
    Contact: str | None = None
    Email: str
    Status: str = "ACTIVE"
    


class UserCreate(BaseModel):
    Name: str
    Role: str
    Contact: str | None = None
    Email: str
    Status: str = "ACTIVE"


class UserUpdate(BaseModel):
    Name: Optional[str] = None
    Role: Optional[str] = None
    Contact: Optional[str] = None
    Status: Optional[str] = None
    # removed allowing the password update


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

class ChangePasswordSchema(BaseModel):
    oldPassword : str
    newPassword : str