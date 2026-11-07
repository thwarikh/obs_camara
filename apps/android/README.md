# OBS Camera Pro — Native Android Application

Native Android camera application built with Kotlin, CameraX, Camera2 interop, Jetpack Compose, and WebRTC.

---

## 📱 System Requirements

- **Android Version**: Android 9.0 (API level 28) or higher
- **Development Tooling**: Android Studio Hedgehog / Iguana / Jellyfish (or newer), JDK 17+

---

## 🛠️ Project Structure

```
apps/android/
├── build.gradle                              # Top-level Gradle configuration
├── settings.gradle                           # Sub-project inclusion
├── gradle.properties
├── gradlew & gradlew.bat                     # Gradle wrapper binaries
├── README.md                                 # Android developer guide
└── app/
    ├── build.gradle                          # App module dependencies & CameraX
    └── src/main/
        ├── AndroidManifest.xml               # Camera, Audio & Foreground Service permissions
        ├── res/values/                       # Theme, colors, strings
        └── java/com/obscamera/pro/
            ├── OBSCameraApp.kt               # Application class & notification channels
            ├── camera/
            │   ├── CameraManager.kt          # CameraX + Camera2 manual ISO/focus/exposure
            │   └── CameraLens.kt             # Dynamic lens & resolution definitions
            ├── streaming/
            │   ├── WebRTCStreamingClient.kt  # WebRTC WHIP client for MediaMTX
            │   └── SignalingClient.kt        # OkHttp WebSocket for remote controls
            ├── audio/
            │   └── AudioCaptureManager.kt    # AudioRecord & dBFS VU meter calculation
            ├── controls/
            │   └── RemoteControlHandler.kt   # Command execution from Desktop
            ├── connection/
            │   └── NetworkMonitor.kt         # Wi-Fi vs USB Tethering detection
            ├── service/
            │   └── CameraStreamingService.kt # Foreground service daemon
            └── ui/
                ├── MainActivity.kt           # Permissions & lifecycle management
                └── MainCameraScreen.kt       # Jetpack Compose dark studio UI
```

---

## 🚀 Building & Running in Android Studio

1. Open **Android Studio**.
2. Select **Open an Existing Project** and navigate to `apps/android`.
3. Allow Gradle to synchronize dependencies.
4. Connect an Android smartphone with **USB Debugging** enabled.
5. Click **Run 'app'** (or press **Shift + F10**).

To build an APK via command line:
```cmd
gradlew.bat assembleRelease
```
The APK will be generated at `apps/android/app/build/outputs/apk/release/app-release.apk`.

---

## ⚡ Pairing with Windows Desktop Control Center

1. On your Windows PC, double-click `run.bat` to launch the Desktop Control Center.
2. Click **Pair Phone Camera** to display the pairing QR code.
3. Open **OBS Camera Pro** on your Android phone, tap the QR scanner icon, and scan the screen.
4. Tap **START STREAM**. The phone begins broadcasting H.264 video and microphone audio directly to MediaMTX.
5. In OBS Studio, click the **OBS** button in the dashboard to instantly create the camera feed as a Browser Source.

