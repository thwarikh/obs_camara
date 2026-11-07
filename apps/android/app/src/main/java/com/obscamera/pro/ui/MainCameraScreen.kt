package com.obscamera.pro.ui

import androidx.camera.view.PreviewView
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalLifecycleOwner
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.viewinterop.AndroidView
import com.obscamera.pro.camera.CameraLens
import com.obscamera.pro.camera.CameraManager

@Composable
fun MainCameraScreen(
    cameraManager: CameraManager,
    isStreaming: Boolean,
    connectionType: String,
    fps: Float,
    bitrateKbps: Int,
    batteryPct: Int,
    audioLevelDb: Float,
    onStartStreaming: () -> Unit,
    onStopStreaming: () -> Unit,
    onOpenPairing: () -> Unit
) {
    val lifecycleOwner = LocalLifecycleOwner.current
    var selectedLens by remember { mutableStateOf(CameraLens.BACK_WIDE) }
    var showControlsDrawer by remember { mutableStateOf(false) }

    var currentZoom by remember { mutableFloatStateOf(1.0f) }
    var currentIso by remember { mutableFloatStateOf(100f) }
    var currentFocus by remember { mutableFloatStateOf(0.0f) }
    var torchOn by remember { mutableStateOf(false) }

    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(Color(0xFF090D16))
    ) {
        // 1. Camera Live Preview
        AndroidView(
            factory = { ctx ->
                PreviewView(ctx).apply {
                    cameraManager.initialize(lifecycleOwner, surfaceProvider) {}
                }
            },
            modifier = Modifier.fillMaxSize()
        )

        // 2. Top HUD Overlay
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(top = 40.dp, start = 16.dp, end = 16.dp),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            // Live Status Pill
            Surface(
                color = if (isStreaming) Color(0xCCEF4444) else Color(0xCC0F172A),
                shape = RoundedCornerShape(20.dp)
            ) {
                Row(
                    modifier = Modifier.padding(horizontal = 12.dp, vertical = 6.dp),
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(6.dp)
                ) {
                    Box(
                        modifier = Modifier
                            .size(8.dp)
                            .clip(CircleShape)
                            .background(if (isStreaming) Color.White else Color(0xFF64748B))
                    )
                    Text(
                        text = if (isStreaming) "LIVE" else "STANDBY",
                        color = Color.White,
                        fontSize = 11.sp,
                        fontWeight = FontWeight.Bold
                    )
                }
            }

            // Connection Badge (Wi-Fi or USB Tethering)
            Surface(
                color = Color(0xCC0F172A),
                shape = RoundedCornerShape(20.dp)
            ) {
                Row(
                    modifier = Modifier.padding(horizontal = 12.dp, vertical = 6.dp),
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(6.dp)
                ) {
                    Icon(
                        imageVector = if (connectionType == "usb_tethering") Icons.Default.Usb else Icons.Default.Wifi,
                        contentDescription = "Connection",
                        tint = Color(0xFF38BDF8),
                        modifier = Modifier.size(14.dp)
                    )
                    Text(
                        text = if (connectionType == "usb_tethering") "USB Wired" else "Wi-Fi",
                        color = Color.White,
                        fontSize = 11.sp,
                        fontWeight = FontWeight.SemiBold
                    )
                }
            }

            // Telemetry: FPS, Bitrate, Battery
            Surface(
                color = Color(0xCC0F172A),
                shape = RoundedCornerShape(20.dp)
            ) {
                Row(
                    modifier = Modifier.padding(horizontal = 12.dp, vertical = 6.dp),
                    horizontalArrangement = Arrangement.spacedBy(10.dp)
                ) {
                    Text("${fps.toInt()} FPS", color = Color(0xFF38BDF8), fontSize = 11.sp, fontWeight = FontWeight.Bold)
                    Text("${bitrateKbps} kbps", color = Color.White, fontSize = 11.sp)
                    Text("${batteryPct}%", color = Color(0xFF10B981), fontSize = 11.sp)
                }
            }
        }

        // 3. Floating Lens Selector
        Row(
            modifier = Modifier
                .align(Alignment.CenterEnd)
                .padding(end = 16.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            Column(
                verticalArrangement = Arrangement.spacedBy(8.dp),
                horizontalAlignment = Alignment.CenterHorizontally
            ) {
                listOf(
                    CameraLens.BACK_ULTRAWIDE to "0.5x",
                    CameraLens.BACK_WIDE to "1x",
                    CameraLens.BACK_TELEPHOTO to "3x",
                    CameraLens.FRONT to "Front"
                ).forEach { (lens, label) ->
                    val isSelected = selectedLens == lens
                    Button(
                        onClick = {
                            selectedLens = lens
                            // Rebind camera with target lens
                        },
                        colors = ButtonDefaults.buttonColors(
                            containerColor = if (isSelected) Color(0xFF38BDF8) else Color(0xAA0F172A)
                        ),
                        contentPadding = PaddingValues(horizontal = 10.dp, vertical = 4.dp),
                        shape = CircleShape,
                        modifier = Modifier.size(46.dp)
                    ) {
                        Text(
                            text = label,
                            color = if (isSelected) Color.Black else Color.White,
                            fontSize = 11.sp,
                            fontWeight = FontWeight.Bold
                        )
                    }
                }
            }
        }

        // 4. Bottom Controls & Action Bar
        Column(
            modifier = Modifier
                .align(Alignment.BottomCenter)
                .fillMaxWidth()
                .padding(bottom = 24.dp, start = 20.dp, end = 20.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            // Audio VU Meter Bar
            val vuLevelPct = ((audioLevelDb + 60f) / 60f).coerceIn(0f, 1f)
            Box(
                modifier = Modifier
                    .fillMaxWidth(0.8f)
                    .height(6.dp)
                    .clip(RoundedCornerShape(3.dp))
                    .background(Color(0x880F172A))
            ) {
                Box(
                    modifier = Modifier
                        .fillMaxHeight()
                        .fillMaxWidth(vuLevelPct)
                        .background(Color(0xFF10B981))
                )
            }

            // Big Start/Stop Button & Action Icons
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceEvenly,
                verticalAlignment = Alignment.CenterVertically
            ) {
                // QR Pairing Button
                IconButton(
                    onClick = onOpenPairing,
                    modifier = Modifier
                        .size(48.dp)
                        .background(Color(0xAA0F172A), CircleShape)
                ) {
                    Icon(Icons.Default.QrCodeScanner, contentDescription = "Pair", tint = Color.White)
                }

                // Broadcast Toggle Button
                Button(
                    onClick = {
                        if (isStreaming) onStopStreaming() else onStartStreaming()
                    },
                    colors = ButtonDefaults.buttonColors(
                        containerColor = if (isStreaming) Color(0xFFEF4444) else Color(0xFF38BDF8)
                    ),
                    shape = RoundedCornerShape(24.dp),
                    modifier = Modifier.height(52.dp).width(180.dp)
                ) {
                    Icon(
                        imageVector = if (isStreaming) Icons.Default.Stop else Icons.Default.PlayArrow,
                        contentDescription = null,
                        tint = if (isStreaming) Color.White else Color.Black
                    )
                    Spacer(Modifier.width(8.dp))
                    Text(
                        text = if (isStreaming) "STOP" else "START STREAM",
                        color = if (isStreaming) Color.White else Color.Black,
                        fontWeight = FontWeight.Bold
                    )
                }

                // Controls Drawer Toggle
                IconButton(
                    onClick = { showControlsDrawer = !showControlsDrawer },
                    modifier = Modifier
                        .size(48.dp)
                        .background(Color(0xAA0F172A), CircleShape)
                ) {
                    Icon(Icons.Default.Tune, contentDescription = "Controls", tint = Color.White)
                }
            }
        }
    }
}

