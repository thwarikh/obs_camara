# OBS Camera Pro - Comprehensive Testing Checklist

Use this checklist to verify production readiness across all components.

## Phase 1: MVP & Desktop Server
- [x] Python virtual environment creates and installs dependencies (`requirements.txt`).
- [x] MediaMTX executable starts on Windows without errors.
- [x] FastAPI desktop server boots and listens on `http://127.0.0.1:8765`.
- [x] Web dashboard serves dark video production interface and Lucide icons.
- [x] QR code generator yields valid base64 PNG and connection JSON.
- [x] OBS Browser Source player page loads at `/obs/camera/{id}`.

## Phase 2: Camera Controls
- [x] Remote zoom command dispatches to mobile client via WebSocket.
- [x] Focus mode (auto vs manual) and focus distance apply to Camera2 / AVFoundation.
- [x] ISO sensitivity and exposure compensation update in real-time.
- [x] Rear flashlight / torch toggles on and off.
- [x] Camera lens switcher cycles through wide, ultra-wide, telephoto, and front.
- [x] Resolution profile changes (720p, 1080p, 4K).

## Phase 3: Audio Infrastructure
- [x] Microphone captures audio via AudioRecord (Android) / AVAudioEngine (iOS).
- [x] Audio RMS dB calculated and reported via telemetry.
- [x] Desktop audio fader scales gain (0% - 200%).
- [x] Mute toggle silences microphone audio without terminating video stream.
- [x] Audio routing toggle selectively enables/disables audio to OBS.

## Phase 4: Multi-Camera
- [x] Multiple devices pair simultaneously with unique device IDs.
- [x] Desktop Studio Grid displays multiple live camera feeds concurrently.
- [x] Per-device control drawer operates independently without affecting other cameras.

## Phase 5: USB Tethering & Reconnection
- [x] Network service detects USB tethering adapters (RNDIS / Apple Ethernet).
- [x] Automatic reconnection when network drops or is restored.

## Phase 6: OBS Studio Integration
- [x] OBS WebSocket v5 connects with or without password.
- [x] Active scenes retrieved from OBS.
- [x] One-click Browser Source injection creates input in OBS Studio.
- [x] RTSP fallback media source creates input in OBS Studio.

