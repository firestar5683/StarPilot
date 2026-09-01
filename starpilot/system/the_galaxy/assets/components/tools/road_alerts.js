import { html, reactive } from "/assets/vendor/arrow-core.js"

const state = reactive({
  loading: true,
  alerts: [],
  activeThreat: null,
  totalCount: 0,
  gps: { lat: 0, lon: 0, bearing: 0 },
  settings: {
    WazePoliceAutoSlowdown: true,
    WazePoliceMinConfirmations: 3,
    WazePoliceTriggerDistance: 1.0,
    WazePoliceSlowdownActive: false,
    WazePoliceSlowdownDist: 0.0
  },
  lastUpdated: ""
})

let timer = null

async function loadData() {
  try {
    const res = await fetch("/api/road_alerts/live")
    if (res.ok) {
      const data = await res.json()
      state.alerts = data.alerts || []
      state.activeThreat = data.active_threat || null
      state.totalCount = data.total_count || 0
      state.gps = data.gps || { lat: 0, lon: 0, bearing: 0 }
      if (data.settings) {
        state.settings = { ...state.settings, ...data.settings }
      }
      state.lastUpdated = new Date().toLocaleTimeString()
    }
  } catch (err) {
    console.error("Failed to load road alerts:", err)
  } finally {
    state.loading = false
  }
}

async function updateSetting(key, val) {
  state.settings[key] = val
  try {
    await fetch("/api/road_alerts/settings", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ key, value: val })
    })
  } catch (err) {
    console.error("Failed to update setting:", err)
  }
}

