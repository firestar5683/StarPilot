import { html } from "/assets/vendor/arrow-core.js";

const HOME_STATE = {
  status: "loading",
  data: null,
  unit: "miles",
  error: "",
  initialized: false,
  refreshTimer: null,
};

const FAVORITE_COLORS = ["#5ec8c8", "#8b6cc5", "#d4a060", "#e05577", "#6cc56e", "#8aa3ff"];
const TOP_MODEL_LIMIT = 3;

function withTimeout(promise, timeoutMs, label) {
  return new Promise((resolve, reject) => {
    const timerId = setTimeout(() => reject(new Error(`${label} timed out`)), timeoutMs);
    promise.then((value) => {
      clearTimeout(timerId);
      resolve(value);
    }).catch((err) => {
      clearTimeout(timerId);
      reject(err);
    });
  });
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function safeUrl(value) {
  const text = String(value ?? "").trim();
  return text.startsWith("https://github.com/") ? text : "";
}

function numberValue(value, fallback = 0) {
  const n = Number(value);
  return Number.isFinite(n) ? n : fallback;
}

function formatInt(value) {
  return Math.round(numberValue(value)).toLocaleString("en-US", { maximumFractionDigits: 0 });
}

function formatOneDecimal(value) {
  return numberValue(value).toLocaleString("en-US", { maximumFractionDigits: 1 });
}

function formatPercent(value) {
  return `${Math.max(0, Math.min(100, Math.round(numberValue(value))))}%`;
}

function formatDuration(seconds) {
  const total = Math.max(0, Math.round(numberValue(seconds)));
  const hours = Math.floor(total / 3600);
  const minutes = Math.floor((total % 3600) / 60);
  if (hours > 0) return `${hours}h ${minutes}m`;
  return `${minutes}m`;
}

function formatDate(value) {
  if (!value) return "No drives yet";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value);
  return date.toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

function formatDriveTimeRange(startValue, endValue) {
  if (!startValue) return "No drives yet";
  const start = new Date(startValue);
  const end = new Date(endValue);
  if (Number.isNaN(start.getTime())) return String(startValue);
  if (Number.isNaN(end.getTime()) || end <= start) return formatDate(startValue);

  const dateLabel = start.toLocaleDateString("en-US", { month: "short", day: "numeric" });
  const startTime = start.toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit" });
  const endTime = end.toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit" });
  if (start.toDateString() === end.toDateString()) {
    return `${dateLabel}, ${startTime}-${endTime}`;
  }

  const endDateLabel = end.toLocaleDateString("en-US", { month: "short", day: "numeric" });
  return `${dateLabel}, ${startTime}-${endDateLabel}, ${endTime}`;
}

function formatBytes(bytes) {
  const value = Math.max(0, numberValue(bytes));
  if (value >= 2 ** 30) return `${formatOneDecimal(value / (2 ** 30))} GB`;
  if (value >= 2 ** 20) return `${formatOneDecimal(value / (2 ** 20))} MB`;
  return `${formatInt(value / 1024)} KB`;
}

function statBlock(title, stats = {}, unit) {
  return `
    <section class="dashboard-card dashboard-summary-card">
      <h2>${escapeHtml(title)}</h2>
      <div class="dashboard-stat-row">
        <div><strong>${formatInt(stats.drives)}</strong><span>drives</span></div>
        <div><strong>${formatOneDecimal(stats.distance)}</strong><span>${escapeHtml(stats.unit || unit)}</span></div>
        <div><strong>${formatOneDecimal(stats.hours)}</strong><span>hours</span></div>
      </div>
    </section>
  `;
}

function fallbackDashboard(data, unit) {
  const disk = Array.isArray(data?.diskUsage) ? data.diskUsage[0] : {};
  const usedText = String(disk?.used || "0 GB");
  const sizeText = String(disk?.size || "0 GB");
  return {
    lastDrive: {
      date: "",
      distance: 0,
      duration: 0,
      avgSpeed: 0,
      engagedPercent: 0,
      model: "Unknown model",
      segmentCount: 0,
      distractedMoments: 0,
      unresponsiveMoments: 0,
      attentionKnown: true,
      distanceUnit: unit,
      speedUnit: unit === "kilometers" ? "kph" : "mph",
    },
    recentDrives: [],
    week: {
      distance: 0,
      duration: 0,
      hours: 0,
      drives: 0,
      engagedPercent: 0,
      dailyDistance: [],
      distanceUnit: unit,
    },
    records: {
      longestDrive: { value: "0", detail: unit },
      mostEngagedDay: { value: "0%", detail: "No drives" },
      bestWeek: { value: "0", detail: unit },
      highestStreak: { value: "0 days", detail: "No drives" },
      longestUndistractedDrive: { value: "0.0 hours", detail: "No clean drives" },
      cleanDriveStreak: { value: "0 drives", detail: "No clean drives" },
    },
    device: { status: "Parked", online: true, uptimeSeconds: null, cpuTempC: null, gpuTempC: null },
    storage: {
      freeBytes: 0,
      usedBytes: 0,
      totalBytes: 0,
      usedPercent: Number.parseFloat(disk?.usedPercentage) || 0,
      legacyText: `${usedText} used of ${sizeText}`,
      segmentCounts: { standard: 0, highResolution: 0, alternate: 0 },
    },
    favoriteModels: [],
  };
}

function driveStatsReady(drive) {
  return drive?.ignored === true || drive?.attentionKnown !== false;
}

function dashboardPendingDriveCount(dashboard) {
  const recent = Array.isArray(dashboard?.recentDrives) ? dashboard.recentDrives : [];
  return recent.filter(drive => !driveStatsReady(drive)).length;
}

function dashboardShouldAutoRefresh(dashboard) {
  const analysis = dashboard?.analysis || {};
  return Boolean(analysis.running)
    || numberValue(analysis.pendingRoutes) > 0
    || dashboardPendingDriveCount(dashboard) > 0;
}

function clearDashboardRefreshTimer() {
  if (HOME_STATE.refreshTimer) {
    clearTimeout(HOME_STATE.refreshTimer);
    HOME_STATE.refreshTimer = null;
  }
}

function scheduleDashboardRefresh(dashboard) {
  clearDashboardRefreshTimer();
  if (!dashboardShouldAutoRefresh(dashboard)) return;
  HOME_STATE.refreshTimer = setTimeout(() => initializeHome(false), 3500);
}

function renderAnalysisStatus(dashboard) {
  const analysis = dashboard?.analysis || {};
  const pendingRoutes = Math.max(0, Math.round(numberValue(analysis.pendingRoutes)));
  const pendingDrives = dashboardPendingDriveCount(dashboard);
  const count = Math.max(pendingRoutes, pendingDrives);
  if (!analysis.running && count <= 0) return "";

  const runningCount = count || Math.max(1, Math.round(numberValue(analysis.batchSize)));
  const label = analysis.running
    ? `Analyzing ${runningCount} ${runningCount === 1 ? "drive" : "drives"}`
    : `${count} ${count === 1 ? "drive" : "drives"} queued`;

  return `
    <div class="dashboard-analysis-status">
      <i class="bi bi-hourglass-split"></i>
      <span>${escapeHtml(label)}</span>
    </div>
  `;
}

function renderLastDrive(drive) {
  const ready = driveStatsReady(drive);
  return `
    <section class="dashboard-card dashboard-last-drive">
      <div class="dashboard-card-kicker"><span></span>Last drive</div>
      <div class="dashboard-drive-date">${escapeHtml(formatDriveTimeRange(drive.date, drive.endDate))}</div>
      <div class="dashboard-drive-metrics">
        <div><strong>${ready ? formatOneDecimal(drive.distance) : "..."}</strong><span>${ready ? escapeHtml(drive.distanceUnit || "miles") : "analyzing"}</span></div>
        <div><strong>${formatDuration(drive.duration)}</strong><span>duration</span></div>
        <div><strong>${ready ? formatInt(drive.avgSpeed) : "..."}</strong><span>${ready ? `${escapeHtml(drive.speedUnit || "mph")} avg` : "speed"}</span></div>
        <div><strong>${ready ? formatPercent(drive.engagedPercent) : "..."}</strong><span>engaged</span></div>
      </div>
      <div class="dashboard-drive-footer">
        <span><i class="bi bi-cpu"></i>${escapeHtml(drive.model || "Unknown model")}</span>
        ${ready
          ? `<span><i class="bi bi-eye"></i>${formatInt(drive.distractedMoments)} distracted</span>
             <span><i class="bi bi-exclamation-triangle"></i>${formatInt(drive.unresponsiveMoments)} unresponsive</span>`
          : `<span><i class="bi bi-hourglass-split"></i>Analyzing stats</span>`}
      </div>
    </section>
  `;
}

function renderWeekChart(week) {
  const days = Array.isArray(week.dailyDistance) && week.dailyDistance.length
    ? week.dailyDistance
    : ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"].map(label => ({ label, distance: 0 }));
  const maxDistance = Math.max(1, ...days.map(day => numberValue(day.distance)));
  const bars = days.map(day => {
    const height = Math.max(4, (numberValue(day.distance) / maxDistance) * 100);
    return `
      <div class="dashboard-day">
        <div class="dashboard-day-bar" style="height:${height}%"></div>
        <span>${escapeHtml(day.label)}</span>
      </div>
    `;
  }).join("");

  return `
    <section class="dashboard-card dashboard-week">
      <h2>This week</h2>
      <div class="dashboard-week-top">
        <div class="dashboard-donut" style="--value:${Math.max(0, Math.min(100, numberValue(week.engagedPercent)))}">
          <strong>${formatPercent(week.engagedPercent)}</strong>
          <span>engaged</span>
        </div>
        <div class="dashboard-week-metrics">
          <div><strong>${formatOneDecimal(week.distance)}</strong><span>${escapeHtml(week.distanceUnit || "miles")}</span></div>
          <div><strong>${formatOneDecimal(week.hours)}</strong><span>hours</span></div>
          <div><strong>${formatInt(week.drives)}</strong><span>drives</span></div>
        </div>
      </div>
      <h3>Distance per day</h3>
      <div class="dashboard-bars">${bars}</div>
    </section>
  `;
}

function recordRow(icon, title, record) {
  return `
    <div class="dashboard-record-row">
      <span><i class="bi ${icon}"></i></span>
      <div>
        <p>${escapeHtml(title)}</p>
        <strong>${escapeHtml(record?.value ?? "0")}</strong>
        <small>${escapeHtml(record?.detail ?? "")}</small>
      </div>
    </div>
  `;
}

function renderRecords(records) {
  return `
    <section class="dashboard-card dashboard-records">
      <h2>Personal records</h2>
      ${recordRow("bi-arrow-right", "Longest drive", records.longestDrive)}
      ${recordRow("bi-check2-circle", "Most-engaged day", records.mostEngagedDay)}
      ${recordRow("bi-graph-up-arrow", "Best week", records.bestWeek)}
      ${recordRow("bi-lightning-charge", "Highest streak", records.highestStreak)}
      ${recordRow("bi-shield-check", "Longest undistracted drive", records.longestUndistractedDrive)}
      ${recordRow("bi-stars", "Clean-drive streak", records.cleanDriveStreak)}
    </section>
  `;
}

function renderRecentDrives(drives) {
  if (!Array.isArray(drives) || drives.length === 0) {
    return `
      <section class="dashboard-card dashboard-recent">
        <h2>Recent drives</h2>
        <div class="dashboard-empty">No local drives found yet.</div>
      </section>
    `;
  }

  const rows = drives.map(drive => {
    const ignored = drive?.ignored === true;
    const ready = driveStatsReady(drive);
    const routeNames = Array.isArray(drive?.routeNames) ? drive.routeNames.filter(Boolean) : [];
    return `
    <div class="dashboard-drive-row ${ready ? "" : "is-pending"} ${ignored ? "is-ignored" : ""}">
      <div class="dashboard-drive-main">
        <strong>${escapeHtml(formatDriveTimeRange(drive.date, drive.endDate))}</strong>
        <span>${escapeHtml(drive.model || "Unknown model")}</span>
      </div>
      <div class="dashboard-drive-details">
        <span>${ignored && drive.attentionKnown === false ? "Stats excluded" : (ready ? `${formatOneDecimal(drive.distance)} ${escapeHtml(drive.distanceUnit || "miles")}` : "Analyzing stats")}</span>
        <span>${formatDuration(drive.duration)}</span>
      </div>
      <div class="dashboard-attention">
        ${ignored
          ? `<span><i class="bi bi-eye-slash"></i> Ignored from stats</span>`
          : ready
          ? `<span>${formatInt(drive.distractedMoments)} distracted</span><span>${formatInt(drive.unresponsiveMoments)} unresponsive</span>`
          : `<span>Waiting for full route analysis</span>`}
      </div>
      <div class="dashboard-engaged-cell">
        <div class="dashboard-mini-bar"><span style="width:${ready && !ignored ? Math.max(0, Math.min(100, numberValue(drive.engagedPercent))) : 0}%"></span></div>
        <strong>${ignored ? "Excluded" : (ready ? `${formatPercent(drive.engagedPercent)} engaged` : "Pending")}</strong>
      </div>
      ${routeNames.length === 0 ? "" : `
        <div class="dashboard-drive-actions">
          <button
            class="dashboard-drive-stats-action"
            data-action="${ignored ? "include" : "ignore"}"
            data-route-names="${escapeHtml(JSON.stringify(routeNames))}"
            title="${ignored ? "Include this drive in local dashboard statistics" : "Exclude this drive from local dashboard statistics"}">
            <i class="bi ${ignored ? "bi-arrow-counterclockwise" : "bi-eye-slash"}"></i>
            <span>${ignored ? "Include drive stats" : "Ignore drive stats"}</span>
          </button>
        </div>
      `}
    </div>
  `;
  }).join("");

  return `
    <section class="dashboard-card dashboard-recent">
      <h2>Recent drives</h2>
      ${rows}
    </section>
  `;
}

function favoriteChart(models) {
  if (!Array.isArray(models) || models.length === 0) {
    return {
      style: "background: conic-gradient(var(--dashboard-track) 0 100%)",
      rows: `<div class="dashboard-empty">No model usage recorded yet.</div>`,
    };
  }

  const topModels = models.slice(0, TOP_MODEL_LIMIT);
  const total = topModels.reduce((sum, model) => sum + Math.max(1, numberValue(model.weight)), 0);
  let start = 0;
  const segments = topModels.map((model, index) => {
    const end = start + (Math.max(1, numberValue(model.weight)) / total) * 100;
    const segment = `${FAVORITE_COLORS[index]} ${start}% ${end}%`;
    start = end;
    return segment;
  });

  const rows = topModels.map((model, index) => `
    <div class="dashboard-model-row">
      <span class="dashboard-swatch" style="background:${FAVORITE_COLORS[index]}"></span>
      <div>
        <strong>${escapeHtml(model.name)}</strong>
        <small>${formatInt(model.drives)} ${numberValue(model.drives) === 1 ? "drive" : "drives"} using this model</small>
      </div>
    </div>
  `).join("");

  return {
    style: `background: conic-gradient(${segments.join(", ")})`,
    rows,
  };
}

function renderFavoriteModels(models) {
  const chart = favoriteChart(models);
  return `
    <section class="dashboard-card dashboard-models">
      <h2>Most used models</h2>
      <div class="dashboard-model-layout">
        <div class="dashboard-favorite-donut" style="${chart.style}"></div>
        <div class="dashboard-model-list">${chart.rows}</div>
      </div>
    </section>
  `;
}

function renderStorage(storage) {
  const usedPercent = Math.max(0, Math.min(100, numberValue(storage.usedPercent)));
  const counts = storage.segmentCounts || {};
  const summary = storage.legacyText || `${formatBytes(storage.usedBytes)} used of ${formatBytes(storage.totalBytes)}`;
  return `
    <section class="dashboard-card dashboard-device-card">
      <h2>Storage</h2>
      <p class="dashboard-muted">${escapeHtml(summary)}</p>
      <div class="dashboard-storage-track"><span style="width:${usedPercent}%"></span></div>
      <div class="dashboard-key-values">
        <div><span>Dashcam footage</span><strong>${formatInt(counts.standard)} segments</strong></div>
        <div><span>High-resolution footage</span><strong>${formatInt(counts.highResolution)} segments</strong></div>
        <div><span>Konik footage</span><strong>${formatInt(counts.alternate)} segments</strong></div>
        <div><span>Free space</span><strong>${formatBytes(storage.freeBytes)}</strong></div>
      </div>
    </section>
  `;
}

function renderVitals(device) {
  const uptime = device.uptimeSeconds == null ? "unknown" : formatDuration(device.uptimeSeconds);
  const cpu = device.cpuTempC == null ? "unknown" : `${formatInt(device.cpuTempC)} C`;
  const gpu = device.gpuTempC == null ? "unknown" : `${formatInt(device.gpuTempC)} C`;
  const lanIp = device.lanIp || "unknown";
  const networkName = device.networkName || "No wireless connectivity";
  return `
    <section class="dashboard-card dashboard-device-card">
      <h2>Vitals</h2>
      <div class="dashboard-key-values">
        <div><span>Status</span><strong>${escapeHtml(device.status || "Parked")}</strong></div>
        <div><span>LAN IP</span><strong>${escapeHtml(lanIp)}</strong></div>
        <div><span>Network</span><strong>${escapeHtml(networkName)}</strong></div>
        <div><span>Uptime</span><strong>${escapeHtml(uptime)}</strong></div>
        <div><span>CPU temp</span><strong>${escapeHtml(cpu)}</strong></div>
        <div><span>GPU temp</span><strong>${escapeHtml(gpu)}</strong></div>
      </div>
    </section>
  `;
}

function renderSoftware(info = {}) {
  const changelogUrl = safeUrl(info.changelogUrl);
  const commitUrl = safeUrl(info.commitUrl);
  const commitHref = changelogUrl || commitUrl;
  const fields = [
    { label: "Branch", value: info.branchName },
    { label: "Build", value: info.buildEnvironment },
    { label: "Commit", value: info.commitHash, href: commitHref },
    { label: "Version date", value: info.versionDate },
    { label: "Fork maintainer", value: info.forkMaintainer },
    { label: "Update available", value: info.updateAvailable },
  ];

  return `
    <section class="dashboard-card dashboard-device-card">
      <h2>Software</h2>
      <div class="dashboard-software-list">
        ${fields.map((field) => `
          <div>
            <span>${escapeHtml(field.label)}</span>
            <strong>${field.href ? `<a href="${escapeHtml(field.href)}" target="_blank" rel="noopener noreferrer">${escapeHtml(field.value ?? "unknown")}</a>` : escapeHtml(field.value ?? "unknown")}</strong>
          </div>
        `).join("")}
      </div>
    </section>
  `;
}

function bindDashboardActions() {
  const refreshButton = document.getElementById("dashboard_refresh");
  if (refreshButton) {
    refreshButton.onclick = () => initializeHome(true);
  }

  document.querySelectorAll(".dashboard-drive-stats-action").forEach((button) => {
    button.onclick = async () => {
      let routeNames = [];
      try {
        routeNames = JSON.parse(button.dataset.routeNames || "[]");
      } catch {
        routeNames = [];
      }
      if (!Array.isArray(routeNames) || routeNames.length === 0) return;

      const action = button.dataset.action === "include" ? "include" : "ignore";
      const confirmed = action === "include" || window.confirm(
        "Ignore this drive's statistics?\n\n" +
        "It will no longer affect local weekly totals, records, model usage, engagement, or attention streaks."
      );
      if (!confirmed) return;

      button.disabled = true;
      try {
        const response = await fetch(`/api/stats/${action}_drive`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ routeNames }),
        });
        const payload = await response.json();
        if (!response.ok) throw new Error(payload.error || `Unable to ${action} drive statistics.`);
        await initializeHome(false);
      } catch (error) {
        window.alert(error?.message || `Unable to ${action} drive statistics.`);
        button.disabled = false;
      }
    };
  });
}

