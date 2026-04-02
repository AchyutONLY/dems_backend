from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from .config import settings

# SQLALCHEMY_DATABASE_URL = f'postgresql://{settings.database_username}@{settings.database_hostname}:{settings.database_port}/{settings.database_name}'
# use the above if using without password

SQLALCHEMY_DATABASE_URL = (
    f"postgresql://{settings.database_username}:"
    f"{settings.database_password}@"
    f"{settings.database_hostname}:"
    f"{settings.database_port}/"
    f"{settings.database_name}"
)
# SQLALCHEMY_DATABASE_URL = "postgresql://postgres.sizmrnrfjmmkaikryeak:v3hrS6iUlsjGJ8Bt@aws-1-ap-southeast-1.pooler.supabase.com:5432/postgres"

engine = create_engine(SQLALCHEMY_DATABASE_URL)

SessionLocal = sessionmaker(autoflush=False,autocommit = False,bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()