"""
OBS Studio Integration REST API.
Controls connection to OBS WebSocket v5, queries scenes, and manages automatic source injection.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List

from app.database.connection import get_db
from app.database.models import OBSConnection, Device
from app.obs.obs_client import obs_client

router = APIRouter(prefix="/api/obs", tags=["obs"])

class OBSConnectRequest(BaseModel):
    host: Optional[str] = "127.0.0.1"
    port: Optional[int] = 4455
    password: Optional[str] = ""

class OBSSceneSwitchRequest(BaseModel):
    scene_name: str

class OBSCreateSourceRequest(BaseModel):
    device_id: str
    target_scene: Optional[str] = None
    use_rtsp_fallback: bool = False
    width: int = 1920
    height: int = 1080
    fps: int = 30

@router.get("/status")
def get_obs_status():
    """
    Returns OBS connection status and active scene information.
    """
    scenes_data = obs_client.get_scenes()
    return {
        "is_connected": obs_client.is_connected,
        "host": obs_client.host,
        "port": obs_client.port,
        "current_scene": scenes_data.get("current_scene"),
        "scenes": scenes_data.get("scenes", [])
    }

@router.post("/connect")
async def connect_obs(payload: OBSConnectRequest, db: Session = Depends(get_db)):
    success = await obs_client.connect(
        host=payload.host,
        port=payload.port,
        password=payload.password
    )

    # Save to DB
    obs_conn = db.query(OBSConnection).first()
    if not obs_conn:
        obs_conn = OBSConnection()
        db.add(obs_conn)
    obs_conn.host = payload.host or "127.0.0.1"
    obs_conn.port = payload.port or 4455
    obs_conn.password = payload.password or ""
    obs_conn.is_connected = success
    db.commit()

    if not success:
        return {"status": "error", "message": f"Could not connect to OBS on {payload.host}:{payload.port}. Ensure OBS WebSocket server is enabled."}

    scenes_data = obs_client.get_scenes()
    return {
        "status": "connected",
        "scenes": scenes_data.get("scenes", []),
        "current_scene": scenes_data.get("current_scene")
    }

@router.post("/disconnect")
async def disconnect_obs():
    await obs_client.disconnect()
    return {"status": "disconnected"}

@router.get("/scenes")
def list_scenes():
    return obs_client.get_scenes()

@router.post("/scenes/switch")
def switch_scene(payload: OBSSceneSwitchRequest):
    success = obs_client.set_current_scene(payload.scene_name)
    if not success:
        raise HTTPException(status_code=400, detail=f"Failed to switch to scene {payload.scene_name}")
    return {"status": "success", "current_scene": payload.scene_name}

@router.get("/scenes/{scene_name}/sources")
def list_sources_in_scene(scene_name: str):
    sources = obs_client.get_sources_in_scene(scene_name)
    return {"scene": scene_name, "sources": sources}

@router.post("/sources/create")
def create_obs_source(payload: OBSCreateSourceRequest, db: Session = Depends(get_db)):
    device = db.query(Device).filter(Device.device_id == payload.device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    res = obs_client.create_or_update_camera_source(
        device_id=device.device_id,
        device_name=device.custom_name,
        target_scene=payload.target_scene,
        use_rtsp_fallback=payload.use_rtsp_fallback,
        width=payload.width,
        height=payload.height,
        fps=payload.fps
    )
    return res

@router.delete("/sources/{device_id}")
def remove_obs_source(device_id: str, db: Session = Depends(get_db)):
    device = db.query(Device).filter(Device.device_id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    success = obs_client.remove_camera_source(device.custom_name)
    return {"status": "removed" if success else "failed"}

@router.post("/outputs/record")
def toggle_obs_record():
    return obs_client.toggle_record()

@router.post("/outputs/stream")
def toggle_obs_stream():
    return obs_client.toggle_stream()

@router.post("/outputs/virtual_cam")
def toggle_obs_virtual_cam():
    return obs_client.toggle_virtual_cam()

@router.get("/outputs/status")
def get_obs_outputs_status():
    return obs_client.get_output_status()

