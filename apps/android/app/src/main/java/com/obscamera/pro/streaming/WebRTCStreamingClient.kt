package com.obscamera.pro.streaming

import android.content.Context
import android.util.Log
import okhttp3.*
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.RequestBody.Companion.toRequestBody
import org.webrtc.*
import java.io.IOException

class WebRTCStreamingClient(
    private val context: Context,
    private val whipUrl: String,
    private val listener: StreamStateListener
) {

    interface StreamStateListener {
        fun onStreamStarted()
        fun onStreamStopped()
        fun onStreamError(error: String)
    }

    private val tag = "OBSCameraPro.WebRTC"
    private val eglBase = EglBase.create()
    private var peerConnectionFactory: PeerConnectionFactory? = null
    private var peerConnection: PeerConnection? = null
    private var videoTrack: VideoTrack? = null
    private var audioTrack: AudioTrack? = null
    private var capturerObserver: CapturerObserver? = null

    private val httpClient = OkHttpClient()
    var isStreaming = false
        private set

    fun initialize() {
        PeerConnectionFactory.initialize(
            PeerConnectionFactory.InitializationOptions.builder(context)
                .setEnableInternalTracer(false)
                .createInitializationOptions()
        )

        val defaultVideoEncoderFactory = DefaultVideoEncoderFactory(
            eglBase.eglBaseContext,
            true,
            true
        )
        val defaultVideoDecoderFactory = DefaultVideoDecoderFactory(eglBase.eglBaseContext)

        peerConnectionFactory = PeerConnectionFactory.builder()
            .setVideoEncoderFactory(defaultVideoEncoderFactory)
            .setVideoDecoderFactory(defaultVideoDecoderFactory)
            .setOptions(PeerConnectionFactory.Options())
            .createPeerConnectionFactory()

        Log.i(tag, "WebRTC PeerConnectionFactory initialized for WHIP: $whipUrl")
    }

    fun startStreaming() {
        val factory = peerConnectionFactory ?: return
        if (isStreaming) return
        isStreaming = true

        // 1. Video Source & Track
        val videoSource = factory.createVideoSource(false)
        this.capturerObserver = videoSource.capturerObserver
        videoTrack = factory.createVideoTrack("obs_camera_video", videoSource)

        // 2. Audio Source & Track
        val audioConstraints = MediaConstraints().apply {
            mandatory.add(MediaConstraints.KeyValuePair("googEchoCancellation", "true"))
            mandatory.add(MediaConstraints.KeyValuePair("googAutoGainControl", "true"))
            mandatory.add(MediaConstraints.KeyValuePair("googHighpassFilter", "true"))
            mandatory.add(MediaConstraints.KeyValuePair("googNoiseSuppression", "true"))
        }
        val audioSource = factory.createAudioSource(audioConstraints)
        audioTrack = factory.createAudioTrack("obs_camera_audio", audioSource)

        // 3. Create PeerConnection
        val iceServers = listOf(
            PeerConnection.IceServer.builder("stun:stun.l.google.com:19302").createIceServer()
        )
        val rtcConfig = PeerConnection.RTCConfiguration(iceServers).apply {
            sdpSemantics = PeerConnection.SdpSemantics.UNIFIED_PLAN
            continualGatheringPolicy = PeerConnection.ContinualGatheringPolicy.GATHER_CONTINUALLY
        }

        peerConnection = factory.createPeerConnection(rtcConfig, object : PeerConnection.Observer {
            override fun onIceCandidate(candidate: IceCandidate?) {}
            override fun onIceCandidatesRemoved(candidates: Array<out IceCandidate>?) {}
            override fun onSignalingChange(state: PeerConnection.SignalingState?) {}
            override fun onIceConnectionChange(state: PeerConnection.IceConnectionState?) {
                Log.d(tag, "ICE Connection State: $state")
            }
            override fun onIceConnectionReceivingChange(receiving: Boolean) {}
            override fun onIceGatheringChange(state: PeerConnection.IceGatheringState?) {}
            override fun onAddStream(stream: MediaStream?) {}
            override fun onRemoveStream(stream: MediaStream?) {}
            override fun onDataChannel(dc: DataChannel?) {}
            override fun onRenegotiationNeeded() {}
            override fun onAddTrack(receiver: RtpReceiver?, streams: Array<out MediaStream>?) {}
        })

        // Add Tracks
        peerConnection?.addTrack(videoTrack, listOf("obs_stream"))
        peerConnection?.addTrack(audioTrack, listOf("obs_stream"))

        // Create SDP Offer for WHIP
        val mediaConstraints = MediaConstraints().apply {
            mandatory.add(MediaConstraints.KeyValuePair("OfferToReceiveAudio", "false"))
            mandatory.add(MediaConstraints.KeyValuePair("OfferToReceiveVideo", "false"))
        }

        peerConnection?.createOffer(object : SdpObserver {
            override fun onCreateSuccess(desc: SessionDescription?) {
                desc?.let { offerSdp ->
                    peerConnection?.setLocalDescription(object : SdpObserver {
                        override fun onCreateSuccess(p0: SessionDescription?) {}
                        override fun onSetSuccess() {
                            sendWhipOffer(offerSdp.description)
                        }
                        override fun onCreateFailure(p0: String?) {}
                        override fun onSetFailure(p0: String?) {}
                    }, offerSdp)
                }
            }
            override fun onSetSuccess() {}
            override fun onCreateFailure(err: String?) {
                listener.onStreamError("Offer creation failed: $err")
            }
            override fun onSetFailure(err: String?) {}
        }, mediaConstraints)
    }

    fun onFrameCaptured(frame: VideoFrame) {
        if (isStreaming) {
            capturerObserver?.onFrameCaptured(frame)
        }
    }

    private fun sendWhipOffer(sdp: String) {
        val requestBody = sdp.toRequestBody("application/sdp; charset=utf-8".toMediaType())
        val request = Request.Builder()
            .url(whipUrl)
            .post(requestBody)
            .build()

        httpClient.newCall(request).enqueue(object : Callback {
            override fun onFailure(call: Call, e: IOException) {
                Log.e(tag, "WHIP request failed: ${e.message}")
                listener.onStreamError("WHIP ingest failed: ${e.message}")
            }

            override fun onResponse(call: Call, response: Response) {
                if (response.isSuccessful) {
                    val answerSdp = response.body?.string() ?: ""
                    val answer = SessionDescription(SessionDescription.Type.ANSWER, answerSdp)
                    peerConnection?.setRemoteDescription(object : SdpObserver {
                        override fun onCreateSuccess(p0: SessionDescription?) {}
                        override fun onSetSuccess() {
                            Log.i(tag, "WebRTC WHIP Session connected successfully to MediaMTX!")
                            listener.onStreamStarted()
                        }
                        override fun onCreateFailure(p0: String?) {}
                        override fun onSetFailure(err: String?) {
                            Log.e(tag, "Failed to set remote answer: $err")
                        }
                    }, answer)
                } else {
                    Log.e(tag, "MediaMTX WHIP returned HTTP ${response.code}")
                    listener.onStreamError("MediaMTX WHIP HTTP ${response.code}")
                }
            }
        })
    }

    fun stopStreaming() {
        isStreaming = false
        try {
            peerConnection?.close()
            peerConnection = null
            videoTrack?.dispose()
            audioTrack?.dispose()
            listener.onStreamStopped()
            Log.i(tag, "Streaming stopped cleanly")
        } catch (e: Exception) {
            Log.w(tag, "Error closing stream: ${e.message}")
        }
    }
}
