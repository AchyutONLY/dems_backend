from passlib.context import CryptContext
from fastapi import Depends
from sqlalchemy.orm import Session
from app.database import get_db,SessionLocal
from app.models import AuditLog,EvidenceItems,User
from app.schemas.audit import AuditCreate
from app.schemas.role import RoleEnum
import os
import smtplib
from email.mime.text import MIMEText
from .config import settings
import random
import string

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
    

# def send_email(receiver: str, subject: str, body: str):
#     sender = settings.sender_mail

#     msg = MIMEText(body)
#     msg["Subject"] = subject
#     msg["From"] = sender
#     msg["To"] = receiver

#     try:
#         with smtplib.SMTP("smtp.gmail.com", 587) as server:
#             server.starttls()
#             server.login(sender, settings.app_password_mail)
#             server.sendmail(sender, receiver, msg.as_string())
#     except Exception as e:
#         print("Email sending failed:", e)


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
    print(body)
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



def send_credentails(username,user_id,badge_number,new_password,mail):
    sender = settings.sender_mail
    receiver = mail

    body = f'''
Hello {username},

Your account has been created.
UserID : {user_id}
Badge Number: {badge_number}
Temporary Password: {new_password}

Please login and change your password.
'''

    msg = MIMEText(body)
    msg["Subject"] = "Your Account Created at DEMS"
    msg["From"] = sender
    msg["To"] = receiver
    print(sender)
    print(receiver)
    print(msg.as_string())
    try:
            
        with smtplib.SMTP("smtp.gmail.com", 587,timeout=10) as server:
            server.starttls()
            server.login(sender, settings.app_password_mail)
            print(sender)
            print(receiver)
            print(msg.as_string())  
            server.sendmail(sender, receiver, msg.as_string())
    except Exception as e:
        print("Email sending failed:", e)




def send_password_updated(username, user_id, badge_number, mail):
    sender = settings.sender_mail
    receiver = mail

    body = f'''
Hello {username},

Your password has been successfully updated.

UserID: {user_id}
Badge Number: {badge_number}

If you did NOT perform this action, please contact support immediately.

Regards,  
DEMS Team
'''


    msg = MIMEText(body)
    msg["Subject"] = "Password Updated - DEMS"
    msg["From"] = sender
    msg["To"] = receiver
    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(sender, settings.app_password_mail)  
            print(sender)
            print(receiver)
            print(msg.as_string())
            server.sendmail(sender, receiver, msg.as_string())
    except Exception as e:
        print("Email sending failed:", e)

def generate_badge(role: str, db: Session):

    if role.lower() == RoleEnum.admin:
        prefix = "ADM"
    elif role.lower() == RoleEnum.inspector:
        prefix = "INS"
    elif role.lower() == RoleEnum.officer:
        prefix = "OFF"
    


    while True:
        number = random.randint(10000, 99999)
        badge = f"{prefix}{number}"

        exists = db.query(User).filter(User.BadgeNumber == badge).first()
        if not exists:
            return badge
        


def generate_password(length=10):
    chars = string.ascii_letters + string.digits + "@#$"
    return ''.join(random.choice(chars) for _ in range(length))



