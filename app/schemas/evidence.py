from pydantic import BaseModel
from datetime import datetime
from typing import Optional
class EvidenceBase(BaseModel):
    CaseID: int
    Description: str | None = None
    EvidenceType: str | None = None
    SourceOrigin: str | None = None
    

class EvidenceCreate(EvidenceBase):
    pass

class EvidenceUpdate(BaseModel):
    Description: Optional[str] = None
    EvidenceType: Optional[str] = None
    SourceOrigin: Optional[str] = None



class EvidenceResponse(EvidenceBase):
    EvidenceID: int

    class Config:
        from_attributes = True