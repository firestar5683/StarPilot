import { html, reactive } from "/assets/vendor/arrow-core.js"
import { Modal } from "/assets/components/modal.js"
import { TailscaleControl } from "/assets/components/tailscale/tailscale.js?v=telemetry-setup-3"

const FACTORY_RESET_STATUS_POLL_INTERVAL_MS = 1000

const state = reactive({
  showResetDefaultModal: false,
  showSaveMeModal: false,
  factoryResetBusy: false,
  factoryResetStatus: null,
})

let initialized = false
let fileInput = null
let factoryResetPollHandle = null

function isToggleRouteActive() {
  return window.location.pathname === "/manage_toggles"
}

function isFactoryResetStatusRelevant(payload) {
  return String(payload?.lastMode || "").trim() === "factory-reset"
}

function toPercent(value) {
  const n = Number(value)
  if (!Number.isFinite(n)) return 0
  return Math.max(0, Math.min(100, n))
}

function shouldContinueFactoryResetPolling() {
  return !!state.factoryResetStatus && (
    !!state.factoryResetStatus.running
    || state.factoryResetStatus.stage === "factory-resetting"
    || state.factoryResetStatus.stage === "rebooting"
    || state.factoryResetStatus.stage === "starting"
  )
}

function stopFactoryResetPolling() {
  if (!factoryResetPollHandle) return
  clearTimeout(factoryResetPollHandle)
  factoryResetPollHandle = null
}

function ensureFactoryResetPolling() {
  if (factoryResetPollHandle) return

  const poll = async () => {
    if (!isToggleRouteActive()) {
      factoryResetPollHandle = null
      return
    }

    await fetchFactoryResetStatus()
    if (shouldContinueFactoryResetPolling()) {
      factoryResetPollHandle = setTimeout(poll, FACTORY_RESET_STATUS_POLL_INTERVAL_MS)
    } else {
      factoryResetPollHandle = null
    }
  }

  factoryResetPollHandle = setTimeout(poll, FACTORY_RESET_STATUS_POLL_INTERVAL_MS)
}

async function fetchFactoryResetStatus() {
  try {
    const response = await fetch("/api/update/fast/status")
    const payload = await response.json()
    if (!response.ok) {
      throw new Error(payload.error || response.statusText || "Failed to load factory reset status")
    }

    state.factoryResetStatus = isFactoryResetStatusRelevant(payload) ? {
      running: !!payload.running,
      stage: String(payload.stage || "idle"),
      message: String(payload.message || ""),
      lastError: String(payload.lastError || ""),
      progressLabel: String(payload.progressLabel || ""),
      progressDetail: String(payload.progressDetail || ""),
      progressPercent: toPercent(payload.progressPercent),
      progressStep: Number(payload.progressStep || 0),
      progressTotalSteps: Number(payload.progressTotalSteps || 5),
    } : null
  } catch (error) {
    if (!shouldContinueFactoryResetPolling()) {
      state.factoryResetStatus = null
    }
  } finally {
    if (shouldContinueFactoryResetPolling()) {
      ensureFactoryResetPolling()
    } else {
      stopFactoryResetPolling()
    }
  }
}

async function restoreToggles(event) {
  const uploadedFile = event.target.files[0]
  if (!uploadedFile) return

  try {
    if (uploadedFile.size > 5_000_000) {
      throw new Error("That toggle backup file is too large.")
    }

    const fileContents = await uploadedFile.text()
    const toggleData = JSON.parse(fileContents)
    if (!toggleData || typeof toggleData !== "object" || Array.isArray(toggleData)) {
      throw new Error("That file is not a valid toggle backup.")
    }

    const response = await fetch("/api/toggles/restore", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(toggleData),
    })

    const result = await response.json().catch(() => ({}))
    if (!response.ok || result.success === false) {
      throw new Error(result.message || "Failed to restore toggles.")
    }
    showSnackbar(result.message || "Toggles restored!")
  } catch (error) {
    const message = error instanceof SyntaxError
      ? "That file is not a valid toggle backup."
      : (error?.message || "Failed to restore toggles.")
    showSnackbar(message, "error")
  } finally {
    event.target.value = ""
  }
}

function initializeFileInput() {
  if (fileInput) return

  fileInput = document.createElement("input")
  fileInput.type = "file"
  fileInput.accept = ".json"
  fileInput.style.display = "none"
  fileInput.addEventListener("change", restoreToggles)
  document.body.appendChild(fileInput)
}

function initialize() {
  if (initialized) return
  initialized = true

  initializeFileInput()
}

