from passlib.context import CryptContext
from fastapi import Depends
from sqlalchemy.orm import Session
from app.database import get_db,SessionLocal
from app.models import AuditLog,EvidenceItems
from app.schemas.audit import AuditCreate
import os
import smtplib
from email.mime.text import MIMEText
from .config import settings

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
    


def check_missing_files():
    db: Session = SessionLocal()

    try:
        evidences = db.query(EvidenceItems).all()

        missing_files = []

        for ev in evidences:
            if ev.FilePath and not os.path.exists(ev.FilePath):
                missing_files.append(
                    f"EvidenceID={ev.EvidenceID}, CaseID={ev.CaseID}, Path={ev.FilePath}"
                )

        if missing_files:
            send_alert_email(missing_files)

    finally:
        db.close()



def send_alert_email(missing_files):
    sender = settings.sender_mail
    receiver = settings.superadmin_mail

    body = "Missing Evidence Files Detected:\n\n" + "\n".join(missing_files)

    msg = MIMEText(body)
    msg["Subject"] = "⚠️ Missing Evidence Files Alert"
    msg["From"] = sender
    msg["To"] = receiver
    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(sender, settings.app_password_mail)  
            server.sendmail(sender, receiver, msg.as_string())
    except Exception as e:
        print("Email sending failed:", e)