from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import CustodyRecords
from app.schemas.custody import CustodyCreate, CustodyUpdate, CustodyResponse
from app.schemas.role import RoleEnum
from .. import oauth2
from app.schemas.is_active import IsActive
from app.schemas.audit_event import AuditEvent
from app.schemas.audit import AuditCreate
from app.utils import create_log


router = APIRouter(prefix="/custody", tags=["Custody"])
#  ---------------------------------------------------------------------------------------------------------------------
# Only inspectors can add custody records
@router.post("/", response_model=CustodyResponse, status_code=status.HTTP_201_CREATED)
def add_custody(
    data: CustodyCreate,
    db: Session = Depends(get_db),
    current_user=Depends(oauth2.get_current_user)
):
    
    if current_user.Role != RoleEnum.inspector:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Not authorized to add custody records")

    search_query = db.query(CustodyRecords).filter(CustodyRecords.EvidenceID == data.EvidenceID,
                                                   CustodyRecords.ActingOfficerID == data.ActingOfficerID).first()
    
    if search_query:
        raise HTTPException(
            status_code = status.HTTP_403_FORBIDDEN,
            detail = "Custody Already Exist for Modification go to modify option"
        )


    new_record = CustodyRecords(**data.model_dump())
    db.add(new_record)
    db.commit()
    db.refresh(new_record)

    Detail_Logs = f"New Custody Record created: RecordID={new_record.RecordID}"
    log_entry = AuditCreate(UserID=current_user.UserID, EventType=AuditEvent.create, Details=Detail_Logs)
    create_log(log_entry, db)
    return new_record

#  ----------------------------------------------------------------------------------------------------
@router.get("/", response_model=list[CustodyResponse]) # All
def list_custody(
    db: Session = Depends(get_db),
    current_user=Depends(oauth2.get_current_user),
    limit: int = 10,
    skip: int = 0,
    ActingOfficerID: int = None,
    Evidence_id:int = None,
):
    query = db.query(CustodyRecords)

    if Evidence_id:
        query = query.filter(CustodyRecords.EvidenceID == Evidence_id)

    if ActingOfficerID:
        query = query.filter(CustodyRecords.ActingOfficerID == ActingOfficerID)

    Detail_Logs = f"Viewed All User Details with limit:{limit},offset:{skip},Acting Officer ID:{ActingOfficerID}"
    logs = AuditCreate(UserID=current_user.UserID, EventType=AuditEvent.read, Details=Detail_Logs)
    create_log(logs, db)
    return query.offset(skip).limit(limit).all()


@router.get("/{record_id}", response_model=CustodyResponse) #All
def get_record(
    record_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(oauth2.get_current_user)
):
    record = db.query(CustodyRecords).filter(CustodyRecords.RecordID == record_id).first()
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Record not found")
    
    Detail_Logs = f"Viewed Custody RecordID={record_id}"
    log_entry = AuditCreate(UserID=current_user.UserID, EventType=AuditEvent.read, Details=Detail_Logs)
    create_log(log_entry, db)

    return record

#  ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
# Only inspectors can update
@router.put("/{record_id}", response_model=CustodyResponse)
def update_record(
    record_id: int,
    data: CustodyUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(oauth2.get_current_user)
):
    
    if current_user.Role == RoleEnum.officer:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Not authorized to update custody records")

    record = db.query(CustodyRecords).filter(CustodyRecords.RecordID == record_id).first()
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Record not found")

    change_details = []
    for field, value in data.model_dump(exclude_unset=True).items():
        old_value = getattr(record, field)
        setattr(record, field, value)
        change_details.append(f"{field}: {old_value} -> {value}")

    Detail_Logs = f"Updated Custody RecordID={record.RecordID}, Changes: {', '.join(change_details)}"
    log_entry = AuditCreate(UserID=current_user.UserID, EventType=AuditEvent.update, Details=Detail_Logs)
    create_log(log_entry, db)

    db.commit()
    db.refresh(record)
    return record

# ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
# only admins
@router.delete("/{record_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_record(
    record_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(oauth2.get_current_user)
):
    # Only admins can delete
    if current_user.Role != RoleEnum.admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Only admins can delete custody records")

    record = db.query(CustodyRecords).filter(CustodyRecords.RecordID == record_id).first()
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Record not found")
    
    Detail_Logs = f"Deleted Custody RecordID={record.RecordID}"
    log_entry = AuditCreate(UserID=current_user.UserID, EventType=AuditEvent.delete, Details=Detail_Logs)
    create_log(log_entry, db)
    db.delete(record)
    db.commit()
    return