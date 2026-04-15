from fastapi import APIRouter, Depends, HTTPException,status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import EvidenceItems,User,Case,CaseAssignment
from app.schemas.evidence import EvidenceCreate, EvidenceUpdate, EvidenceResponse
from app.schemas.role import RoleEnum
from .. import oauth2
from typing import Optional
from app.schemas.is_active import IsActive
from fastapi.responses import FileResponse
from app.schemas.audit_event import AuditEvent
from app.schemas.audit import AuditCreate
from app.utils import create_log
import os
from urllib.parse import quote

router = APIRouter(prefix="/evidence", tags=["Evidence"])

from fastapi import File, UploadFile, Form
import shutil
import os


UPLOAD_DIR = "evidences"

@router.post("/", status_code=status.HTTP_201_CREATED, response_model=EvidenceResponse) # inspector + officer
def add_evidence(
    CaseID: int = Form(...),
    Description: str = Form(None),
    EvidenceType: str = Form(...),
    SourceOrigin: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(oauth2.get_current_user)
):
    case = db.query(Case).filter(Case.CaseID == CaseID).first()
    if not case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                             detail="Case not found")

    if current_user.Role == RoleEnum.admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, 
                            detail="Admins cannot interfere in evidence handling")
    
    if current_user.Role == RoleEnum.inspector and case.ActingInspectorID != current_user.UserID:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, 
                                    detail="Not Your Case")
    if current_user.Role == RoleEnum.officer:
        case_assignment = db.query(CaseAssignment).filter(CaseAssignment.CaseID == case.CaseID,
                                                          CaseAssignment.AssignedOfficerId == current_user.UserID).first()
        if not case_assignment:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, 
                                    detail="Not Your Case")
        

    new_evidence = EvidenceItems(
        CaseID=CaseID,
        Description=Description,
        EvidenceType=EvidenceType,
        SourceOrigin=SourceOrigin,
        SubmittingOfficerID=current_user.UserID
    )

    db.add(new_evidence)
    db.commit()         
    db.refresh(new_evidence)

   
    case_folder = os.path.join(UPLOAD_DIR, f"case_{new_evidence.CaseID}")
    os.makedirs(case_folder, exist_ok=True)

    _, ext = os.path.splitext(file.filename)

    file_name = f"case_id{new_evidence.CaseID}_evidence_id{new_evidence.EvidenceID}{ext}"

    file_path = os.path.join(case_folder, file_name)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    new_evidence.FilePath = file_path
    db.commit()
    db.refresh(new_evidence)



    Detail_Logs = (
        f"New Evidence Created: EvidenceID={new_evidence.EvidenceID}, "
        f"CaseID={new_evidence.CaseID}, File={file_path}"
    )
    log_entry = AuditCreate(UserID=current_user.UserID, EventType=AuditEvent.create, Details=Detail_Logs)
    create_log(log_entry, db)

    return new_evidence

#  ------------------------------------------------------------------------------------------------------------------------------



