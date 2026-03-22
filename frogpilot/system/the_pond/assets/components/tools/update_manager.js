import { html, reactive } from "/assets/vendor/arrow-core.js"

const state = reactive({
  loading: true,
  error: "",
  status: null,
  checkedForUpdates: false,
  checkBusy: false,
  updateBusy: false,
  toggleBusy: false,
  showAdvancedOptions: false,
  branches: [],
  selectedBranch: "",
  hasManualBranchSelection: false,
  branchesError: "",
  branchesBusy: false,
  switchBusy: false,
})

let initialized = false
let pollHandle = null
let reconnectPending = false
let rebootNoticeShown = false
const POLL_INTERVAL_MS = 1000
const ADVANCED_OPTIONS_KEY = "softwareShowAdvancedOptions"

function isUpdateRouteActive() {
  return window.location.pathname === "/manage_updates"
}

function shortHash(value) {
  const text = String(value || "").trim()
  return text ? text.slice(0, 10) : "Unknown"
}

function toPercent(value) {
  const n = Number(value)
  if (!Number.isFinite(n)) return 0
  return Math.max(0, Math.min(100, n))
}

function findBranchInList(branches, target) {
  const wanted = String(target || "").trim()
  if (!wanted || !Array.isArray(branches) || branches.length === 0) return ""
  if (branches.includes(wanted)) return wanted

  const wantedLower = wanted.toLowerCase()
  const caseInsensitive = branches.find((branch) => String(branch || "").toLowerCase() === wantedLower)
  return caseInsensitive || ""
}

function isSelectedBranchDifferent() {
  const currentBranch = String(state.status?.branch || "").trim()
  const selectedBranch = String(state.selectedBranch || "").trim()
  return !!currentBranch && !!selectedBranch && currentBranch !== selectedBranch
}

function normalizeGithubRemote(remoteValue, commitsUrlValue = "") {
  let remote = String(remoteValue || "").trim()
  if (!remote) {
    const commitsUrl = String(commitsUrlValue || "").trim()
    const marker = "/commits/"
    const markerIndex = commitsUrl.indexOf(marker)
    if (commitsUrl.startsWith("https://github.com/") && markerIndex > 0) {
      remote = commitsUrl.slice(0, markerIndex)
    } else {
      return ""
    }
  }

  if (remote.startsWith("git@github.com:")) {
    remote = `https://github.com/${remote.split(":", 2)[1] || ""}`
  } else if (remote.startsWith("ssh://git@github.com/")) {
    remote = `https://github.com/${remote.split("ssh://git@github.com/", 2)[1] || ""}`
  } else if (remote.startsWith("http://github.com/")) {
    remote = `https://github.com/${remote.split("http://github.com/", 2)[1] || ""}`
  }

  if (!remote.startsWith("https://github.com/")) return ""
  remote = remote.replace(/\/+$/, "")
  if (remote.endsWith(".git")) remote = remote.slice(0, -4)
  return remote
}

function currentOrSelectedBranchForCommits() {
  const selected = String(state.selectedBranch || "").trim()
  if (selected) return selected
  return String(state.status?.branch || "").trim()
}

function activeCommitsUrl() {
  const branch = currentOrSelectedBranchForCommits()
  if (!branch) return ""

  const remote = normalizeGithubRemote(state.status?.originRemote, state.status?.commitsUrl)
  if (!remote) return ""
  return `${remote}/commits/${encodeURIComponent(branch)}/`
}

function activeCommitsLabel() {
  const branch = currentOrSelectedBranchForCommits()
  return branch
    ? `View latest commit for the "${branch}" branch`
    : "View latest commit for this branch"
}

function shouldShowPrimaryUpdateAction() {
  if (state.status?.running) return true
  if (isSelectedBranchDifferent()) return true
  return !!state.checkedForUpdates && !!state.status?.updateAvailable
}

function shouldContinuePolling() {
  return !!state.status?.running || state.status?.stage === "rebooting" || reconnectPending
}

function shouldShowRebootNotice() {
  if (state.status?.stage === "rebooting") return true
  if (reconnectPending) return true
  const message = String(state.status?.message || "").toLowerCase()
  return message.includes("reboot")
}

