"""
Application Configuration
"""
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """Application settings"""
    app_name: str = "M01N API"
    app_version: str = "1.0.0"
    debug: bool = True
    database_url: str = "sqlite:///./test.db"
    
    class Config:
        env_file = ".env"

settings = Settings()
