import { html, reactive } from "/assets/vendor/arrow-core.js";

const state = reactive({
  loading: true,
  refreshing: false,
  error: "",
  actionBusy: false,
  sortMode: "alphabetical",
  communityFavoriteFilter: "all",
  models: [],
  currentModel: "",
  summary: { installed: 0, missing: 0, total: 0 },
  status: {
    modelToDownload: "",
    downloadAll: false,
    downloading: false,
    cancelling: false,
    progress: "",
    isOnroad: false,
    terminal: false,
  },
});

let initialized = false;
let pollingHandle = null;
let statusInFlight = false;
let lastStatusSignature = "";

const REQUEST_TIMEOUT_MS = 20000;
const ACTIVE_POLL_INTERVAL_MS = 1000;
const IDLE_POLL_INTERVAL_MS = 4000;

function notify(message, variant = "success") {
  if (typeof showSnackbar === "function") {
    showSnackbar(message, variant);
  } else if (variant === "error") {
    console.error(message);
  } else {
    console.log(message);
  }
}

function logDebug(message, details = null) {
  if (details === null || details === undefined) {
    console.log(`[ModelManager] ${message}`);
  } else {
    console.log(`[ModelManager] ${message}`, details);
  }
}

function isModelRouteActive() {
  return window.location.pathname === "/manage_models";
}

function safeText(value, fallback = "") {
  if (value === null || value === undefined) return fallback;
  return String(value);
}

function toBool(value) {
  return !!value;
}

function toInt(value) {
  const n = Number(value);
  return Number.isFinite(n) ? n : 0;
}

function parseReleased(value) {
  const ts = Date.parse(safeText(value, ""));
  return Number.isNaN(ts) ? 0 : ts;
}

function normalizeSeries(model) {
  return safeText(model?.series, "Custom Series") || "Custom Series";
}

function modelSortCompare(a, b) {
  if (state.sortMode === "release_date") {
    const dateDelta = parseReleased(b?.released) - parseReleased(a?.released);
    if (dateDelta !== 0) return dateDelta;
  }

  return safeText(a?.label, a?.value).localeCompare(
    safeText(b?.label, b?.value),
    undefined,
    { sensitivity: "base", numeric: true },
  );
}

function getFilteredModels() {
  let rows = [...state.models].filter(model => model && typeof model === "object");

  if (state.communityFavoriteFilter === "yes") {
    rows = rows.filter(model => !!model.communityFavorite);
  } else if (state.communityFavoriteFilter === "no") {
    rows = rows.filter(model => !model.communityFavorite);
  }

  return rows;
}

function getSeriesGroups() {
  const grouped = {};

  for (const model of getFilteredModels()) {
    const seriesName = normalizeSeries(model);
    if (!grouped[seriesName]) grouped[seriesName] = [];
    grouped[seriesName].push(model);
  }

  const seriesNames = Object.keys(grouped);
  for (const seriesName of seriesNames) {
    grouped[seriesName].sort(modelSortCompare);
  }

  if (state.sortMode === "release_date") {
    seriesNames.sort((a, b) => {
      const aNewest = Math.max(...grouped[a].map(model => parseReleased(model?.released)));
      const bNewest = Math.max(...grouped[b].map(model => parseReleased(model?.released)));
      const delta = bNewest - aNewest;
      if (delta !== 0) return delta;
      return a.localeCompare(b, undefined, { sensitivity: "base" });
    });
  } else {
    seriesNames.sort((a, b) => a.localeCompare(b, undefined, { sensitivity: "base" }));
  }

  return { grouped, seriesNames };
}

function getVisibleModels() {
  const { grouped, seriesNames } = getSeriesGroups();
  const rows = [];
  for (const seriesName of seriesNames) {
    rows.push(...grouped[seriesName]);
  }
  return rows;
}

function getReleaseOrderedModels() {
  return getFilteredModels().sort(modelSortCompare);
}

function getInstalledModels() {
  const rows = state.sortMode === "release_date" ? getReleaseOrderedModels() : getVisibleModels();
  return rows.filter(model => !!model.installed);
}

function getCurrentModelName() {
  const current = safeText(state.currentModel, "");
  if (!current) return "none";

  const match = state.models.find(model => safeText(model?.value, "") === current);
  if (!match) return current;

  return safeText(match.label, current);
}

