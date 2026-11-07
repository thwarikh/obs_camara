"""
MediaMTX process management and stream state tracking.
"""
import os
import subprocess
import aiohttp
import asyncio
import logging
from typing import Dict, Any, List, Optional
from app.config import settings

logger = logging.getLogger("OBSCameraPro.StreamManager")

class StreamManager:
    def __init__(self):
        self.process: Optional[subprocess.Popen] = None
        self._active_streams: Dict[str, Dict[str, Any]] = {}
        self._mediamtx_api_url = settings.MEDIAMTX_API_URL

    def start_mediamtx(self) -> bool:
        """
        Launches the MediaMTX streaming server if not already running.
        """
        exe_path = os.path.join(settings.MEDIAMTX_DIR, settings.MEDIAMTX_EXECUTABLE)
        config_path = os.path.join(settings.MEDIAMTX_DIR, settings.MEDIAMTX_CONFIG)

        if not os.path.exists(exe_path):
            logger.error(f"MediaMTX binary not found at {exe_path}")
            return False

        try:
            # Check if an instance is already listening on API port 9997
            import socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(0.5)
            result = sock.connect_ex(("127.0.0.1", 9997))
            sock.close()
            if result == 0:
                logger.info("MediaMTX is already running on port 9997.")
                return True

            logger.info(f"Starting MediaMTX process: {exe_path} with config {config_path}")
            self.process = subprocess.Popen(
                [exe_path, config_path],
                cwd=settings.MEDIAMTX_DIR,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
            )
            logger.info(f"MediaMTX process started with PID {self.process.pid}")
            return True
        except Exception as e:
            logger.exception(f"Failed to start MediaMTX: {e}")
            return False

    def stop_mediamtx(self):
        """
        Gracefully terminates the MediaMTX process.
        """
        if self.process:
            try:
                logger.info(f"Terminating MediaMTX process PID {self.process.pid}")
                self.process.terminate()
                self.process.wait(timeout=3)
            except Exception:
                try:
                    self.process.kill()
                except Exception:
                    pass
            finally:
                self.process = None

    async def get_stream_stats_from_mediamtx(self) -> List[Dict[str, Any]]:
        """
        Queries MediaMTX API v3 to inspect active publishing paths.
        """
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self._mediamtx_api_url}/v3/paths/list", timeout=1.5) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        items = data.get("items", [])
                        return items
        except Exception:
            pass
        return []

    def get_stream_urls(self, device_id: str, host_ip: str) -> Dict[str, str]:
        """
        Generates standard dynamic streaming URLs for a specific device.
        """
        clean_id = device_id.lower().replace(":", "").replace("-", "")
        stream_path = f"camera_{clean_id}"
        return {
            "stream_path": stream_path,
            "whip_publish_url": f"http://{host_ip}:{settings.MEDIAMTX_WEBRTC_PORT}/{stream_path}/whip",
            "whep_playback_url": f"http://{host_ip}:{settings.MEDIAMTX_WEBRTC_PORT}/{stream_path}/whep",
            "obs_browser_url": f"http://{host_ip}:{settings.PORT}/obs/camera/{device_id}",
            "rtsp_url": f"rtsp://{host_ip}:{settings.MEDIAMTX_RTSP_PORT}/{stream_path}",
            "rtmp_url": f"rtmp://{host_ip}:{settings.MEDIAMTX_RTMP_PORT}/{stream_path}",
            "hls_url": f"http://{host_ip}:8888/{stream_path}/index.m3u8"
        }

    def record_stream_telemetry(self, device_id: str, telemetry: Dict[str, Any]):
        """
        Caches latest telemetry for device stream health.
        """
        self._active_streams[device_id] = {
            "telemetry": telemetry,
            "updated_at": asyncio.get_event_loop().time()
        }

    def get_stream_health(self, device_id: str) -> Optional[Dict[str, Any]]:
        return self._active_streams.get(device_id)

stream_manager = StreamManager()

