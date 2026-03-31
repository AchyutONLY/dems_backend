from fastapi import APIRouter, Depends,HTTPException,status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import AuditLog,User
from app.schemas.audit import AuditResponse
from app.schemas.audit_event import AuditEvent
from app.utils import create_log
from .. import oauth2
from fastapi import Query
from datetime import datetime
from typing import Optional
from app.models import AuditLog
from app.schemas.role import RoleEnum
from app.schemas.audit import AuditCreate

router = APIRouter(prefix="/audit", tags=["Audit Log"])


@router.get("/", response_model=list[AuditResponse])
def get_logs(
    db: Session = Depends(get_db),
    current_user: User = Depends(oauth2.get_current_user),
    limit: int = Query(50, ge=1, le=1000),  # Default 50, max 1000
    skip: int = Query(0, ge=0),
    user_id: Optional[int] = Query(None, description="Filter by UserID"),
    search: Optional[str] = Query(None, description="Search in description"),
    from_date: Optional[datetime] = Query(None, description="Start of date range"),
    to_date: Optional[datetime] = Query(None, description="End of date range")
):
    # Only admins allowed
    if current_user.Role != RoleEnum.admin:
        raise HTTPException(
            status_code=403,
            detail="Only admins can view audit logs"
        )

    query = db.query(AuditLog)

    if user_id is not None:
        query = query.filter(AuditLog.UserID == user_id)

    if search:
        query = query.filter(AuditLog.Details.ilike(f"%{search}%"))

    if from_date:
        query = query.filter(AuditLog.Timestamp >= from_date)

    if to_date:
        query = query.filter(AuditLog.Timestamp <= to_date)

    # Most recent first
    query = query.order_by(AuditLog.Timestamp.desc())

    # Fetch results with pagination
    logs_list = query.offset(skip).limit(limit).all()

    # Create audit entry for viewing logs
    filter_details = []
    if user_id: filter_details.append(f"user_id={user_id}")
    if search: filter_details.append(f"search='{search}'")
    if from_date: filter_details.append(f"from_date={from_date.isoformat()}")
    if to_date: filter_details.append(f"to_date={to_date.isoformat()}")
    filter_details.append(f"limit={limit}")
    filter_details.append(f"skip={skip}")
    
    Detail_Logs = f"Viewed audit logs with filters: {', '.join(filter_details)}"
    log_entry = AuditCreate(
        UserID=current_user.UserID,
        EventType=AuditEvent.read,
        Details=Detail_Logs
    )
    create_log(log_entry, db)

    return logs_list