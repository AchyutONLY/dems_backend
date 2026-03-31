from fastapi import APIRouter, Depends, HTTPException,status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import EvidenceItems,User,Case,CaseAssignment
from app.schemas.evidence import EvidenceCreate, EvidenceUpdate, EvidenceResponse
from app.schemas.role import RoleEnum
from .. import oauth2
from typing import Optional
from app.schemas.is_active import IsActive
from app.schemas.audit_event import AuditEvent
from app.schemas.audit_event import AuditEvent
from app.schemas.audit import AuditCreate
from app.utils import create_log

router = APIRouter(prefix="/evidence", tags=["Evidence"])

@router.post("/", status_code=status.HTTP_201_CREATED, response_model=EvidenceResponse)
def add_evidence(
    data: EvidenceCreate, 
    db: Session = Depends(get_db),
    current_user: User = Depends(oauth2.get_current_user)
):
    case = db.query(Case).filter(Case.CaseID == data.CaseID).first()
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Case not found"
        )

    if current_user.Role == RoleEnum.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admins cannot interfere in evidence handling"
        )

    new_evidence = EvidenceItems(
        **data.model_dump(),
        SubmittingOfficerID=current_user.UserID
    )
    db.add(new_evidence)
    db.commit()
    db.refresh(new_evidence)
    Detail_Logs = (
    f"New Evidence Created: EvidenceID={new_evidence.EvidenceID}, "
    f"CaseID={new_evidence.CaseID}, SubmittingOfficerID={current_user.UserID}"
    )
    log_entry = AuditCreate(UserID=current_user.UserID, EventType=AuditEvent.create, Details=Detail_Logs)
    create_log(log_entry, db)
    return new_evidence


@router.get("/case/{case_id}", response_model=list[EvidenceResponse])
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

    if current_user.Role == RoleEnum.officer:
        assigned = db.query(CaseAssignment).filter(
            CaseAssignment.CaseID == case.CaseID,
            CaseAssignment.AssignedOfficerId == current_user.UserID
        ).first()
        if not assigned:
            raise HTTPException(status_code=403, detail="Not your case")

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
    


@router.get("/{evidence_id}", response_model=EvidenceResponse)
def get_evidence(
    evidence_id: int, 
    db: Session = Depends(get_db),
    current_user: User = Depends(oauth2.get_current_user)
):
    ev = db.query(EvidenceItems).filter(EvidenceItems.EvidenceID == evidence_id).first()
    if not ev:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evidence not found")

    case = db.query(Case).filter(Case.CaseID == ev.CaseID).first()
    if not case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")

    if current_user.Role == RoleEnum.officer:
        assigned = db.query(CaseAssignment).filter(
            CaseAssignment.CaseID == case.CaseID,
            CaseAssignment.AssignedOfficerId == current_user.UserID
        ).first()
        if not assigned:
            raise HTTPException(status_code=403, detail="Not your case")
    Detail_Logs = (
        f"Viewed EvidenceID={evidence_id}"
    )
    log_entry = AuditCreate(UserID=current_user.UserID, EventType=AuditEvent.read, Details=Detail_Logs)
    create_log(log_entry, db)
    return ev


@router.put("/{evidence_id}", response_model=EvidenceResponse)
def update_evidence(evidence_id: int, data: EvidenceUpdate, db: Session = Depends(get_db),current_user:User = Depends(oauth2.get_current_user)):
    ev = db.query(EvidenceItems).filter(EvidenceItems.EvidenceID == evidence_id).first()
    if not ev:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evidence not found")
    case = db.query(Case).filter(Case.CaseID == ev.CaseID).first()
    if not case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND
                            , detail="No Case Has been assigned to you")
    if current_user.Role == RoleEnum.officer:
        assigned = db.query(CaseAssignment).filter(
            CaseAssignment.CaseID == case.CaseID,
            CaseAssignment.AssignedOfficerId == current_user.UserID
        ).first()

        if not assigned:
            raise HTTPException(status_code=403, detail="Not your case")
    if case.Status == "Inactive":
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

@router.delete("/{evidence_id}",status_code=status.HTTP_204_NO_CONTENT)
def delete_evidence(evidence_id: int, db: Session = Depends(get_db),current_user:User = Depends(oauth2.get_current_user)):
    if current_user.Role != RoleEnum.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Officers/Inspector cannot delete a Evidence"
        )
    ev = db.query(EvidenceItems).filter(EvidenceItems.EvidenceID == evidence_id).first()
    if not ev:
        raise HTTPException(status_code=404, detail="Evidence not found")
    Detail_Logs = (
    f"Deleted EvidenceID={evidence_id}, CaseID={ev.CaseID}, "
    f"SubmittingOfficerID={ev.SubmittingOfficerID}"
    )
    log_entry = AuditCreate(UserID=current_user.UserID, EventType=AuditEvent.delete, Details=Detail_Logs)
    create_log(log_entry, db)
    db.delete(ev)
    db.commit()
