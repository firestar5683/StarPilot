import { html, reactive } from "/assets/vendor/arrow-core.js";

const REQUEST_TIMEOUT_MS = 15000;
const ACTIVE_POLL_INTERVAL_MS = 1000;
const IDLE_POLL_INTERVAL_MS = 4000;

const state = reactive({
  actionBusy: false,
  catalogLoaded: false,
  catalogSections: [],
  error: "",
  fetched: false,
  loadingCatalog: true,
  loadingStatus: true,
  savingSchedule: false,
  savingSelection: false,
  scheduleDraft: "2",
  scheduleSaved: "2",
  scheduleOptions: [],
  search: "",
  selectedDraft: [],
  selectedSaved: [],
  status: {
    cancelling: false,
    downloading: false,
    hasSelection: false,
    isOnroad: false,
    lastUpdate: "Never",
    mapsPresent: false,
    scheduleLabel: "Monthly",
    selectedCount: 0,
    storageBytes: 0,
    storageKnown: false,
    downloadProgress: {
      active: false,
      cancelled: false,
      completed: false,
      downloadedBytes: 0,
      downloadedFiles: 0,
      estimatedDownloadBytes: 0,
      estimateSource: "",
      etaSeconds: 0,
      percent: 0,
      phase: "idle",
      primaryLocation: "",
      storageKnown: false,
      totalFiles: 0,
    },
  },
  tokenLabels: {},
});

let pollingHandle = null;
let statusInFlight = false;

function notify(message, variant = "success") {
  if (typeof showSnackbar === "function") {
    showSnackbar(message, variant);
  } else if (variant === "error") {
    console.error(message);
  } else {
    console.log(message);
  }
}

function isMapsRouteActive() {
  return window.location.pathname === "/manage_maps";
}

function withTimeout(promise, timeoutMs, label) {
  return new Promise((resolve, reject) => {
    const timerId = setTimeout(() => reject(new Error(`${label} timed out`)), timeoutMs);
    promise.then((value) => {
      clearTimeout(timerId);
      resolve(value);
    }).catch((error) => {
      clearTimeout(timerId);
      reject(error);
    });
  });
}

async function fetchJson(url, options = {}) {
  const response = await withTimeout(fetch(url, options), REQUEST_TIMEOUT_MS, `${url} request`);
  const payload = await withTimeout(response.json(), REQUEST_TIMEOUT_MS, `${url} JSON parse`);
  if (!response.ok) {
    throw new Error(payload?.error || payload?.message || `Request failed (${response.status})`);
  }
  return payload;
}

function formatBytes(bytes) {
  const value = Number(bytes || 0);
  if (value <= 0) return "0 MB";
  const units = ["B", "KB", "MB", "GB", "TB"];
  const index = Math.min(Math.floor(Math.log(value) / Math.log(1024)), units.length - 1);
  const scaled = value / (1024 ** index);
  return `${scaled >= 10 || index === 0 ? scaled.toFixed(0) : scaled.toFixed(2)} ${units[index]}`;
}

function formatDuration(seconds) {
  const value = Math.max(0, Math.round(Number(seconds || 0)));
  if (value < 60) return `${value}s`;
  const minutes = Math.floor(value / 60);
  const remainingSeconds = value % 60;
  if (minutes < 60) return `${minutes}m ${remainingSeconds}s`;
  const hours = Math.floor(minutes / 60);
  return `${hours}h ${minutes % 60}m`;
}

function normalizeDownloadProgress(progress) {
  const value = progress && typeof progress === "object" ? progress : {};
  return {
    active: Boolean(value.active),
    cancelled: Boolean(value.cancelled),
    completed: Boolean(value.completed),
    downloadedBytes: Number(value.downloadedBytes || 0),
    downloadedFiles: Number(value.downloadedFiles || 0),
    estimatedDownloadBytes: Number(value.estimatedDownloadBytes || 0),
    estimateSource: String(value.estimateSource || ""),
    etaSeconds: Number(value.etaSeconds || 0),
    percent: Math.max(0, Math.min(100, Number(value.percent || 0))),
    phase: String(value.phase || "idle"),
    primaryLocation: String(value.primaryLocation || ""),
    storageKnown: Boolean(value.storageKnown),
    totalFiles: Number(value.totalFiles || 0),
  };
}

function uniqueSorted(values) {
  return [...new Set(values)].sort((a, b) => a.localeCompare(b, undefined, { sensitivity: "base" }));
}

