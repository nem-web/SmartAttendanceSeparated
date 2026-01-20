import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """ML Service Settings"""
    
    # Service Info
    SERVICE_NAME: str = "ML Service"
    SERVICE_VERSION: str = "1.0.0"
    
    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8001
    
    # ML Parameters
    ML_MODEL: str = "hog"  # hog or cnn
    NUM_JITTERS: int = 5
    MIN_FACE_AREA_RATIO: float = 0.04
    
    # CORS
    CORS_ORIGINS: list = ["http://localhost:8000", "http://localhost:5173"]
    
    # Logging
    LOG_LEVEL: str = "info"
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
