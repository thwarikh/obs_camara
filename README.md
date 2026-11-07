# OBS Camera Pro
### Professional Multi-Device Wireless & USB Camera System for OBS Studio

**OBS Camera Pro** turns Android and iOS smartphones into professional, broadcast-grade, remotely controllable cameras for OBS Studio with ultra-low latency WebRTC streaming, microphone audio, multi-camera studio switching, and automatic OBS integration.

---

## 🌟 Key Features

- **Multi-Device Support**: Connect and stream multiple Android and iPhone devices simultaneously to individual OBS sources.
- **Ultra-Low Latency**: Native WebRTC streaming (WHIP / WHEP) over local Wi-Fi (5 GHz) and USB tethering (50–150 ms typical latency).
- **Zero-Transcode Forwarding**: Direct H.264 & Opus routing via MediaMTX to keep CPU usage low (optimized for Intel Core i3 / 8 GB RAM laptops).
- **Full Remote Camera Controls**: Control mobile camera hardware in real-time from your desktop:
  - Optical & digital zoom (1.0x – 10.0x)
  - Auto & manual focus distance (0.00 – 1.00)
  - ISO sensitivity & exposure compensation (EV)
  - White balance presets (Daylight, Cloudy, Tungsten, Fluorescent, Auto)
  - Multi-lens switching (Rear Wide 1x, Ultra-Wide 0.5x, Telephoto 3x, Front)
  - Video resolution profiles (720p30, 1080p30, 1080p60, 4K30)
  - Torch / flashlight toggle
- **Audio Mixer Strip**: Live VU peak meter, per-camera gain fader (0%–200%), individual mute toggle, and audio-to-OBS routing control.
- **Automatic OBS Source Injection**: One-click creation and synchronization of Browser Sources in OBS Studio via OBS WebSocket v5. RTSP fallback is also supported.
- **Fast QR Code Pairing**: Instantly pair smartphones by scanning the on-screen QR code.
- **Single-Command Startup**: Start everything with one double-click on `run.bat`.

---

## 🏗️ Architecture

```
Mobile Camera Apps (Android / iOS)
       │
       │  Wi-Fi (5 GHz) / USB Tethering
       ▼
MediaMTX Streaming Server (WebRTC WHIP / WHEP :8889, RTSP :8554)
       │
       ▼
Python FastAPI Desktop Backend (:8765)
       ├── Device Manager (QR pairing, capabilities, lifecycle)
       ├── WebSocket Manager (Bidirectional remote controls & telemetry)
       ├── OBS Integration Client (OBS WebSocket v5 :4455)
       ├── Stream Manager (MediaMTX path supervisor & health metrics)
       └── Audio Manager (Gain, mute, VU metering)
       │
       ▼
Desktop Control Dashboard (:8765) ─── Auto Ingestion ───► OBS Studio
```

---

## 🚀 Quick Start (Windows)

