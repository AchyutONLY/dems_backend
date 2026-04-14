from passlib.context import CryptContext
from fastapi import Depends
from sqlalchemy.orm import Session
from app.database import get_db, SessionLocal
from app.models import AuditLog, EvidenceItems, User
from app.schemas.audit import AuditCreate
from app.schemas.role import RoleEnum
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import smtplib
import os
import random
import string
from .config import settings


pwd_context = CryptContext(schemes=["bcrypt_sha256"], deprecated="auto")


def hash(password: str):
    return pwd_context.hash(password)


def verify(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)




def create_log(data: AuditCreate, db: Session = Depends(get_db)):
    new_log = AuditLog(**data.model_dump())
    db.add(new_log)
    db.commit()
    db.refresh(new_log)




def send_email(subject: str, receiver: str, html_content: str):
    sender = settings.sender_mail

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = receiver

    msg.attach(MIMEText(html_content, "html"))

    try:
        with smtplib.SMTP("smtp.gmail.com", 587, timeout=10) as server:
            server.starttls()
            server.login(sender, settings.app_password_mail)
            server.sendmail(sender, receiver, msg.as_string())
    except Exception as e:
        print("Email sending failed:", e)


def base_email_template(title: str, content: str):
    return f"""
    <html>
    <body style="font-family: Inter, Arial, sans-serif; background-color: #f4f6f8; padding: 20px;">
        <div style="max-width: 600px; margin: auto; background: #ffffff; padding: 24px; border-radius: 10px; box-shadow: 0 4px 12px rgba(0,0,0,0.05);">
            
            <h2 style="color: #2f4ea2;">{title}</h2>

            <div style="color: #444; font-size: 14px; line-height: 1.6;">
                {content}
            </div>

            <hr style="margin: 25px 0; border: none; border-top: 1px solid #eee;" />

            <p style="font-size: 12px; color: #888;">
                If you did not expect this email, please contact support.
            </p>

            <p style="font-size: 12px; color: #aaa;">© DEMS System</p>
        </div>
    </body>
    </html>
    """




def send_credentials(username, user_id, badge_number, new_password, mail):
    content = f"""
    <p>Hello <strong>{username}</strong>,</p>

    <p>Your account has been successfully created. Below are your login details:</p>

    <div style="background: #f9fafb; padding: 15px; border-radius: 8px;">
        <p><strong>User ID:</strong> {user_id}</p>
        <p><strong>Badge Number:</strong> {badge_number}</p>
        <p><strong>Temporary Password:</strong> {new_password}</p>
    </div>

    <p>Please log in and change your password immediately.</p>

    <div style="text-align:center; margin-top:20px;">
        <a href="#" style="background:#2f4ea2;color:#fff;padding:10px 20px;border-radius:6px;text-decoration:none;">
            Login to DEMS
        </a>
    </div>
    """

    html = base_email_template("Welcome to DEMS", content)
    send_email("Welcome to DEMS – Your Account Details", mail, html)


def send_password_updated(username, user_id, badge_number, mail):
    content = f"""
    <p>Hello <strong>{username}</strong>,</p>

    <p style="color: green;"><strong>Your password has been successfully updated.</strong></p>

    <div style="background: #f9fafb; padding: 15px; border-radius: 8px;">
        <p><strong>User ID:</strong> {user_id}</p>
        <p><strong>Badge Number:</strong> {badge_number}</p>
    </div>

    <p style="color: red;">
        If you did NOT perform this action, please contact support immediately.
    </p>
    """

    html = base_email_template("Password Updated", content)
    send_email("Password Updated - DEMS", mail, html)


def send_alert_email(missing_files):
    receiver = settings.superadmin_mail

    file_list = "".join([f"<li>{file}</li>" for file in missing_files])

    content = f"""
    <p style="color:red;"><strong>Missing Evidence Files Detected:</strong></p>

    <ul>
        {file_list}
    </ul>
    """

    html = base_email_template("⚠️ Missing Evidence Alert", content)
    send_email("⚠️ Missing Evidence Files Alert", receiver, html)




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




def generate_badge(role: str, db: Session):
    role = role.lower()

    if role == RoleEnum.admin:
        prefix = "ADM"
    elif role == RoleEnum.inspector:
        prefix = "INS"
    elif role == RoleEnum.officer:
        prefix = "OFF"
    else:
        prefix = "USR"

    while True:
        number = random.randint(10000, 99999)
        badge = f"{prefix}{number}"

        exists = db.query(User).filter(User.BadgeNumber == badge).first()
        if not exists:
            return badge


def generate_password(length=10):
    chars = string.ascii_letters + string.digits + "@#$"
    return ''.join(random.choice(chars) for _ in range(length))

