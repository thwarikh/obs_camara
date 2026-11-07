"""
Device management REST API endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from pydantic import BaseModel

from app.database.connection import get_db
from app.database.models import Device, CameraCapability, CameraSetting, AudioSetting, EventLog
from app.devices.device_manager import device_manager
from app.streaming.stream_manager import stream_manager
from app.services.network_service import NetworkService
from app.websocket.ws_manager import ws_manager

router = APIRouter(prefix="/api/devices", tags=["devices"])

class DeviceRegisterRequest(BaseModel):
    device_id: str
    custom_name: Optional[str] = None
    platform: str
    model: str
    os_version: str = ""
    token: str
    ip_address: Optional[str] = None

class DeviceRenameRequest(BaseModel):
    custom_name: str

class CapabilitiesReportRequest(BaseModel):
    supported_lenses: List[str]
    supported_resolutions: List[str]
    supports_torch: bool = True
    supports_manual_focus: bool = True
    supports_manual_exposure: bool = True
    supports_manual_wb: bool = True
    min_iso: int = 50
    max_iso: int = 3200
    min_zoom: float = 1.0
    max_zoom: float = 10.0
    raw_info: Dict[str, Any] = {}

@router.get("")
def list_devices(db: Session = Depends(get_db)):
    """
    Returns all registered devices with their online status, telemetry, and stream links.
    """
    devices = db.query(Device).all()
    host_ip = NetworkService.get_local_ip()
    result = []

    for d in devices:
        telemetry = device_manager.get_telemetry(d.device_id)
        stream_urls = stream_manager.get_stream_urls(d.device_id, host_ip)
        is_online = d.device_id in ws_manager.camera_clients

        result.append({
            "id": d.id,
            "device_id": d.device_id,
            "custom_name": d.custom_name,
            "platform": d.platform,
            "model": d.model,
            "os_version": d.os_version,
            "connection_type": d.connection_type,
            "ip_address": d.ip_address,
            "is_active": d.is_active,
            "is_online": is_online,
            "last_seen": d.last_seen.isoformat() if d.last_seen else None,
            "telemetry": telemetry,
            "stream_urls": stream_urls
        })

    return {"devices": result, "total": len(result)}

@router.get("/pair")
@router.post("/pair")
def create_pairing(host_ip: Optional[str] = None):
    """
    Generates QR code and pairing credentials for mobile app scanning.
    Supports both GET and POST.
    """
    return device_manager.generate_pairing_payload(host_ip)

@router.post("/register")
def register_device(payload: DeviceRegisterRequest, db: Session = Depends(get_db)):
    """
    Called by mobile app upon pairing to register device hardware.
    """
    device = device_manager.register_or_update_device(
        db=db,
        device_id=payload.device_id,
        custom_name=payload.custom_name or f"{payload.platform.capitalize()} Camera",
        platform=payload.platform,
        model=payload.model,
        os_version=payload.os_version,
        ip_address=payload.ip_address or ""
    )

    log_entry = EventLog(
        level="SUCCESS",
        source="device",
        message=f"Device paired: {device.custom_name} ({device.device_id})"
    )
    db.add(log_entry)
    db.commit()

    host_ip = NetworkService.get_local_ip()
    stream_urls = stream_manager.get_stream_urls(device.device_id, host_ip)

    return {
        "status": "success",
        "device_id": device.device_id,
        "custom_name": device.custom_name,
        "stream_urls": stream_urls
    }

@router.get("/{device_id}")
def get_device_detail(device_id: str, db: Session = Depends(get_db)):
    device = db.query(Device).filter(Device.device_id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    caps = db.query(CameraCapability).filter(CameraCapability.device_id == device_id).first()
    settings_obj = db.query(CameraSetting).filter(CameraSetting.device_id == device_id).first()
    audio = db.query(AudioSetting).filter(AudioSetting.device_id == device_id).first()
    host_ip = NetworkService.get_local_ip()

    return {
        "device": {
            "device_id": device.device_id,
            "custom_name": device.custom_name,
            "platform": device.platform,
            "model": device.model,
            "connection_type": device.connection_type,
            "ip_address": device.ip_address,
            "is_online": device.device_id in ws_manager.camera_clients,
        },
        "capabilities": {
            "supported_lenses": caps.supported_lenses if caps else ["back_wide", "front"],
            "supported_resolutions": caps.supported_resolutions if caps else ["720p30", "1080p30"],
            "supports_torch": caps.supports_torch if caps else True,
            "supports_manual_focus": caps.supports_manual_focus if caps else True,
            "supports_manual_exposure": caps.supports_manual_exposure if caps else True,
            "supports_manual_wb": caps.supports_manual_wb if caps else True,
            "min_iso": caps.min_iso if caps else 50,
            "max_iso": caps.max_iso if caps else 3200,
            "min_zoom": caps.min_zoom if caps else 1.0,
            "max_zoom": caps.max_zoom if caps else 10.0,
        } if caps else None,
        "camera_settings": {
            "zoom": settings_obj.zoom if settings_obj else 1.0,
            "focus_mode": settings_obj.focus_mode if settings_obj else "auto",
            "focus_distance": settings_obj.focus_distance if settings_obj else 0.0,
            "exposure_mode": settings_obj.exposure_mode if settings_obj else "auto",
            "exposure_compensation": settings_obj.exposure_compensation if settings_obj else 0.0,
            "iso": settings_obj.iso if settings_obj else 100,
            "shutter_speed_ns": settings_obj.shutter_speed_ns if settings_obj else 0,
            "white_balance_mode": settings_obj.white_balance_mode if settings_obj else "auto",
            "white_balance_temperature": settings_obj.white_balance_temperature if settings_obj else 5500,
            "torch_enabled": settings_obj.torch_enabled if settings_obj else False,
            "torch_level": settings_obj.torch_level if settings_obj else 1.0,
            "lens": settings_obj.lens if settings_obj else "back_wide",
            "resolution_profile": settings_obj.resolution_profile if settings_obj else "1080p30"
        } if settings_obj else None,
        "audio_settings": {
            "muted": audio.muted if audio else False,
            "gain": audio.gain if audio else 1.0,
            "input_source": audio.input_source if audio else "built_in_mic",
            "send_to_obs": audio.send_to_obs if audio else True,
            "echo_cancellation": audio.echo_cancellation if audio else True
        } if audio else None,
        "telemetry": device_manager.get_telemetry(device_id),
        "stream_urls": stream_manager.get_stream_urls(device_id, host_ip)
    }

@router.put("/{device_id}/rename")
def rename_device(device_id: str, payload: DeviceRenameRequest, db: Session = Depends(get_db)):
    device = db.query(Device).filter(Device.device_id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    device.custom_name = payload.custom_name
    db.commit()
    return {"status": "success", "custom_name": device.custom_name}

@router.post("/{device_id}/capabilities")
def report_capabilities(device_id: str, caps: CapabilitiesReportRequest, db: Session = Depends(get_db)):
    device = db.query(Device).filter(Device.device_id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    device_manager.update_capabilities(db, device_id, caps.model_dump())
    return {"status": "success"}

@router.delete("/{device_id}")
async def delete_device(device_id: str, db: Session = Depends(get_db)):
    device = db.query(Device).filter(Device.device_id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    # Clean up associated DB tables
    db.query(CameraCapability).filter(CameraCapability.device_id == device_id).delete()
    db.query(CameraSetting).filter(CameraSetting.device_id == device_id).delete()
    db.query(AudioSetting).filter(AudioSetting.device_id == device_id).delete()
    db.delete(device)
    db.commit()

    ws_manager.disconnect_camera(device_id)
    await ws_manager.broadcast_to_desktop({
        "type": "device_deleted",
        "device_id": device_id
    })
    return {"status": "success", "message": f"Device {device_id} removed"}