### Prerequisites
- Windows 10 or Windows 11 (64-bit)
- Python 3.12+ (or 3.13) installed with "Add Python to PATH" checked
- [OBS Studio](https://obsproject.com/) (version 28.0 or newer with WebSocket enabled)

### Single-Command Run
Double click `run.bat` or run:
```cmd
run.bat
```

The script will automatically:
1. Verify Python and create the virtual environment (`venv`).
2. Install all required dependencies from `requirements.txt`.
3. Check and launch the MediaMTX streaming server.
4. Launch the FastAPI desktop control server on `http://127.0.0.1:8765`.
5. Open the Desktop Control Center in your web browser.

---

## 📱 Mobile App Setup & Pairing

### Android (Kotlin, Jetpack Compose, CameraX)
1. Open `apps/android` in **Android Studio**.
2. Build and install the APK on your Android device (Android 9.0+).
3. On the Desktop Dashboard, click **Pair Phone Camera** to display the pairing QR code.
4. Tap the **QR Scanner** button in the mobile app and scan the screen.
5. Tap **START STREAM**. The phone begins broadcasting H.264 video and microphone audio.

### iOS (Swift, SwiftUI, AVFoundation)
1. Open `apps/ios` in **Xcode** on macOS.
2. Build and install the application on your iPhone (iOS 16.0+).
3. Connect your iPhone to the same Wi-Fi network or enable USB Tethering.
4. Scan the pairing QR code and tap **START STREAM**.

---

## 🎬 OBS Studio Integration

### Step 1: Enable OBS WebSocket
1. In OBS Studio, navigate to **Tools** ➔ **WebSocket Server Settings**.
2. Check **Enable WebSocket server** (Port: `4455`).
3. Set or view your server password (leave blank if authentication is disabled).

### Step 2: Connect from OBS Camera Pro Dashboard
1. Go to the **OBS Integration** tab on the Desktop Dashboard.
2. Enter your host, port, and password, then click **Connect to OBS Studio**.
3. Under **Live Camera Feeds**, click the **OBS** button next to any connected phone.
4. A high-performance Browser Source (`http://127.0.0.1:8765/obs/camera/<device_id>`) will be automatically created in your current OBS scene!

---

## 📁 Project Directory Structure

```
OBS-CAMERA-PRO/
├── apps/
│   ├── android/                  # Native Android Studio Project
│   │   ├── app/src/main/
│   │   │   ├── AndroidManifest.xml
│   │   │   ├── java/com/obscamera/pro/
│   │   │   │   ├── camera/       # CameraX + Camera2 hardware controls
│   │   │   │   ├── streaming/    # WebRTC WHIP client & signaling
│   │   │   │   ├── audio/        # AudioRecord capture & dBFS VU meter
│   │   │   │   ├── controls/     # Remote command execution
│   │   │   │   ├── connection/   # Network detection (Wi-Fi vs USB)
│   │   │   │   ├── service/      # CameraStreamingService foreground daemon
│   │   │   │   └── ui/           # Jetpack Compose UI
│   │   │   └── res/
│   │   ├── build.gradle
│   │   └── settings.gradle
│   ├── ios/                      # Native iOS Xcode Project
│   │   ├── Package.swift
│   │   └── OBSCamera/
│   │       ├── Info.plist
│   │       └── Sources/
│   │           ├── CameraEngine/ # AVFoundation capture & manual controls
│   │           ├── AudioEngine/  # AVAudioEngine capture & metering
│   │           ├── Network/      # WebSocket signaling & network monitor
│   │           └── UI/           # SwiftUI Camera Preview & Controls
│   └── desktop/                  # Desktop Control Center
│       ├── backend/
│       │   ├── main.py           # FastAPI entrypoint & WebSocket multiplexer
│       │   └── app/
│       │       ├── config.py
│       │       ├── database/     # SQLite ORM models & connections
│       │       ├── devices/      # Device lifecycle & QR generator
│       │       ├── streaming/    # MediaMTX stream supervisor
│       │       ├── obs/          # OBS WebSocket v5 integration
│       │       ├── websocket/    # Bidirectional WebSocket router
│       │       ├── services/     # System monitor & network classifier
│       │       └── api/          # REST API endpoints
│       └── frontend/
│           ├── index.html        # Modern dark video production UI
│           ├── obs_player.html   # Dedicated WebRTC WHEP Browser Source
│           ├── css/style.css
│           └── js/app.js
├── services/
│   └── mediamtx/                 # MediaMTX v1.21.3 Windows binary & YAML config
├── shared/
│   └── protocols/                # Shared WebSocket control protocol definitions
├── tests/
│   └── test_backend.py           # Pytest unit & integration test suite
├── scripts/
│   ├── run.bat
│   ├── install.bat
│   └── build.bat
├── docs/
│   ├── ARCHITECTURE.md
│   ├── TROUBLESHOOTING.md
│   └── TESTING_CHECKLIST.md
├── run.bat                       # One-click startup script
├── install.bat                   # One-click installer script
├── requirements.txt
├── PROJECT_STATUS.md
└── README.md
```

---

## 🧪 Testing

Run the automated backend test suite:
```cmd
venv\Scripts\pytest -v tests\test_backend.py
```
Expected result: `8 passed, 0 failed`.

---

## 📄 License
Production Proprietary / Open Source under MIT License.