export function ToggleControl() {
  initialize()
  fetchFactoryResetStatus()

  async function backupToggles() {
    try {
      const response = await fetch("/api/toggles/backup", { method: "POST" })
      if (!response.ok) {
        const result = await response.json().catch(() => ({}))
        throw new Error(result.message || "Failed to create toggle backup.")
      }

      const blob = await response.blob()
      const downloadUrl = URL.createObjectURL(blob)
      const downloadLink = document.createElement("a")
      downloadLink.href = downloadUrl
      downloadLink.download = "toggle-backup.json"
      downloadLink.style.display = "none"
      document.body.appendChild(downloadLink)
      downloadLink.click()
      downloadLink.remove()
      setTimeout(() => URL.revokeObjectURL(downloadUrl), 1000)
      showSnackbar("Toggle backup downloaded.")
    } catch (error) {
      showSnackbar(error?.message || "Failed to create toggle backup.", "error")
    }
  }

  function confirmResetDefault() {
    state.showResetDefaultModal = true;
  }

  async function resetTogglesToDefault() {
    state.showResetDefaultModal = false;
    showSnackbar("Resetting toggles to their default values...");
    await new Promise(resolve => setTimeout(resolve, 3000));
    showSnackbar("Rebooting...");
    await new Promise(resolve => setTimeout(resolve, 3000));
    await fetch("/api/toggles/reset_default", { method: "POST" });
  }

  function triggerRestorePrompt() {
    fileInput.click()
  }

  function confirmSaveMe() {
    state.showSaveMeModal = true;
  }

  async function runFactoryReset() {
    if (state.factoryResetBusy) return

    state.showSaveMeModal = false
    state.factoryResetBusy = true
    try {
      const response = await fetch("/api/update/factory_reset", { method: "POST" })
      const payload = await response.json()
      if (!response.ok) {
        throw new Error(payload.error || response.statusText || "Failed to start factory reset")
      }

      state.factoryResetStatus = {
        running: true,
        stage: "starting",
        message: payload.message || "Factory reset started. Device will reboot when complete.",
        lastError: "",
        progressLabel: "Preparing factory reset",
        progressDetail: "Initializing factory reset...",
        progressPercent: 0,
        progressStep: 1,
        progressTotalSteps: 5,
      }
      ensureFactoryResetPolling()
      showSnackbar(payload.message || "Factory reset started.")
      fetchFactoryResetStatus()
    } catch (error) {
      showSnackbar(error?.message || "Failed to start factory reset", "error")
    } finally {
      state.factoryResetBusy = false
    }
  }

  return html`
    <div class="toggle-control-wrapper">
      <section class="toggle-control-widget">
        <div class="toggle-control-title">Backup/Restore Toggles</div>
        <p class="toggle-control-text">
          Use the buttons below to backup or restore your toggles.
        </p>
        <button class="toggle-control-button" @click="${backupToggles}">Backup Toggles</button>
        <button class="toggle-control-button" @click="${triggerRestorePrompt}">Restore Toggles</button>
      </section>

      <section class="toggle-control-widget" style="margin-left: 1.5rem">
        <div class="toggle-control-title">Reset Toggles to Default</div>
        <p class="toggle-control-text">
          Reset all toggles to default StarPilot settings.
        </p>
        <button class="toggle-control-button" @click="${confirmResetDefault}">
          Reset Toggles to Default
        </button>
        <div class="toggle-control-danger-zone">
          <div class="toggle-control-danger-title">WARNING: Factory Reset</div>
          <p class="toggle-control-danger-text">
            Last resort only. This wipes params, backups, themes, models, maps, and route data, then reboots the device.
          </p>
          <button
            class="toggle-control-button toggle-control-button-danger toggle-control-button-save-me"
            @click="${confirmSaveMe}"
            disabled="${() => state.factoryResetBusy}">
            ${() => state.factoryResetBusy ? "Starting..." : "SAVE ME"}
          </button>
          ${() => state.factoryResetStatus ? html`
            <div class="toggle-control-status ${state.factoryResetStatus.stage === "error" ? "error" : ""}">
              <div class="toggle-control-status-title">Factory Reset Status</div>
              <p class="toggle-control-status-line">
                <strong>Step:</strong>
                ${state.factoryResetStatus.progressStep}/${state.factoryResetStatus.progressTotalSteps}
                ${state.factoryResetStatus.progressLabel ? `- ${state.factoryResetStatus.progressLabel}` : ""}
              </p>
              <div class="toggle-control-status-track ${state.factoryResetStatus.stage === "error" ? "error" : ""}">
                <div class="toggle-control-status-fill ${state.factoryResetStatus.stage === "error" ? "error" : ""}" style="width: ${state.factoryResetStatus.progressPercent}%;"></div>
              </div>
              ${() => state.factoryResetStatus.message ? html`<p class="toggle-control-status-line">${state.factoryResetStatus.message}</p>` : ""}
              ${() => state.factoryResetStatus.progressDetail ? html`<p class="toggle-control-status-line ${state.factoryResetStatus.stage === "error" ? "error" : ""}">${state.factoryResetStatus.progressDetail}</p>` : ""}
              ${() => state.factoryResetStatus.lastError ? html`<p class="toggle-control-status-line error"><strong>Last Error:</strong> ${state.factoryResetStatus.lastError}</p>` : ""}
            </div>
          ` : ""}
        </div>
      </section>

      ${TailscaleControl()}
    </div>
    ${() => state.showResetDefaultModal ? Modal({
    title: "Reset Toggles",
    message: "Are you sure you want to reset all toggles to their default StarPilot values?",
    onConfirm: resetTogglesToDefault,
    onCancel: () => { state.showResetDefaultModal = false; },
    confirmText: "Reset to Default"
  }) : ""}
    ${() => state.showSaveMeModal ? Modal({
    title: "SAVE ME",
    message: "This will factory reset the device by wiping params, backups, themes, models, maps, and route data. The device will reboot when the wipe is complete. This cannot be undone.",
    onConfirm: runFactoryReset,
    onCancel: () => { state.showSaveMeModal = false; },
    confirmText: "Factory Reset"
  }) : ""}
  `
}
