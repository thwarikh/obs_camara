# OBS Camera Pro — Native iOS Application

Native iOS camera application built in Swift, SwiftUI, and AVFoundation with WebRTC low-latency streaming for OBS Studio.

---

## 📱 System Requirements

- **iOS Version**: iOS 16.0 or higher
- **Hardware**: iPhone XR / iPhone 11 or newer (multi-lens devices: Pro models with Ultra-Wide and Telephoto lenses supported)
- **Development Tooling**: macOS with Xcode 15.0+ installed

---

## 🛠️ Project Structure

```
apps/ios/
├── Package.swift                             # Swift Package Manager definition
├── Info.plist                                # Camera & Microphone privacy entitlements
├── README.md                                 # iOS Developer setup guide
└── OBSCamera/
    └── Sources/
        ├── CameraEngine/
        │   ├── CameraEngine.swift            # AVFoundation capture session & manual controls
        │   └── CameraLens.swift              # Hardware lens enumeration & profiles
        ├── AudioEngine/
        │   └── AudioEngine.swift             # AVAudioEngine microphone capture & VU metering
        ├── Network/
        │   └── SignalingWebSocket.swift      # URLSession WebSocket client
        └── UI/
            └── MainCameraView.swift          # SwiftUI camera interface matching desktop design
```

---

## 🚀 Building & Running in Xcode

1. Open **Xcode** on your Mac.
2. Select **File ➔ Open** and select the `apps/ios` folder (or open `Package.swift`).
3. To create a standalone `.xcodeproj` application:
   - In Xcode, select **File ➔ New ➔ Project... ➔ iOS ➔ App**.
   - Set Product Name: `OBSCameraPro`
   - Set Organization Identifier: `com.obscamera`
   - Select Interface: `SwiftUI`
   - Drag and drop the `Sources` folder from `apps/ios/OBSCamera` into your project target.
4. Under **Signing & Capabilities**:
   - Select your Apple Developer Team.
   - Ensure the Bundle Identifier is set (e.g. `com.obscamera.pro`).
5. Connect your iPhone via USB cable or ensure it is on the same local Wi-Fi network as your Mac.
6. Press **Cmd + R** to build and run on your physical iPhone.

---

## ⚡ Pairing with Windows Desktop Control Center

1. On your Windows PC, double-click `run.bat` to launch the Desktop Control Center.
2. Click **Pair Phone Camera** to display the pairing QR code.
3. Open **OBS Camera Pro** on your iPhone and scan the QR code.
4. Tap **START STREAM**. The phone begins broadcasting H.264 video and microphone audio directly to MediaMTX.
5. In OBS Studio, click the **OBS** button in the dashboard to instantly create the camera feed as a Browser Source.

