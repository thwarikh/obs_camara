"""
Remote Camera Control REST API.
Dispatches control commands to mobile phones via WebSocket and updates SQLite database.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any

from app.database.connection import get_db
from app.database.models import CameraSetting, Device, CameraCapability
from app.websocket.ws_manager import ws_manager

router = APIRouter(prefix="/api/controls", tags=["controls"])

class CameraControlRequest(BaseModel):
    device_id: str
    zoom: Optional[float] = Field(None, ge=1.0, le=20.0)
    focus_mode: Optional[str] = None  # auto, continuous, manual
    focus_distance: Optional[float] = Field(None, ge=0.0, le=1.0)
    exposure_mode: Optional[str] = None  # auto, manual
    exposure_compensation: Optional[float] = Field(None, ge=-4.0, le=4.0)
    iso: Optional[int] = Field(None, ge=25, le=12800)
    shutter_speed_ns: Optional[int] = None
    white_balance_mode: Optional[str] = None  # auto, incandescent, daylight, etc.
    white_balance_temperature: Optional[int] = Field(None, ge=2000, le=10000)
    torch_enabled: Optional[bool] = None
    torch_level: Optional[float] = Field(None, ge=0.0, le=1.0)
    lens: Optional[str] = None  # back_wide, back_ultrawide, back_telephoto, front
    resolution_profile: Optional[str] = None  # 720p30, 1080p30, 1080p60, 4k30
    fps: Optional[int] = None

@router.post("")
async def apply_camera_control(payload: CameraControlRequest, db: Session = Depends(get_db)):
    """
    Validates requested camera control parameters, persists in database,
    and forwards realtime command packet to the target phone via WebSocket.
    """
    device = db.query(Device).filter(Device.device_id == payload.device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    settings_obj = db.query(CameraSetting).filter(CameraSetting.device_id == payload.device_id).first()
    if not settings_obj:
        settings_obj = CameraSetting(device_id=payload.device_id)
        db.add(settings_obj)

    command_dict: Dict[str, Any] = {"type": "camera_control_command", "device_id": payload.device_id}

    if payload.zoom is not None:
        settings_obj.zoom = payload.zoom
        command_dict["zoom"] = payload.zoom
    if payload.focus_mode is not None:
        settings_obj.focus_mode = payload.focus_mode
        command_dict["focus_mode"] = payload.focus_mode
    if payload.focus_distance is not None:
        settings_obj.focus_distance = payload.focus_distance
        command_dict["focus_distance"] = payload.focus_distance
    if payload.exposure_mode is not None:
        settings_obj.exposure_mode = payload.exposure_mode
        command_dict["exposure_mode"] = payload.exposure_mode
    if payload.exposure_compensation is not None:
        settings_obj.exposure_compensation = payload.exposure_compensation
        command_dict["exposure_compensation"] = payload.exposure_compensation
    if payload.iso is not None:
        settings_obj.iso = payload.iso
        command_dict["iso"] = payload.iso
    if payload.shutter_speed_ns is not None:
        settings_obj.shutter_speed_ns = payload.shutter_speed_ns
        command_dict["shutter_speed_ns"] = payload.shutter_speed_ns
    if payload.white_balance_mode is not None:
        settings_obj.white_balance_mode = payload.white_balance_mode
        command_dict["white_balance_mode"] = payload.white_balance_mode
    if payload.white_balance_temperature is not None:
        settings_obj.white_balance_temperature = payload.white_balance_temperature
        command_dict["white_balance_temperature"] = payload.white_balance_temperature
    if payload.torch_enabled is not None:
        settings_obj.torch_enabled = payload.torch_enabled
        command_dict["torch_enabled"] = payload.torch_enabled
    if payload.torch_level is not None:
        settings_obj.torch_level = payload.torch_level
        command_dict["torch_level"] = payload.torch_level
    if payload.lens is not None:
        settings_obj.lens = payload.lens
        command_dict["lens"] = payload.lens
    if payload.resolution_profile is not None:
        settings_obj.resolution_profile = payload.resolution_profile
        command_dict["resolution_profile"] = payload.resolution_profile

    db.commit()

    # Forward to phone
    delivered = await ws_manager.send_control_to_camera(payload.device_id, command_dict)

    # Broadcast to other desktop UI sessions so UI state matches
    await ws_manager.broadcast_to_desktop({
        "type": "camera_settings_updated",
        "device_id": payload.device_id,
        "settings": command_dict
    })

    return {
        "status": "applied" if delivered else "cached",
        "delivered_to_device": delivered,
        "device_id": payload.device_id,
        "command": command_dict
    }

