import { html, reactive } from "/assets/vendor/arrow-core.js"
import { formatSecondsToHuman, isGalaxyTunnel } from "/assets/js/utils.js"
import { Modal } from "/assets/components/modal.js";

const logSelectorState = reactive({
  loading: false,
  files: [],
  logsLoadedOnce: false,
  showDeleteAllModal: false,
  logToDelete: null,
  logToRename: null,
  newName: ""
});

let liveEventSource = null;
let livePollTimer = null;
let tmuxLifecycleVersion = 0;
const REMOTE_POLL_INTERVAL_MS = 2000;
const TRANSPORT_LIFECYCLE_INTERVAL_MS = 500;

function isTmuxRouteActive() {
  return window.location.pathname === "/manage_tmux";
}

async function loadTmuxLogs() {
  if (logSelectorState.loading || logSelectorState.logsLoadedOnce) return;

  logSelectorState.loading = true;
  try {
    const res = await fetch("/api/tmux_log/list");
    if (!res.ok) throw new Error(await res.text());

    const data = await res.json();
    logSelectorState.files = data.map(f => {
      const date = new Date(f.timestamp * 1000);
      return {
        filename: f.filename,
        date: date.toLocaleString(),
        timeSince: (Date.now() - date.getTime()) / 1000,
      };
    });
  } catch (err) {
    showSnackbar(`Failed to fetch logs: ${err.message}`, "error");
    logSelectorState.files = [];
  } finally {
    logSelectorState.loading = false;
    logSelectorState.logsLoadedOnce = true;
  }
}

function TmuxLogSelector({ action, closeFn }) {
  loadTmuxLogs();

  async function handleFileClick(file) {
    if (action === "download") {
      const link = document.createElement("a");
      link.href = `/api/tmux_log/download/${encodeURIComponent(file.filename)}`;
      link.download = file.filename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);

    } else if (action === "rename") {
      logSelectorState.logToRename = file;
      logSelectorState.newName = file.filename;

    } else if (action === "delete") {
      logSelectorState.logToDelete = file;
    }
  }

  async function confirmDeleteFile() {
    const file = logSelectorState.logToDelete;
    if (!file) return;

    try {
      const res = await fetch(`/api/tmux_log/delete/${encodeURIComponent(file.filename)}`, {
        method: "DELETE"
      });
      if (!res.ok) throw new Error(await res.text());

      showSnackbar(`${file.filename} deleted successfully!`, "success");
      logSelectorState.files = logSelectorState.files.filter(f => f.filename !== file.filename);
      if (logSelectorState.files.length === 0) {
        logSelectorState.logsLoadedOnce = false;
      }
    } catch (err) {
      showSnackbar(`Delete failed: ${err.message}`, "error");
    } finally {
      logSelectorState.logToDelete = null;
    }
  }

  async function confirmRenameFile() {
    const file = logSelectorState.logToRename;
    let newName = logSelectorState.newName.trim();
    if (!newName.endsWith(".json")) {
      newName += ".json";
    }

    if (!file || !newName || newName === file.filename) {
      logSelectorState.logToRename = null;
      logSelectorState.newName = "";
      return;
    }

    try {
      const res = await fetch(`/api/tmux_log/rename/${encodeURIComponent(file.filename)}/${encodeURIComponent(newName)}`, {
        method: "PUT"
      });
      if (!res.ok) throw new Error(await res.text());

      showSnackbar(`${file.filename} renamed to ${newName}!`, "success");
      logSelectorState.files = logSelectorState.files.map(f =>
        f.filename === file.filename ? { ...f, filename: newName } : f
      );
    } catch (err) {
      showSnackbar(`Rename failed: ${err.message}`, "error");
    } finally {
      logSelectorState.logToRename = null;
      logSelectorState.newName = "";
    }
  }

  return html`
    <div class="tmux-log-selector-wrapper" @click="${(e) => e.target === e.currentTarget && closeFn()}">
      <div id="fileList">
        <div class="fileEntry header">
          <p>Filename</p>
          <p>Date</p>
          <p>Age</p>
        </div>

        ${() => {
      if (logSelectorState.loading && !logSelectorState.logsLoadedOnce) {
        return html`<div class="fileEntry"><p>Loading...</p></div>`;
      }
      if (logSelectorState.files.length === 0) {
        return html`<div class="fileEntry"><p>No tmux logs found!</p></div>`;
      }
      return logSelectorState.files.map(file => html`
            <div class="fileEntry" @click="${() => handleFileClick(file)}">
              <p><span class="label">Filename:</span> <span class="value">${file.filename}</span></p>
              <p><span class="label">Date:</span> <span class="value">${file.date}</span></p>
              <p><span class="label">Age:</span> <span class="value">${file.timeSince < 60 ? "just now" : `${formatSecondsToHuman(file.timeSince, "minutes")} ago`}</span></p>
            </div>
          `);
    }}

        <button @click="${closeFn}" class="cancel-button">Close</button>

        ${() => logSelectorState.logToDelete ? Modal({
      title: "Confirm Delete",
      message: `Are you sure you want to delete <strong>${logSelectorState.logToDelete.filename}</strong>?`,
      onConfirm: confirmDeleteFile,
      onCancel: () => { logSelectorState.logToDelete = null },
      confirmText: "Yes, Delete"
    }) : ""}

        ${() => logSelectorState.logToRename ? Modal({
      title: "Rename Log",
      message: html`
            <div>
              <p>Rename <strong>${logSelectorState.logToRename.filename}</strong> to:</p>
              <div style="margin-top: 10px;">
                <input
                  class="modal-input"
                  type="text"
                  value="${logSelectorState.newName}"
                  @click="${e => e.stopPropagation()}"
                  @input="${(e) => logSelectorState.newName = e.target.value}"
                />
              </div>
            </div>
          `,
      onConfirm: confirmRenameFile,
      onCancel: () => {
        logSelectorState.logToRename = null;
        logSelectorState.newName = "";
      },
      confirmText: "Rename",
      confirmClass: "btn-primary"
    }) : ""}
      </div>
    </div>
  `
}

