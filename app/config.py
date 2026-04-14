from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_hostname: str
    database_port: str
    database_password: str
    database_name: str
    database_username: str
    secret_key: str
    algorithm: str
    access_token_expire_minutes: int
    sender_mail: str 
    superadmin_mail:str 
    app_password_mail:str 
    app_scheduling_time: int
    bootstrap_admin_name: str = "System Admin"
    bootstrap_admin_badge: str = "ADM00001"
    bootstrap_admin_password: str = "Admin@123"
    bootstrap_admin_email: str = "admin@dems.local"
    bootstrap_admin_contact: str = "xxxxxxxxxx"

    class Config:
        env_file = ".env"

settings = Settings()