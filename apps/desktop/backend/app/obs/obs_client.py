"""
OBS Studio integration engine using OBS WebSocket v5.
Handles scene discovery, source creation (Browser Source and RTSP fallback), and audio routing.
"""
import logging
import asyncio
from typing import Dict, Any, List, Optional
from app.config import settings
from app.services.network_service import NetworkService

logger = logging.getLogger("OBSCameraPro.OBSClient")

class OBSClient:
    def __init__(self):
        self.host: str = settings.OBS_WS_HOST
        self.port: int = settings.OBS_WS_PORT
        self.password: str = settings.OBS_WS_PASSWORD
        self.is_connected: bool = False
        self._client = None
        self._lock = asyncio.Lock()

    async def connect(self, host: Optional[str] = None, port: Optional[int] = None, password: Optional[str] = None) -> bool:
        """
        Attempts connection to OBS Studio via WebSocket v5.
        """
        async with self._lock:
            if host:
                self.host = host
            if port:
                self.port = port
            if password is not None:
                self.password = password

            try:
                import obsws_python as obs
                # obsws-python ReqClient handles synchronous protocol calls internally
                self._client = obs.ReqClient(
                    host=self.host,
                    port=self.port,
                    password=self.password,
                    timeout=3
                )
                # Verify with version check
                version_info = self._client.get_version()
                logger.info(f"Connected to OBS Studio: v{version_info.obs_version} (WebSocket v{version_info.obs_web_socket_version})")
                self.is_connected = True
                return True
            except Exception as e:
                logger.warning(f"OBS connection failed ({self.host}:{self.port}): {e}")
                self.is_connected = False
                self._client = None
                return False

    async def disconnect(self):
        async with self._lock:
            if self._client:
                try:
                    self._client.base_client.ws.close()
                except Exception:
                    pass
            self._client = None
            self.is_connected = False

    def get_scenes(self) -> Dict[str, Any]:
        """
        Retrieves list of scenes and currently active scene.
        """
        if not self.is_connected or not self._client:
            return {"scenes": [], "current_scene": None}
        try:
            res = self._client.get_scene_list()
            scenes = [s["sceneName"] for s in res.scenes]
            return {
                "scenes": scenes,
                "current_scene": res.current_program_scene_name
            }
        except Exception as e:
            logger.error(f"Failed to fetch OBS scenes: {e}")
            return {"scenes": [], "current_scene": None}

    def set_current_scene(self, scene_name: str) -> bool:
        if not self.is_connected or not self._client:
            return False
        try:
            self._client.set_current_program_scene(scene_name)
            return True
        except Exception as e:
            logger.error(f"Failed to set current program scene: {e}")
            return False

    def get_sources_in_scene(self, scene_name: str) -> List[Dict[str, Any]]:
        if not self.is_connected or not self._client:
            return []
        try:
            res = self._client.get_scene_item_list(scene_name)
            return [
                {
                    "item_id": item["sceneItemId"],
                    "source_name": item["sourceName"],
                    "source_type": item.get("sourceType", ""),
                    "enabled": item["sceneItemEnabled"]
                }
                for item in res.scene_items
            ]
        except Exception as e:
            logger.error(f"Failed to get sources in scene {scene_name}: {e}")
            return []

    def create_or_update_camera_source(
        self,
        device_id: str,
        device_name: str,
        target_scene: Optional[str] = None,
        use_rtsp_fallback: bool = False,
        width: int = 1920,
        height: int = 1080,
        fps: int = 30
    ) -> Dict[str, Any]:
        """
        Creates or updates an OBS Browser Source (or RTSP VLC/Media source) for a smartphone camera.
        """
        if not self.is_connected or not self._client:
            return {"success": False, "error": "OBS Studio is not connected"}

        try:
            # Determine active scene if not supplied
            if not target_scene:
                scenes_data = self.get_scenes()
                target_scene = scenes_data.get("current_scene")
                if not target_scene and scenes_data.get("scenes"):
                    target_scene = scenes_data["scenes"][0]

            if not target_scene:
                return {"success": False, "error": "No scenes found in OBS"}

            source_name = f"OBS Cam - {device_name}"
            host_ip = NetworkService.get_local_ip()

            if use_rtsp_fallback:
                clean_id = device_id.lower().replace(":", "").replace("-", "")
                rtsp_url = f"rtsp://{host_ip}:{settings.MEDIAMTX_RTSP_PORT}/camera_{clean_id}"
                input_kind = "ffmpeg_source"
                input_settings = {
                    "input": rtsp_url,
                    "is_local_file": False,
                    "restart_on_activate": True,
                    "buffering_mb": 1,
                    "reconnect_delay_sec": 2
                }
            else:
                browser_url = f"http://{host_ip}:{settings.PORT}/obs/camera/{device_id}"
                input_kind = "browser_source"
                input_settings = {
                    "url": browser_url,
                    "width": width,
                    "height": height,
                    "fps": fps,
                    "reroute_audio": True,
                    "restart_when_active": True,
                    "shutdown": False,
                    "css": "body { background-color: rgba(0, 0, 0, 0); margin: 0px auto; overflow: hidden; }"
                }

            # Check if source already exists
            try:
                self._client.get_input_settings(source_name)
                # If it exists, update settings
                self._client.set_input_settings(source_name, input_settings, overlay=True)
                logger.info(f"Updated existing OBS source: {source_name}")
                return {
                    "success": True,
                    "action": "updated",
                    "source_name": source_name,
                    "scene": target_scene,
                    "kind": input_kind
                }
            except Exception:
                # Create input
                self._client.create_input(
                    scene_name=target_scene,
                    input_name=source_name,
                    input_kind=input_kind,
                    input_settings=input_settings,
                    scene_item_enabled=True
                )
                logger.info(f"Created new OBS source: {source_name} in scene {target_scene}")
                return {
                    "success": True,
                    "action": "created",
                    "source_name": source_name,
                    "scene": target_scene,
                    "kind": input_kind
                }
        except Exception as e:
            logger.exception(f"Failed to create OBS source: {e}")
            return {"success": False, "error": str(e)}

    def remove_camera_source(self, device_name: str) -> bool:
        if not self.is_connected or not self._client:
            return False
        source_name = f"OBS Cam - {device_name}"
        try:
            self._client.remove_input(source_name)
            logger.info(f"Removed OBS input: {source_name}")
            return True
        except Exception as e:
            logger.warning(f"Could not remove OBS source {source_name}: {e}")
            return False

    # Production OBS Studio Controls: Recording, Streaming, Virtual Camera
    def toggle_record(self) -> Dict[str, Any]:
        if not self.is_connected or not self._client:
            return {"success": False, "error": "OBS Studio is not connected"}
        try:
            res = self._client.toggle_record()
            return {"success": True, "output_active": res.output_active}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def toggle_stream(self) -> Dict[str, Any]:
        if not self.is_connected or not self._client:
            return {"success": False, "error": "OBS Studio is not connected"}
        try:
            res = self._client.toggle_stream()
            return {"success": True, "output_active": res.output_active}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def toggle_virtual_cam(self) -> Dict[str, Any]:
        if not self.is_connected or not self._client:
            return {"success": False, "error": "OBS Studio is not connected"}
        try:
            res = self._client.toggle_virtual_cam()
            return {"success": True, "output_active": res.output_active}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_output_status(self) -> Dict[str, Any]:
        if not self.is_connected or not self._client:
            return {"recording": False, "streaming": False, "virtual_cam": False}
        try:
            rec = self._client.get_record_status().output_active
            strm = self._client.get_stream_status().output_active
            vcam = self._client.get_virtual_cam_status().output_active
            return {"recording": rec, "streaming": strm, "virtual_cam": vcam}
        except Exception:
            return {"recording": False, "streaming": False, "virtual_cam": False}

obs_client = OBSClient()

