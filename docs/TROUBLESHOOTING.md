# OBS Camera Pro - Troubleshooting & Operational Guide

## 1. Network & Connectivity Issues

### Phone Cannot Connect to Desktop (Pairing Fails)
- **Check Windows Firewall**:
  - Ports used by OBS Camera Pro:
    - `8765` (TCP) - FastAPI Desktop Web Server & WebSockets
    - `8889` (TCP/HTTP) - MediaMTX WebRTC WHIP / WHEP signaling
    - `8189` (UDP) - MediaMTX WebRTC ICE / media traffic
    - `8554` (TCP/UDP) - RTSP stream fallback
  - Ensure Windows Defender Firewall allows incoming connections on private networks for Python and MediaMTX.
- **Check Subnet Alignment**:
  - If using Wi-Fi: ensure the phone and PC are on the same Wi-Fi SSID / local router (and not on a "Guest Network" with client isolation enabled).
  - If using USB Tethering: verify that Windows recognizes the phone network adapter (e.g., Remote NDIS / Apple Mobile Device Ethernet) and displays an IP address in the `192.168.42.x` or `172.20.10.x` range.

## 2. OBS Studio Integration

### "Failed to connect to OBS WebSocket"
1. In OBS Studio, open **Tools -> WebSocket Server Settings**.
2. Check **Enable WebSocket server**.
3. Verify the **Server Port** (default `4455`).
4. If authentication is enabled, copy the password into the OBS Camera Pro Dashboard (**OBS Integration** tab) and click **Connect to OBS Studio**.

### Stream Appears Black in OBS Browser Source
1. In OBS Studio Browser Source properties, check **Shutdown source when not visible** is unchecked.
2. In OBS Studio, enable **Hardware acceleration when available** under Advanced Settings.
3. If WebRTC is blocked by CEF, switch to the RTSP fallback source (`rtsp://127.0.0.1:8554/camera_<device_id>`) in the Dashboard.

## 3. Hardware Camera Controls

### Manual Focus or ISO Slider Has No Effect
- Not all smartphone camera sensors expose manual Camera2 / AVFoundation controls on secondary lenses (e.g., fixed-focus ultra-wide lenses on budget phones).
- OBS Camera Pro automatically queries camera capabilities upon pairing and disables unsupported sliders. Switch to the Primary Rear Wide lens (`1x`) for full manual exposure and focus control.