async function fetchJson(url, options = {}) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);

  try {
    const response = await fetch(url, { ...options, signal: controller.signal });

    let payload = {};
    try {
      payload = await response.json();
    } catch {
      payload = {};
    }

    if (!response.ok) {
      const message = payload?.error || payload?.message || `Request failed (${response.status})`;
      throw new Error(message);
    }

    return payload;
  } finally {
    clearTimeout(timer);
  }
}

async function fetchStatus() {
  if (statusInFlight) return;
  statusInFlight = true;

  try {
    const payload = await fetchJson("/api/models/status");

    const models = Array.isArray(payload.models)
      ? payload.models.filter(model => model && typeof model === "object")
      : [];

    state.models = models;
    state.currentModel = safeText(payload.currentModel, "");

    const summary = payload.summary && typeof payload.summary === "object" ? payload.summary : {};
    state.summary = {
      installed: toInt(summary.installed),
      missing: toInt(summary.missing),
      total: toInt(summary.total),
    };

    state.status = {
      modelToDownload: safeText(payload.modelToDownload, ""),
      downloadAll: toBool(payload.downloadAll),
      downloading: toBool(payload.downloading),
      cancelling: toBool(payload.cancelling),
      progress: safeText(payload.progress, ""),
      isOnroad: toBool(payload.isOnroad),
      terminal: toBool(payload.terminal),
    };

    state.error = "";

    const signature = [
      state.models.length,
      state.currentModel,
      state.status.downloading,
      state.status.downloadAll,
      state.status.modelToDownload,
      state.status.progress,
    ].join("|");

    if (signature !== lastStatusSignature) {
      lastStatusSignature = signature;
      logDebug("Status updated", {
        models: state.models.length,
        currentModel: state.currentModel || "none",
        downloading: state.status.downloading,
        progress: state.status.progress || "Idle",
      });
    }
  } catch (error) {
    state.error = error?.message || String(error);
    logDebug("Status fetch failed", state.error);
  } finally {
    statusInFlight = false;
    state.loading = false;
    state.refreshing = false;
  }
}

async function refreshAll(showToast = false) {
  state.refreshing = true;
  if (state.models.length === 0) {
    state.loading = true;
  }

  await fetchStatus();

  if (showToast && !state.error) {
    notify("Model list refreshed.");
  }
}

function ensurePolling() {
  if (pollingHandle) return;

  const poll = async () => {
    if (!isModelRouteActive()) {
      pollingHandle = null;
      return;
    }

    let nextDelay = IDLE_POLL_INTERVAL_MS;
    try {
      await fetchStatus();
      nextDelay = state.status.downloading ? ACTIVE_POLL_INTERVAL_MS : IDLE_POLL_INTERVAL_MS;
    } finally {
      pollingHandle = setTimeout(poll, nextDelay);
    }
  };

  pollingHandle = setTimeout(poll, ACTIVE_POLL_INTERVAL_MS);
}

async function setActiveModel(modelKey) {
  const payload = await fetchJson("/api/params", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ key: "Model", value: modelKey }),
  });

  notify(payload.message || `Selected "${modelKey}".`);
}

async function startDownload(modelKey) {
  const payload = await fetchJson("/api/models/download", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ model: modelKey }),
  });

  notify(payload.message || `Downloading "${modelKey}"...`);
}

async function startDownloadAll() {
  const payload = await fetchJson("/api/models/download_all", { method: "POST" });
  notify(payload.message || "Started downloading all models.");
}

async function cancelDownload() {
  const payload = await fetchJson("/api/models/cancel", { method: "POST" });
  notify(payload.message || "Cancellation requested.");
}

async function deleteModel(modelKey) {
  const payload = await fetchJson("/api/models/delete", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ model: modelKey }),
  });

  notify(payload.message || `Deleted files for "${modelKey}".`);
}

async function refreshManifest() {
  const payload = await fetchJson("/api/models/refresh_manifest", { method: "POST" });
  notify(payload.message || "Model manifest refreshed.");
}