function isHtmlLike(text) {
  const value = String(text || "").trim()
  return value.startsWith("<!DOCTYPE") || value.startsWith("<html") || value.startsWith("<")
}

async function readJsonPayload(response) {
  const bodyText = await response.text()
  if (!bodyText) return {}

  try {
    return JSON.parse(bodyText)
  } catch (parseError) {
    const error = new Error("Invalid JSON response")
    error.cause = parseError
    error.bodyText = bodyText
    throw error
  }
}

function setRebootingUiState(detail = "Reboot in progress...") {
  state.status = {
    ...(state.status || {}),
    running: false,
    stage: "rebooting",
    progressStep: 5,
    progressTotalSteps: state.status?.progressTotalSteps || 5,
    progressStepPercent: 100,
    progressPercent: 100,
    progressLabel: "Rebooting device",
    progressDetail: detail,
    message: "Update complete. Device is rebooting. Please wait...",
  }
  state.error = ""
}

function isRebootRelatedConnectionError(error) {
  const message = String(error?.message || "")
  return /Invalid JSON response|Unexpected token '<'|Failed to fetch|NetworkError|Load failed/i.test(message)
}

function stopPolling() {
  if (!pollHandle) return
  clearTimeout(pollHandle)
  pollHandle = null
}

function ensurePolling() {
  if (pollHandle) return

  const poll = async () => {
    if (!isUpdateRouteActive()) {
      pollHandle = null
      return
    }

    if (document.visibilityState !== "visible") {
      pollHandle = setTimeout(poll, POLL_INTERVAL_MS)
      return
    }

    await fetchStatus(false)
    if (shouldContinuePolling()) {
      pollHandle = setTimeout(poll, POLL_INTERVAL_MS)
    } else {
      pollHandle = null
    }
  }

  pollHandle = setTimeout(poll, POLL_INTERVAL_MS)
}

async function fetchStatus(showToast) {
  if (showToast) state.checkBusy = true
  try {
    const response = await fetch("/api/update/fast/status")
    const payload = await readJsonPayload(response)
    if (!response.ok) {
      throw new Error(payload.error || response.statusText || "Failed to load update status")
    }

    state.status = payload
    state.error = ""

    if (reconnectPending && !payload.running && payload.stage !== "rebooting") {
      reconnectPending = false
      rebootNoticeShown = false
      showSnackbar("Connection reestablished.")
    }

    if (payload.stage === "rebooting" && !rebootNoticeShown) {
      rebootNoticeShown = true
      showSnackbar("Device rebooting, please wait for reconnection...")
    }

    if (!state.selectedBranch && payload.branch) {
      state.selectedBranch = payload.branch
    }

    if (shouldContinuePolling()) {
      ensurePolling()
    } else {
      stopPolling()
    }

    if (showToast) {
      state.checkedForUpdates = true
      showSnackbar(payload.updateAvailable ? "Update available." : "No update available.")
    }
  } catch (error) {
    const isRebootTransitionError = !showToast
      && (state.status?.running || state.status?.stage === "rebooting" || reconnectPending)
      && (isHtmlLike(error?.bodyText) || isRebootRelatedConnectionError(error))

    if (isRebootTransitionError) {
      reconnectPending = true
      setRebootingUiState("Device rebooting, please wait for reconnection...")
      if (!rebootNoticeShown) {
        rebootNoticeShown = true
        showSnackbar("Device rebooting, please wait for reconnection...")
      }
      ensurePolling()
      return
    }

    const message = error?.message || String(error)
    state.error = message
    if (showToast) {
      showSnackbar(message, "error")
    }
  } finally {
    if (showToast) state.checkBusy = false
  }
}

