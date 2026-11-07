package com.obscamera.pro.ui

import androidx.camera.view.PreviewView
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.CameraAlt
import androidx.compose.material.icons.filled.Close
import androidx.compose.material.icons.filled.FlashOff
import androidx.compose.material.icons.filled.FlashOn
import androidx.compose.material.icons.filled.PlayArrow
import androidx.compose.material.icons.filled.QrCodeScanner
import androidx.compose.material.icons.filled.Stop
import androidx.compose.material.icons.filled.Tune
import androidx.compose.material.icons.filled.Usb
import androidx.compose.material.icons.filled.Wifi
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
    isConnectedToPc: Boolean,
    pcHost: String,
    connectionType: String,
    fps: Float,
    bitrateKbps: Int,
    batteryPct: Int,
    audioLevelDb: Float,
    isScanningQr: Boolean,
    onStartStreaming: () -> Unit,
    onStopStreaming: () -> Unit,
    onStartQrScan: () -> Unit,
    onStopQrScan: () -> Unit,
    onConnectManualIp: (String, Int) -> Unit
) {
    val lifecycleOwner = LocalLifecycleOwner.current
    var selectedLens by remember { mutableStateOf(CameraLens.BACK_WIDE) }
    var showControlsDrawer by remember { mutableStateOf(false) }
    var showPairingDialog by remember { mutableStateOf(false) }

    var currentZoom by remember { mutableFloatStateOf(1.0f) }
    var currentIso by remember { mutableFloatStateOf(100f) }
    var currentFocus by remember { mutableFloatStateOf(0.0f) }
    var torchOn by remember { mutableStateOf(false) }

    var manualIpInput by remember { mutableStateOf(if (pcHost.isNotEmpty()) pcHost else "192.168.1.") }
    var manualPortInput by remember { mutableStateOf("8000") }

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

        // 2. QR Scanning Viewfinder Overlay (When scanning mode active)
        if (isScanningQr) {
            Box(
                modifier = Modifier
                    .fillMaxSize()
                    .background(Color(0x99090D16))
            ) {
                Column(
                    modifier = Modifier.align(Alignment.Center),
                    horizontalAlignment = Alignment.CenterHorizontally,
                    verticalArrangement = Arrangement.spacedBy(20.dp)
                ) {
                    Text(
                        text = "Point camera at Desktop QR Code",
                        color = Color.White,
                        fontSize = 16.sp,
                        fontWeight = FontWeight.Bold
                    )

                    // Target Viewfinder Box
                    Box(
                        modifier = Modifier
                            .size(240.dp)
                            .border(3.dp, Color(0xFF38BDF8), RoundedCornerShape(16.dp))
                    )

                    Text(
                        text = "Align the QR code within this box",
                        color = Color(0xFF94A3B8),
                        fontSize = 13.sp
                    )

                    Button(
                        onClick = onStopQrScan,
                        colors = ButtonDefaults.buttonColors(containerColor = Color(0xFFEF4444)),
                        shape = RoundedCornerShape(20.dp)
                    ) {
                        Icon(Icons.Filled.Close, contentDescription = null, modifier = Modifier.size(16.dp))
                        Spacer(Modifier.width(6.dp))
                        Text("Cancel Scanner", fontWeight = FontWeight.Bold)
                    }
                }
            }
        }

        // 3. Top HUD Overlay
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

            // Connection Badge (Shows PC connection state)
            Surface(
                color = if (isConnectedToPc) Color(0xCC059669) else Color(0xCC0F172A),
                shape = RoundedCornerShape(20.dp),
                onClick = { showPairingDialog = true }
            ) {
                Row(
                    modifier = Modifier.padding(horizontal = 12.dp, vertical = 6.dp),
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(6.dp)
                ) {
                    Icon(
                        imageVector = if (connectionType == "usb_tethering") Icons.Filled.Usb else Icons.Filled.Wifi,
                        contentDescription = "Connection",
                        tint = if (isConnectedToPc) Color.White else Color(0xFF38BDF8),
                        modifier = Modifier.size(14.dp)
                    )
                    Text(
                        text = if (isConnectedToPc) "PC: $pcHost" else "Tap to Pair PC",
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

        // 4. Floating Lens Selector
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

        // 5. Camera Controls Drawer (When opened)
        if (showControlsDrawer) {
            Surface(
                color = Color(0xEE0F172A),
                shape = RoundedCornerShape(16.dp),
                modifier = Modifier
                    .align(Alignment.CenterStart)
                    .padding(start = 16.dp)
                    .width(180.dp)
            ) {
                Column(
                    modifier = Modifier.padding(14.dp),
                    verticalArrangement = Arrangement.spacedBy(12.dp)
                ) {
                    Text("Camera Controls", color = Color.White, fontSize = 12.sp, fontWeight = FontWeight.Bold)

                    // Zoom Slider
                    Text("Zoom: ${String.format("%.1f", currentZoom)}x", color = Color(0xFF38BDF8), fontSize = 11.sp)
                    Slider(
                        value = currentZoom,
                        onValueChange = {
                            currentZoom = it
                            cameraManager.setZoom(it)
                        },
                        valueRange = 1.0f..cameraManager.maxZoomRatio,
                        modifier = Modifier.height(20.dp)
                    )

                    // Torch Toggle
                    Button(
                        onClick = {
                            torchOn = !torchOn
                            cameraManager.setTorch(torchOn)
                        },
                        colors = ButtonDefaults.buttonColors(
                            containerColor = if (torchOn) Color(0xFFF59E0B) else Color(0xFF1E293B)
                        ),
                        modifier = Modifier.fillMaxWidth().height(36.dp)
                    ) {
                        Icon(if (torchOn) Icons.Filled.FlashOn else Icons.Filled.FlashOff, contentDescription = null, modifier = Modifier.size(16.dp))
                        Spacer(Modifier.width(6.dp))
                        Text(if (torchOn) "Torch ON" else "Torch OFF", fontSize = 11.sp)
                    }

                    // Auto-Focus Button
                    Button(
                        onClick = { cameraManager.setAutoFocus() },
                        colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF38BDF8)),
                        modifier = Modifier.fillMaxWidth().height(36.dp)
                    ) {
                        Text("Auto Focus", color = Color.Black, fontSize = 11.sp, fontWeight = FontWeight.Bold)
                    }
                }
            }
        }

        // 6. Bottom Controls & Action Bar
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
                    onClick = { showPairingDialog = true },
                    modifier = Modifier
                        .size(48.dp)
                        .background(Color(0xAA0F172A), CircleShape)
                ) {
                    Icon(Icons.Filled.QrCodeScanner, contentDescription = "Pair", tint = Color.White)
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
                        imageVector = if (isStreaming) Icons.Filled.Stop else Icons.Filled.PlayArrow,
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
                    Icon(Icons.Filled.Tune, contentDescription = "Controls", tint = Color.White)
                }
            }
        }

        // 7. Pairing Dialog
        if (showPairingDialog) {
            AlertDialog(
                onDismissRequest = { showPairingDialog = false },
                containerColor = Color(0xFF0F172A),
                title = {
                    Text("Connect to OBS Studio PC", color = Color.White, fontWeight = FontWeight.Bold)
                },
                text = {
                    Column(verticalArrangement = Arrangement.spacedBy(16.dp)) {
                        Text(
                            text = "Scan the QR code on your PC dashboard, or enter the PC's IP address directly.",
                            color = Color(0xFF94A3B8),
                            fontSize = 13.sp
                        )

                        // Option A: Scan QR Code Button
                        Button(
                            onClick = {
                                showPairingDialog = false
                                onStartQrScan()
                            },
                            colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF38BDF8)),
                            modifier = Modifier.fillMaxWidth().height(48.dp),
                            shape = RoundedCornerShape(12.dp)
                        ) {
                            Icon(Icons.Filled.QrCodeScanner, contentDescription = null, tint = Color.Black)
                            Spacer(Modifier.width(8.dp))
                            Text("Scan Desktop QR Code", color = Color.Black, fontWeight = FontWeight.Bold)
                        }

                        Divider(color = Color(0xFF1E293B))

                        Text("Or Enter PC IP Address:", color = Color.White, fontSize = 12.sp, fontWeight = FontWeight.SemiBold)

                        OutlinedTextField(
                            value = manualIpInput,
                            onValueChange = { manualIpInput = it },
                            label = { Text("PC IP Address (e.g. 192.168.1.5)") },
                            singleLine = true,
                            colors = OutlinedTextFieldDefaults.colors(
                                focusedTextColor = Color.White,
                                unfocusedTextColor = Color.White,
                                focusedBorderColor = Color(0xFF38BDF8),
                                unfocusedBorderColor = Color(0xFF334155)
                            ),
                            modifier = Modifier.fillMaxWidth()
                        )

                        OutlinedTextField(
                            value = manualPortInput,
                            onValueChange = { manualPortInput = it },
                            label = { Text("Port") },
                            singleLine = true,
                            colors = OutlinedTextFieldDefaults.colors(
                                focusedTextColor = Color.White,
                                unfocusedTextColor = Color.White,
                                focusedBorderColor = Color(0xFF38BDF8),
                                unfocusedBorderColor = Color(0xFF334155)
                            ),
                            modifier = Modifier.fillMaxWidth()
                        )
                    }
                },
                confirmButton = {
                    Button(
                        onClick = {
                            val portInt = manualPortInput.toIntOrNull() ?: 8000
                            onConnectManualIp(manualIpInput.trim(), portInt)
                            showPairingDialog = false
                        },
                        colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF10B981))
                    ) {
                        Text("Connect", fontWeight = FontWeight.Bold)
                    }
                },
                dismissButton = {
                    TextButton(onClick = { showPairingDialog = false }) {
                        Text("Cancel", color = Color(0xFF94A3B8))
                    }
                }
            )
        }
    }
}
