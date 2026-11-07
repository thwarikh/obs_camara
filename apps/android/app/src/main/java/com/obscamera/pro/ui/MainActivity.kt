package com.obscamera.pro.ui

import android.Manifest
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.os.BatteryManager
import android.os.Build
import android.os.Bundle
import android.provider.Settings
import android.util.Log
import android.widget.Toast
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.runtime.mutableStateOf
import androidx.core.content.ContextCompat
import androidx.lifecycle.lifecycleScope
import com.google.gson.Gson
import com.google.gson.JsonObject
import com.obscamera.pro.audio.AudioCaptureManager
import com.obscamera.pro.camera.CameraManager
import com.obscamera.pro.connection.NetworkMonitor
import com.obscamera.pro.controls.RemoteControlHandler
import com.obscamera.pro.service.CameraStreamingService
import com.obscamera.pro.streaming.SignalingClient
import com.obscamera.pro.streaming.WebRTCStreamingClient
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody

class MainActivity : ComponentActivity(), SignalingClient.SignalingListener, WebRTCStreamingClient.StreamStateListener {

    private val tag = "OBSCameraPro.Main"
    private lateinit var cameraManager: CameraManager
    private lateinit var audioManager: AudioCaptureManager
    private lateinit var networkMonitor: NetworkMonitor
    private var signalingClient: SignalingClient? = null
    private var controlHandler: RemoteControlHandler? = null
    private var webRtcClient: WebRTCStreamingClient? = null

    private var deviceId: String = ""
    private var isStreamingState = mutableStateOf(false)
    private var isConnectedToPcState = mutableStateOf(false)
    private var pcHostState = mutableStateOf("")
    private var isScanningQrState = mutableStateOf(false)
    private var connectionTypeState = mutableStateOf("wifi")

    private val httpClient = OkHttpClient()

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

        // Generate persistent unique device ID
        deviceId = Settings.Secure.getString(contentResolver, Settings.Secure.ANDROID_ID)
            ?: "android_${Build.MODEL.replace(" ", "_")}"

        cameraManager = CameraManager(this)
        audioManager = AudioCaptureManager()

        networkMonitor = NetworkMonitor(this) { type ->
            connectionTypeState.value = type
        }
        networkMonitor.startMonitoring()

        checkPermissions()

        // Restore saved PC host if previously paired
        val prefs = getSharedPreferences("obs_camera_prefs", Context.MODE_PRIVATE)
        val savedHost = prefs.getString("pc_host", "") ?: ""
        val savedPort = prefs.getInt("pc_port", 8000)
        if (savedHost.isNotEmpty()) {
            pcHostState.value = savedHost
            connectToPc(savedHost, savedPort)
        }

        // Setup ML Kit QR code detection callback
        cameraManager.onQrCodeDetected = { raw ->
            handleScannedQrPayload(raw)
        }

