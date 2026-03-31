from passlib.context import CryptContext
from fastapi import Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import AuditLog
from app.schemas.audit import AuditCreate
pwd_context = CryptContext(schemes=["bcrypt_sha256"], deprecated="auto")

def hash(password: str):
    return pwd_context.hash(password)

def verify(plain_password,hashed_password):
    return pwd_context.verify(plain_password,hashed_password)


def create_log(data: AuditCreate, db: Session = Depends(get_db)):
    new_log = AuditLog(**data.model_dump())
    db.add(new_log)
    db.commit()
    db.refresh(new_log)
    