export function TmuxLog() {
  const state = reactive({
    paused: false,
    latest: '',
    log: '',
    selectorAction: null,
    transport: "connecting",
  });
  const lifecycleVersion = ++tmuxLifecycleVersion;
  let lifecycleTimer = null;

  function applyIncomingLog(data) {
    state.latest = data || "";
    if (!state.paused) {
      state.log = state.latest;
    }
  }

  function stopLiveTransport() {
    if (liveEventSource) {
      liveEventSource.close();
      liveEventSource = null;
    }
    if (livePollTimer) {
      clearInterval(livePollTimer);
      livePollTimer = null;
    }
  }

  async function fetchSnapshot() {
    try {
      const response = await fetch("/api/tmux_log/snapshot");
      if (!response.ok) throw new Error(await response.text());
      const payload = await response.json();
      applyIncomingLog(payload?.data || "");
    } catch (err) {
      console.error("Error fetching tmux log snapshot:", err);
    }
  }

  function startPolling() {
    if (livePollTimer) return;
    if (liveEventSource) {
      liveEventSource.close();
      liveEventSource = null;
    }
    state.transport = "polling";
    fetchSnapshot();
    livePollTimer = setInterval(() => {
      if (!isTmuxRouteActive()) {
        stopLiveTransport();
        return;
      }
      if (document.visibilityState !== "visible") {
        return;
      }
      fetchSnapshot();
    }, REMOTE_POLL_INTERVAL_MS);
  }

  function startEventStream() {
    if (liveEventSource) return;
    if (livePollTimer) {
      clearInterval(livePollTimer);
      livePollTimer = null;
    }
    state.transport = "streaming";
    liveEventSource = new EventSource("/api/tmux_log/live");
    let receivedAnyMessage = false;

    liveEventSource.onmessage = e => {
      if (!isTmuxRouteActive() || document.visibilityState !== "visible") return;
      receivedAnyMessage = true;
      applyIncomingLog(e.data);
    };

    liveEventSource.onerror = err => {
      console.error("Error receiving tmux log stream:", err);
      if (!isTmuxRouteActive()) {
        stopLiveTransport();
        return;
      }
      startPolling();
    };

    // If SSE connects but no payload arrives quickly (common through tunnels), fallback.
    setTimeout(() => {
      if (!receivedAnyMessage && state.transport === "streaming" && isTmuxRouteActive()) {
        startPolling();
      }
    }, 3000);
  }

  function updateTransportForLifecycle() {
    if (lifecycleVersion !== tmuxLifecycleVersion) {
      stopLiveTransport();
      if (lifecycleTimer) {
        clearInterval(lifecycleTimer);
        lifecycleTimer = null;
      }
      return;
    }

    if (!isTmuxRouteActive()) {
      stopLiveTransport();
      state.transport = "inactive";
      if (lifecycleTimer) {
        clearInterval(lifecycleTimer);
        lifecycleTimer = null;
      }
      return;
    }

    if (document.visibilityState !== "visible") {
      stopLiveTransport();
      state.transport = "paused";
      return;
    }

    if (isGalaxyTunnel()) {
      startPolling();
      return;
    }

    if (!liveEventSource && !livePollTimer) {
      startEventStream();
    }
  }

  updateTransportForLifecycle();
  lifecycleTimer = setInterval(updateTransportForLifecycle, TRANSPORT_LIFECYCLE_INTERVAL_MS);

  function getStatusLabel() {
    if (state.transport === "polling") {
      return "Tmux Live Log (Remote Mode)";
    }
    if (state.transport === "streaming") {
      return "Tmux Live Log";
    }
    return "Tmux Live Log";
  }

  function togglePause() {
    state.paused = !state.paused;
    if (!state.paused) {
      state.log = state.latest;
    }
  }

  function captureLog() {
    fetch("/api/tmux_log/capture", { method: "POST" })
      .then(res => {
        if (!res.ok) return res.text().then(msg => { throw new Error(msg); });
        showSnackbar("Current session captured!", "success");
        logSelectorState.files = [];
        logSelectorState.logsLoadedOnce = false;
      })
      .catch(err => {
        showSnackbar(`Capture failed: ${err.message}`, "error");
      });
  }

  function downloadSessions() {
    state.selectorAction = "download";
  }

  function deleteSession() {
    state.selectorAction = "delete";
  }

  function confirmDeleteAllSessions() {
    logSelectorState.showDeleteAllModal = true;
  }

  function deleteAllSessions() {
    logSelectorState.showDeleteAllModal = false;
    fetch("/api/tmux_log/delete_all", { method: "DELETE" })
      .then(res => {
        if (!res.ok) return res.text().then(msg => { throw new Error(msg); });
        showSnackbar("All logs deleted successfully!", "success");
        logSelectorState.files = [];
        logSelectorState.logsLoadedOnce = false;
      })
      .catch(err => {
        showSnackbar(`Delete-all failed: ${err.message}`, "error");
      });
  }

  return html`
    <div class="tmux-block">
      <div class="tmux-wrapper">
        <div class="tmuxContainer">
          <div class="tmuxHeader">${() => getStatusLabel()}</div>
          <pre class="tmuxLog">${() => state.log}</pre>
        </div>
      </div>

      <div class="tmux-controls">
        <button class="tmux-control-button" @click="${captureLog}">💾 Capture Log</button>
        <button class="tmux-control-button" @click="${deleteSession}">🗑️ Delete Log</button>
        <button class="tmux-control-button" @click="${confirmDeleteAllSessions}">🧨 Delete All Logs</button>
        <button class="tmux-control-button" @click="${downloadSessions}">⬇️ Download Log</button>
        <button class="tmux-control-button" @click="${togglePause}">${() => state.paused ? "▶️ Resume Log" : "⏸️ Pause Log"}</button>
        <button class="tmux-control-button" @click="${() => state.selectorAction = 'rename'}">✏️ Rename Log</button>
      </div>

      ${() => state.selectorAction
      ? TmuxLogSelector({
        action: state.selectorAction,
        closeFn: () => (state.selectorAction = null)
      })
      : ""
    }

      ${() => logSelectorState.showDeleteAllModal ? Modal({
      title: "Delete All Logs",
      message: "Are you sure you want to delete all of your session logs?",
      onConfirm: deleteAllSessions,
      onCancel: () => { logSelectorState.showDeleteAllModal = false },
      confirmText: "Delete All"
    }) : ""}
    </div>
  `;
}