@router.get("/{case_id}/{evidence_id}/download") # All 
def download_evidence(
    case_id: int,
    evidence_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(oauth2.get_current_user)
):
    ev = db.query(EvidenceItems).filter(
    EvidenceItems.CaseID == case_id,
    EvidenceItems.EvidenceID == evidence_id).first()

    if not ev:
        raise HTTPException(status_code=404, detail="Evidence not found")

    case = db.query(Case).filter(Case.CaseID == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")


    if not ev.FilePath or not os.path.exists(ev.FilePath):
        raise HTTPException(status_code=404, detail="File not found")

    Detail_Logs = (
        f"Downloaded EvidenceID={evidence_id}, CaseID={case_id}"
    )
    log_entry = AuditCreate(
        UserID=current_user.UserID,
        EventType=AuditEvent.read,
        Details=Detail_Logs
    )
    create_log(log_entry, db)

    file_basename = os.path.basename(ev.FilePath)
    print("Serving file:", ev.FilePath)
    print("Filename:", file_basename)
    return FileResponse(
        path=ev.FilePath,
        filename=file_basename
    )


@router.get("/case/{case_id}", response_model=list[EvidenceResponse]) # All
def list_evidence(
    case_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(oauth2.get_current_user),
    limit: int = 10,
    skip: int = 0,
    search: Optional[str] = None
):
    case = db.query(Case).filter(Case.CaseID == case_id).first()
    if not case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")
    
    
    query = db.query(EvidenceItems).filter(EvidenceItems.CaseID == case_id)
    if search:
        query = query.filter(EvidenceItems.Description.ilike(f"%{search}%"))

    Detail_Logs = (
        f"Viewed evidence list for CaseID={case_id}, "
        f"Search={search}, Limit={limit}, Skip={skip}"
    )
    log_entry = AuditCreate(UserID=current_user.UserID, EventType=AuditEvent.read, Details=Detail_Logs)
    create_log(log_entry, db)
    return query.offset(skip).limit(limit).all()
    



# --------------------------------------------------------------------------------------------------------------------------------------------------

@router.put("/{case_id}/{evidence_id}", response_model=EvidenceResponse) # officer + inspector
def update_evidence(case_id:int,evidence_id: int, data: EvidenceUpdate, db: Session = Depends(get_db),current_user:User = Depends(oauth2.get_current_user)):
    case = db.query(Case).filter(Case.CaseID == case_id).first()
    if not case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND
                            ,detail="No Case found")
    
    ev = db.query(EvidenceItems).filter(EvidenceItems.EvidenceID == evidence_id,EvidenceItems.CaseID == case_id).first()

    if not ev:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evidence not found")
    
    if current_user.Role == RoleEnum.officer:
        assigned = db.query(CaseAssignment).filter(
            CaseAssignment.CaseID == case.CaseID,
            CaseAssignment.AssignedOfficerId == current_user.UserID
        ).first()

        if not assigned:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN
                                , detail="Not your case")
        
    if current_user.Role == RoleEnum.inspector and current_user.UserID != case.ActingInspectorID:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                             detail="Not your case")

    if case.Status == IsActive.inactive:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This Case is Inactive Can't Update the Evidence"
        )

    change_details = []
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        old_value = getattr(ev, field)
        setattr(ev, field, value)
        change_details.append(f"{field}: {old_value} -> {value}")

    Detail_Logs = f"Updated Evidence id:{ev.EvidenceID}, Changes: {', '.join(change_details)}"
    logs = AuditCreate(UserID=current_user.UserID, EventType=AuditEvent.update, Details=Detail_Logs)
    create_log(logs, db)
    db.commit()
    db.refresh(ev)
    return ev




# ------------------------------------------------------------------------------------------------------------------------------

@router.delete("/{evidence_id}", status_code=status.HTTP_204_NO_CONTENT) #admin
def delete_evidence(
    evidence_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(oauth2.get_current_user)
):
    if current_user.Role != RoleEnum.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Officers/Inspector cannot delete a Evidence"
        )

    ev = db.query(EvidenceItems).filter(
        EvidenceItems.EvidenceID == evidence_id
    ).first()

    if not ev:
        raise HTTPException(status_code=404, detail="Evidence not found")

    if ev.FilePath and os.path.exists(ev.FilePath):
        try:
            os.remove(ev.FilePath)
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error deleting file: unable to locate the file"
            )

    Detail_Logs = (
        f"Deleted EvidenceID={evidence_id}, CaseID={ev.CaseID}, "
        f"SubmittingOfficerID={ev.SubmittingOfficerID}"
    )
    log_entry = AuditCreate(
        UserID=current_user.UserID,
        EventType=AuditEvent.delete,
        Details=Detail_Logs
    )
    create_log(log_entry, db)

    db.delete(ev)
    db.commit()
