package com.obscamera.pro.streaming

import androidx.camera.core.ImageProxy
import org.webrtc.JavaI420Buffer

object YuvHelper {

    /**
     * Converts Android CameraX YUV_420_888 ImageProxy to a WebRTC JavaI420Buffer.
     * Safely handles pixelStride = 1 (planar) and pixelStride = 2 (interleaved/semi-planar).
     */
    fun convertYuv420888ToJavaI420(image: ImageProxy): JavaI420Buffer {
        val width = image.width
        val height = image.height
        val planes = image.planes

        val yBuffer = planes[0].buffer
        val uBuffer = planes[1].buffer
        val vBuffer = planes[2].buffer

        val yStride = planes[0].rowStride
        val uStride = planes[1].rowStride
        val vStride = planes[2].rowStride

        val uPixelStride = planes[1].pixelStride
        val vPixelStride = planes[2].pixelStride

        val buffer = JavaI420Buffer.allocate(width, height)
        val dataY = buffer.dataY
        val dataU = buffer.dataU
        val dataV = buffer.dataV

        // 1. Copy Y-Plane
        yBuffer.rewind()
        for (row in 0 until height) {
            yBuffer.position(row * yStride)
            val oldLimit = yBuffer.limit()
            yBuffer.limit(yBuffer.position() + width)
            dataY.put(yBuffer)
            yBuffer.limit(oldLimit)
        }

        // 2. Copy/De-interleave U and V planes
        val chromaHeight = (height + 1) / 2
        val chromaWidth = (width + 1) / 2

        for (row in 0 until chromaHeight) {
            for (col in 0 until chromaWidth) {
                val uIndex = row * uStride + col * uPixelStride
                val vIndex = row * vStride + col * vPixelStride
                dataU.put(uBuffer.get(uIndex))
                dataV.put(vBuffer.get(vIndex))
            }
        }

        dataY.rewind()
        dataU.rewind()
        dataV.rewind()

        return buffer
    }
}