export function RoadAlertsView() {
  if (!timer) {
    loadData()
    timer = setInterval(loadData, 5000)
  }

  return html`
    <div class="road-alerts-container">
      <div class="road-alerts-header">
        <div>
          <h1><i class="bi bi-shield-exclamation text-warning"></i> Live Road Alerts & Hazards</h1>
          <p class="text-muted">Real-time Waze crowd reports & California Highway Patrol (CHP) dispatch forward-correlated with your vehicle route</p>
        </div>
        <div class="road-alerts-meta">
          <button class="btn btn-sm btn-outline-secondary" @click="${loadData}">
            <i class="bi bi-arrow-clockwise"></i> Refresh (${() => state.lastUpdated})
          </button>
        </div>
      </div>

      <!-- Active Closest Threat Banner -->
      ${() => state.activeThreat ? html`
        <div class="active-threat-card ${() => state.activeThreat.category.toLowerCase()}">
          <div class="threat-icon">${() => state.activeThreat.icon}</div>
          <div class="threat-details">
            <div class="threat-title-row">
              <span class="threat-label">${() => state.activeThreat.label}</span>
              <span class="threat-distance">${() => state.activeThreat.distance_miles} mi ahead</span>
            </div>
            <div class="threat-location">
              <i class="bi bi-geo-alt-fill"></i> ${() => state.activeThreat.location} 
              <span class="badge bg-secondary ms-2">${() => state.activeThreat.source || 'Alert'}</span>
            </div>
            ${() => state.activeThreat.detail ? html`<div class="threat-desc">${() => state.activeThreat.detail}</div>` : ''}
          </div>
        </div>
      ` : html`
        <div class="no-threat-banner">
          <i class="bi bi-shield-check text-success"></i> Route Clear — No immediate hazards or police traps detected ahead
        </div>
      `}

      <!-- Waze Police Auto-Slowdown Settings Card -->
      <div class="uniden-card mb-4">
        <h2 class="uniden-card-title"><i class="bi bi-shield-shaded text-primary"></i> Waze Police Auto-Slowdown</h2>
        
        <div class="uniden-setting-row">
          <div class="uniden-setting-info">
            <span class="uniden-setting-label">Auto-Slowdown on Waze Police Ahead</span>
            <span class="uniden-setting-desc">Automatically drop cruise speed to posted speed limit when approaching verified police</span>
          </div>
          <label class="uniden-switch">
            <input type="checkbox" 
                   :checked="${() => state.settings.WazePoliceAutoSlowdown}" 
                   @change="${(e) => e && e.target && updateSetting('WazePoliceAutoSlowdown', e.target.checked)}" />
            <span class="uniden-slider"></span>
          </label>
        </div>

        <div class="uniden-setting-row">
          <div class="uniden-setting-info">
            <span class="uniden-setting-label">Minimum Confirmations</span>
            <span class="uniden-setting-desc">Minimum driver thumbs-up reports required to trigger auto-slowdown</span>
          </div>
          <select class="uniden-select" 
                  @change="${(e) => e && e.target && updateSetting('WazePoliceMinConfirmations', parseInt(e.target.value))}">
            <option value="1" :selected="${() => state.settings.WazePoliceMinConfirmations === 1}">1+ Report (Most Sensitive)</option>
            <option value="2" :selected="${() => state.settings.WazePoliceMinConfirmations === 2}">2+ Reports</option>
            <option value="3" :selected="${() => state.settings.WazePoliceMinConfirmations === 3}">3+ Reports (Recommended)</option>
            <option value="5" :selected="${() => state.settings.WazePoliceMinConfirmations === 5}">5+ Reports (High Confidence)</option>
            <option value="10" :selected="${() => state.settings.WazePoliceMinConfirmations === 10}">10+ Reports (Verified Only)</option>
          </select>
        </div>

        <div class="uniden-setting-row">
          <div class="uniden-setting-info">
            <span class="uniden-setting-label">Trigger Distance</span>
            <span class="uniden-setting-desc">Distance ahead to begin slowing down to road speed limit</span>
          </div>
          <select class="uniden-select" 
                  @change="${(e) => e && e.target && updateSetting('WazePoliceTriggerDistance', parseFloat(e.target.value))}">
            <option value="0.5" :selected="${() => state.settings.WazePoliceTriggerDistance === 0.5}">0.5 Miles</option>
            <option value="0.75" :selected="${() => state.settings.WazePoliceTriggerDistance === 0.75}">0.75 Miles</option>
            <option value="1.0" :selected="${() => state.settings.WazePoliceTriggerDistance === 1.0}">1.0 Mile (Recommended)</option>
            <option value="1.5" :selected="${() => state.settings.WazePoliceTriggerDistance === 1.5}">1.5 Miles</option>
            <option value="2.0" :selected="${() => state.settings.WazePoliceTriggerDistance === 2.0}">2.0 Miles</option>
          </select>
        </div>
      </div>

      <!-- Feed List -->
      <div class="alerts-list-card">
        <div class="alerts-list-header">
          <h2><i class="bi bi-broadcast-pin"></i> Active Incidents Along Route (${() => state.alerts.length})</h2>
        </div>
        <div class="alerts-list">
          ${() => state.loading ? html`<div class="p-4 text-center"><i class="spinner-border spinner-border-sm"></i> Loading incidents...</div>` : ''}
          ${() => !state.loading && state.alerts.length === 0 ? html`
            <div class="p-4 text-center text-muted">No active incidents detected within 15 miles forward cone.</div>
          ` : ''}
          ${() => state.alerts.map(a => html`
            <div class="alert-item ${a.category.toLowerCase()}">
              <div class="alert-item-icon">${a.icon}</div>
              <div class="alert-item-body">
                <div class="alert-item-header">
                  <span class="alert-item-type">${a.label} (${a.type})</span>
                  <span class="alert-item-dist">${a.distance_miles} mi</span>
                </div>
                <div class="alert-item-loc">
                  ${a.location} 
                  <span class="badge ${a.source === 'Waze' ? 'bg-primary' : 'bg-dark'}">${a.source || a.area}</span>
                </div>
                ${a.detail ? html`<div class="alert-item-detail">${a.detail}</div>` : ''}
                <div class="alert-item-time"><i class="bi bi-clock"></i> Reported: ${a.time}</div>
              </div>
            </div>
          `)}
        </div>
      </div>
    </div>
  `
}
