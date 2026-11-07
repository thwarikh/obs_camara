import Foundation
import AVFoundation

public class CameraEngine: NSObject, ObservableObject {
    public let captureSession = AVCaptureSession()
    private var currentDevice: AVCaptureDevice?
    private var videoInput: AVCaptureDeviceInput?
    private let videoOutput = AVCaptureVideoDataOutput()

    @Published public var currentLens: IOSCameraLens = .backWide
    @Published public var currentProfile: IOSResolutionProfile = .p1080_30
    @Published public var isRunning: BooleanLiteralType = false

    public override init() {
        super.init()
    }

    public func configure() {
        captureSession.beginConfiguration()
        captureSession.sessionPreset = currentProfile.preset

        selectDevice(for: currentLens)

        if captureSession.canAddOutput(videoOutput) {
            captureSession.addOutput(videoOutput)
        }

        captureSession.commitConfiguration()
    }

    public func start() {
        DispatchQueue.global(qos: .userInitiated).async { [weak self] in
            self?.captureSession.startRunning()
            DispatchQueue.main.async {
                self?.isRunning = true
            }
        }
    }

    public func stop() {
        DispatchQueue.global(qos: .userInitiated).async { [weak self] in
            self?.captureSession.stopRunning()
            DispatchQueue.main.async {
                self?.isRunning = false
            }
        }
    }

    private func selectDevice(for lens: IOSCameraLens) {
        if let input = videoInput {
            captureSession.removeInput(input)
        }

        let deviceType: AVCaptureDevice.DeviceType
        let position: AVCaptureDevice.Position

        switch lens {
        case .backWide:
            deviceType = .builtInWideAngleCamera
            position = .back
        case .backUltrawide:
            deviceType = .builtInUltraWideCamera
            position = .back
        case .backTelephoto:
            deviceType = .builtInTelephotoCamera
            position = .back
        case .front:
            deviceType = .builtInWideAngleCamera
            position = .front
        }

        let discovery = AVCaptureDevice.DiscoverySession(
            deviceTypes: [deviceType],
            mediaType: .video,
            position: position
        )

        guard let device = discovery.devices.first ?? AVCaptureDevice.default(for: .video) else {
            return
        }

        currentDevice = device

        do {
            let input = try AVCaptureDeviceInput(device: device)
            if captureSession.canAddInput(input) {
                captureSession.addInput(input)
                videoInput = input
            }
        } catch {
            print("Failed to add video input: \(error)")
        }
    }

    // Manual Camera Controls
    public func setZoom(factor: CGFloat) {
        guard let device = currentDevice else { return }
        do {
            try device.lockForConfiguration()
            let clamped = max(1.0, min(factor, device.activeFormat.videoMaxZoomFactor))
            device.videoZoomFactor = clamped
            device.unlockForConfiguration()
        } catch {}
    }

    public func setTorch(enabled: Bool) {
        guard let device = currentDevice, device.hasTorch else { return }
        do {
            try device.lockForConfiguration()
            device.torchMode = enabled ? .on : .off
            device.unlockForConfiguration()
        } catch {}
    }

    public func setManualFocus(lensPosition: Float) {
        guard let device = currentDevice, device.isFocusModeSupported(.locked) else { return }
        do {
            try device.lockForConfiguration()
            device.setFocusModeLocked(lensPosition: max(0.0, min(1.0, lensPosition)), completionHandler: nil)
            device.unlockForConfiguration()
        } catch {}
    }

    public func setAutoFocus() {
        guard let device = currentDevice, device.isFocusModeSupported(.continuousAutoFocus) else { return }
        do {
            try device.lockForConfiguration()
            device.focusMode = .continuousAutoFocus
            device.unlockForConfiguration()
        } catch {}
    }

    public func setManualExposure(iso: Float) {
        guard let device = currentDevice, device.isExposureModeSupported(.custom) else { return }
        do {
            try device.lockForConfiguration()
            let clampedIso = max(device.activeFormat.minISO, min(iso, device.activeFormat.maxISO))
            device.setExposureModeCustom(duration: AVCaptureDevice.currentExposureDuration, iso: clampedIso, completionHandler: nil)
            device.unlockForConfiguration()
        } catch {}
    }

    public func switchLens(_ lens: IOSCameraLens) {
        captureSession.beginConfiguration()
        currentLens = lens
        selectDevice(for: lens)
        captureSession.commitConfiguration()
    }
}

