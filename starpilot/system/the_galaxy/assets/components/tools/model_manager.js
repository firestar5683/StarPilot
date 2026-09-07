import { html, reactive } from "/assets/vendor/arrow-core.js";

const state = reactive({
  loading: true,
  refreshing: false,
  error: "",
  actionBusy: false,
  sortMode: "release_date",
  communityFavoriteFilter: "all",
  userFavoriteFilter: "all",
  allowGpuDownloadsWithoutGpu: false,
  models: [],
  currentModel: "",
  activeSmallModel: "",
  activeBigModel: "",
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

function modelHardwareTag(model) {
  return model?.requiresGpu ? "eGPU" : "On-device GPU";
}

function gpuDownloadBlocked(model) {
  return !!model?.requiresGpu && !model?.gpuAvailable && !state.allowGpuDownloadsWithoutGpu;
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

  if (state.userFavoriteFilter === "yes") {
    rows = rows.filter(model => !!model.userFavorite);
  } else if (state.userFavoriteFilter === "no") {
    rows = rows.filter(model => !model.userFavorite);
  }

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

function getInstalledModels(profile = "") {
  return state.models
    .filter(model => model && typeof model === "object" && !!model.installed)
    .filter(model => !profile || (!!model.requiresGpu === (profile === "big")))
    .sort(modelSortCompare);
}

function getUserFavoriteModels(installedOnly = false) {
  const rows = state.models.filter(model => model && typeof model === "object" && !!model.userFavorite);
  const filtered = installedOnly ? rows.filter(model => !!model.installed) : rows;
  return filtered.sort(modelSortCompare);
}

function getCurrentModelName() {
  const current = safeText(state.currentModel, "");
  if (!current) return "none";

  const match = state.models.find(model => safeText(model?.value, "") === current);
  if (!match) return current;

  return safeText(match.label, current);
}

function getModelName(modelKey, fallback = "none selected") {
  const key = safeText(modelKey, "");
  if (!key) return fallback;
  const match = state.models.find(model => safeText(model?.value, "") === key);
  return match ? safeText(match.label, key) : key;
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
    state.activeSmallModel = safeText(payload.activeSmallModel, "");
    state.activeBigModel = safeText(payload.activeBigModel, "");

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
      state.activeSmallModel,
      state.activeBigModel,
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

async function setActiveModel(modelKey, profile = "") {
  const model = state.models.find(entry => safeText(entry?.value, "") === safeText(modelKey, ""));
  const resolvedProfile = profile || (model?.requiresGpu ? "big" : "small");
  const payload = await fetchJson("/api/models/active", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ profile: resolvedProfile, model: modelKey }),
  });

  notify(payload.message || `Selected "${modelKey}".`);
}

async function startDownload(modelKey) {
  const payload = await fetchJson("/api/models/download", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      model: modelKey,
      allowGpuWithoutGpu: state.allowGpuDownloadsWithoutGpu,
    }),
  });

  notify(payload.message || `Downloading "${modelKey}"...`);
}

async function startDownloadAll() {
  const payload = await fetchJson("/api/models/download_all", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ allowGpuWithoutGpu: state.allowGpuDownloadsWithoutGpu }),
  });
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

async function setUserFavorite(modelKey, shouldFavorite) {
  const key = safeText(modelKey, "");
  if (!key) return;

  const favorites = getUserFavoriteModels(false)
    .map(model => safeText(model.value, ""))
    .filter(Boolean)
    .filter(value => value !== key);

  if (shouldFavorite) {
    favorites.push(key);
  }

  const payload = await fetchJson("/api/models/preferences", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ userFavorites: favorites }),
  });

  notify(payload.message || (shouldFavorite ? "Model added to your favorites." : "Model removed from your favorites."));
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

    const allowedOnroadActions = new Set(["refresh", "favorite", "unfavorite"]);
    if (state.status.isOnroad && !allowedOnroadActions.has(action)) {
      notify("Actions are blocked while onroad.", "error");
      return;
    }

    if (action === "select" || action === "select-small" || action === "select-big") {
      if (!modelKey) return;
      const profile = action === "select-small" ? "small" : action === "select-big" ? "big" : "";
      await setActiveModel(modelKey, profile);
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
    } else if (action === "favorite") {
      if (!modelKey) return;
      await setUserFavorite(modelKey, true);
    } else if (action === "unfavorite") {
      if (!modelKey) return;
      await setUserFavorite(modelKey, false);
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
    if (target instanceof HTMLInputElement && target.id === "mm-gpu-download-override") {
      state.allowGpuDownloadsWithoutGpu = target.checked;
      return;
    }

    if (!(target instanceof HTMLSelectElement)) return;
    if (target.id === "mm-active-small-model-select" || target.id === "mm-active-big-model-select") {
      const modelKey = safeText(target.value, "");
      if (!modelKey) return;
      const profile = target.id === "mm-active-big-model-select" ? "big" : "small";
      runAction(`select-${profile}`, modelKey).catch(() => {});
      return;
    }

    if (target.id === "mm-favorite-model-select") {
      const modelKey = safeText(target.value, "");
      if (!modelKey) return;
      runAction("select", modelKey).catch(() => {});
      target.value = "";
      return;
    }

    if (target.id === "mm-sort-mode-select") {
      const value = safeText(target.value, "release_date");
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

    if (target.id === "mm-user-filter-select") {
      const value = safeText(target.value, "all");
      if (value === "yes" || value === "no" || value === "all") {
        state.userFavoriteFilter = value;
      } else {
        state.userFavoriteFilter = "all";
      }
    }
  });
}

