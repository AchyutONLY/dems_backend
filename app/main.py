from fastapi import FastAPI
from app.database import engine,Base
from app.routers import users, auth,cases,evidence,custody,audit
from apscheduler.schedulers.background import BackgroundScheduler
from .utils import check_missing_files
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

app.include_router(users.router)
app.include_router(cases.router)
app.include_router(evidence.router)
app.include_router(custody.router)
app.include_router(audit.router)
app.include_router(auth.router)


@app.get("/")
def root():
    return {"status":"running"}