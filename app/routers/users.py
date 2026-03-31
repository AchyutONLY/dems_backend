from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User
from app.schemas.users import UserCreate, UserUpdate, UserResponse,UserResponseCreate
from app.schemas.role import RoleEnum
from sqlalchemy.exc import SQLAlchemyError
from typing import Optional
from .. import oauth2
from app import utils
from app.schemas.is_active import IsActive
from app.schemas.audit_event import AuditEvent
from app.schemas.audit import AuditCreate
from app.utils import create_log
router = APIRouter(prefix="/users", tags=["Users"])



@router.post("/",status_code=status.HTTP_201_CREATED ,response_model=UserResponseCreate)
def create_user(user: UserCreate, db: Session = Depends(get_db),current_user:User = Depends(oauth2.get_current_user)):
    if (current_user.Role) != RoleEnum.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admins are allowed to add members"
        )
    try:
        existing = db.query(User).filter(User.BadgeNumber == user.BadgeNumber).first()
        if existing:
            raise HTTPException(status_code=400, detail="BadgeNumber already exists")

        new_user = User(
            Name=user.Name,
            Role=user.Role,
            BadgeNumber=user.BadgeNumber,
            Contact=user.Contact,
            Status=user.Status,
            Password=utils.hash(user.Password)
        )
        
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        Detail_Logs = f"New User Created Name:{new_user.Name},Role:{new_user.Role},BadgeNum:{new_user.BadgeNumber}"
        logs = AuditCreate(UserID=current_user.UserID,EventType=AuditEvent.create,Details=Detail_Logs)
        create_log(logs,db)
        return new_user

    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail="Internal Server Error")


@router.get("/", response_model=list[UserResponse])
def get_users(
    db: Session = Depends(get_db),current_user:User = Depends(oauth2.get_current_user),
    status_isActive: str = None,
    limit: int = 10,
    skip: int = 0,
    search: Optional[str] = None
):
    if (current_user.Role) != RoleEnum.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admins are allowed to view members"
        )
    query = db.query(User)

    if search:
        query = query.filter(User.Name.ilike(f"%{search}%"))
    if status_isActive:
        query = query.filter(User.Status == status_isActive)
    Detail_Logs = f"Viewed All User Details"
    logs = AuditCreate(UserID=current_user.UserID, EventType=AuditEvent.read, Details=Detail_Logs)
    create_log(logs, db)

    return query.offset(skip).limit(limit).all()



@router.get("/{badge_num}", response_model=UserResponse)
def get_user(badge_num: str, db: Session = Depends(get_db),current_user:User = Depends(oauth2.get_current_user)):
    if (current_user.Role) != RoleEnum.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admins are allowed to view a member"
        )
    user = db.query(User).filter(User.BadgeNumber == badge_num).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found")
    
    Detail_Logs = f"Viewed User BadgeNumber:{user.BadgeNumber}"
    logs = AuditCreate(UserID=current_user.UserID, EventType=AuditEvent.read, Details=Detail_Logs)
    create_log(logs, db)
    return user


@router.put("/{badge_num}", response_model=UserResponse)
def update_user(badge_num: str, data: UserUpdate, db: Session = Depends(get_db),
                current_user:User = Depends(oauth2.get_current_user)):
    if (current_user.Role) != RoleEnum.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admins are allowed to view a update a member info"
        )
    user = db.query(User).filter(User.BadgeNumber == badge_num).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    update_data = data.model_dump(exclude_unset=True)

    
    
    if "Password" in update_data:
        update_data["Password"] = utils.hash(update_data.pop("Password"))
        
    change_details = []
    for field, value in update_data.items():
        old_value = getattr(user, field)
        setattr(user, field, value)
        if field == "Password":
            change_details.append(f"{field}: updated password")
        else:
            change_details.append(f"{field}: {old_value} -> {value}")

    try:
        db.commit()
        db.refresh(user)

        Detail_Logs = f"Updated User BadgeNumber:{user.BadgeNumber}, Changes: {', '.join(change_details)}"
        logs = AuditCreate(UserID=current_user.UserID, EventType=AuditEvent.update, Details=Detail_Logs)
        create_log(logs, db)
        return user
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                             detail="Database Error unable to Update details")

@router.delete("/{badge_num}",status_code=status.HTTP_204_NO_CONTENT)
def delete_user(badge_num: str, db: Session = Depends(get_db),current_user:User = Depends(oauth2.get_current_user)):
    if (current_user.Role) != RoleEnum.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admins are allowed to delete a members information"
        )

    user = db.query(User).filter(User.BadgeNumber == badge_num).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="User not found")
    
    if current_user.BadgeNumber == badge_num:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cant remove the current logged in Admin"
        )
    # Prepare log details before deletion
    Detail_Logs = f"Deleted User BadgeNumber:{user.BadgeNumber}, Name:{user.Name}, Role:{user.Role}, Contact:{user.Contact}, Status:{user.Status}"
    logs = AuditCreate(UserID=current_user.UserID, EventType=AuditEvent.delete, Details=Detail_Logs)
    create_log(logs, db)

    try:
        db.delete(user)
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
                            detail="Database Error,Unable to delete the user")
    



