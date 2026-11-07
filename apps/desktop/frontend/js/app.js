/**
 * OBS Camera Pro - Desktop Control Center Frontend Application
 */

const STATE = {
  activeView: 'dashboard',
  devices: [],
  selectedDeviceId: null,
  obsStatus: { is_connected: false, scenes: [], current_scene: null },
  systemMetrics: { cpu_percent: 0, memory_percent: 0, net_ingress_mbps: 0 },
  charts: {
    bitrateChart: null,
    systemChart: null
  },
  ws: null,
  bitrateHistory: [],
  timeLabels: []
};

// Initialize on DOM ready
document.addEventListener('DOMContentLoaded', () => {
  initLucideIcons();
  initNavigation();
  initCharts();
  connectWebSocket();
  fetchInitialData();
  startMetricsPolling();
});

function initLucideIcons() {
  if (window.lucide) {
    lucide.createIcons();
  }
}

function initNavigation() {
  const navItems = document.querySelectorAll('.nav-item');
  navItems.forEach(item => {
    item.addEventListener('click', (e) => {
      e.preventDefault();
      const targetView = item.getAttribute('data-view');
      switchView(targetView);
    });
  });

  // Pairing Modal triggers
  const pairBtn = document.getElementById('openPairModalBtn');
  const closePairBtn = document.getElementById('closePairModalBtn');
  const pairModal = document.getElementById('pairModal');

  if (pairBtn && pairModal) {
    pairBtn.addEventListener('click', () => {
      loadPairingQRCode();
      pairModal.classList.add('active');
    });
  }
  if (closePairBtn && pairModal) {
    closePairBtn.addEventListener('click', () => {
      pairModal.classList.remove('active');
    });
  }

  // Camera control modal close
  const closeControlBtn = document.getElementById('closeControlModalBtn');
  const controlModal = document.getElementById('controlModal');
  if (closeControlBtn && controlModal) {
    closeControlBtn.addEventListener('click', () => {
      controlModal.classList.remove('active');
    });
  }
}

function switchView(viewName) {
  STATE.activeView = viewName;
  document.querySelectorAll('.nav-item').forEach(item => {
    item.classList.toggle('active', item.getAttribute('data-view') === viewName);
  });
  document.querySelectorAll('.page-view').forEach(view => {
    view.classList.toggle('active', view.id === `view-${viewName}`);
  });
  initLucideIcons();

  if (viewName === 'studio') {
    renderStudioGrid();
  } else if (viewName === 'audio') {
    renderAudioMixer();
  } else if (viewName === 'obs') {
    renderOBSView();
  } else if (viewName === 'logs') {
    loadLogs();
  } else if (viewName === 'network') {
    loadNetworkInfo();
  }
}