async function fetchBranches(showToast = false) {
  state.branchesBusy = true
  try {
    const response = await fetch("/api/update/branches")
    const payload = await readJsonPayload(response)
    if (!response.ok) {
      throw new Error(payload.error || response.statusText || "Failed to load branches")
    }

    const branches = Array.isArray(payload.branches) ? payload.branches : []
    const currentBranchRaw = String(payload.currentBranch || state.status?.branch || "").trim()
    const matchedCurrentBranch = findBranchInList(branches, currentBranchRaw)
    state.branches = branches
    state.branchesError = payload.remoteError || ""

    if (branches.length === 0) {
      state.selectedBranch = currentBranchRaw
      state.hasManualBranchSelection = false
    } else if (matchedCurrentBranch && !state.hasManualBranchSelection) {
      // Default to the branch currently installed unless the user picked one explicitly.
      state.selectedBranch = matchedCurrentBranch
    } else if (!state.selectedBranch || !branches.includes(state.selectedBranch)) {
      state.selectedBranch = matchedCurrentBranch || branches[0]
      state.hasManualBranchSelection = false
    }

    if (showToast) {
      showSnackbar(branches.length ? `Loaded ${branches.length} branches.` : "No branches found.")
    }
  } catch (error) {
    const message = error?.message || "Failed to load branches"
    state.branchesError = message
    if (showToast) {
      showSnackbar(message, "error")
    }
  } finally {
    state.branchesBusy = false
  }
}

function setAdvancedOptions(enabled) {
  const next = !!enabled
  state.showAdvancedOptions = next

  if (!next) {
    const currentBranch = String(state.status?.branch || "").trim()
    if (currentBranch) {
      state.selectedBranch = currentBranch
    }
    state.hasManualBranchSelection = false
  }

  try {
    localStorage.setItem(ADVANCED_OPTIONS_KEY, next ? "1" : "0")
  } catch (error) {
    console.warn("Failed to persist advanced options preference", error)
  }

  if (next && state.branches.length === 0 && !state.branchesBusy) {
    fetchBranches(false)
  }
}

async function setAutomaticUpdates(enabled) {
  if (state.toggleBusy) return
  if (state.status?.isOnroad) {
    showSnackbar("Actions are blocked while onroad.", "error")
    return
  }
  state.toggleBusy = true
  try {
    const response = await fetch("/api/params", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ key: "AutomaticUpdates", value: !!enabled }),
    })
    const payload = await response.json()
    if (!response.ok) {
      throw new Error(payload.error || response.statusText || "Failed to update Automatic Updates")
    }

    state.status = { ...(state.status || {}), automaticUpdates: !!enabled }
    showSnackbar(payload.message || "Automatic updates updated.")
  } catch (error) {
    showSnackbar(error?.message || "Failed to update Automatic Updates", "error")
    await fetchStatus(false)
  } finally {
    state.toggleBusy = false
  }
}

async function runFastUpdate() {
  if (state.updateBusy) return
  if (state.status?.running) {
    showSnackbar("Fast update is already running.")
    return
  }
  if (state.status?.isOnroad) {
    showSnackbar("Actions are blocked while onroad.", "error")
    return
  }

  const confirmed = window.confirm(
    "Fast update warning:\n\n" +
    "- This update method skips backup creation.\n" +
    "- Your device will reboot when the update is done.\n\n" +
    "Continue with fast update?"
  )
  if (!confirmed) return

  state.updateBusy = true
  try {
    reconnectPending = false
    rebootNoticeShown = false
    const response = await fetch("/api/update/fast", { method: "POST" })
    const payload = await readJsonPayload(response)
    if (!response.ok) {
      throw new Error(payload.error || response.statusText || "Failed to start fast update")
    }

    state.status = {
      ...(state.status || {}),
      running: true,
      stage: "starting",
      progressStep: 1,
      progressTotalSteps: state.status?.progressTotalSteps || 5,
      progressStepPercent: 0,
      progressPercent: 0,
      progressLabel: "Preparing update",
      progressDetail: "Initializing update process...",
      message: payload.message || "Fast update started. Device will reboot when complete.",
      lastError: "",
    }
    state.error = ""
    showSnackbar(payload.message || "Fast update started.")
    await fetchStatus(false)
    ensurePolling()
  } catch (error) {
    showSnackbar(error?.message || "Failed to start fast update", "error")
  } finally {
    state.updateBusy = false
  }
}

