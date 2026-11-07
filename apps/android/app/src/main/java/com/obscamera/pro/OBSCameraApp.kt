package com.obscamera.pro

import android.app.Application
import android.app.NotificationChannel
import android.app.NotificationManager
import android.os.Build

class OBSCameraApp : Application() {

    companion object {
        const val CHANNEL_ID = "obs_camera_streaming_channel"
        lateinit var instance: OBSCameraApp
            private set
    }

    override fun onCreate() {
        super.onCreate()
        instance = this
        createNotificationChannel()
    }

    private fun createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                CHANNEL_ID,
                "OBS Camera Pro Streaming Service",
                NotificationManager.IMPORTANCE_LOW
            ).apply {
                description = "Keeps camera and audio stream active for OBS Studio broadcast"
            }
            val manager = getSystemService(NotificationManager::class.java)
            manager?.createNotificationChannel(channel)
        }
    }
}

