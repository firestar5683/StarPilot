import { html, reactive } from "/assets/vendor/arrow-core.js"

const state = reactive({
  loading: true,
  saving: false,
  error: "",
  message: "",
  chestnutReady: false,
  isOnroad: false,
  configuration: { enabled: false, lateralModel: "", longitudinalModel: "" },
  runtime: {},
  download: {},
  models: [],
  summary: {},
})

let initialized = false
let pollHandle = null
let selectionDirty = false

function modelById(modelId) {
  return state.models.find(model => model.value === modelId)
}

function modelLabel(modelId) {
  return modelById(modelId)?.label || modelId || "not selected"
}

function availableModels() {
  return state.models.filter(model => model.modelLabArtifactAvailable)
}

function downloadedModels() {
  return availableModels().filter(model => model.modelLabArtifactInstalled)
}

function candidateModels(role) {
  const downloaded = downloadedModels()
  if (role !== "longitudinal") return downloaded
  const lateral = modelById(state.configuration.lateralModel)
  if (!lateral) return downloaded
  return downloaded.filter(model => model.value !== lateral.value)
}

function selectionError() {
  if (state.isOnroad) return "Park before changing the laboratory pair."
  if (downloadedModels().length < 2) return "Download at least two eGPU variants before composing a pair."
  const lateral = modelById(state.configuration.lateralModel)
  const longitudinal = modelById(state.configuration.longitudinalModel)
  if (!lateral || !longitudinal) return "Choose two downloaded eGPU variants."
  if (lateral.value === longitudinal.value) return "Lateral and longitudinal models must be different."
  if (!lateral.modelLabArtifactInstalled || !longitudinal.modelLabArtifactInstalled) {
    return "Download both eGPU variants first."
  }
  if (!state.chestnutReady) return "Connect a firmware-ready Chestnut to enable this pair."
  return ""
}

function applyPayload(payload) {
  const draftSelection = {
    lateralModel: state.configuration.lateralModel,
    longitudinalModel: state.configuration.longitudinalModel,
  }
  state.chestnutReady = Boolean(payload?.chestnutReady)
  state.isOnroad = Boolean(payload?.isOnroad)
  state.configuration = {
    enabled: Boolean(payload?.configuration?.enabled),
    lateralModel: selectionDirty
      ? draftSelection.lateralModel
      : String(payload?.configuration?.lateralModel || ""),
    longitudinalModel: selectionDirty
      ? draftSelection.longitudinalModel
      : String(payload?.configuration?.longitudinalModel || ""),
  }
  state.runtime = payload?.runtime && typeof payload.runtime === "object" ? payload.runtime : {}
  state.download = payload?.download && typeof payload.download === "object" ? payload.download : {}
  state.models = Array.isArray(payload?.models) ? payload.models : []
  state.summary = payload?.summary && typeof payload.summary === "object" ? payload.summary : {}
  state.error = String(payload?.configurationError || "")

  const downloaded = downloadedModels()
  if (!downloaded.some(model => model.value === state.configuration.lateralModel)) {
    state.configuration.lateralModel = downloaded[0]?.value || ""
  }
  if (!downloaded.some(model => model.value === state.configuration.longitudinalModel)) {
    state.configuration.longitudinalModel = downloaded.find(model => (
      model.value !== state.configuration.lateralModel
    ))?.value || ""
  }
}

async function requestJson(url, options = {}) {
  const response = await fetch(url, { cache: "no-store", ...options })
  let payload = {}
  try {
    payload = await response.json()
  } catch {
  }
  if (!response.ok) throw new Error(payload.error || `Request failed (${response.status})`)
  return payload
}

async function refresh() {
  try {
    applyPayload(await requestJson("/api/model-laboratory"))
  } catch (error) {
    state.error = error?.message || String(error)
  } finally {
    state.loading = false
    setTimeout(bindControls, 0)
  }
}

async function save(enabled) {
  if (state.saving) return
  if (enabled) {
    const error = selectionError()
    if (error) {
      state.error = error
      return
    }
  }

  state.saving = true
  state.error = ""
  state.message = ""
  try {
    const payload = await requestJson("/api/model-laboratory", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        enabled,
        lateralModel: state.configuration.lateralModel,
        longitudinalModel: state.configuration.longitudinalModel,
      }),
    })
    selectionDirty = false
    applyPayload(payload)
    state.message = String(payload.message || "Model Laboratory configuration saved.")
  } catch (error) {
    state.error = error?.message || String(error)
  } finally {
    state.saving = false
  }
}

async function prepareModel(modelId) {
  if (state.saving || !modelId) return
  state.saving = true
  state.error = ""
  state.message = ""
  try {
    const payload = await requestJson("/api/model-laboratory/download", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ model: modelId }),
    })
    state.message = String(payload.message || "eGPU variant download queued.")
    await refresh()
  } catch (error) {
    state.error = error?.message || String(error)
  } finally {
    state.saving = false
  }
}

