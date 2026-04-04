from fastapi import APIRouter, Depends, HTTPException,status
from sqlalchemy.orm import Session
from datetime import datetime,timezone
from typing import Optional
from app.database import get_db
from app.models import Case,CaseAssignment
from app.models import User
from typing import List
from app.schemas.cases import CaseCreate, CaseUpdate, CaseOut,OfficerAssign,AssignedOfficersResponse
from app.schemas.role import RoleEnum
from app.schemas.is_active import IsActive
from app.schemas.audit_event import AuditEvent
from app.schemas.audit import AuditCreate
from app.utils import create_log

from .. import oauth2

router = APIRouter(prefix="/cases", tags=["Cases"])

#  ------------------------------------------------------------------------------------------------------------------------------
# Post only Inspector

@router.post("/", status_code=status.HTTP_201_CREATED, response_model=CaseOut)
def create_case(
    case: CaseCreate, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(oauth2.get_current_user)
):
    if current_user.Role != RoleEnum.inspector:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Inspectors are allowed to create cases"
        )

    # Create the case instance
    new_case = Case(
        Title=case.Title,
        Type=case.Type,
        Status=case.Status,
        Description=case.Description,
        DateOpened=datetime.now(timezone.utc),
        ActingInspectorID = current_user.UserID
    )

    # Add to DB and flush to get the CaseID without committing yet
    db.add( new_case)
    db.flush()  # Ensures new_case.CaseID is generated

    # Assign officers if any
    for officer_id in case.AssignedOfficerIDs:
        officer = db.query(User).filter(User.UserID == officer_id).first()

        if not officer:
            raise HTTPException(status_code=404, detail=f"Officer {officer_id} not found")

        if officer.Role != RoleEnum.officer:
            raise HTTPException(status_code=403, detail="Only officers can be assigned")

        if officer.Status == IsActive.inactive:
            raise HTTPException(status_code=400, detail=f"Officer {officer_id} is inactive")

        assignment = CaseAssignment(
            CaseID=new_case.CaseID,
            AssignedOfficerId=officer_id
        )
        db.add(assignment)

    # Commit everything at once
    db.commit()
    db.refresh(new_case)  # Refresh to get latest data

    Detail_Logs = (
    f"Created Case ID:{new_case.CaseID}, Title:{new_case.Title}, "
    f"Type:{new_case.Type}, Status:{new_case.Status}, Description:{new_case.Description}, "
    f"AssignedOfficers:{case.AssignedOfficerIDs}"
    )
    logs = AuditCreate(UserID=current_user.UserID, EventType=AuditEvent.create, Details=Detail_Logs)
    create_log(logs, db)

    return new_case



@router.post("/{case_id}/assign")
def assign_officers(officer_ids:OfficerAssign,case_id:int,db: Session = Depends(get_db),current_user:User = Depends(oauth2.get_current_user)):
    if (current_user.Role) != RoleEnum.inspector:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Inspectors can assign Officers"
        )
    case = db.query(Case).filter(Case.CaseID == case_id).first()
    if not case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, 
                            detail="Case not found")
    if case.ActingInspectorID != current_user.UserID:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not Your Case"
        )
    
    if not officer_ids:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"No Officer ID's were passed")
    count = 0
    for officer_id in officer_ids.officer_ids:
        officer = db.query(User).filter(User.UserID == officer_id).first()

        if not officer:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                 detail=f"Officer {officer_id} not found")

        if officer.Role != RoleEnum.officer:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                 detail="Only officers can be assigned")

        if officer.Status == IsActive.inactive:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                 detail=f"Officer {officer_id} is inactive")
        existing = db.query(CaseAssignment).filter(
            CaseAssignment.CaseID == case_id,
            CaseAssignment.AssignedOfficerId == officer_id
        ).first()

        if existing:
            continue

        assignment = CaseAssignment(
            CaseID=case_id,
            AssignedOfficerId=officer_id
        )
        db.add(assignment)
        count += 1

    db.commit()
    Detail_Logs = f"Assigned Officers {officer_ids.officer_ids} to Case ID:{case_id}"
    logs = AuditCreate(UserID=current_user.UserID, EventType=AuditEvent.update, Details=Detail_Logs)
    create_log(logs, db)

    return {"message":f"assigned {count} officers to case with id: {case_id}"}