function arraysEqual(a, b) {
  if (a.length !== b.length) return false;
  return a.every((value, index) => value === b[index]);
}

function selectionDirty() {
  return !arraysEqual(state.selectedDraft, state.selectedSaved);
}

function scheduleDirty() {
  return state.scheduleDraft !== state.scheduleSaved;
}

function getTokenLabel(token) {
  return state.tokenLabels[token] || token;
}

function setDraftSelection(nextSelection) {
  state.selectedDraft = uniqueSorted(nextSelection);
}

function toggleToken(token, enabled) {
  const next = new Set(state.selectedDraft);
  if (enabled) {
    next.add(token);
  } else {
    next.delete(token);
  }
  setDraftSelection([...next]);
}

function setGroup(group, enabled) {
  const next = new Set(state.selectedDraft);
  for (const region of group.regions || []) {
    if (enabled) {
      next.add(region.token);
    } else {
      next.delete(region.token);
    }
  }
  setDraftSelection([...next]);
}

function applyStatus(payload) {
  const hadSelectionChanges = selectionDirty();
  const hadScheduleChanges = scheduleDirty();
  const selectedLocations = Array.isArray(payload.selectedLocations) ? uniqueSorted(payload.selectedLocations) : [];
  state.status = {
    cancelling: Boolean(payload.cancelling),
    downloading: Boolean(payload.downloading),
    hasSelection: Boolean(payload.hasSelection),
    isOnroad: Boolean(payload.isOnroad),
    lastUpdate: payload.lastUpdate || "Never",
    mapsPresent: Boolean(payload.mapsPresent),
    scheduleLabel: payload.scheduleLabel || "Monthly",
    selectedCount: Number(payload.selectedCount || 0),
    storageBytes: Number(payload.storageBytes || 0),
    storageKnown: Boolean(payload.storageKnown),
    downloadProgress: normalizeDownloadProgress(payload.downloadProgress),
  };
  state.selectedSaved = selectedLocations;
  if (!hadSelectionChanges) {
    state.selectedDraft = selectedLocations;
  }

  const scheduleValue = String(payload.scheduleValue ?? "2");
  state.scheduleSaved = scheduleValue;
  if (!hadScheduleChanges) {
    state.scheduleDraft = scheduleValue;
  }
}

async function fetchCatalog() {
  const payload = await fetchJson("/api/maps/catalog");
  state.catalogSections = Array.isArray(payload.sections) ? payload.sections : [];
  state.scheduleOptions = Array.isArray(payload.scheduleOptions) ? payload.scheduleOptions : [];

  const tokenLabels = {};
  for (const section of state.catalogSections) {
    for (const group of section.groups || []) {
      for (const region of group.regions || []) {
        tokenLabels[region.token] = region.label;
      }
    }
  }
  state.tokenLabels = tokenLabels;
  state.catalogLoaded = true;
  state.loadingCatalog = false;
}

async function fetchStatus() {
  if (statusInFlight) return;
  statusInFlight = true;
  try {
    const payload = await fetchJson("/api/maps/status");
    applyStatus(payload);
    state.error = "";
  } catch (error) {
    state.error = error?.message || String(error);
  } finally {
    state.loadingStatus = false;
    statusInFlight = false;
  }
}

async function initializeMaps() {
  state.loadingCatalog = true;
  state.loadingStatus = true;
  try {
    await fetchCatalog();
    await fetchStatus();
  } catch (error) {
    state.error = error?.message || String(error);
    state.loadingCatalog = false;
    state.loadingStatus = false;
  }
}

function ensurePolling() {
  if (pollingHandle) return;

  const poll = async () => {
    if (!isMapsRouteActive()) {
      pollingHandle = null;
      return;
    }

    try {
      await fetchStatus();
    } finally {
      const nextDelay = state.status.downloading ? ACTIVE_POLL_INTERVAL_MS : IDLE_POLL_INTERVAL_MS;
      pollingHandle = setTimeout(poll, nextDelay);
    }
  };

  pollingHandle = setTimeout(poll, ACTIVE_POLL_INTERVAL_MS);
}

