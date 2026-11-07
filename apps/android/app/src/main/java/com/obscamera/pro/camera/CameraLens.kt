package com.obscamera.pro.camera

enum class CameraLens(val idStr: String, val displayName: String) {
    BACK_WIDE("back_wide", "1x Wide"),
    BACK_ULTRAWIDE("back_ultrawide", "0.5x Ultra-Wide"),
    BACK_TELEPHOTO("back_telephoto", "3x Telephoto"),
    FRONT("front", "Front");

    companion object {
        fun fromId(id: String): CameraLens {
            return values().firstOrNull { it.idStr.equals(id, ignoreCase = true) } ?: BACK_WIDE
        }
    }
}

enum class ResolutionProfile(
    val idStr: String,
    val width: Int,
    val height: Int,
    val fps: Int,
    val targetBitrateKbps: Int
) {
    PROFILE_720P30("720p30", 1280, 720, 30, 2500),
    PROFILE_1080P30("1080p30", 1920, 1080, 30, 5000),
    PROFILE_1080P60("1080p60", 1920, 1080, 60, 8000),
    PROFILE_4K30("4k30", 3840, 2160, 30, 18000);

    companion object {
        fun fromId(id: String): ResolutionProfile {
            return values().firstOrNull { it.idStr.equals(id, ignoreCase = true) } ?: PROFILE_1080P30
        }
    }
}