@router.post("/{case_id}/remove-officers",status_code=status.HTTP_204_NO_CONTENT)
def remove_officers(officer_ids:OfficerAssign,case_id:int,db: Session = Depends(get_db),current_user:User = Depends(oauth2.get_current_user)):
    if (current_user.Role) != RoleEnum.inspector:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Inspectors can remove Officers"
        )
    case = db.query(Case).filter(Case.CaseID == case_id).first()

    if not case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, 
                            detail="Case not found")
    
    if case.ActingInspectorID != current_user.UserID:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not Your Case"
        )
    
    if not officer_ids.officer_ids:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"No Officer ID's were passed")
    
    for officer_id in officer_ids.officer_ids:
        assignment = db.query(CaseAssignment).filter(
            CaseAssignment.CaseID == case_id,
            CaseAssignment.AssignedOfficerId == officer_id
        ).first()

        if not assignment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"{officer_id} not assigned"
            )

        db.delete(assignment)

    db.commit()
    Detail_Logs = f"Removed Officers {officer_ids.officer_ids} from Case ID:{case_id}"
    logs = AuditCreate(UserID=current_user.UserID, EventType=AuditEvent.update, Details=Detail_Logs)
    create_log(logs, db)

#  ------------------------------------------------------------------------------------------------------------------------------

@router.get("/", response_model=list[CaseOut],) # Admin + Inspector
def get_cases(db: Session = Depends(get_db),current_user:User = Depends(oauth2.get_current_user),limit: int = 10,
    is_active:Optional[str] = None,
    skip: int = 0,
    search: Optional[str] = None):

    if (current_user.Role) == RoleEnum.officer:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Inspectors/Admins are allowed to see all the cases"
        )
    query = db.query(Case)
    if search:
        query = query.filter(Case.Title.ilike(f"%{search}%"))
    
    if is_active:
        query = query.filter(Case.Status == is_active)

    Detail_Logs = (
    f"Viewed Cases list by UserID:{current_user.UserID}, "
    f"Search:{search}, StatusFilter:{is_active}, Limit:{limit}, Skip:{skip}"
    )
    logs = AuditCreate(UserID=current_user.UserID, EventType=AuditEvent.read, Details=Detail_Logs)
    create_log(logs, db)

    return query.offset(skip).limit(limit).all()



@router.get("/assigned-officers/{case_id}",response_model=List[AssignedOfficersResponse]) # Admin + Inspector(own case)
def get_assigned_officer_Case_id(case_id: int, db: Session = Depends(get_db),
                                 current_user: User = Depends(oauth2.get_current_user)):
    if current_user.Role == RoleEnum.officer:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Inspectors/Admins can see assigned Officers"
        )
    
    case = db.query(Case).filter(Case.CaseID == case_id).first()
    
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Case not found"
        )
    
    if case.ActingInspectorID != current_user.UserID:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not Your Case"
        )
    
    # Query just the AssignedOfficerId column
    officers = (
        db.query(User)
        .join(CaseAssignment, User.UserID == CaseAssignment.AssignedOfficerId)
        .filter(CaseAssignment.CaseID == case_id)
        .all()
    )
    Detail_Logs = (
    f"Viewed assigned officers for Case ID:{case_id}"
    )
    logs = AuditCreate(UserID=current_user.UserID, EventType=AuditEvent.read, Details=Detail_Logs)
    create_log(logs, db)
    
    return officers
    





@router.get("/assigned", response_model=list[CaseOut]) # inspector(own case) + officer
def get_case(db: Session = Depends(get_db),current_user:User = Depends(oauth2.get_current_user)):
    if current_user.Role == RoleEnum.admin:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND
                            , detail=f"No Cases can be assigned to Admins")

    if current_user.Role == RoleEnum.inspector:
        cases = db.query(Case).filter(Case.ActingInspectorID == current_user.UserID).all()
        return cases
    
    cases = db.query(Case).join(CaseAssignment).filter(
        CaseAssignment.AssignedOfficerId == current_user.UserID
    ).all() 
    if not cases:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND
                            , detail=f"No Cases Have been Assigned to Officer with ID {current_user.UserID}")
    
    Detail_Logs = (
    f"Viewed assigned cases for OfficerID:{current_user.UserID}"
    )
    logs = AuditCreate(UserID=current_user.UserID, EventType=AuditEvent.read, Details=Detail_Logs)
    create_log(logs, db)

    return cases