function initCharts() {
  const bitrateCtx = document.getElementById('bitrateChartCanvas');
  const systemCtx = document.getElementById('systemChartCanvas');

  if (bitrateCtx) {
    STATE.charts.bitrateChart = new Chart(bitrateCtx, {
      type: 'line',
      data: {
        labels: Array(15).fill(''),
        datasets: [{
          label: 'Incoming Bitrate (Mbps)',
          data: Array(15).fill(0),
          borderColor: '#38bdf8',
          backgroundColor: 'rgba(56, 189, 248, 0.1)',
          fill: true,
          tension: 0.35,
          borderWidth: 2
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          x: { grid: { color: '#1e293b' }, ticks: { color: '#64748b' } },
          y: { grid: { color: '#1e293b' }, ticks: { color: '#64748b' }, beginAtZero: true }
        }
      }
    });
  }

  if (systemCtx) {
    STATE.charts.systemChart = new Chart(systemCtx, {
      type: 'doughnut',
      data: {
        labels: ['CPU', 'RAM', 'Free'],
        datasets: [{
          data: [15, 45, 40],
          backgroundColor: ['#38bdf8', '#818cf8', '#1e293b'],
          borderWidth: 0
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        cutout: '72%',
        plugins: {
          legend: {
            position: 'bottom',
            labels: { color: '#94a3b8', font: { size: 11 } }
          }
        }
      }
    });
  }
}

function connectWebSocket() {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const wsUrl = `${protocol}//${window.location.host}/ws/devices`;

  try {
    STATE.ws = new WebSocket(wsUrl);

    STATE.ws.onopen = () => {
      document.getElementById('backendStatusDot').className = 'status-dot online';
      document.getElementById('backendStatusText').innerText = 'Backend Connected';
    };

    STATE.ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        handleWsMessage(msg);
      } catch (e) {
        console.error('Error parsing WS message:', e);
      }
    };

    STATE.ws.onclose = () => {
      document.getElementById('backendStatusDot').className = 'status-dot offline';
      document.getElementById('backendStatusText').innerText = 'Reconnecting...';
      setTimeout(connectWebSocket, 3000);
    };
  } catch (err) {
    setTimeout(connectWebSocket, 5000);
  }
}

function handleWsMessage(msg) {
  if (msg.type === 'device_connected' || msg.type === 'device_disconnected' || msg.type === 'device_deleted') {
    fetchDevices();
  } else if (msg.type === 'telemetry_update') {
    updateDeviceTelemetryInMemory(msg.device_id, msg.data);
  } else if (msg.type === 'camera_settings_updated') {
    // If control drawer is open for this device, sync sliders
    if (STATE.selectedDeviceId === msg.device_id) {
      syncControlDrawerValues(msg.settings);
    }
  }
}

async function fetchInitialData() {
  await Promise.all([
    fetchDevices(),
    fetchOBSStatus(),
    fetchSystemMetrics()
  ]);
}

async function fetchDevices() {
  try {
    const res = await fetch('/api/devices');
    const data = await res.json();
    STATE.devices = data.devices || [];
    renderDashboardDevices();
    updateOverviewCounters();
    if (STATE.activeView === 'studio') renderStudioGrid();
    if (STATE.activeView === 'audio') renderAudioMixer();
  } catch (err) {
    console.error('Failed to fetch devices:', err);
  }
}

function updateOverviewCounters() {
  const connectedCount = STATE.devices.filter(d => d.is_online).length;
  document.getElementById('metricConnectedCount').innerText = connectedCount;
  document.getElementById('metricActiveStreams').innerText = connectedCount;

  let totalBitrate = 0;
  let totalFps = 0;
  let fpsCount = 0;

  STATE.devices.forEach(d => {
    if (d.telemetry) {
      totalBitrate += (d.telemetry.bitrate_kbps || 0);
      if (d.telemetry.fps > 0) {
        totalFps += d.telemetry.fps;
        fpsCount++;
      }
    }
  });

  const totalMbps = (totalBitrate / 1000).toFixed(1);
  document.getElementById('metricTotalBitrate').innerText = `${totalMbps} Mbps`;
  const avgFps = fpsCount > 0 ? (totalFps / fpsCount).toFixed(0) : '0';
  document.getElementById('metricAvgFps').innerText = `${avgFps} FPS`;
}

function renderDashboardDevices() {
  const container = document.getElementById('dashboardCameraList');
  if (!container) return;

  if (STATE.devices.length === 0) {
    container.innerHTML = `
      <div style="grid-column: 1/-1; padding: 36px; text-align: center; color: var(--text-dim); background: var(--bg-card); border-radius: 12px; border: 1px dashed var(--border-color);">
        <i data-lucide="smartphone" style="width: 36px; height: 36px; margin: 0 auto 12px; opacity: 0.5;"></i>
        <h4 style="color: #fff; margin-bottom: 6px;">No Cameras Paired Yet</h4>
        <p style="font-size: 13px; max-width: 380px; margin: 0 auto 16px;">Scan the pairing QR code from the OBS Camera Pro app on your Android or iPhone.</p>
        <button class="btn btn-primary btn-sm" onclick="document.getElementById('openPairModalBtn').click()">
          <i data-lucide="qr-code"></i> Show Pairing QR Code
        </button>
      </div>
    `;
    initLucideIcons();
    return;
  }

  container.innerHTML = STATE.devices.map(dev => `
    <div class="camera-preview-card">
      <div class="preview-screen">
        <iframe src="${dev.stream_urls.obs_browser_url}" class="preview-video" frameborder="0"></iframe>
        <div class="preview-badges">
          <span class="badge-tag ${dev.is_online ? 'badge-live' : ''}">
            <span class="status-dot ${dev.is_online ? 'online' : 'offline'}"></span>
            ${dev.is_online ? 'LIVE' : 'OFFLINE'}
          </span>
          <span class="badge-tag">
            <i data-lucide="${dev.connection_type === 'usb_tethering' ? 'usb' : 'wifi'}"></i>
            ${dev.connection_type === 'usb_tethering' ? 'USB Wired' : 'Wi-Fi'}
          </span>
        </div>
      </div>
      <div class="card-body">
        <div class="card-title-row">
          <h4 class="camera-name">${dev.custom_name}</h4>
          <span style="font-size: 11px; color: var(--text-dim); text-transform: uppercase;">${dev.platform}</span>
        </div>
        <div class="telemetry-bar">
          <span>FPS: <strong>${(dev.telemetry?.fps || 0).toFixed(0)}</strong></span>
          <span>Bitrate: <strong>${dev.telemetry?.bitrate_kbps || 0} kbps</strong></span>
          <span>Bat: <strong>${dev.telemetry?.battery_pct || 100}%</strong></span>
        </div>
        <div class="card-actions-row">
          <button class="btn btn-secondary btn-sm" style="flex: 1;" onclick="openCameraControls('${dev.device_id}')">
            <i data-lucide="sliders"></i> Controls
          </button>
          <button class="btn btn-primary btn-sm" onclick="sendToOBS('${dev.device_id}')" title="Inject into OBS Studio">
            <i data-lucide="tv"></i> OBS
          </button>
          <button class="btn btn-sm" style="background: rgba(239, 68, 68, 0.15); color: #ef4444; border: 1px solid rgba(239, 68, 68, 0.4); padding: 6px 10px;" onclick="deleteCameraDevice('${dev.device_id}', '${dev.custom_name}')" title="Delete Camera">
            <i data-lucide="trash-2"></i>
          </button>
        </div>
      </div>
    </div>
  `).join('');

  initLucideIcons();
}

function renderStudioGrid() {
  const container = document.getElementById('studioGridContainer');
  if (!container) return;
  renderDashboardDevices(); // shares card structure
}

function renderAudioMixer() {
  const container = document.getElementById('audioMixerContainer');
  if (!container) return;

  if (STATE.devices.length === 0) {
    container.innerHTML = `<p style="color: var(--text-dim);">No mobile audio sources detected.</p>`;
    return;
  }

  container.innerHTML = STATE.devices.map(dev => `
    <div class="audio-channel-strip">
      <div class="card-title-row">
        <h4 class="camera-name">${dev.custom_name}</h4>
        <span class="badge-tag" style="font-size: 10px;">${dev.device_id.substring(0, 8)}</span>
      </div>
      <div class="vu-meter-bar">
        <div class="vu-meter-level" id="vu-${dev.device_id}" style="width: ${Math.min(100, Math.max(5, (dev.telemetry?.audio_level_db || -60) + 60))}%"></div>
      </div>
      <div class="form-group">
        <div class="form-label">
          <span>Gain / Volume</span>
          <span id="gainVal-${dev.device_id}">100%</span>
        </div>
        <input type="range" class="slider-input" min="0" max="2" step="0.05" value="1.0"
          oninput="onAudioGainChange('${dev.device_id}', this.value)">
      </div>
      <div class="form-group">
        <div class="form-label">
          <span>Audio/Video Sync Offset</span>
          <span id="delayVal-${dev.device_id}" style="color: var(--accent-cyan); font-weight: 600;">0 ms</span>
        </div>
        <input type="range" class="slider-input" min="-500" max="500" step="10" value="0"
          oninput="document.getElementById('delayVal-${dev.device_id}').innerText = (this.value > 0 ? '+' : '') + this.value + ' ms'"
          onchange="onAudioSyncDelayChange('${dev.device_id}', this.value)">
      </div>
      <div style="display: flex; gap: 8px;">
        <button class="btn btn-secondary btn-sm" style="flex: 1;" onclick="toggleAudioMute('${dev.device_id}', this)">
          <i data-lucide="mic"></i> Mute
        </button>
        <button class="btn btn-secondary btn-sm" style="flex: 1;" onclick="toggleSendToOBS('${dev.device_id}', this)">
          <i data-lucide="volume-2"></i> OBS Audio
        </button>
      </div>
    </div>
  `).join('');

  initLucideIcons();
}

async function openCameraControls(deviceId) {
  STATE.selectedDeviceId = deviceId;
  const modal = document.getElementById('controlModal');
  const res = await fetch(`/api/devices/${deviceId}`);
  const data = await res.json();

  document.getElementById('controlDeviceTitle').innerText = `Camera Controls - ${data.device.custom_name}`;

  if (data.camera_settings) {
    syncControlDrawerValues(data.camera_settings);
  }

  modal.classList.add('active');
}

function syncControlDrawerValues(settings) {
  if (settings.zoom !== undefined) {
    document.getElementById('controlZoom').value = settings.zoom;
    document.getElementById('zoomValDisplay').innerText = `${parseFloat(settings.zoom).toFixed(1)}x`;
  }
  if (settings.focus_distance !== undefined) {
    document.getElementById('controlFocusDist').value = settings.focus_distance;
    document.getElementById('focusValDisplay').innerText = parseFloat(settings.focus_distance).toFixed(2);
  }
  if (settings.iso !== undefined) {
    document.getElementById('controlISO').value = settings.iso;
    document.getElementById('isoValDisplay').innerText = settings.iso;
  }
  if (settings.exposure_compensation !== undefined) {
    document.getElementById('controlExpComp').value = settings.exposure_compensation;
    document.getElementById('expValDisplay').innerText = `${settings.exposure_compensation > 0 ? '+' : ''}${settings.exposure_compensation}`;
  }
  if (settings.torch_enabled !== undefined) {
    document.getElementById('controlTorch').checked = settings.torch_enabled;
  }
  if (settings.lens !== undefined) {
    document.getElementById('controlLensSelect').value = settings.lens;
  }
  if (settings.resolution_profile !== undefined) {
    document.getElementById('controlResSelect').value = settings.resolution_profile;
  }
}

async function dispatchCameraControl(key, value) {
  if (!STATE.selectedDeviceId) return;
  const payload = { device_id: STATE.selectedDeviceId, [key]: value };
  try {
    await fetch('/api/controls', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
  } catch (err) {
    console.error('Failed to send control command:', err);
  }
}

async function onAudioGainChange(deviceId, value) {
  document.getElementById(`gainVal-${deviceId}`).innerText = `${Math.round(value * 100)}%`;
  await fetch('/api/audio', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ device_id: deviceId, gain: parseFloat(value) })
  });
}