async function runAction(action, modelKey = "") {
  if (state.actionBusy) {
    notify("Please wait for the current action to finish.", "error");
    return;
  }

  state.actionBusy = true;
  try {
    if (action === "refresh") {
      await refreshManifest();
      await refreshAll(false);
      return;
    }

    if (state.status.isOnroad && action !== "refresh") {
      notify("Actions are blocked while onroad.", "error");
      return;
    }

    if (action === "select") {
      if (!modelKey) return;
      await setActiveModel(modelKey);
    } else if (action === "download") {
      if (!modelKey) return;
      await startDownload(modelKey);
    } else if (action === "download-all") {
      await startDownloadAll();
    } else if (action === "cancel") {
      await cancelDownload();
    } else if (action === "delete") {
      if (!modelKey) return;
      const confirmed = window.confirm(`Delete local files for model \"${modelKey}\"?`);
      if (!confirmed) return;
      await deleteModel(modelKey);
    }

    await fetchStatus();
  } catch (error) {
    notify(error?.message || String(error), "error");
  } finally {
    state.actionBusy = false;
  }
}

function bindDomHandlers() {
  if (window.__modelManagerHandlersBound) return;
  window.__modelManagerHandlersBound = true;

  document.addEventListener("click", event => {
    if (!isModelRouteActive()) return;

    const target = event.target;
    if (!(target instanceof Element)) return;

    const button = target.closest("[data-mm-action]");
    if (!button) return;

    const action = safeText(button.getAttribute("data-mm-action"), "");
    const modelKey = safeText(button.getAttribute("data-model"), "");

    runAction(action, modelKey).catch(() => {});
  });

  document.addEventListener("change", event => {
    if (!isModelRouteActive()) return;

    const target = event.target;
    if (!(target instanceof HTMLSelectElement)) return;
    if (target.id === "mm-active-model-select") {
      const modelKey = safeText(target.value, "");
      if (!modelKey) return;
      runAction("select", modelKey).catch(() => {});
      return;
    }

    if (target.id === "mm-sort-mode-select") {
      const value = safeText(target.value, "alphabetical");
      state.sortMode = value === "release_date" ? "release_date" : "alphabetical";
      return;
    }

    if (target.id === "mm-community-filter-select") {
      const value = safeText(target.value, "all");
      if (value === "yes" || value === "no" || value === "all") {
        state.communityFavoriteFilter = value;
      } else {
        state.communityFavoriteFilter = "all";
      }
    }
  });
}

function renderActions(model) {
  const modelKey = safeText(model.value, "");
  const modelIsDownloading = state.status.downloading && !state.status.downloadAll && state.status.modelToDownload === modelKey;

  if (state.currentModel === modelKey) {
    return html`<span class="mm-chip mm-chip-active">Active</span>`;
  }

  if (state.status.downloading) {
    if (state.status.downloadAll || modelIsDownloading) {
      return html`<button class="mm-btn mm-btn-danger" data-mm-action="cancel">Cancel</button>`;
    }
    return html`<span class="mm-chip">Busy</span>`;
  }

  if (model.installed) {
    return html`
      <button class="mm-btn mm-btn-secondary" data-mm-action="select" data-model="${modelKey}">Set Active</button>
      <button class="mm-btn mm-btn-danger" data-mm-action="delete" data-model="${modelKey}">Delete</button>
    `;
  }

  return html`<button class="mm-btn mm-btn-primary" data-mm-action="download" data-model="${modelKey}">Download</button>`;
}

function renderModelRow(model) {
  const label = safeText(model.label, safeText(model.value, "Unnamed"));
  const key = safeText(model.value, "");

  return html`
    <div class="mm-row">
      <div class="mm-row-main">
        <div class="mm-row-title">
          <span>${label}</span>
        </div>
        <div class="mm-row-meta">
          <span class="mm-chip">${key}</span>
          ${state.sortMode === "release_date" ? "" : model.series ? html`<span class="mm-chip">${safeText(model.series)}</span>` : ""}
          ${model.version ? html`<span class="mm-chip">Version ${safeText(model.version)}</span>` : ""}
          ${model.released ? html`<span class="mm-chip">Released ${safeText(model.released)}</span>` : ""}
          ${model.communityFavorite ? html`<span class="mm-chip mm-chip-favorite">Community Favorite</span>` : ""}
          ${model.partial ? html`<span class="mm-chip mm-chip-warning">Partial Files</span>` : ""}
        </div>
      </div>
      <div class="mm-row-actions">
        ${renderActions(model)}
      </div>
    </div>
  `;
}

function renderSeriesSection(seriesName, models) {
  return html`
    <section class="mm-series">
      <header class="mm-series-header">
        <h3>${seriesName}</h3>
        <span>${models.length}</span>
      </header>
      <div class="mm-series-body">
        ${models.map(model => renderModelRow(model))}
      </div>
    </section>
  `;
}

