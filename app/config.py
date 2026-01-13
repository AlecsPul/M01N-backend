"""
Application Configuration
"""
from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    """Application settings"""
    # Application
    app_name: str = "M01N API"
    app_version: str = "1.0.0"
    debug: bool = True
    
    # Supabase
    supabase_url: str
    supabase_key: str
    
    # Database
    database_url: str
    
    # OpenAI
    openai_api_key: str
    
    # Security
    secret_key: str = "change-this-to-a-secure-secret-key"
    
    # CORS
    allowed_origins: str = "*"
    
    @property
    def cors_origins(self) -> List[str]:
        """Parse CORS origins from comma-separated string"""
        if self.allowed_origins == "*":
            return ["*"]
        return [origin.strip() for origin in self.allowed_origins.split(",")]
    
    class Config:
        env_file = ".env"
        case_sensitive = False

settings = Settings()