        setContent {
            MainCameraScreen(
                cameraManager = cameraManager,
                isStreaming = isStreamingState.value,
                isConnectedToPc = isConnectedToPcState.value,
                pcHost = pcHostState.value,
                connectionType = connectionTypeState.value,
                fps = 30.0f,
                bitrateKbps = 5000,
                batteryPct = getBatteryPercentage(),
                audioLevelDb = audioManager.currentAudioLevelDb,
                isScanningQr = isScanningQrState.value,
                onStartStreaming = { startBroadcast() },
                onStopStreaming = { stopBroadcast() },
                onStartQrScan = {
                    isScanningQrState.value = true
                    cameraManager.isQrScanningEnabled = true
                    Toast.makeText(this, "Point camera at desktop QR code", Toast.LENGTH_SHORT).show()
                },
                onStopQrScan = {
                    isScanningQrState.value = false
                    cameraManager.isQrScanningEnabled = false
                },
                onConnectManualIp = { host, port ->
                    connectToPc(host, port)
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

    private fun handleScannedQrPayload(raw: String) {
        lifecycleScope.launch(Dispatchers.Main) {
            isScanningQrState.value = false
            cameraManager.isQrScanningEnabled = false
            try {
                val json = Gson().fromJson(raw, JsonObject::class.java)
                val host = json.get("host")?.asString ?: ""
                val port = json.get("port")?.asInt ?: 8000
                if (host.isNotEmpty()) {
                    Toast.makeText(this@MainActivity, "QR Scanned: Connecting to $host:$port", Toast.LENGTH_SHORT).show()
                    connectToPc(host, port)
                } else {
                    Toast.makeText(this@MainActivity, "Invalid QR Code format", Toast.LENGTH_SHORT).show()
                }
            } catch (e: Exception) {
                Log.w(tag, "Failed to parse QR JSON: ${e.message}")
                Toast.makeText(this@MainActivity, "Could not read QR: ${e.message}", Toast.LENGTH_SHORT).show()
            }
        }
    }

    fun connectToPc(host: String, port: Int) {
        if (host.isBlank()) {
            Toast.makeText(this, "Please enter a valid PC IP Address", Toast.LENGTH_SHORT).show()
            return
        }

        lifecycleScope.launch(Dispatchers.IO) {
            try {
                // 1. Register device with Desktop Backend
                val registerUrl = "http://$host:$port/api/devices/register"
                val jsonPayload = JsonObject().apply {
                    addProperty("device_id", deviceId)
                    addProperty("custom_name", "${Build.MANUFACTURER} ${Build.MODEL}")
                    addProperty("platform", "android")
                    addProperty("model", Build.MODEL)
                    addProperty("os_version", "Android ${Build.VERSION.RELEASE}")
                    addProperty("token", "paired_token")
                }

                val request = Request.Builder()
                    .url(registerUrl)
                    .post(jsonPayload.toString().toRequestBody("application/json; charset=utf-8".toMediaType()))
                    .build()

                val response = httpClient.newCall(request).execute()
                val isSuccess = response.isSuccessful
                val respBody = response.body?.string() ?: ""

                withContext(Dispatchers.Main) {
                    if (isSuccess) {
                        // 2. Save credentials
                        val prefs = getSharedPreferences("obs_camera_prefs", Context.MODE_PRIVATE)
                        prefs.edit().putString("pc_host", host).putInt("pc_port", port).apply()

                        pcHostState.value = host
                        isConnectedToPcState.value = true

                        // Parse WHIP stream URL from server response
                        var whipUrl = "http://$host:8889/camera_${deviceId.lowercase().replace("-", "")}/whip"
                        try {
                            val respJson = Gson().fromJson(respBody, JsonObject::class.java)
                            respJson.getAsJsonObject("stream_urls")?.get("whip_publish_url")?.asString?.let {
                                whipUrl = it
                            }
                        } catch (e: Exception) {}

                        // 3. Initialize WebRTC WHIP streaming client
                        webRtcClient?.stopStreaming()
                        webRtcClient = WebRTCStreamingClient(this@MainActivity, whipUrl, this@MainActivity)
                        webRtcClient?.initialize()

                        // Pipe camera frames to WebRTC
                        cameraManager.onFrameAvailable = { videoFrame ->
                            webRtcClient?.onFrameCaptured(videoFrame)
                        }

                        // 4. Connect Signaling WebSocket
                        signalingClient?.disconnect()
                        signalingClient = SignalingClient(deviceId, host, port, this@MainActivity)
                        signalingClient?.connect()

                        // 5. Initialize Remote Control Handler if preview is active
                        cameraManager.cachedLifecycleOwner?.let { owner ->
                            cameraManager.cachedSurfaceProvider?.let { provider ->
                                signalingClient?.let { client ->
                                    controlHandler = RemoteControlHandler(cameraManager, audioManager, client, owner, provider)
                                }
                            }
                        }

                        Toast.makeText(this@MainActivity, "Connected to OBS PC ($host:$port)", Toast.LENGTH_LONG).show()
                    } else {
                        Toast.makeText(this@MainActivity, "PC Connection failed: HTTP ${response.code}", Toast.LENGTH_LONG).show()
                    }
                }
            } catch (e: Exception) {
                Log.e(tag, "Connection error: ${e.message}", e)
                withContext(Dispatchers.Main) {
                    Toast.makeText(this@MainActivity, "Connection error: ${e.localizedMessage ?: e.message}", Toast.LENGTH_LONG).show()
                }
            }
        }
    }

    private fun startBroadcast() {
        if (!isConnectedToPcState.value) {
            Toast.makeText(this, "Please pair with your PC first using the QR button", Toast.LENGTH_LONG).show()
            return
        }

        isStreamingState.value = true
        audioManager.startCapture()

        // 1. Enable CameraX to WebRTC frame piping
        cameraManager.isStreamingToWebRtc = true
        webRtcClient?.startStreaming()

        // 2. Start Foreground Service
        val serviceIntent = Intent(this, CameraStreamingService::class.java)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            startForegroundService(serviceIntent)
        } else {
            startService(serviceIntent)
        }

        // 3. Start live telemetry loop to Desktop Dashboard
        lifecycleScope.launch(Dispatchers.IO) {
            while (isActive && isStreamingState.value) {
                signalingClient?.sendTelemetry(
                    fps = 30.0f,
                    bitrateKbps = 5000,
                    batteryPct = getBatteryPercentage(),
                    isCharging = false,
                    batteryTempC = 34.0f,
                    audioLevelDb = audioManager.currentAudioLevelDb,
                    networkType = connectionTypeState.value
                )
                delay(1000)
            }
        }

        Toast.makeText(this, "Streaming live video to OBS Studio!", Toast.LENGTH_SHORT).show()
    }

    private fun stopBroadcast() {
        isStreamingState.value = false
        cameraManager.isStreamingToWebRtc = false
        webRtcClient?.stopStreaming()
        audioManager.stopCapture()
        stopService(Intent(this, CameraStreamingService::class.java))
        Toast.makeText(this, "Broadcast stopped", Toast.LENGTH_SHORT).show()
    }

    private fun getBatteryPercentage(): Int {
        val bm = getSystemService(Context.BATTERY_SERVICE) as? BatteryManager
        return bm?.getIntProperty(BatteryManager.BATTERY_PROPERTY_CAPACITY) ?: 80
    }

    override fun onConnected() {
        lifecycleScope.launch(Dispatchers.Main) {
            isConnectedToPcState.value = true
            Log.i(tag, "Signaling WebSocket connected to desktop")
        }
    }

    override fun onDisconnected() {
        lifecycleScope.launch(Dispatchers.Main) {
            Log.w(tag, "Signaling WebSocket disconnected")
        }
    }

    override fun onControlCommandReceived(command: JsonObject) {
        controlHandler?.handleCommand(command)
    }

    override fun onStreamStarted() {
        lifecycleScope.launch(Dispatchers.Main) {
            Log.i(tag, "WebRTC live stream ingest active")
        }
    }

    override fun onStreamStopped() {
        lifecycleScope.launch(Dispatchers.Main) {
            Log.i(tag, "WebRTC live stream ingest stopped")
        }
    }

    override fun onStreamError(error: String) {
        lifecycleScope.launch(Dispatchers.Main) {
            Log.e(tag, "WebRTC live stream error: $error")
        }
    }

    override fun onDestroy() {
        super.onDestroy()
        networkMonitor.stopMonitoring()
        webRtcClient?.stopStreaming()
        audioManager.stopCapture()
        signalingClient?.disconnect()
    }
}