async function saveSelection() {
  if (state.savingSelection || !selectionDirty()) return;

  state.savingSelection = true;
  try {
    const payload = await fetchJson("/api/maps/selection", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ selectedLocations: state.selectedDraft }),
    });
    if (payload.status) {
      applyStatus(payload.status);
    }
    notify(payload.message || "Map selection saved.");
  } catch (error) {
    notify(error?.message || "Failed to save map selection.", "error");
  } finally {
    state.savingSelection = false;
  }
}

async function saveSchedule() {
  if (state.savingSchedule || !scheduleDirty()) return;

  state.savingSchedule = true;
  try {
    const payload = await fetchJson("/api/maps/schedule", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ schedule: state.scheduleDraft }),
    });
    if (payload.status) {
      applyStatus(payload.status);
    }
    notify(payload.message || "Map schedule updated.");
  } catch (error) {
    notify(error?.message || "Failed to update map schedule.", "error");
  } finally {
    state.savingSchedule = false;
  }
}

async function startDownload() {
  if (state.actionBusy || state.status.downloading || state.status.isOnroad || state.selectedDraft.length === 0) {
    return;
  }

  state.actionBusy = true;
  try {
    const payload = await fetchJson("/api/maps/download", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        selectedLocations: state.selectedDraft,
        schedule: state.scheduleDraft,
      }),
    });
    if (payload.status) {
      applyStatus(payload.status);
    }
    notify(payload.message || "Map download started.");
  } catch (error) {
    notify(error?.message || "Failed to start map download.", "error");
  } finally {
    state.actionBusy = false;
  }
}

async function cancelDownload() {
  if (state.actionBusy || !state.status.downloading) return;

  state.actionBusy = true;
  try {
    const payload = await fetchJson("/api/maps/cancel", { method: "POST" });
    if (payload.status) {
      applyStatus(payload.status);
    }
    notify(payload.message || "Map download cancellation requested.");
  } catch (error) {
    notify(error?.message || "Failed to cancel map download.", "error");
  } finally {
    state.actionBusy = false;
  }
}

async function removeMaps() {
  if (state.actionBusy || state.status.downloading || state.status.isOnroad || !state.status.mapsPresent) {
    return;
  }

  state.actionBusy = true;
  try {
    const payload = await fetchJson("/api/maps/remove", { method: "POST" });
    if (payload.status) {
      applyStatus(payload.status);
    }
    notify(payload.message || "Maps removed.");
  } catch (error) {
    notify(error?.message || "Failed to remove maps.", "error");
  } finally {
    state.actionBusy = false;
  }
}

function resetDraftSelection() {
  state.selectedDraft = [...state.selectedSaved];
}

function clearDraftSelection() {
  state.selectedDraft = [];
}

function getVisibleRegions(group) {
  const query = state.search.trim().toLowerCase();
  if (!query) return group.regions || [];

  return (group.regions || []).filter((region) => {
    const haystack = `${region.label} ${region.code} ${region.token}`.toLowerCase();
    return haystack.includes(query);
  });
}

function getVisibleSections() {
  return state.catalogSections.map((section) => {
    const groups = (section.groups || [])
      .map((group) => ({ ...group, visibleRegions: getVisibleRegions(group) }))
      .filter((group) => group.visibleRegions.length > 0);
    return { ...section, groups };
  }).filter((section) => section.groups.length > 0);
}

function selectedCountForGroup(group) {
  const groupTokens = new Set((group.regions || []).map((region) => region.token));
  return state.selectedDraft.filter((token) => groupTokens.has(token)).length;
}

function selectedCountForSection(section) {
  const sectionTokens = new Set(section.groups.flatMap((group) => (group.regions || []).map((region) => region.token)));
  return state.selectedDraft.filter((token) => sectionTokens.has(token)).length;
}

function renderSelectedSummary() {
  if (state.selectedDraft.length === 0) {
    return html`<p class="maps-muted">No regions selected.</p>`;
  }

  return html`
    <div class="maps-chip-list">
      ${state.selectedDraft.map((token) => html`<span class="maps-chip">${getTokenLabel(token)}</span>`)}
    </div>
  `;
}

function downloadSizeLabel() {
  const progress = state.status.downloadProgress;
  if (!selectionDirty() && progress.estimatedDownloadBytes > 0) {
    return `~${formatBytes(progress.estimatedDownloadBytes)} additional`;
  }
  if (state.selectedDraft.length > 0) {
    return "Not yet available";
  }
  return "Select regions";
}

function storageLabel() {
  return state.status.storageKnown ? formatBytes(state.status.storageBytes) : "Calculating…";
}

