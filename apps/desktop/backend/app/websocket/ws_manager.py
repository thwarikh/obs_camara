"""
Central WebSocket connection manager for OBS Camera Pro.
Routes real-time controls, telemetry, and signaling between mobile apps and desktop dashboard.
"""
import json
import logging
from typing import Dict, Set, Any, Optional
from fastapi import WebSocket

logger = logging.getLogger("OBSCameraPro.WSManager")

class ConnectionManager:
    def __init__(self):
        # Desktop UI WebSocket clients
        self.desktop_clients: Set[WebSocket] = set()
        # Mobile camera device WebSockets: device_id -> WebSocket
        self.camera_clients: Dict[str, WebSocket] = {}
        # Stream telemetry / signaling WebSockets: device_id -> Set[WebSocket]
        self.stream_clients: Dict[str, Set[WebSocket]] = {}
        # OBS status subscribers
        self.obs_clients: Set[WebSocket] = set()

    async def connect_desktop(self, websocket: WebSocket):
        await websocket.accept()
        self.desktop_clients.add(websocket)
        logger.info(f"Desktop client connected. Total desktop clients: {len(self.desktop_clients)}")

    def disconnect_desktop(self, websocket: WebSocket):
        self.desktop_clients.discard(websocket)
        logger.info(f"Desktop client disconnected. Remaining: {len(self.desktop_clients)}")

    async def connect_camera(self, device_id: str, websocket: WebSocket):
        await websocket.accept()
        self.camera_clients[device_id] = websocket
        logger.info(f"Camera device connected: {device_id}")
        # Notify desktop clients
        await self.broadcast_to_desktop({
            "type": "device_connected",
            "device_id": device_id
        })

    def disconnect_camera(self, device_id: str):
        if device_id in self.camera_clients:
            del self.camera_clients[device_id]
            logger.info(f"Camera device disconnected: {device_id}")

    async def connect_stream(self, device_id: str, websocket: WebSocket):
        await websocket.accept()
        if device_id not in self.stream_clients:
            self.stream_clients[device_id] = set()
        self.stream_clients[device_id].add(websocket)

    def disconnect_stream(self, device_id: str, websocket: WebSocket):
        if device_id in self.stream_clients:
            self.stream_clients[device_id].discard(websocket)
            if not self.stream_clients[device_id]:
                del self.stream_clients[device_id]

    async def broadcast_to_desktop(self, message: Dict[str, Any]):
        """
        Sends event to all connected desktop UI dashboards.
        """
        stale = []
        payload = json.dumps(message)
        for client in self.desktop_clients:
            try:
                await client.send_text(payload)
            except Exception:
                stale.append(client)
        for dead in stale:
            self.desktop_clients.discard(dead)

    async def send_control_to_camera(self, device_id: str, command: Dict[str, Any]) -> bool:
        """
        Dispatches a remote control command to the specific mobile device.
        """
        ws = self.camera_clients.get(device_id)
        if not ws:
            logger.warning(f"Device {device_id} is not connected for control commands.")
            return False
        try:
            await ws.send_text(json.dumps(command))
            return True
        except Exception as e:
            logger.error(f"Failed to send control command to {device_id}: {e}")
            return False

    async def broadcast_telemetry(self, device_id: str, telemetry: Dict[str, Any]):
        """
        Broadcasts mobile telemetry to desktop clients and stream watchers.
        """
        msg = {
            "type": "telemetry_update",
            "device_id": device_id,
            "data": telemetry
        }
        await self.broadcast_to_desktop(msg)

        if device_id in self.stream_clients:
            payload = json.dumps(msg)
            stale = []
            for ws in self.stream_clients[device_id]:
                try:
                    await ws.send_text(payload)
                except Exception:
                    stale.append(ws)
            for dead in stale:
                self.stream_clients[device_id].discard(dead)

ws_manager = ConnectionManager()

