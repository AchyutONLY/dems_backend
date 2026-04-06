from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User
from app.schemas.users import UserCreate, UserUpdate, UserResponse,UserResponseCreate,ChangePasswordSchema
from app.schemas.role import RoleEnum
from sqlalchemy.exc import SQLAlchemyError
from typing import Optional
from .. import oauth2
from app import utils
from app.schemas.is_active import IsActive
from app.schemas.audit_event import AuditEvent
from app.schemas.audit import AuditCreate
from app.utils import create_log,generate_badge,generate_password,send_credentails,send_password_updated
router = APIRouter(prefix="/users", tags=["Users"])

# Only Admins

#  ------------------------------------------------------------------------------------------------------------------------------

@router.post("/",status_code=status.HTTP_201_CREATED ,response_model=UserResponseCreate)
def create_user(user: UserCreate, db: Session = Depends(get_db),current_user:User = Depends(oauth2.get_current_user)):
    if (current_user.Role) != RoleEnum.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admins are allowed to add members"
        )
    try:
        new_badge_number = generate_badge(user.Role,db)
        new_password = generate_password()


        new_user = User(
            Name=user.Name,
            Role=user.Role,
            BadgeNumber=new_badge_number,
            Contact=user.Contact,
            Status=user.Status,
            Password=utils.hash(new_password),
            Email = user.Email
        )
        
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        Detail_Logs = f"New User Created Name:{new_user.Name},Role:{new_user.Role},BadgeNum:{new_user.BadgeNumber}"
        logs = AuditCreate(UserID=current_user.UserID,EventType=AuditEvent.create,Details=Detail_Logs)
        create_log(logs,db)
        send_credentails(new_user.Name,new_user.UserID,new_user.BadgeNumber,new_password,user.Email)
        return new_user

    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail="Internal Server Error")

# ------------------------------------------------------------------------------------------------------------------------------


@router.get("/", response_model=list[UserResponse])
def get_users(
    db: Session = Depends(get_db),current_user:User = Depends(oauth2.get_current_user),
    badge_num:str = None,
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
    if badge_num:
        query = query.filter(User.BadgeNumber == badge_num)
    if search:
        query = query.filter(User.Name.ilike(f"%{search}%"))
    if status_isActive:
        query = query.filter(User.Status == status_isActive)
    Detail_Logs = f"Viewed All User Details"
    logs = AuditCreate(UserID=current_user.UserID, EventType=AuditEvent.read, Details=Detail_Logs)
    create_log(logs, db)

    return query.offset(skip).limit(limit).all()

#  ------------------------------------------------------------------------------------------------------------------------------


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

    # removed the updating password
        
    change_details = []
    for field, value in update_data.items():
        old_value = getattr(user, field)
        setattr(user, field, value)
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
    
#  ------------------------------------------------------------------------------------------------------------------------------

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
    
#  ------------------------------------------------------------------------------------------------------------------------------

# Everyone
@router.post("/change-password")
def change_password(
    password_data: ChangePasswordSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(oauth2.get_current_user)
):
    if not utils.verify(password_data.oldPassword, current_user.Password):
        raise HTTPException(status_code=400, detail="Incorrect password")
    
    if password_data.oldPassword == password_data.newPassword:

        raise HTTPException(status_code=400, detail="New password cannot be same as old password")

    current_user.Password = utils.hash(password_data.newPassword)

    db.commit()
    send_password_updated(current_user.Name,current_user.UserID,current_user.BadgeNumber,current_user.Email)
    return {"message": "Password updated successfully"}