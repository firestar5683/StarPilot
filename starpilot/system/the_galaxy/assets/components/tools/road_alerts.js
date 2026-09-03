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
    WazePoliceSlowdownDist: 0.0,
    RoadAlertShowPolice: true,
    RoadAlertShowMajorAccidents: true,
    RoadAlertShowMinorAccidents: true,
    RoadAlertShowDebris: true,
    RoadAlertShowClosures: true,
    RoadAlertShowWeather: true,
    RoadAlertSlowdownMajorAccidents: true,
    RoadAlertSlowdownMinorAccidents: false,
    RoadAlertSlowdownDebris: true,
    RoadAlertSlowdownClosures: true,
    RoadAlertSlowdownWeather: false,
    WazeSessionId: "",
    WazeSecretKey: "",
    WazeAuthStatus: "Idle"
  },
  showSessionGrabber: false,
  grabberRawInput: "",
  lastUpdated: ""
})

let loadedOnce = false

function notify(msg, level) {
  if (typeof window.showSnackbar === "function") {
    window.showSnackbar(msg, level)
  } else {
    console.log("[Snackbar]", level || "info", msg)
  }
}

async function loadData() {
  try {
    const res = await fetch("/api/road_alerts/live", { cache: "no-store" })
    if (res.ok) {
      const data = await res.json()
      state.alerts = data.alerts || []
      state.activeThreat = data.active_threat || null
      state.totalCount = data.total_count || 0
      state.gps = data.gps || { lat: 0, lon: 0, bearing: 0 }
      if (data.settings) {
        for (const [k, v] of Object.entries(data.settings)) {
          state.settings[k] = v
        }
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
    const res = await fetch("/api/road_alerts/settings", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ [key]: val, key, value: val })
    })
    if (res.ok) {
      await loadData()
      notify(`Updated ${key}`)
    }
  } catch (err) {
    notify("Failed to update setting", "error")
  }
}