async function toggleAudioMute(deviceId, btn) {
  const isMuted = btn.classList.toggle('btn-danger');
  btn.innerHTML = `<i data-lucide="${isMuted ? 'mic-off' : 'mic'}"></i> ${isMuted ? 'Unmute' : 'Mute'}`;
  initLucideIcons();
  await fetch('/api/audio', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ device_id: deviceId, muted: isMuted })
  });
}

async function deleteCameraDevice(deviceId, name) {
  if (!confirm(`Are you sure you want to remove "${name || deviceId}" from OBS Camera Pro?`)) {
    return;
  }
  try {
    const res = await fetch(`/api/devices/${encodeURIComponent(deviceId)}`, {
      method: 'DELETE'
    });
    if (res.ok) {
      STATE.devices = STATE.devices.filter(d => d.device_id !== deviceId);
      renderDashboardDevices();
      renderStudioGrid();
      showNotification(`Camera ${name || deviceId} removed successfully`, 'success');
    } else {
      showNotification('Failed to remove camera', 'error');
    }
  } catch (err) {
    showNotification('Network error while removing camera', 'error');
  }
}

async function loadPairingQRCode() {
  const container = document.getElementById('qrCodeContainer');
  container.innerHTML = `
    <div style="padding: 24px; text-align: center; color: var(--text-dim);">
      <div class="status-dot connecting" style="margin: 0 auto 10px; width: 12px; height: 12px;"></div>
      Generating QR code...
    </div>
  `;
  try {
    const res = await fetch('/api/devices/pair', {
      method: 'POST',
      headers: { 'Accept': 'application/json' }
    });
    if (!res.ok) {
      throw new Error(`HTTP ${res.status}: ${res.statusText}`);
    }
    const data = await res.json();
    container.innerHTML = `
      <img src="${data.qr_data_uri}" alt="Pairing QR Code" style="width: 220px; height: 220px; border-radius: 8px; margin: 0 auto; display: block; border: 1px solid var(--border-color);">
      <div style="font-size: 12px; color: var(--text-dim); text-align: center; margin-top: 12px;">
        Host IP: <strong style="color: var(--accent-cyan);">${data.payload.host}</strong> | Port: <strong style="color: #fff;">${data.payload.port}</strong>
      </div>
    `;
  } catch (e) {
    console.error('Failed to load pairing QR code:', e);
    container.innerHTML = `<p style="color: var(--danger); text-align: center; padding: 12px;">Failed to generate QR code: ${e.message}</p>`;
  }
}

