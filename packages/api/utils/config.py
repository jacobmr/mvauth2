from pydantic_settings import BaseSettings
from typing import Optional
import os

class Settings(BaseSettings):
    # Database
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./community_auth.db")
    
    # Supabase settings
    supabase_service_key: str = os.getenv("SUPABASE_SERVICE_KEY", "")
    
    # Clerk.com settings
    clerk_publishable_key: str = os.getenv("CLERK_PUBLISHABLE_KEY", "")
    clerk_secret_key: str = os.getenv("CLERK_SECRET_KEY", "")
    clerk_jwt_verification_url: str = "https://api.clerk.com/v1/jwks"
    
    # JWT settings for service tokens
    jwt_secret_key: str = os.getenv("JWT_SECRET_KEY", "your-super-secret-key-change-in-production")
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24 * 7  # 7 days
    
    # Service-to-service authentication
    service_token: str = os.getenv("SERVICE_TOKEN", "your-service-token-change-in-production")
    
    # Community settings
    community_name: str = os.getenv("COMMUNITY_NAME", "Your Community")
    admin_emails: list[str] = os.getenv("ADMIN_EMAILS", "").split(",")
    
    class Config:
        env_file = ".env"

settings = Settings()