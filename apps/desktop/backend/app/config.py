"""
Application Configuration for OBS Camera Pro Desktop Backend.
Uses Pydantic BaseSettings for robust environment and file configuration.
"""
from pydantic_settings import BaseSettings
from pydantic import Field
from typing import List
import os

class Settings(BaseSettings):
    APP_NAME: str = "OBS Camera Pro"
    VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    # HTTP & WebSocket Server
    HOST: str = "0.0.0.0"
    PORT: int = 8765
    
    # MediaMTX Streaming Server Configuration
    MEDIAMTX_DIR: str = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../services/mediamtx"))
    MEDIAMTX_EXECUTABLE: str = "mediamtx.exe"
    MEDIAMTX_CONFIG: str = "mediamtx.yml"
    MEDIAMTX_API_URL: str = "http://127.0.0.1:9997"
    MEDIAMTX_WEBRTC_PORT: int = 8889
    MEDIAMTX_RTSP_PORT: int = 8554
    MEDIAMTX_RTMP_PORT: int = 1935
    
    # Database
    DATABASE_URL: str = f"sqlite:///{os.path.abspath(os.path.join(os.path.dirname(__file__), '../obscam.db'))}"
    
    # Security & Pairing
    PAIRING_SECRET_KEY: str = "obs-camera-pro-production-secret-key-2026"
    TOKEN_EXPIRE_HOURS: int = 72
    
    # OBS WebSocket defaults
    OBS_WS_HOST: str = "127.0.0.1"
    OBS_WS_PORT: int = 4455
    OBS_WS_PASSWORD: str = ""
    OBS_AUTO_CREATE_SOURCES: bool = True
    OBS_PRIMARY_SOURCE_TYPE: str = "browser"  # 'browser' or 'rtsp'
    
    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()

