import { html, reactive } from "/assets/vendor/arrow-core.js"

const state = reactive({
  loading: true,
  error: "",
  snapshot: [],
  sections: [],
  isOnroad: false,
  refreshing: false,
  busySection: "",
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

function buildReportText() {
  const lines = []
  lines.push("StarPilot Troubleshoot Report")
  lines.push(`Generated: ${new Date().toISOString()}`)
  lines.push(`Onroad: ${state.isOnroad ? "Yes" : "No"}`)
  lines.push("")
  lines.push("Snapshot")
  for (const item of state.snapshot) {
    lines.push(`- ${item.label}: ${formatValue(item.value)}`)
  }

  for (const section of state.sections) {
    lines.push("")
    lines.push(section.title)
    for (const item of section.items || []) {
      lines.push(`- ${item.label}: ${formatValue(item.value)} (default: ${formatValue(item.defaultValue)})`)
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
  const items = Array.isArray(section?.items) ? section.items : []
  return items.map((item) => html`
    <div class="troubleshootItemRow">
      <div class="troubleshootItemLabel">${item.label}</div>
      <div class="troubleshootItemValue">${formatValue(item.value)}</div>
      <div class="troubleshootItemDefault">${formatValue(item.defaultValue)}</div>
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
          </div>
          ${() => state.error ? html`<p class="troubleshootError"><strong>Error:</strong> ${state.error}</p>` : ""}
          <p class="troubleshootStatusLine"><strong>Onroad:</strong> ${state.isOnroad ? "Yes" : "No"}</p>
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

        ${() => state.sections.map((section) => html`
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
            <div class="troubleshootHeaderRow">
              <span>Setting</span>
              <span>Current</span>
              <span>Default</span>
            </div>
            ${itemRows(section)}
          </div>
        `)}
      ` : ""}
    </div>
  `
}
