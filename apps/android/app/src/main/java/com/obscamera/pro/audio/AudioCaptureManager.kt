package com.obscamera.pro.audio

import android.annotation.SuppressLint
import android.media.AudioFormat
import android.media.AudioRecord
import android.media.MediaRecorder
import android.util.Log
import kotlin.math.log10
import kotlin.math.sqrt

class AudioCaptureManager {

    private val tag = "OBSCameraPro.Audio"
    private var audioRecord: AudioRecord? = null
    private var isRecording = false
    private var recordingThread: Thread? = null

    var isMuted: Boolean = false
    var gain: Float = 1.0f
    var currentAudioLevelDb: Float = -60.0f
        private set

    companion object {
        private const val SAMPLE_RATE = 48000
        private const val CHANNEL_CONFIG = AudioFormat.CHANNEL_IN_MONO
        private const val AUDIO_FORMAT = AudioFormat.ENCODING_PCM_16BIT
    }

    @SuppressLint("MissingPermission")
    fun startCapture() {
        if (isRecording) return

        val minBufferSize = AudioRecord.getMinBufferSize(SAMPLE_RATE, CHANNEL_CONFIG, AUDIO_FORMAT)
        val bufferSize = minBufferSize * 2

        try {
            audioRecord = AudioRecord(
                MediaRecorder.AudioSource.MIC,
                SAMPLE_RATE,
                CHANNEL_CONFIG,
                AUDIO_FORMAT,
                bufferSize
            )

            if (audioRecord?.state != AudioRecord.STATE_INITIALIZED) {
                Log.e(tag, "AudioRecord initialization failed")
                return
            }

            audioRecord?.startRecording()
            isRecording = true

            recordingThread = Thread {
                val buffer = ShortArray(1024)
                while (isRecording) {
                    val read = audioRecord?.read(buffer, 0, buffer.size) ?: 0
                    if (read > 0) {
                        calculateRmsLevel(buffer, read)
                    }
                }
            }.apply {
                priority = Thread.MAX_PRIORITY
                start()
            }

            Log.i(tag, "Microphone capture started at ${SAMPLE_RATE}Hz")
        } catch (e: Exception) {
            Log.e(tag, "Error starting audio capture: ${e.message}", e)
        }
    }

    fun stopCapture() {
        isRecording = false
        try {
            audioRecord?.stop()
            audioRecord?.release()
        } catch (e: Exception) {
            Log.w(tag, "Error stopping audioRecord: ${e.message}")
        } finally {
            audioRecord = null
            recordingThread = null
            currentAudioLevelDb = -60.0f
        }
    }

    private fun calculateRmsLevel(buffer: ShortArray, readSize: Int) {
        if (isMuted) {
            currentAudioLevelDb = -60.0f
            return
        }

        var sum = 0.0
        for (i in 0 until readSize) {
            val sample = buffer[i] * gain
            sum += sample * sample
        }
        val rms = sqrt(sum / readSize)
        // Convert to dBFS (Full Scale 32767 for 16-bit)
        val db = if (rms > 0) {
            20 * log10(rms / 32767.0)
        } else {
            -60.0
        }
        currentAudioLevelDb = db.coerceIn(-60.0, 0.0).toFloat()
    }
}