function renderActions(model) {
  const modelKey = safeText(model.value, "");
  const modelIsDownloading = state.status.downloading && !state.status.downloadAll && state.status.modelToDownload === modelKey;
  const profile = model.requiresGpu ? "big" : "small";
  const isActive = profile === "big" ? state.activeBigModel === modelKey : state.activeSmallModel === modelKey;

  if (isActive) {
    return html`<span class="mm-chip mm-chip-active">Active ${profile === "big" ? "Big" : "Small"}</span>`;
  }

  if (state.status.downloading) {
    if (state.status.downloadAll || modelIsDownloading) {
      return html`<button class="mm-btn mm-btn-danger" data-mm-action="cancel">Cancel</button>`;
    }
    return html`<span class="mm-chip">Busy</span>`;
  }

  if (model.installed) {
    return html`
      <button class="mm-btn mm-btn-secondary" data-mm-action="select-${profile}" data-model="${modelKey}">Set Active ${profile === "big" ? "Big" : "Small"}</button>
      ${model.builtin
        ? ""
        : html`<button class="mm-btn mm-btn-danger" data-mm-action="delete" data-model="${modelKey}">Delete</button>`}
    `;
  }

  return html`
    <button class="mm-btn mm-btn-primary" data-mm-action="download" data-model="${modelKey}" disabled="${() => gpuDownloadBlocked(model) || false}">
      ${() => gpuDownloadBlocked(model) ? "GPU Required" : "Download"}
    </button>
  `;
}