async function deleteModel(modelId) {
  if (state.saving || !modelId) return
  const model = modelById(modelId)
  if (!window.confirm(`Delete the eGPU variant for "${model?.label || modelId}"? The normal on-device model will not be removed.`)) return
  state.saving = true
  state.error = ""
  state.message = ""
  try {
    const payload = await requestJson("/api/model-laboratory/artifact", {
      method: "DELETE",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ model: modelId }),
    })
    selectionDirty = false
    applyPayload(payload)
    state.message = String(payload.message || "eGPU variant deleted.")
  } catch (error) {
    state.error = error?.message || String(error)
  } finally {
    state.saving = false
  }
}

function bindControls() {
  const lateral = document.getElementById("ml-lateral-model")
  const longitudinal = document.getElementById("ml-longitudinal-model")
  const enable = document.getElementById("ml-enable")
  const disable = document.getElementById("ml-disable")
  const refreshButton = document.getElementById("ml-refresh")
  document.querySelectorAll("[data-ml-download]").forEach(button => {
    if (button.dataset.bound === "1") return
    button.dataset.bound = "1"
    button.addEventListener("click", () => prepareModel(button.dataset.mlDownload))
  })
  document.querySelectorAll("[data-ml-delete]").forEach(button => {
    if (button.dataset.bound === "1") return
    button.dataset.bound = "1"
    button.addEventListener("click", () => deleteModel(button.dataset.mlDelete))
  })

  if (lateral) {
    lateral.value = state.configuration.lateralModel
    if (lateral.dataset.bound !== "1") {
      lateral.dataset.bound = "1"
      lateral.addEventListener("change", event => {
        selectionDirty = true
        state.configuration.lateralModel = event.target.value
        const long = modelById(state.configuration.longitudinalModel)
        const lat = modelById(event.target.value)
        if (long && lat && long.value === lat.value) {
          state.configuration.longitudinalModel = candidateModels("longitudinal")[0]?.value || ""
          if (longitudinal) longitudinal.value = state.configuration.longitudinalModel
        }
      })
    }
  }
  if (longitudinal) {
    longitudinal.value = state.configuration.longitudinalModel
    if (longitudinal.dataset.bound !== "1") {
      longitudinal.dataset.bound = "1"
      longitudinal.addEventListener("change", event => {
        selectionDirty = true
        state.configuration.longitudinalModel = event.target.value
      })
    }
  }
  if (enable && enable.dataset.bound !== "1") {
    enable.dataset.bound = "1"
    enable.addEventListener("click", () => save(true))
  }
  if (disable && disable.dataset.bound !== "1") {
    disable.dataset.bound = "1"
    disable.addEventListener("click", () => save(false))
  }
  if (refreshButton && refreshButton.dataset.bound !== "1") {
    refreshButton.dataset.bound = "1"
    refreshButton.addEventListener("click", refresh)
  }
}

function ensurePolling() {
  if (pollHandle) return
  const poll = async () => {
    if (window.location.pathname !== "/model_laboratory") {
      pollHandle = null
      return
    }
    await refresh()
    pollHandle = setTimeout(poll, state.download?.model ? 1000 : 5000)
  }
  pollHandle = setTimeout(poll, 5000)
}

function renderModel(model) {
  const artifactStatus = model.modelLabArtifactInstalled
    ? "eGPU variant downloaded"
    : "eGPU variant not downloaded"
  return html`
    <div class="ml-model">
      <div>
        <strong>${model.label}</strong>
        <div class="ml-muted">${model.value} · ${model.series || "Unknown series"}</div>
      </div>
      <div class="ml-chips">
        <span class="ml-chip">${model.version || "unknown version"}</span>
        <span class="ml-chip">${model.modelSize || "small"}</span>
        <span class="${`ml-chip ${model.modelLabArtifactInstalled ? "ml-chip-good" : "ml-chip-warning"}`}">
          ${artifactStatus}
        </span>
        ${model.modelLabArtifactAvailable && !model.modelLabArtifactInstalled ? html`
          <button class="ml-button" data-ml-download="${model.value}" disabled="${() => state.saving || state.isOnroad || Boolean(state.download?.model)}">
            ${() => state.download?.model === model.value
              ? `Downloading · ${state.download?.progress || "starting…"}`
              : "Download eGPU variant"}
          </button>
        ` : ""}
        ${model.modelLabArtifactInstalled ? html`
          <button class="ml-button ml-button-danger" data-ml-delete="${model.value}" disabled="${() => state.saving || state.isOnroad || Boolean(state.download?.model)}">
            Delete eGPU variant
          </button>
        ` : ""}
      </div>
    </div>
  `
}

