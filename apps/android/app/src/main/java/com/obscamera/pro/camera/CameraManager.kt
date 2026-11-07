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
import java.util.concurrent.Executors

class CameraManager(private val context: Context) {

    private val tag = "OBSCameraPro.CamManager"
    private var cameraProvider: ProcessCameraProvider? = null
    private var camera: Camera? = null
    private var camera2Control: Camera2CameraControl? = null
    private var camera2Info: Camera2CameraInfo? = null

    var currentLens: CameraLens = CameraLens.BACK_WIDE
        private set
    var currentProfile: ResolutionProfile = ResolutionProfile.PROFILE_1080P30
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

        try {
            camera = provider.bindToLifecycle(
                lifecycleOwner,
                cameraSelector,
                preview
            )

            camera2Control = Camera2CameraControl.from(camera!!.cameraControl)
            camera2Info = Camera2CameraInfo.from(camera!!.cameraInfo)

            // Cache hardware capabilities
            camera?.cameraInfo?.zoomState?.value?.let {
                maxZoomRatio = it.maxZoomRatio
            }

            Log.i(tag, "Camera bound successfully: Lens=$currentLens, Resolution=$currentProfile")
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

    fun switchLens(lens: CameraLens, lifecycleOwner: LifecycleOwner, surfaceProvider: Preview.SurfaceProvider) {
        if (currentLens == lens) return
        currentLens = lens
        bindCamera(lifecycleOwner, surfaceProvider)
    }

    fun switchProfile(profile: ResolutionProfile, lifecycleOwner: LifecycleOwner, surfaceProvider: Preview.SurfaceProvider) {
        if (currentProfile == profile) return
        currentProfile = profile
        bindCamera(lifecycleOwner, surfaceProvider)
    }
}

