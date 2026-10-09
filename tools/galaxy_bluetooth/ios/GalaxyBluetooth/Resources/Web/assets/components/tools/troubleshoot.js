import { html, reactive } from "/assets/vendor/arrow-core.js"

const state = reactive({
  loading: true,
  error: "",
  vehicleStatus: {
    available: false,
    summary: "",
    summarySeverity: "neutral",
    items: [],
  },
  snapshot: [],
  sections: [],
  isOnroad: false,
  refreshing: false,
  busySection: "",
  showNonDefaultOnly: false,
})

let initialized = false

function formatValue(value) {
  if (typeof value === "boolean") return value ? "On" : "Off"
  if (typeof value === "number") {
    if (Number.isInteger(value)) return String(value)
    return String(Number(value.toFixed(4)))
  }
  if (value === null || value === undefined) return "n/a"
  const text = String(value).trim()
  return text || "(empty)"
}

function formatLearnedValue(value) {
  if (value === null || value === undefined) return ""
  const text = String(value).trim()
  return text ? formatValue(value) : ""
}

function valuesMatch(left, right) {
  if (left === right) return true
  if ((left === null || left === undefined) && (right === null || right === undefined)) return true

  if (typeof left === "number" && typeof right === "number") {
    return Math.abs(left - right) < 1e-9
  }

  const leftText = String(left ?? "").trim()
  const rightText = String(right ?? "").trim()
  if (!leftText && !rightText) return true

  const leftNumber = Number(leftText)
  const rightNumber = Number(rightText)
  if (leftText !== "" && rightText !== "" && Number.isFinite(leftNumber) && Number.isFinite(rightNumber)) {
    return Math.abs(leftNumber - rightNumber) < 1e-9
  }

  return leftText === rightText
}

function isNonDefaultItem(item) {
  return !valuesMatch(item?.value, item?.defaultValue)
}

function getVisibleSectionItems(section) {
  const items = Array.isArray(section?.items) ? section.items : []
  if (!state.showNonDefaultOnly) return items
  return items.filter(isNonDefaultItem)
}

function getVisibleSections() {
  const sections = Array.isArray(state.sections) ? state.sections : []
  if (!state.showNonDefaultOnly) return sections
  return sections.filter((section) => getVisibleSectionItems(section).length > 0)
}

function countNonDefaultItems() {
  return (Array.isArray(state.sections) ? state.sections : []).reduce((count, section) => {
    const items = Array.isArray(section?.items) ? section.items : []
    return count + items.filter(isNonDefaultItem).length
  }, 0)
}

function statusBadgeClass(severity) {
  const safeSeverity = String(severity || "neutral").trim().toLowerCase()
  return `troubleshootStatusBadge troubleshootStatusBadge${safeSeverity.charAt(0).toUpperCase()}${safeSeverity.slice(1)}`
}

function buildReportText() {
  const lines = []
  lines.push("StarPilot Troubleshoot Report")
  lines.push(`Generated: ${new Date().toISOString()}`)
  lines.push(`Onroad: ${state.isOnroad ? "Yes" : "No"}`)
  lines.push(`Only non-default values: ${state.showNonDefaultOnly ? "Yes" : "No"}`)
  if (state.vehicleStatus?.summary) {
    lines.push("")
    lines.push("Vehicle Fault Status")
    lines.push(`Summary: ${state.vehicleStatus.summary}`)
    for (const item of state.vehicleStatus.items || []) {
      lines.push(`- ${item.label}: ${formatValue(item.value)}`)
    }
  }
  lines.push("")
  lines.push("Snapshot")
  for (const item of state.snapshot) {
    lines.push(`- ${item.label}: ${formatValue(item.value)}`)
  }

  for (const section of getVisibleSections()) {
    lines.push("")
    lines.push(section.title)
    for (const item of getVisibleSectionItems(section)) {
      const learnedSuffix = formatLearnedValue(item.learnedValue)
        ? `, learned: ${formatLearnedValue(item.learnedValue)}`
        : ""
      lines.push(`- ${item.label}: ${formatValue(item.value)} (default: ${formatValue(item.defaultValue)}${learnedSuffix})`)
    }
  }

  return lines.join("\n")
}