async function fetchOBSStatus() {
  try {
    const res = await fetch('/api/obs/status');
    const data = await res.json();
    STATE.obsStatus = data;
    const dot = document.getElementById('obsStatusDot');
    const text = document.getElementById('obsStatusText');
    if (data.is_connected) {
      dot.className = 'status-dot online';
      text.innerText = `OBS: Connected (${data.current_scene || 'Default'})`;
    } else {
      dot.className = 'status-dot offline';
      text.innerText = 'OBS: Disconnected';
    }
  } catch (err) {
    console.error('Failed to get OBS status:', err);
  }
}

async function sendToOBS(deviceId) {
  try {
    const res = await fetch('/api/obs/sources/create', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ device_id: deviceId })
    });
    const result = await res.json();
    if (result.success) {
      alert(`Successfully injected into OBS: ${result.source_name} in scene [${result.scene}]`);
    } else {
      alert(`OBS Error: ${result.error || 'Check OBS WebSocket connection'}`);
    }
  } catch (e) {
    alert('Failed to communicate with OBS API');
  }
}

async function connectOBS() {
  const host = document.getElementById('obsHostInput').value;
  const port = parseInt(document.getElementById('obsPortInput').value);
  const password = document.getElementById('obsPasswordInput').value;

  try {
    const res = await fetch('/api/obs/connect', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ host, port, password })
    });
    const data = await res.json();
    fetchOBSStatus();
    if (data.status === 'connected') {
      alert('Connected to OBS Studio successfully!');
    } else {
      alert(data.message || 'OBS connection failed');
    }
  } catch (e) {
    alert('OBS connection request failed');
  }
}