async function triggerAction(action, payload = {}) {
  try {
    const res = await fetch(`/api/road_alerts/action/${action}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    })
    const data = await res.json()
    if (res.ok && data.status === "ok") {
      notify(data.message || "Action successful", "success")
      await loadData()
    } else {
      notify(data.message || data.error || "Action failed", "error")
    }
  } catch (err) {
    notify("Request failed", "error")
  }
}

function openWazeLogin() {
  window.open("https://www.waze.com/live-map", "_blank", "width=850,height=750")
  state.showSessionGrabber = true
}

function parseAndSaveSessionString() {
  const raw = state.grabberRawInput.trim()
  if (!raw) {
    notify("Please paste your Waze cookie or session string", "error")
    return
  }

  let sessionId = ""
  let secretKey = ""

  // Case 1: JSON format
  if (raw.startsWith("{") && raw.endsWith("}")) {
    try {
      const obj = JSON.parse(raw)
      sessionId = obj.sessionId || obj.session_id || obj._waze_session || obj.session || ""
      secretKey = obj.secretKey || obj.secret_key || obj._csrf_token || obj.secret || ""
    } catch (e) {}
  }

  // Case 2: Cookie Header format (e.g. "_waze_session=abc123; secret=xyz456")
  if (!sessionId) {
    const sessionMatch = raw.match(/_?waze_session=([^;]+)/i) || raw.match(/session_?id=([^;]+)/i)
    if (sessionMatch) sessionId = sessionMatch[1].trim()
  }

  if (!secretKey) {
    const secretMatch = raw.match(/secret(_key)?=([^;]+)/i) || raw.match(/csrf_?token=([^;]+)/i)
    if (secretMatch) secretKey = secretMatch[1].trim()
  }

  // Case 3: Raw single token
  if (!sessionId && !raw.includes("=") && !raw.includes(";")) {
    sessionId = raw
  }

  if (sessionId) {
    updateSetting("WazeSessionId", sessionId)
    if (secretKey) updateSetting("WazeSecretKey", secretKey)
    updateSetting("WazeAuthStatus", "User Account Linked")
    notify("Successfully imported Waze User Account Session!", "success")
    state.showSessionGrabber = false
    state.grabberRawInput = ""
  } else {
    notify("Could not find a valid _waze_session token in pasted text", "error")
  }
}

let pollInterval = null

export function RoadAlerts() {
  if (!pollInterval) {
    loadData()
    pollInterval = setInterval(loadData, 3000)
  }

  return html`
    <link rel="stylesheet" href="/assets/components/tools/road_alerts.css">

    <style>
      details.road-card summary.road-card-title {
        cursor: pointer;
        user-select: none;
        list-style: none;
        display: flex;
        justify-content: space-between;
        align-items: center;
        transition: color 0.15s ease;
        margin-bottom: 0;
        padding-bottom: 6px;
      }
      details.road-card summary::-webkit-details-marker {
        display: none;
      }
      details.road-card[open] summary.road-card-title {
        border-bottom: 1px solid #2d2d38;
        margin-bottom: 16px;
        padding-bottom: 10px;
      }
      details.road-card summary .toggle-arrow {
        transition: transform 0.2s ease;
        font-size: 1rem;
        color: #8f92a1;
      }
      details.road-card[open] summary .toggle-arrow {
        transform: rotate(180deg);
        color: #fff;
      }
      .card-content-wrapper {
        margin-top: 10px;
      }
    </style>

    <div class="road-container">
      <!-- 1. Header -->
      <div class="road-header">
        <div class="road-header-title">
          <h1><i class="bi bi-shield-exclamation text-danger"></i> Live Road Alerts & Police Radar</h1>
          <p>Real-time Sabre, CHP Statewide Incident stream & Waze Police Speed Traps</p>
        </div>
        <div class="road-header-actions">
          <button class="btn btn-sm btn-outline-secondary" @click="${loadData}">
            <i class="bi bi-arrow-clockwise"></i> Refresh
          </button>
        </div>
      </div>

      <!-- 2. Active Closest Threat Banner (Strictly matching C3X popup) -->
      ${() => state.activeThreat ? html`
        <div class="active-threat-card ${() => (state.activeThreat.category || '').toLowerCase()}">
          <div class="threat-icon">${() => state.activeThreat.icon || '⚠️'}</div>
          <div class="threat-details">
            <div class="threat-title-row">
              <span class="threat-label">${() => state.activeThreat.label}</span>
              <span class="threat-distance">${() => state.activeThreat.is_radar ? 'LIVE DETECTION' : (state.activeThreat.distance_miles + ' mi ahead')}</span>
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

      <!-- 3. Waze Session & Token Management (Collapsible, collapsed by default) -->
      <details class="road-card">
        <summary class="road-card-title">
          <span><i class="bi bi-person-badge text-info"></i> Waze Session & Token Management</span>
          <i class="bi bi-chevron-down toggle-arrow"></i>
        </summary>
        
        <div class="card-content-wrapper">
          <div class="road-setting-row">
            <div class="road-setting-info">
              <span class="road-setting-label">Authentication Status</span>
              <span class="road-setting-desc">${() => state.settings.WazeAuthStatus || 'Idle'}</span>
            </div>
            <div class="d-flex gap-2">
              <button class="btn btn-sm btn-outline-info" @click="${(e) => { e.preventDefault(); e.stopPropagation(); openWazeLogin(); }}">
                <i class="bi bi-box-arrow-up-right"></i> Link Real Account
              </button>
              <button class="btn btn-sm btn-primary" @click="${(e) => { e.preventDefault(); e.stopPropagation(); triggerAction('waze_register'); }}">
                <i class="bi bi-arrow-repeat"></i> Re-Register Guest
              </button>
            </div>
          </div>

          ${() => state.showSessionGrabber ? html`
            <div class="p-3 my-2 rounded bg-dark border border-info">
              <h6 class="text-info mb-2"><i class="bi bi-magic"></i> Browser Session Grabber:</h6>
              <p class="small text-muted mb-2">
                1. A new window opened to <strong>waze.com/live-map</strong> (sign in with your Google/Waze account if prompted).<br>
                2. Open browser Console (F12) and type <code>document.cookie</code>, or paste your Cookie string below:
              </p>
              <div class="d-flex gap-2">
                <input type="text" class="form-control form-control-sm bg-black text-light border-secondary"
                       placeholder="Paste document.cookie or _waze_session=..."
                       value="${() => state.grabberRawInput}"
                       @input="${(e) => { state.grabberRawInput = (e.target || e.currentTarget).value; }}" />
                <button class="btn btn-sm btn-success text-nowrap" @click="${parseAndSaveSessionString}">
                  <i class="bi bi-check-lg"></i> Import Session
                </button>
                <button class="btn btn-sm btn-outline-secondary" @click="${() => { state.showSessionGrabber = false; }}">
                  Cancel
                </button>
              </div>
            </div>
          ` : ''}

          <div class="road-setting-row">
            <div class="road-setting-info">
              <span class="road-setting-label">Waze Session ID</span>
              <span class="road-setting-desc">Active session token (_waze_session cookie or device token)</span>
            </div>
            <input type="text" class="form-control form-control-sm w-50 bg-dark text-light border-secondary"
                   value="${() => state.settings.WazeSessionId || ''}"
                   placeholder="e.g. 123456789"
                   @change="${(e) => { const el = e && (e.currentTarget || e.target); if (el) updateSetting('WazeSessionId', el.value); }}" />
          </div>

          <div class="road-setting-row">
            <div class="road-setting-info">
              <span class="road-setting-label">Waze Secret Key</span>
              <span class="road-setting-desc">Associated session cryptographic secret key</span>
            </div>
            <input type="text" class="form-control form-control-sm w-50 bg-dark text-light border-secondary"
                   value="${() => state.settings.WazeSecretKey || ''}"
                   placeholder="e.g. 987654321"
                   @change="${(e) => { const el = e && (e.currentTarget || e.target); if (el) updateSetting('WazeSecretKey', el.value); }}" />
          </div>
        </div>
      </details>

      <!-- 4. Unified Road Alert & Police Auto-Slowdown (Collapsible, collapsed by default) -->
      <details class="road-card">
        <summary class="road-card-title">
          <span><i class="bi bi-speedometer2 text-danger"></i> Road Alert & Police Auto-Slowdown</span>
          <i class="bi bi-chevron-down toggle-arrow"></i>
        </summary>

        <div class="card-content-wrapper">
          <p class="text-muted small mb-3">Automatically drop vehicle cruise target down to the posted road speed limit when approaching verified hazards or police traps:</p>

          <!-- 1. Minimum Confirmations (Global for crowd-sourced Waze reports) -->
          <div class="road-setting-row">
            <div class="road-setting-info">
              <span class="road-setting-label">Minimum Confirmations</span>
              <span class="road-setting-desc">Minimum driver thumbs-up reports required for crowd-sourced Waze slowdown alerts</span>
            </div>
            <select class="road-select" 
                    value="${() => String(Number(state.settings.WazePoliceMinConfirmations || 3))}"
                    @change="${(e) => { const el = e && (e.currentTarget || e.target); if (el) updateSetting('WazePoliceMinConfirmations', parseInt(el.value, 10)); }}">
              <option value="1" selected="${() => Number(state.settings.WazePoliceMinConfirmations) === 1}">1+ Report (Most Sensitive)</option>
              <option value="2" selected="${() => Number(state.settings.WazePoliceMinConfirmations) === 2}">2+ Reports</option>
              <option value="3" selected="${() => Number(state.settings.WazePoliceMinConfirmations) === 3}">3+ Reports (Recommended)</option>
              <option value="5" selected="${() => Number(state.settings.WazePoliceMinConfirmations) === 5}">5+ Reports (High Confidence)</option>
              <option value="10" selected="${() => Number(state.settings.WazePoliceMinConfirmations) === 10}">10+ Reports (Verified Only)</option>
            </select>
          </div>

          <!-- 2. Trigger Distance (Global for all slowdown alerts) -->
          <div class="road-setting-row">
            <div class="road-setting-info">
              <span class="road-setting-label">Trigger Distance</span>
              <span class="road-setting-desc">Distance ahead to begin slowing down to road speed limit for upcoming alerts</span>
            </div>
            <select class="road-select" 
                    value="${() => String(Number(state.settings.WazePoliceTriggerDistance || 1))}"
                    @change="${(e) => { const el = e && (e.currentTarget || e.target); if (el) updateSetting('WazePoliceTriggerDistance', parseFloat(el.value)); }}">
              <option value="0.5" selected="${() => Number(state.settings.WazePoliceTriggerDistance) === 0.5}">0.5 Miles</option>
              <option value="0.75" selected="${() => Number(state.settings.WazePoliceTriggerDistance) === 0.75}">0.75 Miles</option>
              <option value="1" selected="${() => Number(state.settings.WazePoliceTriggerDistance) === 1 || Number(state.settings.WazePoliceTriggerDistance) === 1.0}">1.0 Mile (Recommended)</option>
              <option value="1.5" selected="${() => Number(state.settings.WazePoliceTriggerDistance) === 1.5}">1.5 Miles</option>
              <option value="2" selected="${() => Number(state.settings.WazePoliceTriggerDistance) === 2 || Number(state.settings.WazePoliceTriggerDistance) === 2.0}">2.0 Miles</option>
            </select>
          </div>

          <!-- 3. Slowdown for Police Ahead -->
          <div class="road-setting-row">
            <div class="road-setting-info">
              <span class="road-setting-label">🚨 Slowdown for Police Ahead</span>
              <span class="road-setting-desc">Automatically drop cruise speed to posted speed limit when approaching verified police traps</span>
            </div>
            <label class="road-switch">
              <input type="checkbox" 
                     checked="${() => !!state.settings.WazePoliceAutoSlowdown}" 
                     @change="${(e) => { const el = e && (e.currentTarget || e.target); if (el) updateSetting('WazePoliceAutoSlowdown', el.checked); }}" />
              <span class="road-slider"></span>
            </label>
          </div>

          <!-- 4. Road Hazard Category Slowdowns -->
          <div class="road-setting-row">
            <div class="road-setting-info">
              <span class="road-setting-label">💥 Slowdown for Major Accidents</span>
              <span class="road-setting-desc">Drop to road speed limit when within trigger distance of major injury collisions / SigAlerts</span>
            </div>
            <label class="road-switch">
              <input type="checkbox" 
                     checked="${() => !!state.settings.RoadAlertSlowdownMajorAccidents}" 
                     @change="${(e) => { const el = e && (e.currentTarget || e.target); if (el) updateSetting('RoadAlertSlowdownMajorAccidents', el.checked); }}" />
              <span class="road-slider"></span>
            </label>
          </div>

          <div class="road-setting-row">
            <div class="road-setting-info">
              <span class="road-setting-label">🚗 Slowdown for Minor Accidents</span>
              <span class="road-setting-desc">Drop to road speed limit when within trigger distance of minor collisions</span>
            </div>
            <label class="road-switch">
              <input type="checkbox" 
                     checked="${() => !!state.settings.RoadAlertSlowdownMinorAccidents}" 
                     @change="${(e) => { const el = e && (e.currentTarget || e.target); if (el) updateSetting('RoadAlertSlowdownMinorAccidents', el.checked); }}" />
              <span class="road-slider"></span>
            </label>
          </div>

          <div class="road-setting-row">
            <div class="road-setting-info">
              <span class="road-setting-label">⚠️ Slowdown for Debris & Road Hazards</span>
              <span class="road-setting-desc">Drop to road speed limit when within trigger distance of debris in lane, stalled vehicles, or vehicle fires</span>
            </div>
            <label class="road-switch">
              <input type="checkbox" 
                     checked="${() => !!state.settings.RoadAlertSlowdownDebris}" 
                     @change="${(e) => { const el = e && (e.currentTarget || e.target); if (el) updateSetting('RoadAlertSlowdownDebris', el.checked); }}" />
              <span class="road-slider"></span>
            </label>
          </div>

          <div class="road-setting-row">
            <div class="road-setting-info">
              <span class="road-setting-label">⛔ Slowdown for Road & Lane Closures</span>
              <span class="road-setting-desc">Drop to road speed limit when within trigger distance of active Caltrans lane/ramp closures</span>
            </div>
            <label class="road-switch">
              <input type="checkbox" 
                     checked="${() => !!state.settings.RoadAlertSlowdownClosures}" 
                     @change="${(e) => { const el = e && (e.currentTarget || e.target); if (el) updateSetting('RoadAlertSlowdownClosures', el.checked); }}" />
              <span class="road-slider"></span>
            </label>
          </div>

          <div class="road-setting-row">
            <div class="road-setting-info">
              <span class="road-setting-label">🌧️ Slowdown for Severe Weather</span>
              <span class="road-setting-desc">Drop to road speed limit when within trigger distance of fog/snow/ice/flooding warnings</span>
            </div>
            <label class="road-switch">
              <input type="checkbox" 
                     checked="${() => !!state.settings.RoadAlertSlowdownWeather}" 
                     @change="${(e) => { const el = e && (e.currentTarget || e.target); if (el) updateSetting('RoadAlertSlowdownWeather', el.checked); }}" />
              <span class="road-slider"></span>
            </label>
          </div>
        </div>
      </details>

      <!-- 5. Incident Category Display Filters (Collapsible, collapsed by default) -->
      <details class="road-card">
        <summary class="road-card-title">
          <span><i class="bi bi-funnel-fill text-warning"></i> Incident Category Display Filters</span>
          <i class="bi bi-chevron-down toggle-arrow"></i>
        </summary>
        
        <div class="card-content-wrapper">
          <div class="road-setting-row">
            <div class="road-setting-info">
              <span class="road-setting-label">🚨 Police Reports & Traps</span>
              <span class="road-setting-desc">Show Waze police speed traps & CHP highway officers in feed & UI</span>
            </div>
            <label class="road-switch">
              <input type="checkbox" 
                     checked="${() => !!state.settings.RoadAlertShowPolice}" 
                     @change="${(e) => { const el = e && (e.currentTarget || e.target); if (el) updateSetting('RoadAlertShowPolice', el.checked); }}" />
              <span class="road-slider"></span>
            </label>
          </div>

          <div class="road-setting-row">
            <div class="road-setting-info">
              <span class="road-setting-label">💥 Major Collisions & SigAlerts</span>
              <span class="road-setting-desc">Show fatal, injury collisions, and ambulance dispatches</span>
            </div>
            <label class="road-switch">
              <input type="checkbox" 
                     checked="${() => !!state.settings.RoadAlertShowMajorAccidents}" 
                     @change="${(e) => { const el = e && (e.currentTarget || e.target); if (el) updateSetting('RoadAlertShowMajorAccidents', el.checked); }}" />
              <span class="road-slider"></span>
            </label>
          </div>

          <div class="road-setting-row">
            <div class="road-setting-info">
              <span class="road-setting-label">🚗 Minor Collisions & Fender Benders</span>
              <span class="road-setting-desc">Show property damage only collisions & minor hit-and-runs</span>
            </div>
            <label class="road-switch">
              <input type="checkbox" 
                     checked="${() => !!state.settings.RoadAlertShowMinorAccidents}" 
                     @change="${(e) => { const el = e && (e.currentTarget || e.target); if (el) updateSetting('RoadAlertShowMinorAccidents', el.checked); }}" />
              <span class="road-slider"></span>
            </label>
          </div>

          <div class="road-setting-row">
            <div class="road-setting-info">
              <span class="road-setting-label">⚠️ Debris & Road Hazards</span>
              <span class="road-setting-desc">Show objects in lane, stalled vehicles, tires, vehicle fires</span>
            </div>
            <label class="road-switch">
              <input type="checkbox" 
                     checked="${() => !!state.settings.RoadAlertShowDebris}" 
                     @change="${(e) => { const el = e && (e.currentTarget || e.target); if (el) updateSetting('RoadAlertShowDebris', el.checked); }}" />
              <span class="road-slider"></span>
            </label>
          </div>

          <div class="road-setting-row">
            <div class="road-setting-info">
              <span class="road-setting-label">⛔ Road & Lane Closures</span>
              <span class="road-setting-desc">Show Caltrans active closures, ramp blocks, traffic advisories</span>
            </div>
            <label class="road-switch">
              <input type="checkbox" 
                     checked="${() => !!state.settings.RoadAlertShowClosures}" 
                     @change="${(e) => { const el = e && (e.currentTarget || e.target); if (el) updateSetting('RoadAlertShowClosures', el.checked); }}" />
              <span class="road-slider"></span>
            </label>
          </div>

          <div class="road-setting-row">
            <div class="road-setting-info">
              <span class="road-setting-label">🌧️ Weather Hazards</span>
              <span class="road-setting-desc">Show high winds, dense fog, snow/ice, flooding</span>
            </div>
            <label class="road-switch">
              <input type="checkbox" 
                     checked="${() => !!state.settings.RoadAlertShowWeather}" 
                     @change="${(e) => { const el = e && (e.currentTarget || e.target); if (el) updateSetting('RoadAlertShowWeather', el.checked); }}" />
              <span class="road-slider"></span>
            </label>
          </div>
        </div>
      </details>

      <!-- 6. Feed List (Active Incidents Along Route) At The Bottom -->
      <div class="alerts-list-card mb-4">
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

export const RoadAlertsView = RoadAlerts;