@router.get("/assigned/{officer_id}", response_model=list[CaseOut]) #Admin + Inspector (Cases assigned to a Officer)
def get_case_officer(officer_id:int,db: Session = Depends(get_db),current_user:User = Depends(oauth2.get_current_user)):

    if current_user.Role == RoleEnum.officer:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Inspector/Admis can see the assigned Cases to Any officer"
        )
    
    user = db.query(User).filter(User.UserID == officer_id).first()


    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND
                            , detail=f"No Officer with ID {officer_id}")
    
    if user.Role != RoleEnum.officer:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="the given Id Does Not belong to a Officer"
        )
    
    cases = db.query(Case).join(CaseAssignment).filter(
        CaseAssignment.AssignedOfficerId == officer_id
    ).all() 
    if not cases:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND
                            , detail=f"No Cases Have been Assigned to Officer with ID {officer_id}")

    Detail_Logs = (
    f"Inspector/Admin viewed assigned cases for OfficerID:{officer_id}"
    )
    logs = AuditCreate(UserID=current_user.UserID, EventType=AuditEvent.read, Details=Detail_Logs)
    create_log(logs, db)
    return cases


#  ------------------------------------------------------------------------------------------------------------------------------

@router.put("/{case_id}", response_model=CaseOut) # Inspector (assigned case)
def update_case(case_id: int, update_data: CaseUpdate, db: Session = Depends(get_db),current_user:User = Depends(oauth2.get_current_user)):
    if (current_user.Role) != RoleEnum.inspector:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Inspectors are allowed to update case data"
        )
    
    case = db.query(Case).filter(Case.CaseID == case_id).first()

    if not case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND
                            , detail="Case not found")

    if case.ActingInspectorID != current_user.UserID:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not Your Case"
        )
    
    update_details = []
    for key, value in update_data.model_dump(exclude_unset=True).items():
        old_value = getattr(case, key)
        setattr(case, key, value)
        update_details.append(f"{key}: {old_value} -> {value}")

    db.commit()
    db.refresh(case)
    Detail_Logs = f"Updated Case ID:{case.CaseID}, Changes: {', '.join(update_details)}"
    logs = AuditCreate(UserID=current_user.UserID, EventType=AuditEvent.update, Details=Detail_Logs)
    create_log(logs, db)

    return case

@router.put("/{case_id}/close", response_model=CaseOut) # Inspector (assigned case)
def close_case(case_id: int, db: Session = Depends(get_db),current_user:User = Depends(oauth2.get_current_user)):

    if (current_user.Role) != RoleEnum.inspector:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Inspectors are allowed to Close a Case"
        )

    case = db.query(Case).filter(Case.CaseID == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    if case.ActingInspectorID != current_user.UserID:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not Your Case"
        )
    case.Status = IsActive.inactive
    case.DateClosed = datetime.now(timezone.utc)

    db.commit()
    db.refresh(case)
    Detail_Logs = f"Closed Case ID:{case.CaseID}, Title:{case.Title}, ClosedByUserID:{current_user.UserID}"
    logs = AuditCreate(UserID=current_user.UserID, EventType=AuditEvent.update, Details=Detail_Logs)
    create_log(logs, db)
    return case

#  ------------------------------------------------------------------------------------------------------------------------------


@router.delete("/{case_id}",status_code=status.HTTP_204_NO_CONTENT) #admin
def delete_case(case_id: int, db: Session = Depends(get_db),current_user:User = Depends(oauth2.get_current_user)):
    if (current_user.Role) != RoleEnum.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admins are allowed to delete a case data"
        )
    case = db.query(Case).filter(Case.CaseID == case_id).first()
    if not case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND
                            , detail="Case not found")
    
    
    Detail_Logs = (
    f"Deleted Case ID:{case.CaseID}, Title:{case.Title}, "
    f"Type:{case.Type}, Status:{case.Status}, Description:{case.Description}"
    )
    logs = AuditCreate(UserID=current_user.UserID, EventType=AuditEvent.delete, Details=Detail_Logs)
    create_log(logs, db)

    db.delete(case)
    db.commit()

    