function renderDashboard(state) {
  const shell = document.getElementById("home_shell");
  if (!shell) return;

  if (state.status === "error") {
    clearDashboardRefreshTimer();
    shell.innerHTML = `
      <div class="dashboard dashboard-narrow">
        <div class="dashboard-error">Failed to load dashboard: ${escapeHtml(state.error)}</div>
        <button id="dashboard_refresh" class="dashboard-refresh"><i class="bi bi-arrow-clockwise"></i>Refresh</button>
      </div>
    `;
    bindDashboardActions();
    return;
  }

  if (state.status !== "ready" || !state.data) {
    shell.innerHTML = `
      <div class="dashboard dashboard-narrow">
        <div class="dashboard-loading">Loading dashboard...</div>
      </div>
    `;
    return;
  }

  const data = state.data || {};
  const dashboard = data.dashboard || fallbackDashboard(data, state.unit);
  const driveStats = data.driveStats || {};
  const device = dashboard.device || {};
  const status = device.status || "Parked";
  const onlineText = device.online === false ? "device offline" : "device online";

  shell.innerHTML = `
    <main class="dashboard">
      <header class="dashboard-header">
        <div>
          <h1>Dashboard</h1>
          <p><span class="dashboard-status-dot"></span><strong>${escapeHtml(status)}</strong> - ${escapeHtml(onlineText)}</p>
        </div>
        <button id="dashboard_refresh" class="dashboard-refresh"><i class="bi bi-arrow-clockwise"></i>Refresh</button>
      </header>

      ${renderLastDrive(dashboard.lastDrive || fallbackDashboard(data, state.unit).lastDrive)}
      ${renderAnalysisStatus(dashboard)}

      <div class="dashboard-section-label"><span></span>Your driving</div>
      <div class="dashboard-summary-grid">
        ${statBlock("All time", driveStats.all, state.unit)}
        ${statBlock("Past week", driveStats.week, state.unit)}
        ${statBlock("StarPilot", driveStats.starpilot, state.unit)}
      </div>

      <div class="dashboard-two-column">
        ${renderWeekChart(dashboard.week || {})}
        ${renderRecords(dashboard.records || {})}
      </div>

      ${renderRecentDrives(dashboard.recentDrives || [])}

      <div class="dashboard-two-column dashboard-model-storage">
        ${renderFavoriteModels(dashboard.favoriteModels || [])}
        ${renderStorage(dashboard.storage || {})}
      </div>

      <div class="dashboard-section-label"><span></span>Your device</div>
      <div class="dashboard-device-grid">
        ${renderVitals(device)}
        ${renderSoftware(data.softwareInfo || {})}
      </div>
    </main>
  `;

  bindDashboardActions();
  scheduleDashboardRefresh(dashboard);
}

