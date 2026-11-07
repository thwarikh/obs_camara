import Foundation
import AVFoundation

public enum IOSCameraLens: String, CaseIterable {
    case backWide = "back_wide"
    case backUltrawide = "back_ultrawide"
    case backTelephoto = "back_telephoto"
    case front = "front"

    public var displayName: String {
        switch self {
        case .backWide: return "1x Wide"
        case .backUltrawide: return "0.5x Ultra-Wide"
        case .backTelephoto: return "3x Telephoto"
        case .front: return "Front"
        }
    }
}

public enum IOSResolutionProfile: String, CaseIterable {
    case p720_30 = "720p30"
    case p1080_30 = "1080p30"
    case p1080_60 = "1080p60"
    case p4k_30 = "4k30"

    public var preset: AVCaptureSession.Preset {
        switch self {
        case .p720_30: return .hd1280x720
        case .p1080_30, .p1080_60: return .hd1920x1080
        case .p4k_30: return .hd4K3840x2160
        }
    }
}

