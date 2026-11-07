package com.obscamera.pro.streaming

import android.os.Handler
import android.os.Looper
import android.util.Log
import com.google.gson.Gson
import com.google.gson.JsonObject
import okhttp3.*
import java.util.concurrent.TimeUnit

class SignalingClient(
    private val deviceId: String,
    private val host: String,
    private val port: Int,
    private val listener: SignalingListener
) {

    interface SignalingListener {
        fun onConnected()
        fun onDisconnected()
        fun onControlCommandReceived(command: JsonObject)
    }

    private val tag = "OBSCameraPro.Signaling"
    private val gson = Gson()
    private val client = OkHttpClient.Builder()
        .readTimeout(0, TimeUnit.MILLISECONDS)
        .pingInterval(10, TimeUnit.SECONDS)
        .build()

    private var webSocket: WebSocket? = null
    private var isConnected = false
    private val mainHandler = Handler(Looper.getMainLooper())

    fun connect() {
        val wsUrl = "ws://$host:$port/ws/camera/$deviceId"
        Log.i(tag, "Connecting signaling WebSocket to $wsUrl")
        val request = Request.Builder().url(wsUrl).build()

        webSocket = client.newWebSocket(request, object : WebSocketListener() {
            override fun onOpen(ws: WebSocket, response: Response) {
                isConnected = true
                Log.i(tag, "Signaling WebSocket connected successfully")
                mainHandler.post { listener.onConnected() }
            }

            override fun onMessage(ws: WebSocket, text: String) {
                try {
                    val json = gson.fromJson(text, JsonObject::class.java)
                    mainHandler.post { listener.onControlCommandReceived(json) }
                } catch (e: Exception) {
                    Log.e(tag, "Failed to parse signaling message: ${e.message}")
                }
            }

            override fun onClosing(ws: WebSocket, code: Int, reason: String) {
                isConnected = false
            }

            override fun onClosed(ws: WebSocket, code: Int, reason: String) {
                isConnected = false
                mainHandler.post { listener.onDisconnected() }
            }

            override fun onFailure(ws: WebSocket, t: Throwable, response: Response?) {
                isConnected = false
                Log.w(tag, "Signaling connection failure: ${t.message}")
                mainHandler.post { listener.onDisconnected() }
            }
        })
    }

    fun sendTelemetry(
        fps: Float,
        bitrateKbps: Int,
        batteryPct: Int,
        isCharging: Boolean,
        batteryTempC: Float,
        audioLevelDb: Float,
        networkType: String
    ) {
        if (!isConnected) return

        val envelope = JsonObject().apply {
            addProperty("type", "telemetry")
            addProperty("device_id", deviceId)
            val payload = JsonObject().apply {
                addProperty("fps", fps)
                addProperty("bitrate_kbps", bitrateKbps)
                addProperty("battery_pct", batteryPct)
                addProperty("is_charging", isCharging)
                addProperty("battery_temp_c", batteryTempC)
                addProperty("audio_level_db", audioLevelDb)
                addProperty("network_type", networkType)
            }
            add("payload", payload)
        }

        webSocket?.send(gson.toJson(envelope))
    }

    fun sendControlConfirmation(applied: JsonObject) {
        if (!isConnected) return
        val envelope = JsonObject().apply {
            addProperty("type", "camera_control_applied")
            addProperty("device_id", deviceId)
            add("payload", applied)
        }
        webSocket?.send(gson.toJson(envelope))
    }

    fun disconnect() {
        try {
            webSocket?.close(1000, "Normal closure")
        } catch (e: Exception) {}
        isConnected = false
    }
}