async function copyToClipboard() {
  const text = buildReportText()
  try {
    if (navigator?.clipboard?.writeText) {
      await navigator.clipboard.writeText(text)
    } else {
      const textArea = document.createElement("textarea")
      textArea.value = text
      textArea.style.position = "fixed"
      textArea.style.left = "-9999px"
      document.body.appendChild(textArea)
      textArea.focus()
      textArea.select()
      document.execCommand("copy")
      document.body.removeChild(textArea)
    }
    showSnackbar("Troubleshoot report copied to clipboard.", "", 2500, { key: "troubleshoot-copy" })
  } catch (error) {
    showSnackbar(error?.message || "Failed to copy report.", "error", 3000, { key: "troubleshoot-copy" })
  }
}

async function fetchTroubleshoot(showToast = false) {
  state.refreshing = true
  try {
    const response = await fetch("/api/troubleshoot")
    const payload = await response.json()
    if (!response.ok) {
      throw new Error(payload.error || response.statusText || "Failed to load troubleshoot data")
    }

    state.snapshot = Array.isArray(payload.snapshot) ? payload.snapshot : []
    state.sections = Array.isArray(payload.sections) ? payload.sections : []
    state.vehicleStatus = {
      available: !!payload.vehicleStatus?.available,
      summary: String(payload.vehicleStatus?.summary || ""),
      summarySeverity: String(payload.vehicleStatus?.summarySeverity || "neutral"),
      items: Array.isArray(payload.vehicleStatus?.items) ? payload.vehicleStatus.items : [],
    }
    state.isOnroad = !!payload.isOnroad
    state.error = ""

    if (showToast) {
      showSnackbar("Troubleshoot data refreshed.", "", 1800, { key: "troubleshoot-refresh" })
    }
  } catch (error) {
    const message = error?.message || "Failed to load troubleshoot data"
    state.error = message
    if (showToast) {
      showSnackbar(message, "error", 3000, { key: "troubleshoot-refresh" })
    }
  } finally {
    state.loading = false
    state.refreshing = false
  }
}

async function resetSection(section) {
  const sectionId = String(section?.id || "")
  if (!sectionId || state.busySection) return

  const sectionTitle = String(section?.title || "this section")
  if (!confirm(`Reset ${sectionTitle} to defaults?`)) return

  state.busySection = sectionId
  try {
    const response = await fetch("/api/troubleshoot/reset", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ sectionId }),
    })
    const payload = await response.json()
    if (!response.ok) {
      throw new Error(payload.error || response.statusText || "Failed to reset section")
    }

    showSnackbar(payload.message || `${sectionTitle} reset.`, "", 2500, { key: "troubleshoot-reset" })
    await fetchTroubleshoot(false)
  } catch (error) {
    showSnackbar(error?.message || "Failed to reset section.", "error", 3000, { key: "troubleshoot-reset" })
  } finally {
    state.busySection = ""
  }
}

function initialize() {
  if (initialized) return
  initialized = true
  fetchTroubleshoot(false)
}

function itemRows(section) {
  const items = getVisibleSectionItems(section)
  const rowClassName = section?.hasLearnedColumn ? "troubleshootItemRow troubleshootItemRowLearned" : "troubleshootItemRow"
  return items.map((item) => html`
    <div class="${`${rowClassName} ${isNonDefaultItem(item) ? "troubleshootItemRowChanged" : ""}`.trim()}">
      <div class="troubleshootItemLabel">
        <span>${item.label}</span>
        ${isNonDefaultItem(item) ? html`<span class="troubleshootChangedBadge">Changed</span>` : ""}
      </div>
      <div class="${`troubleshootItemValue ${isNonDefaultItem(item) ? "troubleshootItemValueChanged" : ""}`.trim()}">${formatValue(item.value)}</div>
      <div class="troubleshootItemDefault">${formatValue(item.defaultValue)}</div>
      ${section?.hasLearnedColumn ? html`<div class="troubleshootItemLearned">${formatLearnedValue(item.learnedValue)}</div>` : ""}
    </div>
  `)
}

