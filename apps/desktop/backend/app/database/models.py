"""
SQLAlchemy ORM Models for OBS Camera Pro.
Implements complete schemas for devices, pairings, capabilities, streams, controls, audio, and OBS.
"""
from sqlalchemy import Column, Integer, String, Boolean, Float, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.database.connection import Base

def utcnow():
    return datetime.now(timezone.utc)

class Device(Base):
    __tablename__ = "devices"
    
    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(String(64), unique=True, index=True, nullable=False)
    custom_name = Column(String(100), default="Mobile Camera")
    platform = Column(String(20), default="android")  # android, ios
    model = Column(String(100), default="Unknown Device")
    os_version = Column(String(50), default="")
    app_version = Column(String(20), default="1.0.0")
    connection_type = Column(String(30), default="wifi")  # wifi, usb_tethering
    ip_address = Column(String(45), default="")
    is_active = Column(Boolean, default=False)
    is_paired = Column(Boolean, default=False)
    last_seen = Column(DateTime, default=utcnow)
    created_at = Column(DateTime, default=utcnow)
    
    # Relationships
    pairings = relationship("DevicePairing", back_populates="device", cascade="all, delete-orphan")
    capabilities = relationship("CameraCapability", back_populates="device", uselist=False, cascade="all, delete-orphan")
    camera_settings = relationship("CameraSetting", back_populates="device", uselist=False, cascade="all, delete-orphan")
    audio_settings = relationship("AudioSetting", back_populates="device", uselist=False, cascade="all, delete-orphan")
    stream_sessions = relationship("StreamSession", back_populates="device", cascade="all, delete-orphan")

class DevicePairing(Base):
    __tablename__ = "device_pairings"
    
    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(String(64), ForeignKey("devices.device_id"), nullable=False)
    pairing_token = Column(String(128), unique=True, index=True, nullable=False)
    secret_salt = Column(String(64), nullable=False)
    token_expiry = Column(DateTime, nullable=False)
    is_revoked = Column(Boolean, default=False)
    paired_at = Column(DateTime, default=utcnow)
    
    device = relationship("Device", back_populates="pairings")

class CameraCapability(Base):
    __tablename__ = "camera_capabilities"
    
    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(String(64), ForeignKey("devices.device_id"), unique=True, nullable=False)
    supported_lenses = Column(JSON, default=list)  # ["back_wide", "back_ultrawide", "back_telephoto", "front"]
    supported_resolutions = Column(JSON, default=list)  # ["720p30", "1080p30", "1080p60", "4k30"]
    supports_torch = Column(Boolean, default=True)
    supports_manual_focus = Column(Boolean, default=True)
    supports_manual_exposure = Column(Boolean, default=True)
    supports_manual_wb = Column(Boolean, default=True)
    min_iso = Column(Integer, default=50)
    max_iso = Column(Integer, default=3200)
    min_zoom = Column(Float, default=1.0)
    max_zoom = Column(Float, default=10.0)
    raw_info = Column(JSON, default=dict)
    
    device = relationship("Device", back_populates="capabilities")

class CameraSetting(Base):
    __tablename__ = "camera_settings"
    
    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(String(64), ForeignKey("devices.device_id"), unique=True, nullable=False)
    zoom = Column(Float, default=1.0)
    focus_mode = Column(String(20), default="auto")  # auto, continuous, manual
    focus_distance = Column(Float, default=0.0)
    exposure_mode = Column(String(20), default="auto")
    exposure_compensation = Column(Float, default=0.0)
    iso = Column(Integer, default=100)
    shutter_speed_ns = Column(Integer, default=0)
    white_balance_mode = Column(String(20), default="auto")
    white_balance_temperature = Column(Integer, default=5500)
    torch_enabled = Column(Boolean, default=False)
    torch_level = Column(Float, default=1.0)
    lens = Column(String(30), default="back_wide")
    resolution_profile = Column(String(30), default="1080p30")
    fps = Column(Integer, default=30)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)
    
    device = relationship("Device", back_populates="camera_settings")

class AudioSetting(Base):
    __tablename__ = "audio_settings"
    
    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(String(64), ForeignKey("devices.device_id"), unique=True, nullable=False)
    muted = Column(Boolean, default=False)
    gain = Column(Float, default=1.0)
    input_source = Column(String(50), default="built_in_mic")
    echo_cancellation = Column(Boolean, default=True)
    send_to_obs = Column(Boolean, default=True)
    audio_sync_offset_ms = Column(Integer, default=0)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)
    
    device = relationship("Device", back_populates="audio_settings")

class StreamSession(Base):
    __tablename__ = "stream_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(String(64), ForeignKey("devices.device_id"), nullable=False)
    stream_path = Column(String(100), nullable=False)  # e.g. /camera-cam01
    profile = Column(String(30), default="1080p30")
    status = Column(String(20), default="active")  # active, stopped, error
    started_at = Column(DateTime, default=utcnow)
    stopped_at = Column(DateTime, nullable=True)
    avg_fps = Column(Float, default=0.0)
    avg_bitrate_kbps = Column(Integer, default=0)
    total_bytes = Column(Integer, default=0)
    
    device = relationship("Device", back_populates="stream_sessions")

class StreamProfile(Base):
    __tablename__ = "stream_profiles"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False)  # 720p30, 1080p30, 1080p60, 4k30
    width = Column(Integer, nullable=False)
    height = Column(Integer, nullable=False)
    fps = Column(Integer, nullable=False)
    target_bitrate_kbps = Column(Integer, nullable=False)
    max_bitrate_kbps = Column(Integer, nullable=False)
    video_codec = Column(String(20), default="H264")
    audio_codec = Column(String(20), default="Opus")

class OBSConnection(Base):
    __tablename__ = "obs_connections"
    
    id = Column(Integer, primary_key=True, index=True)
    host = Column(String(100), default="127.0.0.1")
    port = Column(Integer, default=4455)
    password = Column(String(100), default="")
    is_connected = Column(Boolean, default=False)
    auto_create_sources = Column(Boolean, default=True)
    fallback_mode = Column(String(20), default="browser")  # browser, rtsp
    last_connected = Column(DateTime, nullable=True)

class OBSScene(Base):
    __tablename__ = "obs_scenes"
    
    id = Column(Integer, primary_key=True, index=True)
    scene_name = Column(String(100), unique=True, nullable=False)
    is_current = Column(Boolean, default=False)
    source_count = Column(Integer, default=0)

class ApplicationSetting(Base):
    __tablename__ = "application_settings"
    
    key = Column(String(100), primary_key=True, index=True)
    value = Column(Text, nullable=False)
    description = Column(String(255), default="")
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

class EventLog(Base):
    __tablename__ = "event_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    level = Column(String(20), default="INFO")  # INFO, WARNING, ERROR, SUCCESS
    source = Column(String(50), default="system")
    message = Column(String(255), nullable=False)
    details = Column(Text, default="")
    timestamp = Column(DateTime, default=utcnow, index=True)

