from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.security.oauth2 import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from .. import database,models,utils,oauth2
from datetime import datetime,timezone
from app.schemas import auth
from sqlalchemy.exc import SQLAlchemyError
from app.schemas.is_active import IsActive
from app.schemas.audit_event import AuditEvent
from app.schemas.audit import AuditCreate
from app.utils import create_log

router = APIRouter(tags=['Authentication'])


@router.post("/login",response_model=auth.Token)
def login(user_credentials: OAuth2PasswordRequestForm = Depends(),db: Session = Depends(database.get_db)):
    user = db.query(models.User).filter(models.User.BadgeNumber == user_credentials.username).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid Credentials"
        )
    if not utils.verify(user_credentials.password, user.Password):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid Credentials"
        )
    if user.Status != "ACTIVE":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"{user.Role} {user.Name} is {IsActive.inactive}"
        )
    access_token = oauth2.create_access_token(
        data={"BadgeNumber": user.BadgeNumber}
    )
    user.LastLogin = datetime.now(timezone.utc)
    try:
        db.commit()
        db.refresh(user)
        
        Detail_Logs = f"User BadgeNumber={user.BadgeNumber} logged in successfully"
        log_entry = AuditCreate(UserID=user.UserID, EventType=AuditEvent.read, Details=Detail_Logs)
        create_log(log_entry, db)
        return {
            "access_token": access_token,
            "token_type": "bearer"
        }
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                             detail="Database Error unable to Update details")
    