async function renderOBSView() {
  await fetchOBSStatus();
  await updateOBSOutputsUI();
  const sceneList = document.getElementById('obsSceneList');
  if (!sceneList) return;

  if (!STATE.obsStatus.is_connected) {
    sceneList.innerHTML = `<p style="color: var(--text-dim); font-size: 13px;">Connect to OBS Studio above to manage scenes and sources.</p>`;
    return;
  }

  sceneList.innerHTML = STATE.obsStatus.scenes.map(s => `
    <div style="display: flex; align-items: center; justify-content: space-between; padding: 10px 14px; background: var(--bg-secondary); border-radius: 8px; border: 1px solid ${s === STATE.obsStatus.current_scene ? 'var(--accent-cyan)' : 'var(--border-color)'};">
      <span style="font-size: 13.5px; font-weight: 500; color: #fff;">${s}</span>
      ${s === STATE.obsStatus.current_scene 
        ? `<span class="badge-tag badge-live">PROGRAM</span>` 
        : `<button class="btn btn-secondary btn-sm" onclick="switchOBSScene('${s}')">Switch Scene</button>`
      }
    </div>
  `).join('');
}

async function toggleOBSOutput(outputType) {
  try {
    const res = await fetch(`/api/obs/outputs/${outputType}`, { method: 'POST' });
    const data = await res.json();
    if (!data.success && data.error) {
      alert(`OBS Error: ${data.error}`);
    }
    await updateOBSOutputsUI();
  } catch (err) {
    console.error(`Failed to toggle OBS ${outputType}:`, err);
  }
}

