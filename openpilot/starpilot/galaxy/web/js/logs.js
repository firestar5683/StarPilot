import { GxState } from "./state.js"
import { GxNotice } from "./notice.js"
import { TroubleshootPage, TmuxPage } from "./diagnostic-tools.js"
import { navigate } from "./router.js"
import { SystemMonitor } from "./system-monitor.js"
import { CrashReportsFeed } from "./crash-reports.js"
import { AndroidAutoLogsFeed, BUNDLE_URL, fileUrl, outcomeLabel } from "./android-auto-logs.js"
import { MenuTile } from "./menu-tile.js"

export const Logs = {
  name: "Logs",
  components: { GxState, GxNotice, SystemMonitor, TroubleshootPage, TmuxPage, MenuTile },
  props: { path: { type: String, required: true }, mode: { type: String, required: true }, unauthorized: { type: Function, required: true } },
  data: () => ({ crashes: { reports: [], scanIncomplete: false, listLimited: false, status: "idle", error: "", selected: null, preview: null, previewStatus: "idle" }, search: "",
    aaLogs: { sessions: [], others: [], status: "idle", error: "" } }),
  computed: {
    visibleReports() { return this.crashes.reports.filter((item) => item.name.toLowerCase().includes(this.search.toLowerCase())) },
  },
  created() {
    this.crashFeed = new CrashReportsFeed({ publish: (update) => Object.assign(this.crashes, update), unauthorized: this.unauthorized })
    this.aaFeed = new AndroidAutoLogsFeed({ publish: (update) => Object.assign(this.aaLogs, update), unauthorized: this.unauthorized })
  },
  mounted() {
    if (this.path === "/logs/crashes" && this.mode === "local") this.crashFeed.start()
    if (this.path === "/logs/android-auto" && this.mode === "local") this.aaFeed.start()
  },
  beforeUnmount() { this.crashFeed.stop(); this.aaFeed.stop() },
  watch: {
    path(next, previous) {
      if (next === "/logs/crashes" && this.mode === "local") this.crashFeed.start()
      else if (previous === "/logs/crashes") { this.crashFeed.stop(); this.search = "" }
      if (next === "/logs/android-auto" && this.mode === "local") this.aaFeed.start()
      else if (previous === "/logs/android-auto") this.aaFeed.stop()
    },
  },
  methods: {
    go: navigate,
    openTroubleshoot() { navigate("/logs/troubleshoot") },
    openTmux() { navigate("/logs/tmux") },
    openMonitor() { navigate("/logs/monitor") },
    openCrashes() { if (this.mode === "local") navigate("/logs/crashes") },
    openAndroidAuto() { if (this.mode === "local") navigate("/logs/android-auto") },
    bundleUrl: () => BUNDLE_URL,
    fileUrl,
    outcomeLabel,
    reportDate(seconds) { return new Date(seconds * 1000).toLocaleString() },
    reportSize(bytes) { return `${(bytes / 1024).toFixed(1)} KiB` },
    async copyPreview() {
      if (!this.crashes.preview) return
      try { await navigator.clipboard.writeText(this.crashes.preview.text) }
      catch { this.crashes.error = "Copy is unavailable in this browser." }
    },
  },
  template: `
    <div class="gx-view">
      <h2 v-if="path === '/logs'">Logs & Diagnostics</h2>
      <p v-if="path === '/logs'" class="gx-note">Live console, driving configuration, system activity, crash reports and Android Auto logs.</p>
      <div v-if="path === '/logs'" class="gx-grid">
        <MenuTile icon="bi-cpu" title="System Monitor" :description="mode === 'sample' ? 'Inspect a synthetic activity sample' : 'Inspect local system activity'" @select="openMonitor" />
        <MenuTile icon="bi-file-text" title="Crash Reports" :description="mode === 'local' ? 'Read local reports' : ''"
          :availability="mode === 'local' ? '' : 'Unavailable in preview'" :disabled="mode !== 'local'" @select="openCrashes" />
        <MenuTile icon="bi-phone" title="Android Auto" :description="mode === 'local' ? 'Session logs and a download for bug reports' : ''"
          :availability="mode === 'local' ? '' : 'Unavailable in preview'" :disabled="mode !== 'local'" @select="openAndroidAuto" />
        <MenuTile icon="bi-terminal" title="tmux Live View" description="Read the launcher console tail" @select="openTmux" />
        <MenuTile icon="bi-wrench" title="Troubleshoot" description="Read device and vehicle diagnostics" @select="openTroubleshoot" />
      </div>
      <TroubleshootPage v-else-if="path === '/logs/troubleshoot'" :mode="mode" :unauthorized="unauthorized" />
      <TmuxPage v-else-if="path === '/logs/tmux'" :mode="mode" :unauthorized="unauthorized" />
      <template v-else-if="path === '/logs/monitor'"><SystemMonitor :mode="mode" :unauthorized="unauthorized" /></template>
      <template v-else-if="path === '/logs/crashes' && mode === 'local'">

        <h2>Crash Reports</h2>
        <div class="gx-crash-controls"><input class="gx-field" type="search" v-model="search" placeholder="Search report names" aria-label="Search crash reports"></div>
        <p v-if="crashes.scanIncomplete" class="gx-note">Directory scan is incomplete; newer reports may be omitted.</p>
        <p v-else-if="crashes.listLimited" class="gx-note">Showing the 200 newest reports; older reports are omitted.</p>
        <GxState v-if="crashes.status === 'loading'" loading>Loading crash reports…</GxState>
        <GxNotice tone="danger" v-else-if="crashes.status === 'unavailable' && !crashes.error">Crash reports are unavailable.</GxNotice>
        <GxState v-else-if="crashes.status === 'ready' && !visibleReports.length">{{ search ? 'No matching reports.' : 'No crash reports.' }}</GxState>
        <div v-if="crashes.status === 'ready'" class="gx-crash-list">
          <button v-for="report in visibleReports" :key="report.id" type="button" class="gx-card gx-crash-row gx-panel" @click="crashFeed.open(report)"><strong>{{ report.name }}</strong><span>{{ reportDate(report.modifiedAt) }} · {{ reportSize(report.size) }}</span></button>
        </div>
        <GxState v-if="crashes.previewStatus === 'loading'" loading>Loading report…</GxState>
        <section v-else-if="crashes.preview" class="gx-card gx-crash-preview gx-panel"><div class="gx-crash-preview__head"><strong>{{ crashes.preview.name }}</strong><button type="button" class="gx-btn gx-btn--tonal" @click="copyPreview">Copy visible text</button></div><p v-if="crashes.preview.truncated" class="gx-note">Preview truncated to the first 256 KiB.</p><pre>{{ crashes.preview.text }}</pre></section>
        <GxNotice tone="danger" v-if="crashes.error">{{ crashes.error }}</GxNotice>
      </template>
      <section v-else-if="path === '/logs/android-auto' && mode === 'local'" class="gx-aa-logs" aria-labelledby="gx-aa-logs-title">
        <header class="gx-aa-logs__header">
          <div><h2 id="gx-aa-logs-title">Android Auto Logs</h2>
            <p class="gx-note">The last 20 connection sessions, newest first. The archive includes every session, a readable report for each, Android Auto settings without Bluetooth addresses, and the car view's renderer logs.</p></div>
          <div class="gx-aa-logs__actions"><a class="gx-btn" :href="bundleUrl()" download><i class="bi bi-file-earmark-zip" aria-hidden="true"></i><span>Download all logs</span><span class="gx-aa-logs__format">ZIP</span></a><button type="button" class="gx-btn gx-btn--tonal" @click="aaFeed.load()"><i class="bi bi-arrow-clockwise" aria-hidden="true"></i><span>Refresh</span></button></div>
        </header>
        <GxState v-if="aaLogs.status === 'loading'" loading>Loading Android Auto logs…</GxState>
        <GxNotice v-else-if="aaLogs.status === 'unavailable'" tone="danger">{{ aaLogs.error || 'Android Auto logs are unavailable.' }}</GxNotice>
        <GxState v-else-if="aaLogs.status === 'ready' && !aaLogs.sessions.length">No Android Auto sessions have been logged yet.</GxState>
        <div v-if="aaLogs.status === 'ready'" class="gx-aa-log-list">
          <article v-for="log in aaLogs.sessions" :key="log.name" class="gx-card gx-aa-log">
            <div class="gx-aa-log__body"><strong>{{ outcomeLabel(log.outcome) }}</strong><span>{{ log.car || 'Car not identified' }}{{ log.transport ? ' · ' + log.transport : '' }}{{ log.trigger ? ' · ' + log.trigger : '' }}</span><span>{{ reportDate(log.modifiedAt) }} · {{ reportSize(log.size) }}</span></div>
            <a class="gx-icon-btn gx-aa-log__download" :href="fileUrl(log.name)" :download="log.name" :aria-label="'Download ' + log.name" :title="'Download ' + log.name"><i class="bi bi-download" aria-hidden="true"></i></a>
          </article>
        </div>
        <template v-if="aaLogs.status === 'ready' && aaLogs.others.length">
          <h3 class="gx-aa-logs__section-title">Renderer logs</h3>
          <div class="gx-aa-log-list">
            <article v-for="log in aaLogs.others" :key="log.name" class="gx-card gx-aa-log">
              <div class="gx-aa-log__body"><strong>{{ log.name }}</strong><span>{{ reportDate(log.modifiedAt) }} · {{ reportSize(log.size) }}</span></div>
              <a class="gx-icon-btn gx-aa-log__download" :href="fileUrl(log.name)" :download="log.name" :aria-label="'Download ' + log.name" :title="'Download ' + log.name"><i class="bi bi-download" aria-hidden="true"></i></a>
            </article>
          </div>
        </template>
      </section>
      <GxState v-else>This Logs & Diagnostics page is unavailable in the offline preview.</GxState>
    </div>`,
}