export function ModelManager() {
  if (!initialized) {
    initialized = true;
    bindDomHandlers();
    logDebug("Initializing component");
    refreshAll().catch(error => {
      state.error = error?.message || String(error);
      state.loading = false;
      state.refreshing = false;
      logDebug("Initial refresh failed", state.error);
    });
  }
  ensurePolling();

  return html`
    <div class="mm-wrapper">
      <h2>Model Manager</h2>

      ${() => state.error ? html`<div class="mm-error">${state.error}</div>` : ""}

      <div class="mm-debug">
        Available Models=${() => state.models.length}
        Current Model=${() => getCurrentModelName()}
      </div>

      <div class="mm-toolbar">
        <div class="mm-summary">
          <span><b>${state.summary.installed}</b> installed</span>
          <span><b>${state.summary.missing}</b> missing</span>
          <span><b>${state.summary.total}</b> total</span>
        </div>

        <div class="mm-actions">
          ${() => state.status.downloading
            ? html`<button class="mm-btn mm-btn-danger" data-mm-action="cancel">Cancel Download</button>`
            : html`<button class="mm-btn mm-btn-primary" data-mm-action="download-all">Download All Missing</button>`}
          <button class="mm-btn mm-btn-secondary" data-mm-action="refresh">Refresh</button>
        </div>
      </div>

      <div class="mm-status">
        <span class="mm-chip">Current: ${getCurrentModelName()}</span>
        <span class="mm-chip">Progress: ${safeText(state.status.progress, "Idle")}</span>
        ${() => state.status.isOnroad ? html`<span class="mm-chip mm-chip-warning">Onroad: actions disabled</span>` : ""}
      </div>

      <div class="mm-filters">
        <label class="mm-filter-label" for="mm-active-model-select">Active Model</label>
        <select class="mm-select" id="mm-active-model-select">
          ${(() => {
            const orderedInstalled = getInstalledModels().sort((a, b) => {
              const aCurrent = safeText(a.value) === state.currentModel ? 0 : 1;
              const bCurrent = safeText(b.value) === state.currentModel ? 0 : 1;
              if (aCurrent !== bCurrent) return aCurrent - bCurrent;
              return safeText(a.label, a.value).localeCompare(safeText(b.label, b.value), undefined, { sensitivity: "base" });
            });

            return orderedInstalled.length > 0
              ? orderedInstalled.map(model => html`
                <option value="${safeText(model.value)}" selected="${() => safeText(model.value) === state.currentModel || false}">
                  ${safeText(model.label, model.value)}
                </option>              `)
              : html`<option value="">No installed models</option>`;
          })()}
        </select>

        <label class="mm-filter-label" for="mm-sort-mode-select">Sort</label>
        <select class="mm-select" id="mm-sort-mode-select">
          <option value="alphabetical" selected="${() => state.sortMode === "alphabetical" || false}">Alphabetical</option>
          <option value="release_date" selected="${() => state.sortMode === "release_date" || false}">Release Date</option>
        </select>

        <div class="mm-filter-break"></div>

        <label class="mm-filter-label" for="mm-community-filter-select">Community Favorite</label>
        <select class="mm-select" id="mm-community-filter-select">
          <option value="all" selected="${() => state.communityFavoriteFilter === "all" || false}">All</option>
          <option value="yes" selected="${() => state.communityFavoriteFilter === "yes" || false}">Yes</option>
          <option value="no" selected="${() => state.communityFavoriteFilter === "no"}">No</option>
        </select>
      </div>

      ${() => state.loading ? html`<div class="mm-empty">Loading models...</div>` : ""}

      ${() => !state.loading ? html`
        <div class="mm-list">
          ${(() => {
            if (state.sortMode === "release_date") {
              const models = getReleaseOrderedModels();
              return models.length === 0
                ? html`<div class="mm-empty">No models available.</div>`
                : models.map(model => renderModelRow(model));
            }

            const { grouped, seriesNames } = getSeriesGroups();
            return seriesNames.length === 0
              ? html`<div class="mm-empty">No models available.</div>`
              : seriesNames.map(seriesName => renderSeriesSection(seriesName, grouped[seriesName]));
          })()}
        </div>
      ` : ""}
    </div>
  `;
}