function renderDownloadProgress() {
  const progress = state.status.downloadProgress;
  const visible = state.status.downloading || (!selectionDirty() && (progress.completed || progress.cancelled || progress.estimatedDownloadBytes > 0));
  if (!visible) return "";

  const isActive = state.status.downloading;
  const title = isActive ? "Download Progress" : progress.completed ? "Last Download" : progress.cancelled ? "Download Cancelled" : "Download Estimate";
  const sizeLabel = progress.estimatedDownloadBytes > 0 ? `~${formatBytes(progress.estimatedDownloadBytes)} additional storage` : "Storage estimate unavailable";
  const storedLabel = progress.downloadedBytes > 0 ? `${formatBytes(progress.downloadedBytes)} added storage` : "Storage reconciles after completion";
  const filesLabel = progress.totalFiles > 0 ? `${progress.downloadedFiles} / ${progress.totalFiles} files` : "Waiting for map service...";
  const etaLabel = isActive && progress.etaSeconds > 0 ? `About ${formatDuration(progress.etaSeconds)} remaining` : "ETA unavailable until files start arriving";
  const sourceLabel = progress.estimateSource === "previous_additional_storage"
    ? "Estimate based on additional storage from the last download of this exact selection."
    : "File progress comes from mapd; storage is reconciled after the transfer ends.";

  return html`
    <div class="maps-progress-card">
      <div class="maps-progress-header">
        <strong>${title}</strong>
        <span>${Math.round(progress.percent)}%</span>
      </div>
      <div class="maps-progress-track" role="progressbar" aria-valuemin="0" aria-valuemax="100" aria-valuenow="${Math.round(progress.percent)}">
        <div class="maps-progress-fill" style="width: ${progress.percent}%;"></div>
      </div>
      <div class="maps-progress-meta">
        <span>${sizeLabel}</span>
        <span>${storedLabel}</span>
        <span>${filesLabel}</span>
        <span>${etaLabel}</span>
      </div>
      ${progress.primaryLocation ? html`<p class="maps-progress-location">Current region: ${progress.primaryLocation}</p>` : ""}
      <p class="maps-progress-note">${sourceLabel}</p>
    </div>
  `;
}

function renderGroup(group) {
  const selectedCount = selectedCountForGroup(group);

  return html`
    <article class="maps-group-card">
      <div class="maps-group-header">
        <div>
          <h3>${group.title}</h3>
          <p>${selectedCount} selected</p>
        </div>
        <div class="maps-group-actions">
          <button class="maps-btn maps-btn-secondary maps-btn-small" @click="${() => setGroup(group, true)}">Select All</button>
          <button class="maps-btn maps-btn-secondary maps-btn-small" @click="${() => setGroup(group, false)}">Clear</button>
        </div>
      </div>
      <div class="maps-region-list">
        ${group.visibleRegions.map((region) => html`
          <label class="maps-region-row">
            <input
              type="checkbox"
              checked="${() => state.selectedDraft.includes(region.token)}"
              @change="${(event) => toggleToken(region.token, event.target.checked)}"
            />
            <span class="maps-region-label">${region.label}</span>
            <span class="maps-region-code">${region.code}</span>
          </label>
        `)}
      </div>
    </article>
  `;
}

