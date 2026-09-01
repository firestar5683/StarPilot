import { html, reactive } from "/assets/vendor/arrow-core.js"

const state = reactive({
  loading: true,
  status: {
    connected: false,
    name: "Uniden Radar Detector",
    mac: "",
    rssi: null,
  },
  settings: {
    UnidenR4Enabled: true,
    UnidenR4Mode: "all_threat",
    UnidenR4AutoMute: true,
    UnidenR4QuietRideSpeed: 35,
    UnidenR4Volume: 5,
    UnidenR4Brightness: "auto",
    UnidenR4KBand: true,
    UnidenR4KaBand: true,
    UnidenR4Laser: true,
    UnidenR4MRCD: true,
    UnidenR4POP: false,
    UnidenR4MuteMemory: true,
    UnidenR4AlertVolume: 5,
    UnidenAutoSlowdown: true,
  }
})

function notify(msg, level) {
  if (typeof window.showSnackbar === "function") {
    window.showSnackbar(msg, level)
  } else {
    console.log("[Snackbar]", level || "info", msg)
  }
}

async function loadData() {
  try {
    const [resStatus, resSettings] = await Promise.all([
      fetch("/api/uniden/status", { cache: "no-store" }),
      fetch("/api/uniden/settings", { cache: "no-store" })
    ])
    if (resStatus.ok) state.status = await resStatus.json()
    if (resSettings.ok) {
      const data = await resSettings.json()
      for (const [k, v] of Object.entries(data)) {
        state.settings[k] = v
      }
    }
  } catch (e) {
    console.error("Failed to load Uniden R4 data:", e)
  } finally {
    state.loading = false
  }
}

async function updateSetting(key, val) {
  state.settings[key] = val
  try {
    const res = await fetch("/api/uniden/settings", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ [key]: val })
    })
    if (res.ok) {
      const data = await res.json()
      for (const [k, v] of Object.entries(data)) {
        state.settings[k] = v
      }
      notify(`Updated ${key}`)
    }
  } catch (e) {
    notify("Failed to update setting", "error")
  }
}

async function sendAction(action) {
  try {
    const res = await fetch(`/api/uniden/action/${action}`, { method: "POST" })
    const data = await res.json()
    notify(data.message || "Action sent")
    loadData()
  } catch (e) {
    notify(`Action failed: ${e.message}`, "error")
  }
}

let loadedOnce = false

