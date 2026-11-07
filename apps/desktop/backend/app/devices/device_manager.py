"""
Device manager for OBS Camera Pro.
Handles QR pairing tokens, capability negotiations, and device lifecycle.
"""
import io
import base64
import secrets
import qrcode
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session

from app.config import settings
from app.database.models import Device, DevicePairing, CameraCapability, CameraSetting, AudioSetting, EventLog
from app.services.network_service import NetworkService

class DeviceManager:
    def __init__(self):
        # In-memory fast cache for live telemetry & active connections
        self._telemetry_cache: Dict[str, Dict[str, Any]] = {}
        self._connected_clients: Dict[str, Any] = {}

    def generate_pairing_payload(self, host_ip: Optional[str] = None) -> Dict[str, Any]:
        """
        Creates a new pairing token and returns QR code data URI + parameters.
        """
        if not host_ip:
            host_ip = NetworkService.get_local_ip()

        token = secrets.token_urlsafe(32)
        payload = {
            "app": "OBS_CAMERA_PRO",
            "version": settings.VERSION,
            "host": host_ip,
            "port": settings.PORT,
            "token": token,
            "ws_url": f"ws://{host_ip}:{settings.PORT}/ws/devices",
            "whip_base": f"http://{host_ip}:{settings.MEDIAMTX_WEBRTC_PORT}",
            "expires_in": 3600 * 24
        }

        # Render QR code image
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=8,
            border=2,
        )
        import json
        qr.add_data(json.dumps(payload))
        qr.make(fit=True)
        img = qr.make_image(fill_color="#38bdf8", back_color="#0f172a")

        buffered = io.BytesIO()
        img.save(buffered, format="PNG")
        qr_base64 = base64.b64encode(buffered.getvalue()).decode("utf-8")
        qr_data_uri = f"data:image/png;base64,{qr_base64}"

        return {
            "token": token,
            "qr_data_uri": qr_data_uri,
            "payload": payload
        }

    def register_or_update_device(
        self,
        db: Session,
        device_id: str,
        custom_name: str,
        platform: str,
        model: str,
        os_version: str,
        ip_address: str
    ) -> Device:
        """
        Registers a new phone or updates an existing device record.
        """
        device = db.query(Device).filter(Device.device_id == device_id).first()
        conn_type = NetworkService.detect_connection_type(ip_address)

        if not device:
            device = Device(
                device_id=device_id,
                custom_name=custom_name or f"{platform.capitalize()} Camera",
                platform=platform.lower(),
                model=model,
                os_version=os_version,
                connection_type=conn_type,
                ip_address=ip_address,
                is_active=True,
                is_paired=True,
                last_seen=datetime.now(timezone.utc)
            )
            db.add(device)
            db.flush()

            # Create default settings
            default_cam = CameraSetting(device_id=device_id)
            default_audio = AudioSetting(device_id=device_id)
            default_caps = CameraCapability(
                device_id=device_id,
                supported_lenses=["back_wide", "front"],
                supported_resolutions=["720p30", "1080p30", "1080p60"]
            )
            db.add(default_cam)
            db.add(default_audio)
            db.add(default_caps)
            db.commit()
            db.refresh(device)
        else:
            device.model = model or device.model
            device.os_version = os_version or device.os_version
            device.ip_address = ip_address
            device.connection_type = conn_type
            device.is_active = True
            device.last_seen = datetime.now(timezone.utc)
            db.commit()
            db.refresh(device)

        return device

    def update_capabilities(self, db: Session, device_id: str, caps_data: Dict[str, Any]):
        caps = db.query(CameraCapability).filter(CameraCapability.device_id == device_id).first()
        if not caps:
            caps = CameraCapability(device_id=device_id)
            db.add(caps)

        caps.supported_lenses = caps_data.get("supported_lenses", ["back_wide", "front"])
        caps.supported_resolutions = caps_data.get("supported_resolutions", ["720p30", "1080p30"])
        caps.supports_torch = caps_data.get("supports_torch", True)
        caps.supports_manual_focus = caps_data.get("supports_manual_focus", True)
        caps.supports_manual_exposure = caps_data.get("supports_manual_exposure", True)
        caps.supports_manual_wb = caps_data.get("supports_manual_wb", True)
        caps.min_iso = caps_data.get("min_iso", 50)
        caps.max_iso = caps_data.get("max_iso", 3200)
        caps.min_zoom = caps_data.get("min_zoom", 1.0)
        caps.max_zoom = caps_data.get("max_zoom", 10.0)
        caps.raw_info = caps_data.get("raw_info", {})
        db.commit()

    def update_telemetry(self, device_id: str, telemetry: Dict[str, Any]):
        self._telemetry_cache[device_id] = {
            **telemetry,
            "received_at": datetime.now(timezone.utc).isoformat()
        }

    def get_telemetry(self, device_id: str) -> Dict[str, Any]:
        return self._telemetry_cache.get(device_id, {
            "fps": 0.0,
            "bitrate_kbps": 0,
            "battery_pct": 100,
            "is_charging": False,
            "battery_temp_c": 28.0,
            "audio_level_db": -60.0,
            "network_type": "wifi",
            "network_rtt_ms": 0.0,
            "packet_loss_pct": 0.0,
            "dropped_frames": 0
        })

    def mark_offline(self, db: Session, device_id: str):
        device = db.query(Device).filter(Device.device_id == device_id).first()
        if device:
            device.is_active = False
            device.last_seen = datetime.now(timezone.utc)
            db.commit()

device_manager = DeviceManager()