export function ModelLaboratory() {
  if (!initialized) {
    initialized = true
    refresh()
  }
  ensurePolling()
  setTimeout(bindControls, 0)

  return html`
    <div class="ml-wrapper">
      <header class="ml-hero">
        <div>
          <h2>Model Laboratory</h2>
          <p>Use the lateral judgment of one small model and the longitudinal judgment of another.</p>
        </div>
        <div class="ml-chips">
          <span class="${() => `ml-chip ${state.chestnutReady ? "ml-chip-good" : "ml-chip-warning"}`}">
            ${() => state.chestnutReady ? "Chestnut ready" : "Chestnut required"}
          </span>
          <span class="${() => `ml-chip ${state.isOnroad ? "ml-chip-warning" : "ml-chip-good"}`}">
            ${() => state.isOnroad ? "Onroad · locked" : "Parked · configurable"}
          </span>
        </div>
      </header>

      ${() => state.error ? html`<div class="ml-alert ml-alert-error">${state.error}</div>` : ""}
      ${() => state.message ? html`<div class="ml-alert ml-alert-good">${state.message}</div>` : ""}
      ${() => state.loading ? html`<div class="ml-card">Loading laboratory status…</div>` : ""}

      ${() => !state.loading ? html`
        <section class="ml-card">
          <div class="ml-card-heading">
            <div>
              <h3>Available models</h3>
              <p>Download eGPU-compatible small models. These are separate from the small models in Model Manager because they are compiled for the eGPU.</p>
              <p>${() => `${state.summary.ready || 0} downloaded · ${Math.max((state.summary.published || 0) - (state.summary.ready || 0), 0)} available to download.`}</p>
            </div>
          </div>
          <div class="ml-model-list">${() => availableModels().map(renderModel)}</div>
        </section>

        <section class="ml-card">
          <div class="ml-card-heading">
            <div>
              <h3>Compose a pair</h3>
              <p>Choose from downloaded eGPU variant combinations below.</p>
            </div>
            <span class="${() => `ml-state ${state.configuration.enabled ? "is-enabled" : ""}`}">
              ${() => state.configuration.enabled ? "Enabled" : "Disabled"}
            </span>
          </div>

          <div class="ml-pair">
            <label>
              <span>Lateral model</span>
              <small>Path shape, curvature, lane geometry, and driving desire</small>
              <select id="ml-lateral-model" class="ml-select">
                <option value="">Choose a model</option>
                ${() => candidateModels("lateral").map(model => html`
                  <option value="${model.value}">
                    ${model.label} · ${model.version}
                  </option>
                `)}
              </select>
            </label>
            <div class="ml-plus">+</div>
            <label>
              <span>Longitudinal model</span>
              <small>Speed, acceleration, stopping, leads, and scene confidence</small>
              <select id="ml-longitudinal-model" class="ml-select">
                <option value="">Choose a model</option>
                ${() => candidateModels("longitudinal").map(model => html`
                  <option value="${model.value}">
                    ${model.label} · ${model.version}
                  </option>
                `)}
              </select>
            </label>
          </div>

          <div class="ml-preview">
            <b>${() => modelLabel(state.configuration.lateralModel)}</b>
            <span>steers</span>
            <i class="bi bi-arrow-left-right"></i>
            <b>${() => modelLabel(state.configuration.longitudinalModel)}</b>
            <span>paces</span>
          </div>

          ${() => selectionError() ? html`<p class="ml-validation">${selectionError()}</p>` : ""}
          <div class="ml-actions">
            <button id="ml-enable" class="ml-button ml-button-primary" disabled="${() => state.saving || Boolean(selectionError())}">
              Enable for next drive
            </button>
            <button id="ml-disable" class="ml-button" disabled="${() => state.saving || state.isOnroad || !state.configuration.enabled}">
              Disable
            </button>
            <button id="ml-refresh" class="ml-button" disabled="${() => state.saving}">Refresh</button>
          </div>
        </section>

        <section class="ml-card">
          <div class="ml-card-heading">
            <div>
              <h3>Runtime</h3>
              <p>The configuration activates when modeld starts for a drive.</p>
            </div>
            <span class="${() => `ml-state ${state.runtime?.active ? "is-enabled" : ""}`}">
              ${() => state.runtime?.active ? "Pair active" : state.runtime?.requested ? "Pair requested" : "Inactive"}
            </span>
          </div>
          <div class="ml-runtime-grid">
            <div><span>Lateral</span><b>${() => modelLabel(state.runtime?.lateralModel)}</b></div>
            <div><span>Longitudinal</span><b>${() => modelLabel(state.runtime?.longitudinalModel)}</b></div>
          </div>
          ${() => state.runtime?.error ? html`<div class="ml-alert ml-alert-error">${state.runtime.error}</div>` : ""}
          <p class="ml-muted">Both roles evaluate the same frame at 20 Hz. A runtime failure suppresses that frame and falls back to the built-in QCOM model.</p>
        </section>

      ` : ""}
    </div>
  `
}
