# OBS Camera Pro - Architecture & Technical Specification

## 1. High-Level System Architecture

```mermaid
flowchart TD
    subgraph Mobile Devices
        A[Android Device\nCameraX + Camera2 + WebRTC]
        B[iOS Device\nAVFoundation + WebRTC]
    end

    subgraph Network Layer
        NET[Wi-Fi 5GHz / USB Tethering]
    end

    subgraph Desktop Infrastructure
        MTX[MediaMTX Streaming Server\nWebRTC WHIP / WHEP :8889\nRTSP :8554]
        API[FastAPI Desktop Server :8765]
        WS[WebSocket Control Router\n/ws/camera/{id}\n/ws/devices]
        DB[(SQLite Database\nobscam.db)]
    end

    subgraph User & Broadcast Interfaces
        DASH[Desktop Control Dashboard\nHTML5 / CSS3 / Chart.js]
        OBS[OBS Studio\nBrowser Source / RTSP Media Source\nOBS WebSocket v5 :4455]
    end

    A -- "WHIP Video & Audio" --> MTX
    B -- "WHIP Video & Audio" --> MTX
    A -- "WebSocket Control & Telemetry" --> WS
    B -- "WebSocket Control & Telemetry" --> WS

    MTX -- "WHEP Stream" --> OBS
    API -- "Auto Source Injection" --> OBS
    WS <--> DASH
    API <--> DB
```

## 2. Low-Latency Streaming Pipeline

1. **Ingest (Mobile -> MediaMTX)**:
   - Mobile camera captures NV21 / YUV420 frames and encodes H.264 video using hardware encoders (`MediaCodec` on Android, `VideoToolbox` on iOS).
   - Audio is encoded using Opus at 48 kHz.
   - Encoded tracks are transmitted over WebRTC WHIP (WebRTC HTTP Ingestion Protocol) directly to MediaMTX on port 8889.
   - No cloud relay or unnecessary transcoding is performed, achieving typical glass-to-glass latencies of 80–150 ms over local Wi-Fi and 50–90 ms over USB tethering.

2. **Egress (MediaMTX -> OBS Studio)**:
   - Primary Method: **OBS Browser Source**.
     - URL: `http://127.0.0.1:8765/obs/camera/<device_id>`
     - WebRTC WHEP (WebRTC HTTP Egress Protocol) receives H.264 video and Opus audio natively in CEF (Chromium Embedded Framework) inside OBS Studio.
   - Fallback Method: **OBS Media Source (RTSP)**.
     - URL: `rtsp://127.0.0.1:8554/camera_<device_id>`

3. **Separate Control Channel**:
   - Video streaming (UDP WebRTC) and camera control commands (TCP WebSocket) are strictly decoupled.
   - High-bitrate video transmission does not impede instantaneous response of zoom, focus, exposure, and lens switching.

