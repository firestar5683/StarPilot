import { html, reactive } from "/assets/vendor/arrow-core.js"

const state = reactive({
  loading: true,
  alerts: [],
  activeThreat: null,
  totalCount: 0,
  gps: { lat: 0, lon: 0, bearing: 0 },
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
      state.lastUpdated = new Date().toLocaleTimeString()
    }
  } catch (err) {
    console.error("Failed to load road alerts:", err)
  } finally {
    state.loading = false
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
          <p class="text-muted">Real-time California Highway Patrol (CHP) & Caltrans road hazards forward-correlated with your vehicle route</p>
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
            <div class="threat-location"><i class="bi bi-geo-alt-fill"></i> ${() => state.activeThreat.location} (${() => state.activeThreat.area})</div>
            ${() => state.activeThreat.detail ? html`<div class="threat-desc">${() => state.activeThreat.detail}</div>` : ''}
          </div>
        </div>
      ` : html`
        <div class="no-threat-banner">
          <i class="bi bi-shield-check text-success"></i> Route Clear — No immediate hazards or road closures ahead
        </div>
      `}

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
                <div class="alert-item-loc">${a.location} <span class="badge bg-dark">${a.area}</span></div>
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