export function MapsManager() {
  if (!state.fetched) {
    state.fetched = true;
    initializeMaps();
  }
  ensurePolling();

  const visibleSections = () => getVisibleSections();

  return html`
    <div class="maps-page">
      <section class="maps-card maps-hero">
        <div class="maps-hero-copy">
          <h1>Maps</h1>
          <p>Select regions, start downloads, and manage offline maps entirely from Galaxy.</p>
        </div>
        <div class="maps-status-grid">
          <div class="maps-stat">
            <span class="maps-stat-label">Downloader</span>
            <span class="maps-stat-value">${() => state.loadingStatus ? "Checking..." : (state.status.downloading ? (state.status.cancelling ? "Cancelling" : "Downloading") : "Idle")}</span>
          </div>
          <div class="maps-stat">
            <span class="maps-stat-label">Saved Regions</span>
            <span class="maps-stat-value">${() => state.status.selectedCount}</span>
          </div>
          <div class="maps-stat">
            <span class="maps-stat-label">Additional Storage</span>
            <span class="maps-stat-value">${() => downloadSizeLabel()}</span>
          </div>
          <div class="maps-stat">
            <span class="maps-stat-label">Last Updated</span>
            <span class="maps-stat-value">${() => state.status.lastUpdate}</span>
          </div>
          <div class="maps-stat">
            <span class="maps-stat-label">Storage Used</span>
            <span class="maps-stat-value">${() => storageLabel()}</span>
          </div>
        </div>
        ${() => state.error ? html`<p class="maps-error">${state.error}</p>` : ""}
        ${() => state.status.isOnroad ? html`<p class="maps-warning">Map downloads and removal are blocked while driving.</p>` : ""}
        ${() => selectionDirty() ? html`<p class="maps-warning">You have unsaved region changes. Downloading now will use the current Galaxy selection.</p>` : ""}
        ${() => scheduleDirty() ? html`<p class="maps-warning">You have an unsaved schedule change. Downloading now will also apply it.</p>` : ""}
        ${() => renderDownloadProgress()}
        <div class="maps-action-row">
          <button
            class="maps-btn maps-btn-primary"
            @click="${() => state.status.downloading ? cancelDownload() : startDownload()}"
            disabled="${() => state.loadingStatus || state.actionBusy || state.status.isOnroad || (!state.status.downloading && state.selectedDraft.length === 0)}"
          >
            ${() => state.status.downloading ? (state.status.cancelling ? "Cancelling..." : "Cancel Download") : "Download Maps"}
          </button>
          <button
            class="maps-btn maps-btn-danger"
            @click="${removeMaps}"
            disabled="${() => state.loadingStatus || state.actionBusy || state.status.downloading || state.status.isOnroad || !state.status.mapsPresent}"
          >Remove Maps</button>
          <button
            class="maps-btn maps-btn-secondary"
            @click="${saveSelection}"
            disabled="${() => state.loadingCatalog || state.savingSelection || !selectionDirty()}"
          >${() => state.savingSelection ? "Saving..." : "Save Selection"}</button>
          <button class="maps-btn maps-btn-secondary" @click="${resetDraftSelection}" disabled="${() => !selectionDirty()}">Reset</button>
          <button class="maps-btn maps-btn-secondary" @click="${clearDraftSelection}" disabled="${() => state.selectedDraft.length === 0}">Clear All</button>
        </div>
      </section>

      <section class="maps-card maps-toolbar-card">
        <div class="maps-toolbar-row">
          <label class="maps-field maps-search-field">
            <span>Search Regions</span>
            <input
              class="maps-input"
              type="search"
              placeholder="Filter by name or code"
              value="${() => state.search}"
              @input="${(event) => { state.search = event.target.value; }}"
            />
          </label>
          <label class="maps-field maps-schedule-field">
            <span>Auto Update Schedule</span>
            <select class="maps-select" value="${() => state.scheduleDraft}" @change="${(event) => { state.scheduleDraft = event.target.value; }}">
              ${() => state.scheduleOptions.map((option) => html`<option value="${option.value}">${option.label}</option>`)}
            </select>
          </label>
          <button class="maps-btn maps-btn-secondary maps-schedule-button" @click="${saveSchedule}" disabled="${() => state.savingSchedule || !scheduleDirty()}">
            ${() => state.savingSchedule ? "Applying..." : "Apply Schedule"}
          </button>
        </div>
        <div class="maps-toolbar-meta">
          <span class="maps-muted">Saved schedule: ${() => state.status.scheduleLabel}</span>
          <span class="maps-muted">Draft regions: ${() => state.selectedDraft.length}</span>
        </div>
        <div class="maps-selected-summary">
          <h2>Selected Regions</h2>
          ${() => renderSelectedSummary()}
        </div>
      </section>

      ${() => state.loadingCatalog ? html`<section class="maps-card"><p class="maps-muted">Loading map catalog...</p></section>` : ""}
      ${() => !state.loadingCatalog && visibleSections().length === 0 ? html`<section class="maps-card"><p class="maps-muted">No regions match the current search.</p></section>` : ""}
      ${() => visibleSections().map((section) => html`
        <section class="maps-card maps-section-card">
          <div class="maps-section-header">
            <div>
              <h2>${section.title}</h2>
              <p>${selectedCountForSection(section)} selected</p>
            </div>
          </div>
          <div class="maps-group-grid">
            ${section.groups.map((group) => renderGroup(group))}
          </div>
        </section>
      `)}
    </div>
  `;
}
