from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import engine, Base, SessionLocal
from app.routers import users, auth,cases,evidence,custody,audit
from apscheduler.schedulers.background import BackgroundScheduler
from .utils import check_missing_files, hash
from .models import User
app = FastAPI()
scheduler = BackgroundScheduler()
from datetime import datetime
from .config import settings

scheduler.add_job(
    check_missing_files,
    "interval",
    minutes=1,
    next_run_time=datetime.now()  
)

@app.on_event("startup")
def start_scheduler():
    scheduler.add_job(check_missing_files, "interval", minutes=settings.app_scheduling_time)  # ⏱ every 5 min
    scheduler.start()

@app.on_event("shutdown")
def stop_scheduler():
    scheduler.shutdown()

Base.metadata.create_all(bind=engine)


def ensure_bootstrap_admin():
    db = SessionLocal()
    try:
        existing_admin = db.query(User).filter(User.Role == "admin").first()
        if existing_admin:
            return

        desired_badge = settings.bootstrap_admin_badge.strip() or "ADM00001"
        badge_taken = db.query(User).filter(User.BadgeNumber == desired_badge).first()
        badge = "ADM00001" if badge_taken else desired_badge
        if badge_taken and desired_badge == "ADM00001":
            badge = f"ADM{datetime.now().strftime('%H%M%S')}"

        bootstrap_admin = User(
            Name=settings.bootstrap_admin_name,
            Role="admin",
            BadgeNumber=badge,
            Contact=settings.bootstrap_admin_contact or None,
            Status="ACTIVE",
            Password=hash(settings.bootstrap_admin_password),
            Email=settings.bootstrap_admin_email,
        )
        db.add(bootstrap_admin)
        db.commit()
        print(
            "Bootstrap admin created. "
            f"Badge: {bootstrap_admin.BadgeNumber}, "
            f"Password: {settings.bootstrap_admin_password}"
        )
    finally:
        db.close()


@app.on_event("startup")
def startup_tasks():
    ensure_bootstrap_admin()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(users.router)
app.include_router(cases.router)
app.include_router(evidence.router)
app.include_router(custody.router)
app.include_router(audit.router)
app.include_router(auth.router)


@app.get("/")
def root():
    return {"status":"running"}