package com.obscamera.pro.ui

import android.Manifest
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import android.provider.Settings
import android.widget.Toast
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.core.content.ContextCompat
import com.google.gson.JsonObject
import com.obscamera.pro.audio.AudioCaptureManager
import com.obscamera.pro.camera.CameraManager
import com.obscamera.pro.connection.NetworkMonitor
import com.obscamera.pro.controls.RemoteControlHandler
import com.obscamera.pro.service.CameraStreamingService
import com.obscamera.pro.streaming.SignalingClient

class MainActivity : ComponentActivity(), SignalingClient.SignalingListener {

    private lateinit var cameraManager: CameraManager
    private lateinit var audioManager: AudioCaptureManager
    private lateinit var networkMonitor: NetworkMonitor
    private var signalingClient: SignalingClient? = null
    private var controlHandler: RemoteControlHandler? = null

    private var deviceId: String = ""
    private var isStreaming: Boolean = false
    private var connectionType: String = "wifi"

    private val requiredPermissions = buildList {
        add(Manifest.permission.CAMERA)
        add(Manifest.permission.RECORD_AUDIO)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            add(Manifest.permission.POST_NOTIFICATIONS)
        }
    }.toTypedArray()

    private val permissionLauncher = registerForActivityResult(
        ActivityResultContracts.RequestMultiplePermissions()
    ) { permissions ->
        val allGranted = permissions.entries.all { it.value }
        if (!allGranted) {
            Toast.makeText(this, "Camera & Audio permissions are required for OBS broadcast.", Toast.LENGTH_LONG).show()
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        // Unique device ID
        deviceId = Settings.Secure.getString(contentResolver, Settings.Secure.ANDROID_ID) ?: "android_${System.currentTimeMillis()}"

        cameraManager = CameraManager(this)
        audioManager = AudioCaptureManager()

        networkMonitor = NetworkMonitor(this) { type ->
            connectionType = type
        }
        networkMonitor.startMonitoring()

        checkPermissions()

        setContent {
            MainCameraScreen(
                cameraManager = cameraManager,
                isStreaming = isStreaming,
                connectionType = connectionType,
                fps = 30.0f,
                bitrateKbps = 5000,
                batteryPct = 85,
                audioLevelDb = audioManager.currentAudioLevelDb,
                onStartStreaming = { startBroadcast() },
                onStopStreaming = { stopBroadcast() },
                onOpenPairing = {
                    Toast.makeText(this, "Scan QR Code on PC Dashboard to pair", Toast.LENGTH_SHORT).show()
                }
            )
        }
    }

    private fun checkPermissions() {
        val missing = requiredPermissions.filter {
            ContextCompat.checkSelfPermission(this, it) != PackageManager.PERMISSION_GRANTED
        }
        if (missing.isNotEmpty()) {
            permissionLauncher.launch(missing.toTypedArray())
        }
    }

    private fun startBroadcast() {
        isStreaming = true
        audioManager.startCapture()

        // Start Foreground Service to keep streaming alive
        val serviceIntent = Intent(this, CameraStreamingService::class.java)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            startForegroundService(serviceIntent)
        } else {
            startService(serviceIntent)
        }

        Toast.makeText(this, "Broadcasting to OBS Studio", Toast.LENGTH_SHORT).show()
    }

    private fun stopBroadcast() {
        isStreaming = false
        audioManager.stopCapture()
        stopService(Intent(this, CameraStreamingService::class.java))
        signalingClient?.disconnect()
    }

    override fun onConnected() {
        // Signaling active
    }

    override fun onDisconnected() {
        // Reconnect if streaming
    }

    override fun onControlCommandReceived(command: JsonObject) {
        controlHandler?.handleCommand(command)
    }

    override fun onDestroy() {
        super.onDestroy()
        networkMonitor.stopMonitoring()
        audioManager.stopCapture()
        signalingClient?.disconnect()
    }
}