async function runBranchSwitch() {
  if (state.switchBusy) return
  if (state.status?.running) {
    showSnackbar("An update action is already running.")
    return
  }
  if (state.status?.isOnroad) {
    showSnackbar("Actions are blocked while onroad.", "error")
    return
  }

  const targetBranch = String(state.selectedBranch || "").trim()
  if (!targetBranch) {
    showSnackbar("Select a target branch first.", "error")
    return
  }

  const currentBranch = String(state.status?.branch || "").trim()
  const actionLabel = currentBranch && currentBranch === targetBranch ? "update" : "switch and update"
  const confirmed = window.confirm(
    `This will ${actionLabel} to the '${targetBranch}' branch.\n\n` +
    "- This update method skips backup creation.\n" +
    "- Your device will reboot when the update is done.\n\n" +
    "Continue?"
  )
  if (!confirmed) return

  state.switchBusy = true
  try {
    reconnectPending = false
    rebootNoticeShown = false
    const response = await fetch("/api/update/branch", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ branch: targetBranch }),
    })
    const payload = await readJsonPayload(response)
    if (!response.ok) {
      throw new Error(payload.error || response.statusText || "Failed to start branch switch")
    }

    state.status = {
      ...(state.status || {}),
      running: true,
      stage: "starting",
      progressStep: 1,
      progressTotalSteps: state.status?.progressTotalSteps || 5,
      progressStepPercent: 0,
      progressPercent: 0,
      progressLabel: "Preparing branch switch",
      progressDetail: "Initializing branch switch...",
      message: payload.message || `Branch switch started for '${targetBranch}'. Device will reboot when complete.`,
      lastError: "",
    }
    state.error = ""
    showSnackbar(payload.message || "Branch switch started.")
    await fetchStatus(false)
    ensurePolling()
  } catch (error) {
    showSnackbar(error?.message || "Failed to start branch switch", "error")
  } finally {
    state.switchBusy = false
  }
}

function initialize() {
  if (initialized) return
  initialized = true

  try {
    state.showAdvancedOptions = localStorage.getItem(ADVANCED_OPTIONS_KEY) === "1"
  } catch (error) {
    state.showAdvancedOptions = false
  }

  const initTasks = [fetchStatus(false)]
  if (state.showAdvancedOptions) {
    initTasks.push(fetchBranches(false))
  }

  Promise.all(initTasks).finally(() => {
    state.loading = false
  })
}

