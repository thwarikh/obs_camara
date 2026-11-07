"""
OBS Camera Pro - Multi-Device Hardware Simulator
Simulates one or multiple mobile cameras (Android & iOS) connecting to the Desktop Control Center.
Emits real-time telemetry, responds to remote camera controls, and optionally transmits synthetic video/audio via FFmpeg.
"""
import asyncio
import json
import random
import sys
import os
import aiohttp
import argparse
import subprocess
import shutil

DEFAULT_DEVICES = [
    {
        "device_id": "pixel8-pro-alpha",
        "custom_name": "Studio Cam 1 (Pixel 8 Pro)",
        "platform": "android",
        "model": "Google Pixel 8 Pro",
        "os_version": "Android 14",
        "ip_address": "192.168.1.101"
    },
    {
        "device_id": "iphone15-pro-beta",
        "custom_name": "Studio Cam 2 (iPhone 15 Pro)",
        "platform": "ios",
        "model": "iPhone 15 Pro Max",
        "os_version": "iOS 17.4",
        "ip_address": "192.168.1.102"
    },
    {
        "device_id": "s24-ultra-gamma",
        "custom_name": "Studio Cam 3 (S24 Ultra)",
        "platform": "android",
        "model": "Samsung Galaxy S24 Ultra",
        "os_version": "Android 14",
        "ip_address": "192.168.1.103"
    }
]

async def simulate_device(dev_info, host="127.0.0.1", port=8765, stream_video=False):
    device_id = dev_info["device_id"]
    ws_url = f"ws://{host}:{port}/ws/camera/{device_id}"
    api_reg_url = f"http://{host}:{port}/api/devices/register"

    print(f"[*] Starting simulator for {dev_info['custom_name']} ({device_id})...")

    stream_path = f"camera_{device_id.replace('-', '').lower()}"

    # 1. Register device with backend
    async with aiohttp.ClientSession() as session:
        try:
            reg_payload = {
                **dev_info,
                "token": "simulated-token-999"
            }
            async with session.post(api_reg_url, json=reg_payload) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    stream_path = data['stream_urls']['stream_path']
                    print(f"[OK] {dev_info['custom_name']} registered. Stream Path: {stream_path}")
                else:
                    print(f"[!] Registration returned HTTP {resp.status}")
        except Exception as e:
            print(f"[!] Could not register device {device_id}: {e}")
            return

    # 2. Optionally start synthetic video streaming with FFmpeg
    ffmpeg_proc = None
    if stream_video:
        ffmpeg_bin = shutil.which("ffmpeg")
        if ffmpeg_bin:
            rtsp_target = f"rtsp://{host}:8554/{stream_path}"
            print(f"[*] Launching synthetic video pipeline for {dev_info['custom_name']} -> {rtsp_target}")
            cmd = [
                ffmpeg_bin,
                "-re",
                "-f", "lavfi", "-i", f"testsrc=size=1920x1080:rate=30",
                "-f", "lavfi", "-i", f"sine=frequency=440:sample_rate=48000",
                "-c:v", "libx264", "-preset", "ultrafast", "-tune", "zerolatency",
                "-pix_fmt", "yuv420p",
                "-c:a", "aac",
                "-f", "rtsp", "-rtsp_transport", "tcp",
                rtsp_target
            ]
            ffmpeg_proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            print("[!] FFmpeg not found in PATH; skipping synthetic video transmission.")

    # 3. Maintain WebSocket connection
    try:
        while True:
            try:
                async with aiohttp.ClientSession() as ws_session:
                    async with ws_session.ws_connect(ws_url) as ws:
                        print(f"[CONNECTED] {dev_info['custom_name']} connected to control WebSocket.")

                        # Capabilities report
                        caps_msg = {
                            "type": "capabilities_report",
                            "device_id": device_id,
                            "payload": {
                                "supported_lenses": ["back_wide", "back_ultrawide", "back_telephoto", "front"],
                                "supported_resolutions": ["720p30", "1080p30", "1080p60", "4k30"],
                                "supports_torch": True,
                                "supports_manual_focus": True,
                                "supports_manual_exposure": True,
                                "min_iso": 50,
                                "max_iso": 3200,
                                "min_zoom": 1.0,
                                "max_zoom": 10.0
                            }
                        }
                        await ws.send_json(caps_msg)

                        # Background task for sending telemetry
                        async def send_telemetry():
                            battery = random.randint(80, 95)
                            while not ws.closed:
                                fps = round(random.uniform(29.8, 30.1), 1)
                                bitrate = random.randint(4800, 5200)
                                audio_db = round(random.uniform(-42.0, -18.0), 1)
                                temp_c = round(random.uniform(32.0, 36.5), 1)

                                telemetry_packet = {
                                    "type": "telemetry",
                                    "device_id": device_id,
                                    "payload": {
                                        "fps": fps,
                                        "bitrate_kbps": bitrate,
                                        "battery_pct": battery,
                                        "is_charging": True,
                                        "battery_temp_c": temp_c,
                                        "audio_level_db": audio_db,
                                        "network_type": "wifi",
                                        "network_rtt_ms": round(random.uniform(4.0, 12.0), 1),
                                        "packet_loss_pct": 0.0,
                                        "dropped_frames": 0
                                    }
                                }
                                await ws.send_json(telemetry_packet)
                                await asyncio.sleep(1.0)

                        telemetry_task = asyncio.create_task(send_telemetry())

                        # Listen for desktop control commands
                        async for msg in ws:
                            if msg.type == aiohttp.WSMsgType.TEXT:
                                data = json.loads(msg.data)
                                msg_type = data.get("type")
                                if msg_type == "camera_control_command":
                                    print(f"[{dev_info['custom_name']} CONTROL RECV] {data}")
                                    applied = {}
                                    for k, v in data.items():
                                        if k not in ["type", "device_id"]:
                                            applied[k] = v
                                    # Send confirmation
                                    conf = {
                                        "type": "camera_control_applied",
                                        "device_id": device_id,
                                        "payload": applied
                                    }
                                    await ws.send_json(conf)
                                elif msg_type == "audio_control_command":
                                    print(f"[{dev_info['custom_name']} AUDIO RECV] {data}")

                        telemetry_task.cancel()

            except Exception as e:
                print(f"[RETRY] {dev_info['custom_name']} disconnected: {e}. Reconnecting in 3s...")
                await asyncio.sleep(3.0)
    finally:
        if ffmpeg_proc:
            ffmpeg_proc.terminate()

async def main():
    parser = argparse.ArgumentParser(description="OBS Camera Pro - Multi-Device Hardware Simulator")
    parser.add_argument("--count", type=int, default=3, help="Number of simulated cameras (1-3)")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Desktop server host")
    parser.add_argument("--port", type=int, default=8765, help="Desktop server port")
    parser.add_argument("--video", action="store_true", help="Transmit synthetic video/audio patterns via FFmpeg")
    args = parser.parse_args()

    active_devs = DEFAULT_DEVICES[:args.count]
    tasks = [simulate_device(dev, args.host, args.port, args.video) for dev in active_devs]
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nSimulator stopped.")
