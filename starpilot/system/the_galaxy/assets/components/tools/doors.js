import { html, reactive } from "/assets/vendor/arrow-core.js"

const state = reactive({
  loading: true,
  lockDoors: false,
  unlockDoors: false,
  lockDoorsTimer: 0,
  lockBusy: false,
  unlockBusy: false,
})

let settingsLoaded = false

async function loadDoorSettings() {
  try {
    const res = await fetch("/api/doors/settings")
    if (res.ok) {
      const data = await res.json()
      state.lockDoors = !!data.lockDoors
      state.unlockDoors = !!data.unlockDoors
      state.lockDoorsTimer = Number(data.lockDoorsTimer) || 0
    }
  } catch (err) {
    console.error("Failed to load door settings:", err)
  } finally {
    state.loading = false
  }
}

async function updateSetting(key, val) {
  try {
    const payload = { [key]: val }
    const res = await fetch("/api/doors/settings", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    })
    if (res.ok) {
      const data = await res.json()
      state.lockDoors = !!data.lockDoors
      state.unlockDoors = !!data.unlockDoors
      state.lockDoorsTimer = Number(data.lockDoorsTimer) || 0
      showSnackbar("Door setting updated")
    }
  } catch (err) {
    console.error("Failed to update door setting:", err)
    showSnackbar("Failed to update setting")
  }
}

export function DoorControl () {
  if (!settingsLoaded) {
    settingsLoaded = true
    loadDoorSettings()
  }

  async function lockDoors () {
    if (state.lockBusy) return
    state.lockBusy = true
    try {
      const response = await fetch("/api/doors/lock", { method: "POST" })
      const result = await response.json()
      showSnackbar(result.message || "Doors locked!")
    } catch (e) {
      showSnackbar("Failed to lock doors")
    } finally {
      state.lockBusy = false
    }
  }

  async function unlockDoors () {
    if (state.unlockBusy) return
    state.unlockBusy = true
    try {
      const response = await fetch("/api/doors/unlock", { method: "POST" })
      const result = await response.json()
      showSnackbar(result.message || "Doors unlocked!")
    } catch (e) {
      showSnackbar("Failed to unlock doors")
    } finally {
      state.unlockBusy = false
    }
  }

  return html`
    <div class="door-control-wrapper">
      <section class="door-control-widget">
        <div class="door-control-title">Lock & Unlock Doors</div>
        <p class="door-control-text">
          Remotely control your vehicle door locks or configure automated drive & park locking behaviors.
        </p>

        <div class="door-buttons-grid">
          <button class="door-control-button" @click="${lockDoors}" :disabled="${() => state.lockBusy}">
            ${() => state.lockBusy ? "🔒 Locking..." : "🔒 Lock Doors"}
          </button>
          <button class="door-control-button" @click="${unlockDoors}" :disabled="${() => state.unlockBusy}">
            ${() => state.unlockBusy ? "🔓 Unlocking..." : "🔓 Unlock Doors"}
          </button>
        </div>

        <div class="door-divider"></div>

        <div class="door-settings-title">Automatic Door Controls</div>

        <div class="door-setting-row">
          <div class="door-setting-info">
            <div class="door-setting-label">Auto Lock on Drive</div>
            <div class="door-setting-desc">Automatically lock doors when shifting out of Park</div>
          </div>
          <label class="door-switch">
            <input type="checkbox" :checked="${() => state.lockDoors}" @change="${(e) => updateSetting("lockDoors", e.target.checked)}" />
            <span class="door-slider"></span>
          </label>
        </div>

        <div class="door-setting-row">
          <div class="door-setting-info">
            <div class="door-setting-label">Auto Unlock in Park</div>
            <div class="door-setting-desc">Automatically unlock doors when shifting into Park</div>
          </div>
          <label class="door-switch">
            <input type="checkbox" :checked="${() => state.unlockDoors}" @change="${(e) => updateSetting("unlockDoors", e.target.checked)}" />
            <span class="door-slider"></span>
          </label>
        </div>

        <div class="door-setting-row">
          <div class="door-setting-info">
            <div class="door-setting-label">Walk-Away Lock Timer</div>
            <div class="door-setting-desc">Auto-lock after parking and driver leaves vehicle</div>
          </div>
          <select class="door-select" :value="${() => String(state.lockDoorsTimer)}" @change="${(e) => updateSetting("lockDoorsTimer", Number(e.target.value))}">
            <option value="0">Disabled (Never)</option>
            <option value="15">15 seconds</option>
            <option value="30">30 seconds</option>
            <option value="60">60 seconds</option>
            <option value="120">2 minutes</option>
            <option value="300">5 minutes</option>
          </select>
        </div>
      </section>
    </div>
  `
}