const STATS_ATTEMPT_TIMEOUTS_MS = [5000, 20000];

async function fetchDashboardStats(timeoutMs) {
  const statsResponse = await withTimeout(fetch("/api/stats"), timeoutMs, "stats request");

  if (!statsResponse.ok) throw new Error(`stats API error: ${statsResponse.status}`);

  return withTimeout(statsResponse.json(), timeoutMs, "stats JSON parse");
}

async function initializeHome(force = false) {
  if (force) {
    clearDashboardRefreshTimer();
    HOME_STATE.status = "loading";
    renderDashboard(HOME_STATE);
  }

  let statsJson = null;
  let lastError = null;
  for (const timeoutMs of STATS_ATTEMPT_TIMEOUTS_MS) {
    try {
      statsJson = await fetchDashboardStats(timeoutMs);
      lastError = null;
      break;
    } catch (err) {
      lastError = err;
    }
  }

  if (lastError) {
    HOME_STATE.status = "error";
    HOME_STATE.error = lastError?.message || String(lastError);
  } else {
    const payloadUnit = statsJson?.dashboard?.week?.distanceUnit || statsJson?.driveStats?.all?.unit;

    HOME_STATE.data = statsJson;
    HOME_STATE.unit = payloadUnit || HOME_STATE.unit || "miles";
    HOME_STATE.status = "ready";
  }

  renderDashboard(HOME_STATE);
}

export function Home() {
  setTimeout(() => {
    renderDashboard(HOME_STATE);
    if (!HOME_STATE.initialized) {
      HOME_STATE.initialized = true;
      initializeHome();
    }
  }, 0);

  return html`<div id="home_shell"><p>Loading dashboard...</p></div>`;
}
