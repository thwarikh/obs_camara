package com.obscamera.pro.camera

import android.annotation.SuppressLint
import android.content.Context
import android.hardware.camera2.CameraCharacteristics
import android.hardware.camera2.CameraMetadata
import android.hardware.camera2.CaptureRequest
import android.util.Log
import android.util.Range
import android.util.Size
import androidx.camera.camera2.interop.Camera2CameraControl
import androidx.camera.camera2.interop.Camera2CameraInfo
import androidx.camera.camera2.interop.CaptureRequestOptions
import androidx.camera.core.*
import androidx.camera.lifecycle.ProcessCameraProvider
import androidx.core.content.ContextCompat
import androidx.lifecycle.LifecycleOwner
import com.google.mlkit.vision.barcode.BarcodeScanning
import com.google.mlkit.vision.common.InputImage
import com.obscamera.pro.streaming.YuvHelper
import org.webrtc.VideoFrame
import java.util.concurrent.Executors

class CameraManager(private val context: Context) {

    private val tag = "OBSCameraPro.CamManager"
    private var cameraProvider: ProcessCameraProvider? = null
    private var camera: Camera? = null
    private var camera2Control: Camera2CameraControl? = null
    private var camera2Info: Camera2CameraInfo? = null

    var isQrScanningEnabled: Boolean = false
    var onQrCodeDetected: ((String) -> Unit)? = null
    var isStreamingToWebRtc: Boolean = false
    var onFrameAvailable: ((VideoFrame) -> Unit)? = null

    var cachedLifecycleOwner: LifecycleOwner? = null
        private set
    var cachedSurfaceProvider: Preview.SurfaceProvider? = null
        private set

    var currentLens: CameraLens = CameraLens.BACK_WIDE
        private set
    var currentProfile: ResolutionProfile = ResolutionProfile.PROFILE_1080P30
        private set
    var currentRotationDegrees: Int = 0
        private set

    // Hardware bounds
    var isoRange: Range<Int> = Range(50, 3200)
        private set
    var maxZoomRatio: Float = 10f
        private set

    fun initialize(lifecycleOwner: LifecycleOwner, surfaceProvider: Preview.SurfaceProvider, onReady: () -> Unit) {
        val cameraProviderFuture = ProcessCameraProvider.getInstance(context)
        cameraProviderFuture.addListener({
            cameraProvider = cameraProviderFuture.get()
            bindCamera(lifecycleOwner, surfaceProvider)
            onReady()
        }, ContextCompat.getMainExecutor(context))
    }

    @SuppressLint("UnsafeOptInUsageError")
    fun bindCamera(lifecycleOwner: LifecycleOwner, surfaceProvider: Preview.SurfaceProvider) {
        cachedLifecycleOwner = lifecycleOwner
        cachedSurfaceProvider = surfaceProvider
        val provider = cameraProvider ?: return
        provider.unbindAll()

        val cameraSelector = if (currentLens == CameraLens.FRONT) {
            CameraSelector.DEFAULT_FRONT_CAMERA
        } else {
            CameraSelector.DEFAULT_BACK_CAMERA
        }

        val targetResolution = Size(currentProfile.width, currentProfile.height)

        val preview = Preview.Builder()
            .setTargetResolution(targetResolution)
            .build()
            .also {
                it.setSurfaceProvider(surfaceProvider)
            }

        val analysisExecutor = Executors.newSingleThreadExecutor()
        val imageAnalysis = ImageAnalysis.Builder()
            .setTargetResolution(targetResolution)
            .setBackpressureStrategy(ImageAnalysis.STRATEGY_KEEP_ONLY_LATEST)
            .build()
            .also { analysis ->
                analysis.setAnalyzer(analysisExecutor) { imageProxy ->
                    val mediaImage = imageProxy.image
                    currentRotationDegrees = imageProxy.imageInfo.rotationDegrees

                    // 1. Process QR Scanning if requested
                    if (isQrScanningEnabled && mediaImage != null) {
                        val inputImage = InputImage.fromMediaImage(
                            mediaImage,
                            imageProxy.imageInfo.rotationDegrees
                        )
                        val scanner = BarcodeScanning.getClient()
                        scanner.process(inputImage)
                            .addOnSuccessListener { barcodes ->
                                for (barcode in barcodes) {
                                    barcode.rawValue?.let { raw ->
                                        if (raw.contains("OBS_CAMERA_PRO") || raw.contains("host") || raw.contains("http") || raw.contains("ws")) {
                                            isQrScanningEnabled = false
                                            onQrCodeDetected?.invoke(raw)
                                        }
                                    }
                                }
                            }
                    }

                    // 2. Stream video frame to WebRTC if broadcasting
                    if (isStreamingToWebRtc && onFrameAvailable != null && mediaImage != null) {
                        try {
                            val i420Buffer = YuvHelper.convertYuv420888ToJavaI420(imageProxy)
                            val videoFrame = VideoFrame(i420Buffer, imageProxy.imageInfo.rotationDegrees, System.nanoTime())
                            onFrameAvailable?.invoke(videoFrame)
                            videoFrame.release()
                        } catch (e: Exception) {
                            Log.w(tag, "Frame conversion error: ${e.message}")
                        }
                    }

                    imageProxy.close()
                }
            }

        try {
            camera = provider.bindToLifecycle(
                lifecycleOwner,
                cameraSelector,
                preview,
                imageAnalysis
            )

            camera2Control = Camera2CameraControl.from(camera!!.cameraControl)
            camera2Info = Camera2CameraInfo.from(camera!!.cameraInfo)

            // Cache hardware capabilities
            camera?.cameraInfo?.zoomState?.value?.let {
                maxZoomRatio = it.maxZoomRatio
            }

            Log.i(tag, "Camera bound successfully with QR Analysis: Lens=$currentLens, Resolution=$currentProfile")
        } catch (e: Exception) {
            Log.e(tag, "Failed to bind camera use cases: ${e.message}", e)
        }
    }