function renderModelRow(model) {
  const label = safeText(model.label, safeText(model.value, "Unnamed"));
  const key = safeText(model.value, "");
  const favoriteAction = model.userFavorite ? "unfavorite" : "favorite";
  const favoriteTitle = model.userFavorite ? "Remove from your favorites" : "Add to your favorites";

  return html`
    <div class="mm-row">
      <div class="mm-row-main">
        <div class="mm-row-title">
          <span>${label}</span>
        </div>
        <div class="mm-row-meta">
          <span class="mm-chip">${key}</span>
          ${model.builtin ? html`<span class="mm-chip">Built-in</span>` : ""}
          <span class="mm-chip ${model.requiresGpu ? "mm-chip-egpu" : "mm-chip-device-gpu"}">${modelHardwareTag(model)}</span>
          ${state.sortMode === "release_date" ? "" : model.series ? html`<span class="mm-chip">${safeText(model.series)}</span>` : ""}
          ${model.version ? html`<span class="mm-chip">Version ${safeText(model.version)}</span>` : ""}
          ${model.released ? html`<span class="mm-chip">Released ${safeText(model.released)}</span>` : ""}
          ${model.userFavorite ? html`<span class="mm-chip mm-chip-user-favorite">Your Favorite</span>` : ""}
          ${model.communityFavorite ? html`<span class="mm-chip mm-chip-favorite">Community Favorite</span>` : ""}
          ${model.partial ? html`<span class="mm-chip mm-chip-warning">Partial Files</span>` : ""}
        </div>
      </div>
      <div class="mm-row-actions">
        <button
          class="mm-icon-btn ${model.userFavorite ? "is-active" : ""}"
          data-mm-action="${favoriteAction}"
          data-model="${key}"
          title="${favoriteTitle}"
          aria-label="${favoriteTitle}">
          <i class="bi ${model.userFavorite ? "bi-star-fill" : "bi-star"}"></i>
        </button>
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
        <span class="mm-chip">Loaded: ${() => getCurrentModelName()}</span>
        <span class="mm-chip mm-chip-device-gpu">Active Small: ${() => getModelName(state.activeSmallModel)}</span>
        <span class="mm-chip mm-chip-egpu">Active Big: ${() => getModelName(state.activeBigModel)}</span>
        <span class="mm-chip">Progress: ${safeText(state.status.progress, "Idle")}</span>
        <span class="mm-chip">${() => getUserFavoriteModels(false).length} personal favorites</span>
        ${() => state.status.isOnroad ? html`<span class="mm-chip mm-chip-warning">Onroad: actions disabled</span>` : ""}
      </div>

      <div class="mm-filters">
        <label class="mm-filter-label" for="mm-active-small-model-select">Active Small</label>
        <select class="mm-select" id="mm-active-small-model-select">
          ${() => {
            const orderedInstalled = getInstalledModels("small").sort((a, b) => {
              const aCurrent = safeText(a.value) === state.activeSmallModel ? 0 : 1;
              const bCurrent = safeText(b.value) === state.activeSmallModel ? 0 : 1;
              if (aCurrent !== bCurrent) return aCurrent - bCurrent;
              return safeText(a.label, a.value).localeCompare(safeText(b.label, b.value), undefined, { sensitivity: "base" });
            });

            return orderedInstalled.length > 0
              ? orderedInstalled.map(model => html`
                <option value="${safeText(model.value)}" selected="${() => safeText(model.value) === state.activeSmallModel || false}">
                  ${safeText(model.label, model.value)}
                </option>              `)
              : html`<option value="">No installed models</option>`;
          }}
        </select>

        <label class="mm-filter-label" for="mm-active-big-model-select">Active Big</label>
        <select class="mm-select" id="mm-active-big-model-select" disabled="${() => getInstalledModels("big").length === 0}">
          ${() => {
            const orderedInstalled = getInstalledModels("big").sort((a, b) => {
              const aCurrent = safeText(a.value) === state.activeBigModel ? 0 : 1;
              const bCurrent = safeText(b.value) === state.activeBigModel ? 0 : 1;
              if (aCurrent !== bCurrent) return aCurrent - bCurrent;
              return safeText(a.label, a.value).localeCompare(safeText(b.label, b.value), undefined, { sensitivity: "base" });
            });

            return orderedInstalled.length > 0
              ? html`
                ${state.activeBigModel ? "" : html`<option value="" selected>Choose an eGPU model</option>`}
                ${orderedInstalled.map(model => html`
                  <option value="${safeText(model.value)}" selected="${() => safeText(model.value) === state.activeBigModel || false}">
                    ${safeText(model.label, model.value)}
                  </option>
                `)}
              `
              : html`<option value="">No installed eGPU models</option>`;
          }}
        </select>

        <label class="mm-filter-label" for="mm-favorite-model-select">Favorite Models</label>
        <select class="mm-select" id="mm-favorite-model-select" disabled="${() => getUserFavoriteModels(true).length === 0}">
          ${(() => {
            const favorites = getUserFavoriteModels(true);
            return favorites.length > 0
              ? html`
                <option value="">Choose a favorite</option>
                ${favorites.map(model => html`
                  <option value="${safeText(model.value)}">
                    ${safeText(model.label, model.value)}
                  </option>
                `)}
              `
              : html`<option value="">No installed favorites</option>`;
          })()}
        </select>

        <label class="mm-filter-label" for="mm-sort-mode-select">Sort</label>
        <select class="mm-select" id="mm-sort-mode-select">
          <option value="alphabetical" selected="${() => state.sortMode === "alphabetical" || false}">Alphabetical</option>
          <option value="release_date" selected="${() => state.sortMode === "release_date" || false}">Release Date</option>
        </select>

        <div class="mm-filter-break"></div>

        <label class="mm-filter-label" for="mm-user-filter-select">Your Favorite</label>
        <select class="mm-select" id="mm-user-filter-select">
          <option value="all" selected="${() => state.userFavoriteFilter === "all" || false}">All</option>
          <option value="yes" selected="${() => state.userFavoriteFilter === "yes" || false}">Yes</option>
          <option value="no" selected="${() => state.userFavoriteFilter === "no"}">No</option>
        </select>

        <label class="mm-filter-label" for="mm-community-filter-select">Community Favorite</label>
        <select class="mm-select" id="mm-community-filter-select">
          <option value="all" selected="${() => state.communityFavoriteFilter === "all" || false}">All</option>
          <option value="yes" selected="${() => state.communityFavoriteFilter === "yes" || false}">Yes</option>
          <option value="no" selected="${() => state.communityFavoriteFilter === "no"}">No</option>
        </select>

        <div class="mm-filter-break"></div>

        <label class="mm-filter-checkbox" for="mm-gpu-download-override">
          <input
            id="mm-gpu-download-override"
            type="checkbox"
            checked="${() => state.allowGpuDownloadsWithoutGpu || false}">
          Download GPU models without GPU
        </label>
        <span class="mm-chip mm-chip-warning">GPU models are very large and will not run without an external GPU.</span>
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