export function UpdateManager() {
  initialize()

  return html`
    <div class="updateManager">
      <h2>Software</h2>

      ${() => state.loading ? html`<div class="updateCard">Loading update status...</div>` : ""}
      ${() => !state.loading ? html`
        <div class="updateCard">
          <div class="updateGrid">
            <p><strong>Current Branch:</strong> ${state.status?.branch || "Unknown"}</p>
            <p><strong>Installed Commit:</strong> ${shortHash(state.status?.localCommit)}</p>
            <p><strong>Latest Commit:</strong> ${shortHash(state.status?.remoteCommit)}</p>
            <p><strong>Update Available:</strong> ${state.status?.updateAvailable ? "Yes" : "No"}</p>
            <p><strong>Status:</strong> ${state.status?.stage || "idle"}</p>
            <p><strong>Onroad:</strong> ${state.status?.isOnroad ? "Yes" : "No"}</p>
          </div>

          <div class="updateProgressCard">
            <div class="updateProgressHeader">
              <span>
                Step ${state.status?.progressStep || 0}/${state.status?.progressTotalSteps || 5}:
                ${state.status?.progressLabel || "Idle"}
              </span>
              <span>${Math.round(toPercent(state.status?.progressPercent))}%</span>
            </div>
            <div class="updateProgressTrack ${state.status?.stage === "error" ? "error" : ""}">
              <div class="updateProgressFill ${state.status?.stage === "error" ? "error" : ""}" style="width: ${toPercent(state.status?.progressPercent)}%;"></div>
            </div>
            ${() => state.status?.progressDetail ? html`<p class="updateProgressDetail ${state.status?.stage === "error" ? "error" : ""}">${state.status.progressDetail}</p>` : ""}
          </div>

          ${() => state.status?.isOnroad ? html`<p class="updateWarning"><strong>Onroad: actions disabled</strong></p>` : ""}

          <label class="updateToggleRow">
            <span>Automatically install updates</span>
            <input
              type="checkbox"
              class="ds-toggle"
              checked="${() => !!state.status?.automaticUpdates || false}"
              disabled="${() => !!state.status?.isOnroad || state.toggleBusy || !!state.status?.running || false}"
              @change="${(event) => setAutomaticUpdates(!!event.target.checked)}"
            />
          </label>

          <label class="updateToggleRow updateAdvancedToggle">
            <span>Show advanced options</span>
            <input
              type="checkbox"
              class="ds-toggle"
              checked="${() => state.showAdvancedOptions || false}"
              @change="${(event) => setAdvancedOptions(!!event.target.checked)}"
            />
          </label>

          ${() => state.showAdvancedOptions ? html`
            <div class="updateBranchSection">
              <div class="updateBranchHeader">
                <strong>Branch switching</strong>
                ${state.branchesBusy ? html`<span>Loading...</span>` : ""}
              </div>
              <p class="updateAdvancedNote">
                For advanced users only. Switching to test/dev branches can introduce instability.
              </p>
              <div class="updateBranchRow">
                <select
                  class="updateSelect"
                  disabled="${() => !!state.status?.isOnroad || !!state.status?.running || state.switchBusy || state.branchesBusy || state.branches.length === 0 || false}"
                  @change="${(event) => {
                    state.selectedBranch = String(event.target.value || "")
                    state.hasManualBranchSelection = true
                  }}">
                  ${() => state.branches.length
                    ? state.branches.map((branch) => html`<option value="${branch}" selected="${() => branch === state.selectedBranch || false}">${branch}${branch === state.status?.branch ? " (current)" : ""}</option>`)
                    : html`<option value="">No branches found</option>`
                  }
                </select>
                <button
                  class="updateButton"
                  disabled="${() => state.branchesBusy || !!state.status?.running || false}"
                  @click="${() => fetchBranches(true)}">
                  ${state.branchesBusy ? "Refreshing..." : "Refresh Branches"}
                </button>
              </div>
              ${() => state.branchesError ? html`<p class="updateError"><strong>Branch List:</strong> ${state.branchesError}</p>` : ""}
            </div>
          ` : ""}

          ${() => state.status?.message && state.status?.stage !== "rebooting" ? html`<p class="updateMessage">${state.status.message}</p>` : ""}
          ${() => state.status?.remoteError ? html`<p class="updateError"><strong>Remote Check:</strong> ${state.status.remoteError}</p>` : ""}
          ${() => state.status?.lastError ? html`<p class="updateError"><strong>Last Error:</strong> ${state.status.lastError}</p>` : ""}
          ${() => state.error ? html`<p class="updateError"><strong>Error:</strong> ${state.error}</p>` : ""}

          <div class="updateActions">
            ${() => !isSelectedBranchDifferent() ? html`
              <button class="updateButton" @click="${() => fetchStatus(true)}">
                ${state.checkBusy ? "Checking..." : "Check for Updates"}
              </button>
            ` : ""}
            ${() => shouldShowPrimaryUpdateAction() ? html`
              <button
                class="updateButton danger"
                disabled="${() => !!state.status?.isOnroad || !!state.status?.running || (isSelectedBranchDifferent() ? state.switchBusy : state.updateBusy) || false}"
                @click="${() => isSelectedBranchDifferent() ? runBranchSwitch() : runFastUpdate()}">
                ${state.status?.running
                  ? "Update Running..."
                  : (isSelectedBranchDifferent()
                    ? (state.switchBusy ? "Starting..." : "Switch + Update")
                    : (state.updateBusy ? "Starting..." : "Fast Update (No Backup)"))}
              </button>
            ` : ""}
          </div>
          ${() => !state.status?.running && !shouldShowPrimaryUpdateAction()
            ? html`<p class="updateHint">Run <strong>Check for Updates</strong> first, or select a different branch in advanced options.</p>`
            : ""}
          ${() => shouldShowRebootNotice()
            ? html`<p class="updateHint updateRebootNotice">Device rebooting, please wait for reconnection...</p>`
            : ""}
          ${() => activeCommitsUrl() ? html`
            <div class="updateFooter">
              <a class="updateLink" href="${activeCommitsUrl()}" target="_blank" rel="noopener noreferrer">
                ${activeCommitsLabel()}
              </a>
            </div>
          ` : ""}
        </div>
      ` : ""}
    </div>
  `
}
