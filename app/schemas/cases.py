from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from typing import List

class CaseBase(BaseModel):
    Title: str
    Type: str
    Status: str
    Description: Optional[str] = None




class CaseCreate(CaseBase):
    AssignedOfficerIDs: List[int]
    pass


class CaseUpdate(BaseModel):
    Title: Optional[str] = None
    Type: Optional[str] = None
    Status: Optional[str] = None
    Description: Optional[str] = None


class CaseOut(CaseBase):
    CaseID: int
    DateOpened: datetime
    DateClosed: Optional[datetime]

    model_config = {
        "from_attributes": True
        }
    
class OfficerAssign(BaseModel):
    officer_ids: list[int]


class AssignedOfficersResponse(BaseModel):
    UserID: int
    BadgeNumber: str
    Status: str
    Contact: str
    Name:str
    Role:str

    model_config = {
        "from_attributes": True
    }