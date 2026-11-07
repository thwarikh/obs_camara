import SwiftUI
import AVFoundation

public struct CameraPreviewView: UIViewRepresentable {
    public let session: AVCaptureSession

    public init(session: AVCaptureSession) {
        self.session = session
    }

    public func makeUIView(context: Context) -> UIView {
        let view = UIView(frame: .zero)
        let previewLayer = AVCaptureVideoPreviewLayer(session: session)
        previewLayer.videoGravity = .resizeAspectFill
        view.layer.addSublayer(previewLayer)
        context.coordinator.previewLayer = previewLayer
        return view
    }

    public func updateUIView(_ uiView: UIView, context: Context) {
        DispatchQueue.main.async {
            context.coordinator.previewLayer?.frame = uiView.bounds
        }
    }

    public func makeCoordinator() -> Coordinator {
        Coordinator()
    }

    public class Coordinator {
        var previewLayer: AVCaptureVideoPreviewLayer?
    }
}

public struct MainCameraView: View {
    @StateObject private var cameraEngine = CameraEngine()
    @StateObject private var audioEngine = IOSAudioEngine()
    @State private var isStreaming: Bool = false
    @State private var currentLens: IOSCameraLens = .backWide

    public init() {}

    public var body: some View {
        ZStack {
            Color(red: 0.04, green: 0.05, blue: 0.09).ignoresSafeArea()

            // 1. Live Preview
            CameraPreviewView(session: cameraEngine.captureSession)
                .ignoresSafeArea()

            // 2. Top HUD
            VStack {
                HStack {
                    HStack(spacing: 6) {
                        Circle()
                            .fill(isStreaming ? Color.red : Color.gray)
                            .frame(width: 8, height: 8)
                        Text(isStreaming ? "LIVE" : "STANDBY")
                            .font(.system(size: 11, weight: .bold))
                            .foregroundColor(.white)
                    }
                    .padding(.horizontal, 10)
                    .padding(.vertical, 5)
                    .background(Color.black.opacity(0.6))
                    .cornerRadius(16)

                    Spacer()

                    HStack(spacing: 10) {
                        Text("30 FPS")
                            .font(.system(size: 11, weight: .bold))
                            .foregroundColor(Color(red: 0.22, green: 0.74, blue: 0.97))
                        Text("5000 kbps")
                            .font(.system(size: 11))
                            .foregroundColor(.white)
                    }
                    .padding(.horizontal, 10)
                    .padding(.vertical, 5)
                    .background(Color.black.opacity(0.6))
                    .cornerRadius(16)
                }
                .padding(.horizontal, 16)
                .padding(.top, 10)

                Spacer()

                // 3. Floating Lens Selector
                HStack(spacing: 12) {
                    ForEach(IOSCameraLens.allCases, id: \.self) { lens in
                        Button(action: {
                            currentLens = lens
                            cameraEngine.switchLens(lens)
                        }) {
                            Text(lens.displayName)
                                .font(.system(size: 11, weight: .bold))
                                .foregroundColor(currentLens == lens ? .black : .white)
                                .padding(.horizontal, 12)
                                .padding(.vertical, 8)
                                .background(currentLens == lens ? Color(red: 0.22, green: 0.74, blue: 0.97) : Color.black.opacity(0.6))
                                .cornerRadius(20)
                        }
                    }
                }
                .padding(.bottom, 16)

                // 4. Bottom Action Bar
                HStack(spacing: 24) {
                    Button(action: {
                        isStreaming.toggle()
                        if isStreaming {
                            audioEngine.start()
                        } else {
                            audioEngine.stop()
                        }
                    }) {
                        HStack {
                            Image(systemName: isStreaming ? "stop.fill" : "play.fill")
                            Text(isStreaming ? "STOP" : "START STREAM")
                                .fontWeight(.bold)
                        }
                        .foregroundColor(isStreaming ? .white : .black)
                        .frame(width: 180, height: 50)
                        .background(isStreaming ? Color.red : Color(red: 0.22, green: 0.74, blue: 0.97))
                        .cornerRadius(25)
                    }
                }
                .padding(.bottom, 32)
            }
        }
        .onAppear {
            cameraEngine.configure()
            cameraEngine.start()
        }
        .onDisappear {
            cameraEngine.stop()
            audioEngine.stop()
        }
    }
}