    fun setZoom(ratio: Float) {
        val clamped = ratio.coerceIn(1.0f, maxZoomRatio)
        camera?.cameraControl?.setZoomRatio(clamped)
    }

    @SuppressLint("UnsafeOptInUsageError")
    fun setTorch(enabled: Boolean) {
        camera?.cameraControl?.enableTorch(enabled)
    }

    @SuppressLint("UnsafeOptInUsageError")
    fun setManualFocus(distance: Float) {
        // Distance 0.0f (infinity) to 1.0f (macro)
        val control = camera2Control ?: return
        val options = CaptureRequestOptions.Builder()
            .setCaptureRequestOption(CaptureRequest.CONTROL_AF_MODE, CameraMetadata.CONTROL_AF_MODE_OFF)
            .setCaptureRequestOption(CaptureRequest.LENS_FOCUS_DISTANCE, distance * 10f)
            .build()
        control.setCaptureRequestOptions(options)
    }

    @SuppressLint("UnsafeOptInUsageError")
    fun setAutoFocus() {
        val control = camera2Control ?: return
        val options = CaptureRequestOptions.Builder()
            .setCaptureRequestOption(CaptureRequest.CONTROL_AF_MODE, CameraMetadata.CONTROL_AF_MODE_CONTINUOUS_PICTURE)
            .build()
        control.setCaptureRequestOptions(options)
    }

    @SuppressLint("UnsafeOptInUsageError")
    fun setManualExposure(iso: Int, exposureCompensation: Float) {
        val control = camera2Control ?: return
        val options = CaptureRequestOptions.Builder()
            .setCaptureRequestOption(CaptureRequest.CONTROL_AE_MODE, CameraMetadata.CONTROL_AE_MODE_OFF)
            .setCaptureRequestOption(CaptureRequest.SENSOR_SENSITIVITY, iso)
            .build()
        control.setCaptureRequestOptions(options)
    }

    @SuppressLint("UnsafeOptInUsageError")
    fun setWhiteBalance(modeStr: String) {
        val control = camera2Control ?: return
        val mode = when (modeStr.lowercase()) {
            "daylight" -> CameraMetadata.CONTROL_AWB_MODE_DAYLIGHT
            "cloudy" -> CameraMetadata.CONTROL_AWB_MODE_CLOUDY_DAYLIGHT
            "incandescent" -> CameraMetadata.CONTROL_AWB_MODE_INCANDESCENT
            "fluorescent" -> CameraMetadata.CONTROL_AWB_MODE_FLUORESCENT
            else -> CameraMetadata.CONTROL_AWB_MODE_AUTO
        }
        val options = CaptureRequestOptions.Builder()
            .setCaptureRequestOption(CaptureRequest.CONTROL_AWB_MODE, mode)
            .build()
        control.setCaptureRequestOptions(options)
    }

    fun switchLens(
        lens: CameraLens,
        lifecycleOwner: LifecycleOwner? = null,
        surfaceProvider: Preview.SurfaceProvider? = null
    ) {
        val owner = lifecycleOwner ?: cachedLifecycleOwner ?: return
        val provider = surfaceProvider ?: cachedSurfaceProvider ?: return

        val wasFront = (currentLens == CameraLens.FRONT)
        val isTargetFront = (lens == CameraLens.FRONT)
        currentLens = lens

        if (wasFront != isTargetFront) {
            bindCamera(owner, provider)
        }

        // Apply optical/digital zoom ratio for target lens focal length
        when (lens) {
            CameraLens.BACK_ULTRAWIDE -> {
                val minZoom = camera?.cameraInfo?.zoomState?.value?.minZoomRatio ?: 1.0f
                setZoom(if (minZoom < 1.0f) minZoom else 0.6f)
            }
            CameraLens.BACK_WIDE -> {
                setZoom(1.0f)
            }
            CameraLens.BACK_TELEPHOTO -> {
                val maxZoom = camera?.cameraInfo?.zoomState?.value?.maxZoomRatio ?: 10.0f
                setZoom(3.0f.coerceAtMost(maxZoom))
            }
            CameraLens.FRONT -> {
                setZoom(1.0f)
            }
        }
    }

    fun toggleCameraFacing(
        lifecycleOwner: LifecycleOwner? = null,
        surfaceProvider: Preview.SurfaceProvider? = null
    ): CameraLens {
        val target = if (currentLens == CameraLens.FRONT) CameraLens.BACK_WIDE else CameraLens.FRONT
        switchLens(target, lifecycleOwner, surfaceProvider)
        return target
    }

    fun switchProfile(profile: ResolutionProfile, lifecycleOwner: LifecycleOwner? = null, surfaceProvider: Preview.SurfaceProvider? = null) {
        val owner = lifecycleOwner ?: cachedLifecycleOwner ?: return
        val provider = surfaceProvider ?: cachedSurfaceProvider ?: return
        if (currentProfile == profile) return
        currentProfile = profile
        bindCamera(owner, provider)
    }
}

