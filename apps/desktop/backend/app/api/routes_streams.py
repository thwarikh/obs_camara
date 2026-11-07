"""
Stream management REST API.
Controls live stream sessions and reports active streaming bandwidth and status.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone

from app.database.connection import get_db
from app.database.models import StreamSession, Device
from app.streaming.stream_manager import stream_manager
from app.services.network_service import NetworkService
from app.websocket.ws_manager import ws_manager

router = APIRouter(prefix="/api/streams", tags=["streams"])

class StreamActionRequest(BaseModel):
    device_id: str
    action: str  # start, stop
    profile: Optional[str] = "1080p30"

@router.get("")
async def get_streams_overview(db: Session = Depends(get_db)):
    """
    Returns active streams and MediaMTX path status.
    """
    mediamtx_paths = await stream_manager.get_stream_stats_from_mediamtx()
    devices = db.query(Device).filter(Device.is_active == True).all()
    host_ip = NetworkService.get_local_ip()

    streams = []
    for d in devices:
        urls = stream_manager.get_stream_urls(d.device_id, host_ip)
        telemetry = stream_manager.get_stream_health(d.device_id)
        is_live = False

        # Match against mediamtx paths
        clean_path = urls["stream_path"]
        for p in mediamtx_paths:
            if p.get("name") == clean_path and p.get("ready"):
                is_live = True
                break

        streams.append({
            "device_id": d.device_id,
            "custom_name": d.custom_name,
            "platform": d.platform,
            "stream_path": clean_path,
            "is_live": is_live or (d.device_id in ws_manager.camera_clients),
            "urls": urls,
            "health": telemetry
        })

    return {
        "active_streams": streams,
        "mediamtx_paths": mediamtx_paths
    }

@router.post("/start")
async def start_stream(payload: StreamActionRequest, db: Session = Depends(get_db)):
    device = db.query(Device).filter(Device.device_id == payload.device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    host_ip = NetworkService.get_local_ip()
    urls = stream_manager.get_stream_urls(payload.device_id, host_ip)

    cmd = {
        "type": "stream_start_command",
        "device_id": payload.device_id,
        "profile": payload.profile,
        "whip_url": urls["whip_publish_url"]
    }
    await ws_manager.send_control_to_camera(payload.device_id, cmd)

    # Record session in DB
    session = StreamSession(
        device_id=payload.device_id,
        stream_path=urls["stream_path"],
        profile=payload.profile or "1080p30",
        status="active"
    )
    db.add(session)
    db.commit()

    return {"status": "started", "urls": urls}

@router.post("/stop")
async def stop_stream(payload: StreamActionRequest, db: Session = Depends(get_db)):
    cmd = {
        "type": "stream_stop_command",
        "device_id": payload.device_id
    }
    await ws_manager.send_control_to_camera(payload.device_id, cmd)

    active_sess = db.query(StreamSession).filter(
        StreamSession.device_id == payload.device_id,
        StreamSession.status == "active"
    ).all()
    for s in active_sess:
        s.status = "stopped"
        s.stopped_at = datetime.now(timezone.utc)
    db.commit()

    return {"status": "stopped", "device_id": payload.device_id}

