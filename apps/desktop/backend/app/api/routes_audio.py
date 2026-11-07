"""
Audio Mixer REST API.
Manages per-camera audio volume, mute toggles, input selection, and OBS routing.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional

from app.database.connection import get_db
from app.database.models import AudioSetting, Device
from app.websocket.ws_manager import ws_manager

router = APIRouter(prefix="/api/audio", tags=["audio"])

class AudioControlRequest(BaseModel):
    device_id: str
    muted: Optional[bool] = None
    gain: Optional[float] = Field(None, ge=0.0, le=2.0)
    input_source: Optional[str] = None
    echo_cancellation: Optional[bool] = None
    send_to_obs: Optional[bool] = None
    audio_sync_offset_ms: Optional[int] = Field(None, ge=-1000, le=1000)

@router.post("")
async def update_audio_settings(payload: AudioControlRequest, db: Session = Depends(get_db)):
    device = db.query(Device).filter(Device.device_id == payload.device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    audio = db.query(AudioSetting).filter(AudioSetting.device_id == payload.device_id).first()
    if not audio:
        audio = AudioSetting(device_id=payload.device_id)
        db.add(audio)

    cmd = {"type": "audio_control_command", "device_id": payload.device_id}

    if payload.muted is not None:
        audio.muted = payload.muted
        cmd["muted"] = payload.muted
    if payload.gain is not None:
        audio.gain = payload.gain
        cmd["gain"] = payload.gain
    if payload.input_source is not None:
        audio.input_source = payload.input_source
        cmd["input_source"] = payload.input_source
    if payload.echo_cancellation is not None:
        audio.echo_cancellation = payload.echo_cancellation
        cmd["echo_cancellation"] = payload.echo_cancellation
    if payload.send_to_obs is not None:
        audio.send_to_obs = payload.send_to_obs
    if payload.audio_sync_offset_ms is not None:
        audio.audio_sync_offset_ms = payload.audio_sync_offset_ms

    db.commit()

    # Deliver to phone
    delivered = await ws_manager.send_control_to_camera(payload.device_id, cmd)

    # Broadcast to desktop mixer
    await ws_manager.broadcast_to_desktop({
        "type": "audio_settings_updated",
        "device_id": payload.device_id,
        "audio": cmd
    })

    return {
        "status": "success",
        "delivered_to_device": delivered,
        "device_id": payload.device_id,
        "audio": cmd
    }

