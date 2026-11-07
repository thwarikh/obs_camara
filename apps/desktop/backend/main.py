"""
OBS Camera Pro - Desktop Backend Server
Entrypoint running FastAPI, WebSocket router, MediaMTX supervisor, and OBS integration.
"""
import os
import sys
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware

# Ensure app package is importable
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from app.config import settings
from app.database.connection import init_db, SessionLocal
from app.streaming.stream_manager import stream_manager
from app.websocket.ws_manager import ws_manager
from app.devices.device_manager import device_manager
from app.database.models import EventLog

from app.api.routes_devices import router as devices_router
from app.api.routes_controls import router as controls_router
from app.api.routes_audio import router as audio_router
from app.api.routes_streams import router as streams_router
from app.api.routes_obs import router as obs_router
from app.api.routes_system import router as system_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("OBSCameraPro.Main")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. Initialize SQLite Database
    logger.info("Initializing SQLite database models...")
    init_db()

    # Log startup event
    db = SessionLocal()
    db.add(EventLog(level="SUCCESS", source="system", message="OBS Camera Pro Desktop Backend started"))
    db.commit()
    db.close()

    # 2. Launch MediaMTX Streaming Server
    logger.info("Verifying MediaMTX streaming infrastructure...")
    mediamtx_running = stream_manager.start_mediamtx()
    if mediamtx_running:
        logger.info("MediaMTX server ready for low-latency WebRTC (WHEP / WHIP) and RTSP.")
    else:
        logger.warning("MediaMTX could not be auto-started. Verify services/mediamtx/mediamtx.exe.")

    yield

    # Shutdown: Clean up subprocesses
    logger.info("Shutting down OBS Camera Pro services...")
    stream_manager.stop_mediamtx()

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    lifespan=lifespan
)

# Enable CORS for local Wi-Fi & USB network access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount REST API routers
app.include_router(devices_router)
app.include_router(controls_router)
app.include_router(audio_router)
app.include_router(streams_router)
app.include_router(obs_router)
app.include_router(system_router)

# Mount frontend static directories
frontend_dir = os.path.abspath(os.path.join(current_dir, "../frontend"))
app.mount("/css", StaticFiles(directory=os.path.join(frontend_dir, "css")), name="css")
app.mount("/js", StaticFiles(directory=os.path.join(frontend_dir, "js")), name="js")
if os.path.exists(os.path.join(frontend_dir, "assets")):
    app.mount("/assets", StaticFiles(directory=os.path.join(frontend_dir, "assets")), name="assets")

# Root dashboard route
@app.get("/", response_class=HTMLResponse)
async def serve_dashboard():
    return FileResponse(os.path.join(frontend_dir, "index.html"))

# OBS Browser Source player route
@app.get("/obs/camera/{device_id}", response_class=HTMLResponse)
async def serve_obs_player(device_id: str):
    return FileResponse(os.path.join(frontend_dir, "obs_player.html"))

# WebSocket: Desktop Dashboard live feed
@app.websocket("/ws/devices")
async def websocket_desktop_endpoint(websocket: WebSocket):
    await ws_manager.connect_desktop(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # Handle client messages if needed
    except WebSocketDisconnect:
        ws_manager.disconnect_desktop(websocket)
    except Exception:
        ws_manager.disconnect_desktop(websocket)

# WebSocket: Mobile Phone Camera bidirectional control channel
@app.websocket("/ws/camera/{device_id}")
async def websocket_camera_endpoint(websocket: WebSocket, device_id: str):
    await ws_manager.connect_camera(device_id, websocket)
    db = SessionLocal()
    try:
        # Update last seen and online
        device_manager.register_or_update_device(
            db=db,
            device_id=device_id,
            custom_name="",
            platform="",
            model="",
            os_version="",
            ip_address=websocket.client.host if websocket.client else ""
        )
        while True:
            raw_text = await websocket.receive_text()
            import json
            msg = json.loads(raw_text)
            msg_type = msg.get("type")

            if msg_type == "telemetry":
                telemetry_data = msg.get("payload", {})
                device_manager.update_telemetry(device_id, telemetry_data)
                stream_manager.record_stream_telemetry(device_id, telemetry_data)
                await ws_manager.broadcast_telemetry(device_id, telemetry_data)
            elif msg_type == "camera_control_applied":
                # Hardware confirmation from phone
                applied_payload = msg.get("payload", {})
                await ws_manager.broadcast_to_desktop({
                    "type": "camera_settings_updated",
                    "device_id": device_id,
                    "settings": applied_payload
                })
            elif msg_type == "capabilities_report":
                device_manager.update_capabilities(db, device_id, msg.get("payload", {}))
    except WebSocketDisconnect:
        ws_manager.disconnect_camera(device_id)
        device_manager.mark_offline(db, device_id)
        await ws_manager.broadcast_to_desktop({
            "type": "device_disconnected",
            "device_id": device_id
        })
    except Exception as e:
        logger.error(f"Error in camera WS {device_id}: {e}")
        ws_manager.disconnect_camera(device_id)
    finally:
        db.close()

# WebSocket: Dedicated stream telemetry / signaling
@app.websocket("/ws/stream/{device_id}")
async def websocket_stream_endpoint(websocket: WebSocket, device_id: str):
    await ws_manager.connect_stream(device_id, websocket)
    try:
        while True:
            await websocket.receive_text()
    except Exception:
        ws_manager.disconnect_stream(device_id, websocket)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=settings.HOST, port=settings.PORT, reload=settings.DEBUG)