export function UnidenR4View() {
  if (!loadedOnce) {
    loadedOnce = true
    loadData()
  }

  return html`
    <div class="uniden-container">
      <div class="uniden-header">
        <h1><i class="bi bi-broadcast"></i> Uniden R4 Radar Settings</h1>
        <div class="${() => `uniden-status-badge ${state.status.connected ? 'uniden-status-connected' : 'uniden-status-disconnected'}`}">
          <i class="${() => `bi ${state.status.connected ? 'bi-bluetooth' : 'bi-slash-circle'}`}"></i>
          <span>${() => state.status.connected ? `Connected (${state.status.rssi ? state.status.rssi + ' dBm' : 'BLE'})` : 'Disconnected'}</span>
        </div>
      </div>

      <div class="uniden-grid">
        <!-- Connection Card -->
        <div class="uniden-card">
          <h2 class="uniden-card-title"><i class="bi bi-link-45deg"></i> Device & Connection</h2>
          
          <div class="uniden-setting-row">
            <div class="uniden-setting-info">
              <span class="uniden-setting-label">Enable Radar Integration</span>
              <span class="uniden-setting-desc">Process BLE alerts from Uniden R4</span>
            </div>
            <label class="uniden-switch">
              <input type="checkbox" 
                     checked="${() => !!state.settings.UnidenR4Enabled}" 
                     @change="${(e) => { const el = e && (e.currentTarget || e.target); if (el) updateSetting('UnidenR4Enabled', el.checked); }}" />
              <span class="uniden-slider"></span>
            </label>
          </div>

          <div class="uniden-setting-row">
            <div class="uniden-setting-info">
              <span class="uniden-setting-label">Paired Device</span>
              <span class="uniden-setting-desc">${() => `${state.status.name} (${state.status.mac})`}</span>
            </div>
          </div>

          <div class="uniden-actions">
            <button class="uniden-btn uniden-btn-warning" @click="${() => sendAction('mute')}">
              <i class="bi bi-volume-mute-fill"></i> Mute Current Alert
            </button>
            <button class="uniden-btn uniden-btn-primary" @click="${() => sendAction('connect')}">
              <i class="bi bi-arrow-repeat"></i> Reconnect
            </button>
          </div>
        </div>

        <!-- Sensitivity & Sound Card -->
        <div class="uniden-card">
          <h2 class="uniden-card-title"><i class="bi bi-sliders"></i> Sensitivity & Audio</h2>

          <div class="uniden-setting-row">
            <div class="uniden-setting-info">
              <span class="uniden-setting-label">Detection Mode</span>
              <span class="uniden-setting-desc">Radar sensitivity profile</span>
            </div>
            <select class="uniden-select" 
                    @change="${(e) => { const el = e && (e.currentTarget || e.target); if (el) updateSetting('UnidenR4Mode', el.value); }}">
              <option value="all_threat" :selected="${() => state.settings.UnidenR4Mode === 'all_threat'}">All Threat</option>
              <option value="highway" :selected="${() => state.settings.UnidenR4Mode === 'highway'}">Highway</option>
              <option value="city" :selected="${() => state.settings.UnidenR4Mode === 'city'}">City</option>
              <option value="advanced" :selected="${() => state.settings.UnidenR4Mode === 'advanced'}">Advanced</option>
            </select>
          </div>

          <div class="uniden-setting-row">
            <div class="uniden-setting-info">
              <span class="uniden-setting-label">Main Volume</span>
              <span class="uniden-setting-desc">Alert speaker level (0-8)</span>
            </div>
            <div class="uniden-range-container">
              <input type="range" min="0" max="8" class="uniden-range" 
                     value="${() => state.settings.UnidenR4Volume}"
                     @change="${(e) => { const el = e && (e.currentTarget || e.target); if (el) updateSetting('UnidenR4Volume', parseInt(el.value)); }}" />
              <span class="uniden-range-val">${() => state.settings.UnidenR4Volume}</span>
            </div>
          </div>

          <div class="uniden-setting-row">
            <div class="uniden-setting-info">
              <span class="uniden-setting-label">Auto Mute</span>
              <span class="uniden-setting-desc">Automatically reduce volume after initial alert beep</span>
            </div>
            <label class="uniden-switch">
              <input type="checkbox" 
                     checked="${() => !!state.settings.UnidenR4AutoMute}" 
                     @change="${(e) => { const el = e && (e.currentTarget || e.target); if (el) updateSetting('UnidenR4AutoMute', el.checked); }}" />
              <span class="uniden-slider"></span>
            </label>
          </div>

          <div class="uniden-setting-row">
            <div class="uniden-setting-info">
              <span class="uniden-setting-label">Quiet Ride Speed</span>
              <span class="uniden-setting-desc">Mute all alerts below this speed (MPH)</span>
            </div>
            <div class="uniden-range-container">
              <input type="range" min="0" max="90" step="5" class="uniden-range"
                     value="${() => state.settings.UnidenR4QuietRideSpeed}"
                     @change="${(e) => { const el = e && (e.currentTarget || e.target); if (el) updateSetting('UnidenR4QuietRideSpeed', parseInt(el.value)); }}" />
              <span class="uniden-range-val">${() => `${state.settings.UnidenR4QuietRideSpeed} mph`}</span>
            </div>
          </div>
        </div>

        <!-- Radar Bands Card -->
        <div class="uniden-card">
          <h2 class="uniden-card-title"><i class="bi bi-reception-4"></i> Radar & Laser Bands</h2>

          <div class="uniden-setting-row">
            <div class="uniden-setting-info">
              <span class="uniden-setting-label">Ka Band</span>
              <span class="uniden-setting-desc">Police radar standard (33.4 - 36.0 GHz)</span>
            </div>
            <label class="uniden-switch">
              <input type="checkbox" 
                     checked="${() => !!state.settings.UnidenR4KaBand}" 
                     @change="${(e) => { const el = e && (e.currentTarget || e.target); if (el) updateSetting('UnidenR4KaBand', el.checked); }}" />
              <span class="uniden-slider"></span>
            </label>
          </div>

          <div class="uniden-setting-row">
            <div class="uniden-setting-info">
              <span class="uniden-setting-label">K Band</span>
              <span class="uniden-setting-desc">24.050 - 24.250 GHz</span>
            </div>
            <label class="uniden-switch">
              <input type="checkbox" 
                     checked="${() => !!state.settings.UnidenR4KBand}" 
                     @change="${(e) => { const el = e && (e.currentTarget || e.target); if (el) updateSetting('UnidenR4KBand', el.checked); }}" />
              <span class="uniden-slider"></span>
            </label>
          </div>

          <div class="uniden-setting-row">
            <div class="uniden-setting-info">
              <span class="uniden-setting-label">Laser Detection</span>
              <span class="uniden-setting-desc">LIDAR optical alert</span>
            </div>
            <label class="uniden-switch">
              <input type="checkbox" 
                     checked="${() => !!state.settings.UnidenR4Laser}" 
                     @change="${(e) => { const el = e && (e.currentTarget || e.target); if (el) updateSetting('UnidenR4Laser', el.checked); }}" />
              <span class="uniden-slider"></span>
            </label>
          </div>

          <div class="uniden-setting-row">
            <div class="uniden-setting-info">
              <span class="uniden-setting-label">MRCD / MRCT</span>
              <span class="uniden-setting-desc">MultaRadar speed cameras</span>
            </div>
            <label class="uniden-switch">
              <input type="checkbox" 
                     checked="${() => !!state.settings.UnidenR4MRCD}" 
                     @change="${(e) => { const el = e && (e.currentTarget || e.target); if (el) updateSetting('UnidenR4MRCD', el.checked); }}" />
              <span class="uniden-slider"></span>
            </label>
          </div>

          <div class="uniden-setting-row">
            <div class="uniden-setting-info">
              <span class="uniden-setting-label">POP Mode</span>
              <span class="uniden-setting-desc">Super-fast pulse radar detection</span>
            </div>
            <label class="uniden-switch">
              <input type="checkbox" 
                     checked="${() => !!state.settings.UnidenR4POP}" 
                     @change="${(e) => { const el = e && (e.currentTarget || e.target); if (el) updateSetting('UnidenR4POP', el.checked); }}" />
              <span class="uniden-slider"></span>
            </label>
          </div>
        </div>

        <!-- Openpilot Cruise Integration Card -->
        <div class="uniden-card">
          <h2 class="uniden-card-title"><i class="bi bi-shield-shaded"></i> Openpilot Radar Slowdown</h2>

          <div class="uniden-setting-row">
            <div class="uniden-setting-info">
              <span class="uniden-setting-label">Auto-Slowdown on Radar Alert</span>
              <span class="uniden-setting-desc">Automatically drop cruise speed to the active road speed limit when police radar is detected</span>
            </div>
            <label class="uniden-switch">
              <input type="checkbox" 
                     checked="${() => !!state.settings.UnidenAutoSlowdown}" 
                     @change="${(e) => { const el = e && (e.currentTarget || e.target); if (el) updateSetting('UnidenAutoSlowdown', el.checked); }}" />
              <span class="uniden-slider"></span>
            </label>
          </div>
        </div>

        <!-- Display & Memory Card -->
        <div class="uniden-card">
          <h2 class="uniden-card-title"><i class="bi bi-display"></i> Display & Memory</h2>

          <div class="uniden-setting-row">
            <div class="uniden-setting-info">
              <span class="uniden-setting-label">OLED Brightness</span>
              <span class="uniden-setting-desc">R4 Screen display level</span>
            </div>
            <select class="uniden-select" 
                    @change="${(e) => { const el = e && (e.currentTarget || e.target); if (el) updateSetting('UnidenR4Brightness', el.value); }}">
              <option value="auto" :selected="${() => state.settings.UnidenR4Brightness === 'auto'}">Auto</option>
              <option value="bright" :selected="${() => state.settings.UnidenR4Brightness === 'bright'}">Bright</option>
              <option value="dim" :selected="${() => state.settings.UnidenR4Brightness === 'dim'}">Dim</option>
              <option value="dimmer" :selected="${() => state.settings.UnidenR4Brightness === 'dimmer'}">Dimmer</option>
              <option value="dark" :selected="${() => state.settings.UnidenR4Brightness === 'dark'}">Dark</option>
              <option value="off" :selected="${() => state.settings.UnidenR4Brightness === 'off'}">Off</option>
            </select>
          </div>

          <div class="uniden-setting-row">
            <div class="uniden-setting-info">
              <span class="uniden-setting-label">Mute Memory</span>
              <span class="uniden-setting-desc">Auto-lockout known stationary false alerts via GPS</span>
            </div>
            <label class="uniden-switch">
              <input type="checkbox" 
                     checked="${() => !!state.settings.UnidenR4MuteMemory}" 
                     @change="${(e) => { const el = e && (e.currentTarget || e.target); if (el) updateSetting('UnidenR4MuteMemory', el.checked); }}" />
              <span class="uniden-slider"></span>
            </label>
          </div>
        </div>
      </div>
    </div>
  `
}