async function updateOBSOutputsUI() {
  try {
    const res = await fetch('/api/obs/outputs/status');
    const data = await res.json();

    const recBtn = document.getElementById('obsRecordBtn');
    const recText = document.getElementById('obsRecordBtnText');
    if (recBtn && recText) {
      if (data.recording) {
        recBtn.className = 'btn btn-danger';
        recText.innerText = 'Stop Recording (ACTIVE)';
      } else {
        recBtn.className = 'btn btn-secondary';
        recText.innerText = 'Start Recording';
      }
    }

    const strmBtn = document.getElementById('obsStreamBtn');
    const strmText = document.getElementById('obsStreamBtnText');
    if (strmBtn && strmText) {
      if (data.streaming) {
        strmBtn.className = 'btn btn-primary';
        strmText.innerText = 'Stop OBS Stream (LIVE)';
      } else {
        strmBtn.className = 'btn btn-secondary';
        strmText.innerText = 'Start OBS Stream';
      }
    }

    const vcamBtn = document.getElementById('obsVcamBtn');
    const vcamText = document.getElementById('obsVcamBtnText');
    if (vcamBtn && vcamText) {
      if (data.virtual_cam) {
        vcamBtn.className = 'btn btn-primary';
        vcamText.innerText = 'Stop Virtual Camera';
      } else {
        vcamBtn.className = 'btn btn-secondary';
        vcamText.innerText = 'Start Virtual Camera';
      }
    }
    initLucideIcons();
  } catch (e) {}
}

async function switchOBSScene(sceneName) {
  await fetch('/api/obs/scenes/switch', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ scene_name: sceneName })
  });
  renderOBSView();
}

function startMetricsPolling() {
  setInterval(async () => {
    await fetchSystemMetrics();
  }, 2000);
}

async function fetchSystemMetrics() {
  try {
    const res = await fetch('/api/system/metrics');
    const data = await res.json();
    STATE.systemMetrics = data;

    document.getElementById('metricCpu').innerText = `${data.cpu_percent}%`;
    document.getElementById('metricMemory').innerText = `${data.memory_percent}%`;

    // Update Bitrate Chart
    if (STATE.charts.bitrateChart) {
      const chart = STATE.charts.bitrateChart;
      chart.data.datasets[0].data.push(data.net_ingress_mbps);
      chart.data.datasets[0].data.shift();
      chart.update('none');
    }

    // Update Doughnut Chart
    if (STATE.charts.systemChart) {
      const freeMem = Math.max(0, 100 - data.cpu_percent - data.memory_percent);
      STATE.charts.systemChart.data.datasets[0].data = [data.cpu_percent, data.memory_percent, freeMem];
      STATE.charts.systemChart.update('none');
    }
  } catch (e) {
    // suppress transient errors
  }
}

async function loadLogs() {
  const tbody = document.getElementById('logTableBody');
  if (!tbody) return;
  try {
    const res = await fetch('/api/system/logs');
    const data = await res.json();
    tbody.innerHTML = data.logs.map(l => `
      <tr>
        <td>${l.timestamp?.substring(11, 19) || ''}</td>
        <td><span class="log-level ${l.level}">${l.level}</span></td>
        <td>${l.source}</td>
        <td>${l.message}</td>
      </tr>
    `).join('');
  } catch (e) {}
}

async function loadNetworkInfo() {
  const container = document.getElementById('networkInterfacesContainer');
  if (!container) return;
  try {
    const res = await fetch('/api/system/network');
    const data = await res.json();
    container.innerHTML = data.interfaces.map(iface => `
      <div style="background: var(--bg-secondary); padding: 14px; border-radius: 8px; border: 1px solid var(--border-color); display: flex; align-items: center; justify-content: space-between;">
        <div>
          <h5 style="color: #fff; font-size: 14px;">${iface.name}</h5>
          <span style="font-size: 12px; color: var(--text-dim);">${iface.ip} (${iface.netmask})</span>
        </div>
        <span class="badge-tag" style="text-transform: uppercase;">
          <i data-lucide="${iface.type === 'usb_tethering' ? 'usb' : 'wifi'}"></i>
          ${iface.type}
        </span>
      </div>
    `).join('');
    initLucideIcons();
  } catch (e) {}
}

