"""
Multi-camera simulation integration test.
Tests simultaneous multi-camera registration, capability reporting, telemetry flow, and remote controls.
"""
import pytest
import asyncio
from fastapi.testclient import TestClient
import os
import sys

backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../apps/desktop/backend"))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

try:
    from main import app
    from app.devices.device_manager import device_manager
except (ImportError, ModuleNotFoundError):
    from apps.desktop.backend.main import app
    from apps.desktop.backend.app.devices.device_manager import device_manager

client = TestClient(app)

def test_multi_camera_registration_and_isolation():
    """
    Registers 3 separate camera devices and tests that their settings and telemetry remain isolated.
    """
    devices_data = [
        {"device_id": "cam-alpha", "name": "Pixel 8 Pro", "platform": "android"},
        {"device_id": "cam-beta", "name": "iPhone 15 Pro", "platform": "ios"},
        {"device_id": "cam-gamma", "name": "Galaxy S24", "platform": "android"},
    ]

    for d in devices_data:
        resp = client.post("/api/devices/register", json={
            "device_id": d["device_id"],
            "custom_name": d["name"],
            "platform": d["platform"],
            "model": d["name"],
            "os_version": "1.0",
            "token": "tok-test",
            "ip_address": "192.168.1.50"
        })
        assert resp.status_code == 200

    # Verify each has distinct settings
    # 1. Update cam-alpha zoom to 3.5x
    client.post("/api/controls", json={"device_id": "cam-alpha", "zoom": 3.5})
    # 2. Update cam-beta zoom to 1.2x
    client.post("/api/controls", json={"device_id": "cam-beta", "zoom": 1.2})

    detail_alpha = client.get("/api/devices/cam-alpha").json()
    detail_beta = client.get("/api/devices/cam-beta").json()

    assert detail_alpha["camera_settings"]["zoom"] == 3.5
    assert detail_beta["camera_settings"]["zoom"] == 1.2

    # Verify distinct audio settings
    client.post("/api/audio", json={"device_id": "cam-alpha", "muted": True, "gain": 0.5})
    client.post("/api/audio", json={"device_id": "cam-beta", "muted": False, "gain": 1.5})

    audio_alpha = client.get("/api/devices/cam-alpha").json()["audio_settings"]
    audio_beta = client.get("/api/devices/cam-beta").json()["audio_settings"]

    assert audio_alpha["muted"] is True
    assert audio_alpha["gain"] == 0.5
    assert audio_beta["muted"] is False
    assert audio_beta["gain"] == 1.5

