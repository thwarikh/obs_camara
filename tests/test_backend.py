"""
Integration and Unit Tests for OBS Camera Pro Desktop Backend.
"""
import pytest
from fastapi.testclient import TestClient
import os
import sys

# Add apps/desktop/backend to sys.path
backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../apps/desktop/backend"))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

try:
    from main import app
    from app.devices.device_manager import device_manager
    from app.streaming.stream_manager import stream_manager
    from app.services.network_service import NetworkService
    from app.streaming.abr_controller import abr_controller
except (ImportError, ModuleNotFoundError):
    from apps.desktop.backend.main import app
    from apps.desktop.backend.app.devices.device_manager import device_manager
    from apps.desktop.backend.app.streaming.stream_manager import stream_manager
    from apps.desktop.backend.app.services.network_service import NetworkService
    from apps.desktop.backend.app.streaming.abr_controller import abr_controller

client = TestClient(app)

def test_root_dashboard_serves_html():
    response = client.get("/")
    assert response.status_code == 200
    assert "OBS Camera Pro" in response.text
    assert "Production Dashboard" in response.text

def test_obs_browser_player_serves_html():
    response = client.get("/obs/camera/test-phone-01")
    assert response.status_code == 200
    assert "videoPlayer" in response.text
    assert "startWhepSession" in response.text

def test_device_pairing_generation():
    # Test POST
    response_post = client.post("/api/devices/pair")
    assert response_post.status_code == 200
    data = response_post.json()
    assert "token" in data
    assert "qr_data_uri" in data
    assert data["qr_data_uri"].startswith("data:image/png;base64,")
    assert data["payload"]["app"] == "OBS_CAMERA_PRO"
    assert "whip_base" in data["payload"]

    # Test GET
    response_get = client.get("/api/devices/pair")
    assert response_get.status_code == 200
    get_data = response_get.json()
    assert "token" in get_data
    assert "qr_data_uri" in get_data

def test_device_registration_and_listing():
    reg_payload = {
        "device_id": "test-android-device-01",
        "custom_name": "Studio Cam Alpha",
        "platform": "android",
        "model": "Pixel 8 Pro",
        "os_version": "Android 14",
        "token": "valid-token-123",
        "ip_address": "192.168.1.150"
    }
    reg_resp = client.post("/api/devices/register", json=reg_payload)
    assert reg_resp.status_code == 200
    reg_data = reg_resp.json()
    assert reg_data["status"] == "success"
    assert "stream_urls" in reg_data
    assert "whip_publish_url" in reg_data["stream_urls"]
    assert "obs_browser_url" in reg_data["stream_urls"]

    # Test listing
    list_resp = client.get("/api/devices")
    assert list_resp.status_code == 200
    devices = list_resp.json()["devices"]
    found = [d for d in devices if d["device_id"] == "test-android-device-01"]
    assert len(found) == 1
    assert found[0]["custom_name"] == "Studio Cam Alpha"

def test_camera_controls_dispatch():
    control_payload = {
        "device_id": "test-android-device-01",
        "zoom": 2.5,
        "focus_mode": "manual",
        "focus_distance": 0.45,
        "iso": 400,
        "exposure_compensation": 1.0,
        "torch_enabled": True,
        "lens": "back_ultrawide",
        "resolution_profile": "1080p60"
    }
    resp = client.post("/api/controls", json=control_payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["device_id"] == "test-android-device-01"
    assert data["command"]["zoom"] == 2.5
    assert data["command"]["iso"] == 400
    assert data["command"]["lens"] == "back_ultrawide"

def test_audio_controls_dispatch():
    audio_payload = {
        "device_id": "test-android-device-01",
        "gain": 1.4,
        "muted": False,
        "send_to_obs": True
    }
    resp = client.post("/api/audio", json=audio_payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert data["audio"]["gain"] == 1.4

def test_system_metrics_and_network():
    metrics_resp = client.get("/api/system/metrics")
    assert metrics_resp.status_code == 200
    m = metrics_resp.json()
    assert "cpu_percent" in m
    assert "memory_percent" in m
    assert "net_ingress_mbps" in m

    net_resp = client.get("/api/system/network")
    assert net_resp.status_code == 200
    n = net_resp.json()
    assert "local_ip" in n
    assert "interfaces" in n

def test_obs_status_endpoint():
    resp = client.get("/api/obs/status")
    assert resp.status_code == 200
    data = resp.json()
    assert "is_connected" in data
    assert "scenes" in data

def test_obs_output_controls():
    status_resp = client.get("/api/obs/outputs/status")
    assert status_resp.status_code == 200
    status_data = status_resp.json()
    assert "recording" in status_data
    assert "streaming" in status_data
    assert "virtual_cam" in status_data

    # Toggle tests (gracefully handles disconnected OBS)
    rec_resp = client.post("/api/obs/outputs/record")
    assert rec_resp.status_code == 200

def test_device_manager_telemetry_cache():
    dev_id = "test-telemetry-dev-99"
    test_telem = {
        "fps": 59.9,
        "bitrate_kbps": 8200,
        "battery_pct": 92,
        "is_charging": True,
        "battery_temp_c": 34.5,
        "audio_level_db": -22.4,
        "network_type": "usb_tethering",
        "network_rtt_ms": 5.2,
        "packet_loss_pct": 0.0,
        "dropped_frames": 0
    }
    device_manager.update_telemetry(dev_id, test_telem)
    cached = device_manager.get_telemetry(dev_id)
    assert cached["fps"] == 59.9
    assert cached["bitrate_kbps"] == 8200
    assert cached["network_type"] == "usb_tethering"
    assert "received_at" in cached

def test_abr_controller_evaluation():
    dev_id = "test-abr-dev-01"
    # Normal / pristine metrics
    pristine_eval = abr_controller.evaluate_telemetry(dev_id, {
        "network_rtt_ms": 12.0,
        "packet_loss_pct": 0.1,
        "battery_temp_c": 31.0,
        "bitrate_kbps": 6000,
        "fps": 30.0
    })
    assert pristine_eval["health_grade"] == "EXCELLENT"

    # Degraded metrics (high packet loss and high temp)
    degraded_eval = abr_controller.evaluate_telemetry(dev_id, {
        "network_rtt_ms": 250.0,
        "packet_loss_pct": 8.5,
        "battery_temp_c": 45.0,
        "bitrate_kbps": 3000,
        "fps": 22.0
    })
    assert degraded_eval["health_grade"] == "CRITICAL"
    assert degraded_eval["action"] == "downgrade"


