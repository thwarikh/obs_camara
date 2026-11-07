package com.obscamera.pro.controls

import android.util.Log
import androidx.lifecycle.LifecycleOwner
import androidx.camera.core.Preview
import com.google.gson.JsonObject
import com.obscamera.pro.audio.AudioCaptureManager
import com.obscamera.pro.camera.CameraLens
import com.obscamera.pro.camera.CameraManager
import com.obscamera.pro.camera.ResolutionProfile
import com.obscamera.pro.streaming.SignalingClient

class RemoteControlHandler(
    private val cameraManager: CameraManager,
    private val audioManager: AudioCaptureManager,
    private val signalingClient: SignalingClient,
    private val lifecycleOwner: LifecycleOwner,
    private val surfaceProvider: Preview.SurfaceProvider
) {

    private val tag = "OBSCameraPro.Controls"

    fun handleCommand(cmd: JsonObject) {
        val type = cmd.get("type")?.asString ?: return
        val applied = JsonObject()

        when (type) {
            "camera_control_command" -> {
                if (cmd.has("zoom")) {
                    val z = cmd.get("zoom").asFloat
                    cameraManager.setZoom(z)
                    applied.addProperty("zoom", z)
                }
                if (cmd.has("torch_enabled")) {
                    val t = cmd.get("torch_enabled").asBoolean
                    cameraManager.setTorch(t)
                    applied.addProperty("torch_enabled", t)
                }
                if (cmd.has("focus_mode")) {
                    val mode = cmd.get("focus_mode").asString
                    if (mode == "manual" && cmd.has("focus_distance")) {
                        val dist = cmd.get("focus_distance").asFloat
                        cameraManager.setManualFocus(dist)
                        applied.addProperty("focus_distance", dist)
                    } else {
                        cameraManager.setAutoFocus()
                        applied.addProperty("focus_mode", mode)
                    }
                }
                if (cmd.has("iso")) {
                    val iso = cmd.get("iso").asInt
                    val comp = cmd.get("exposure_compensation")?.asFloat ?: 0f
                    cameraManager.setManualExposure(iso, comp)
                    applied.addProperty("iso", iso)
                }
                if (cmd.has("white_balance_mode")) {
                    val wb = cmd.get("white_balance_mode").asString
                    cameraManager.setWhiteBalance(wb)
                    applied.addProperty("white_balance_mode", wb)
                }
                if (cmd.has("lens")) {
                    val lensId = cmd.get("lens").asString
                    val targetLens = CameraLens.fromId(lensId)
                    cameraManager.switchLens(targetLens, lifecycleOwner, surfaceProvider)
                    applied.addProperty("lens", targetLens.idStr)
                }
                if (cmd.has("resolution_profile")) {
                    val profId = cmd.get("resolution_profile").asString
                    val targetProf = ResolutionProfile.fromId(profId)
                    cameraManager.switchProfile(targetProf, lifecycleOwner, surfaceProvider)
                    applied.addProperty("resolution_profile", targetProf.idStr)
                }

                // Send confirmation back to desktop
                signalingClient.sendControlConfirmation(applied)
            }

            "audio_control_command" -> {
                if (cmd.has("muted")) {
                    val m = cmd.get("muted").asBoolean
                    audioManager.isMuted = m
                    applied.addProperty("muted", m)
                }
                if (cmd.has("gain")) {
                    val g = cmd.get("gain").asFloat
                    audioManager.gain = g
                    applied.addProperty("gain", g)
                }
                signalingClient.sendControlConfirmation(applied)
            }
        }
    }
}

