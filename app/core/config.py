import os
from typing import Optional
from pydantic_settings import BaseSettings

from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    PROJECT_NAME: str = "ZoKe"
    API_V1_STR: str = "/api/v1"
    
    # Database
    DATABASE_URL: str
    
    # Redis
    REDIS_URL: str
    
    # Firebase
    # Default path for local development
    FIREBASE_CREDENTIALS_PATH: str = "firebase_key.json"
    # Alternatively provide the contents as a JSON string for Render
    FIREBASE_CREDENTIALS_JSON: Optional[str] = None
    
    # Security
    SECRET_KEY: str = "super_secret_humor_key"
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "allow"

settings = Settings()
if os.getenv("RENDER"):
    print(f"INFO: Running on Render. Environment variables loaded.")
else:
    print(f"DEBUG: Loaded DATABASE_URL={settings.DATABASE_URL[:10]}...")