export function Troubleshoot() {
  initialize()

  return html`
    <div class="troubleshootPage">
      <h2>Troubleshoot</h2>

      ${() => state.loading ? html`<div class="troubleshootCard">Loading troubleshoot data...</div>` : ""}

      ${() => !state.loading ? html`
        <div class="troubleshootCard">
          <p class="troubleshootIntro">
            Quick diagnostics snapshot for weird behavior reports and copy-ready debug logs.
          </p>
          <div class="troubleshootActionRow">
            <button class="troubleshootButton" disabled="${() => state.refreshing || false}" @click="${() => fetchTroubleshoot(true)}">              ${state.refreshing ? "Refreshing..." : "Refresh"}
            </button>
            <button class="troubleshootButton" @click="${copyToClipboard}">
              Copy to Clipboard
            </button>
            <label class="troubleshootToggle">
              <input
                type="checkbox"
                ?checked="${() => state.showNonDefaultOnly}"
                @change="${(e) => { state.showNonDefaultOnly = !!e.target.checked }}" />
              <span>Only non-default values</span>
            </label>
          </div>
          ${() => state.error ? html`<p class="troubleshootError"><strong>Error:</strong> ${state.error}</p>` : ""}
          <p class="troubleshootStatusLine"><strong>Onroad:</strong> ${state.isOnroad ? "Yes" : "No"}</p>
          <p class="troubleshootStatusLine"><strong>Changed Settings:</strong> ${() => countNonDefaultItems()}</p>
        </div>

        <div class="troubleshootCard">
          <div class="troubleshootSectionHeader">
            <h3>Vehicle Fault Status</h3>
            <span class="${() => statusBadgeClass(state.vehicleStatus?.available ? "ok" : state.vehicleStatus?.summarySeverity || "neutral")}">
              ${() => state.vehicleStatus?.available ? "Live" : "Unavailable"}
            </span>
          </div>
          <p class="troubleshootFaultSummary">${() => state.vehicleStatus?.summary || "Vehicle fault status unavailable."}</p>
          <div class="troubleshootFaultGrid">
            ${() => (state.vehicleStatus?.items || []).map((item) => html`
              <div class="troubleshootFaultItem">
                <div class="troubleshootFaultLabel">${item.label}</div>
                <div class="${() => statusBadgeClass(item.severity)}">${formatValue(item.value)}</div>
              </div>
            `)}
          </div>
        </div>

        <div class="troubleshootCard">
          <h3>Snapshot</h3>
          <div class="troubleshootHeaderRow troubleshootHeaderRowSnapshot">
            <span>Field</span>
            <span>Value</span>
          </div>
          ${() => state.snapshot.map((item) => html`
            <div class="troubleshootSnapshotRow">
              <div class="troubleshootItemLabel">${item.label}</div>
              <div class="troubleshootItemValue">${formatValue(item.value)}</div>
            </div>
          `)}
        </div>

        ${() => getVisibleSections().map((section) => html`
          <div class="troubleshootCard">
            <div class="troubleshootSectionHeader">
              <h3>${section.title}</h3>
              ${section.resettable ? html`
                <button
                  class="troubleshootButton troubleshootDanger"
                  disabled="${() => state.busySection === section.id || false}"
                  @click="${() => resetSection(section)}">                  ${state.busySection === section.id ? "Resetting..." : "Reset to Default"}
                </button>
              ` : ""}
            </div>
            <div class="${section?.hasLearnedColumn ? "troubleshootHeaderRow troubleshootHeaderRowLearned" : "troubleshootHeaderRow"}">
              <span>Setting</span>
              <span>Current</span>
              <span>Default</span>
              ${section?.hasLearnedColumn ? html`<span>Learned</span>` : ""}
            </div>
            ${itemRows(section)}
          </div>
        `)}

        ${() => state.showNonDefaultOnly && countNonDefaultItems() === 0 ? html`
          <div class="troubleshootCard">
            No settings are currently different from their defaults.
          </div>
        ` : ""}
      ` : ""}
    </div>
  `
}
