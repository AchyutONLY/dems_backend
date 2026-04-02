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

    class Config:
        env_file = ".env"

settings = Settings()