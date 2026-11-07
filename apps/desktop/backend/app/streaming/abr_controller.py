"""
Adaptive Bitrate (ABR) and Thermal Quality Controller for OBS Camera Pro.
Monitors packet loss, round-trip time (RTT), dropped frames, and mobile device battery temperature.
Automatically calculates optimal resolution and bitrate target recommendations.
"""
import time
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger("OBSCameraPro.ABRController")

class ABRController:
    def __init__(self):
        # Cache per-device network history and state: device_id -> dict
        self._device_states: Dict[str, Dict[str, Any]] = {}

    def evaluate_telemetry(self, device_id: str, telemetry: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyzes incoming telemetry packet and determines stream health and ABR recommendation.
        """
        now = time.time()
        rtt_ms = telemetry.get("network_rtt_ms", 10.0)
        packet_loss = telemetry.get("packet_loss_pct", 0.0)
        temp_c = telemetry.get("battery_temp_c", 30.0)
        current_bitrate = telemetry.get("bitrate_kbps", 5000)
        fps = telemetry.get("fps", 30.0)

        # 1. Calculate Stream Health Grade
        if packet_loss > 5.0 or rtt_ms > 200.0 or temp_c > 44.0:
            health_grade = "CRITICAL"
        elif packet_loss > 2.0 or rtt_ms > 100.0 or temp_c > 40.0:
            health_grade = "DEGRADED"
        elif packet_loss > 0.5 or rtt_ms > 60.0:
            health_grade = "FAIR"
        else:
            health_grade = "EXCELLENT"

        # 2. Compute Recommended Profile and Target Bitrate
        state = self._device_states.setdefault(device_id, {
            "current_recommended_profile": "1080p30",
            "last_downgrade_time": 0,
            "last_upgrade_time": now,
            "consecutive_good_checks": 0
        })

        recommended_profile = state["current_recommended_profile"]
        action = "maintain"

        # Check for necessary downgrade
        if health_grade in ["CRITICAL", "DEGRADED"]:
            if now - state["last_downgrade_time"] > 10:  # 10s cooldown
                if recommended_profile == "4k30":
                    recommended_profile = "1080p30"
                    action = "downgrade"
                elif recommended_profile == "1080p60":
                    recommended_profile = "1080p30"
                    action = "downgrade"
                elif recommended_profile == "1080p30":
                    recommended_profile = "720p30"
                    action = "downgrade"

                state["current_recommended_profile"] = recommended_profile
                state["last_downgrade_time"] = now
                state["consecutive_good_checks"] = 0
                logger.warning(f"ABR [Device {device_id}]: Downgrading profile to {recommended_profile} due to {health_grade} network/thermal conditions.")
        elif health_grade == "EXCELLENT":
            state["consecutive_good_checks"] += 1
            # Require 30 consecutive seconds of pristine metrics before upgrading
            if state["consecutive_good_checks"] >= 30 and (now - state["last_downgrade_time"] > 45):
                if recommended_profile == "720p30":
                    recommended_profile = "1080p30"
                    action = "upgrade"
                elif recommended_profile == "1080p30":
                    recommended_profile = "1080p60"
                    action = "upgrade"

                state["current_recommended_profile"] = recommended_profile
                state["last_upgrade_time"] = now
                state["consecutive_good_checks"] = 0
                logger.info(f"ABR [Device {device_id}]: Network stable. Upgrading profile to {recommended_profile}.")

        result = {
            "device_id": device_id,
            "health_grade": health_grade,
            "action": action,
            "recommended_profile": recommended_profile,
            "metrics": {
                "rtt_ms": rtt_ms,
                "packet_loss_pct": packet_loss,
                "temp_c": temp_c,
                "fps": fps,
                "bitrate_kbps": current_bitrate
            },
            "timestamp": now
        }
        return result

abr_controller = ABRController()

