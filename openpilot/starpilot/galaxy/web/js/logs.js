import { TroubleshootPage, TmuxPage } from "./diagnostic-tools.js"
import { navigate } from "./router.js"
import { SystemMonitor } from "./system-monitor.js"
import { CrashReportsFeed } from "./crash-reports.js"
import { MenuTile } from "./menu-tile.js"

export const Logs = {
  name: "Logs",
  components: { SystemMonitor, TroubleshootPage, TmuxPage, MenuTile },
  props: { path: { type: String, required: true }, mode: { type: String, required: true }, unauthorized: { type: Function, required: true } },
  data: () => ({ crashes: { reports: [], scanIncomplete: false, listLimited: false, status: "idle", error: "", selected: null, preview: null, previewStatus: "idle" }, search: "" }),
  computed: {
    visibleReports() { return this.crashes.reports.filter((item) => item.name.toLowerCase().includes(this.search.toLowerCase())) },
  },
  created() {
    this.crashFeed = new CrashReportsFeed({ publish: (update) => Object.assign(this.crashes, update), unauthorized: this.unauthorized })
  },
  mounted() { if (this.path === "/logs/crashes" && this.mode === "local") this.crashFeed.start() },
  beforeUnmount() { this.crashFeed.stop() },
  watch: {
    path(next, previous) {
      if (next === "/logs/crashes" && this.mode === "local") this.crashFeed.start()
      else if (previous === "/logs/crashes") { this.crashFeed.stop(); this.search = "" }
    },
  },
  methods: {
    go: navigate,
    openTroubleshoot() { navigate("/logs/troubleshoot") },
    openTmux() { navigate("/logs/tmux") },
    openMonitor() { navigate("/logs/monitor") },
    openCrashes() { if (this.mode === "local") navigate("/logs/crashes") },
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
      <p v-if="path === '/logs'" class="gx-note">Live console, driving configuration, system activity and crash reports.</p>
      <div v-if="path === '/logs'" class="gx-grid">
        <MenuTile icon="bi-cpu" title="System Monitor" :description="mode === 'sample' ? 'Inspect a synthetic activity sample' : 'Inspect local system activity'" @select="openMonitor" />
        <MenuTile icon="bi-file-text" title="Crash Reports" :description="mode === 'local' ? 'Read local reports' : ''"
          :availability="mode === 'local' ? '' : 'Unavailable in preview'" :disabled="mode !== 'local'" @select="openCrashes" />
        <MenuTile icon="bi-terminal" title="tmux Live View" description="Read the launcher console tail" @select="openTmux" />
        <MenuTile icon="bi-wrench" title="Troubleshoot" description="Read device and vehicle diagnostics" @select="openTroubleshoot" />
      </div>
      <TroubleshootPage v-else-if="path === '/logs/troubleshoot'" :mode="mode" :unauthorized="unauthorized" @navigate="go" />
      <TmuxPage v-else-if="path === '/logs/tmux'" :mode="mode" :unauthorized="unauthorized" @navigate="go" />
      <template v-else-if="path === '/logs/monitor'"><SystemMonitor :mode="mode" :unauthorized="unauthorized" /></template>
      <template v-else-if="path === '/logs/crashes' && mode === 'local'">

        <h2>Crash Reports</h2>
        <div class="gx-crash-controls"><input class="gx-field" type="search" v-model="search" placeholder="Search report names" aria-label="Search crash reports"><button type="button" class="gx-btn gx-btn--tonal" @click="crashFeed.load()">Refresh</button></div>
        <p v-if="crashes.scanIncomplete" class="gx-note">Directory scan is incomplete; newer reports may be omitted.</p>
        <p v-else-if="crashes.listLimited" class="gx-note">Showing the 200 newest reports; older reports are omitted.</p>
        <p v-if="crashes.status === 'loading'">Loading crash reports…</p>
        <p v-else-if="crashes.status === 'unavailable'" role="alert">Crash reports are unavailable.</p>
        <p v-else-if="crashes.status === 'ready' && !visibleReports.length">{{ search ? 'No matching reports.' : 'No crash reports.' }}</p>
        <div v-if="crashes.status === 'ready'" class="gx-crash-list">
          <button v-for="report in visibleReports" :key="report.id" type="button" class="gx-card gx-crash-row" @click="crashFeed.open(report)"><strong>{{ report.name }}</strong><span>{{ reportDate(report.modifiedAt) }} · {{ reportSize(report.size) }}</span></button>
        </div>
        <section v-if="crashes.previewStatus === 'loading'" class="gx-card">Loading report…</section>
        <section v-else-if="crashes.preview" class="gx-card gx-crash-preview"><div class="gx-crash-preview__head"><strong>{{ crashes.preview.name }}</strong><button type="button" class="gx-btn gx-btn--tonal" @click="copyPreview">Copy visible text</button></div><p v-if="crashes.preview.truncated" class="gx-note">Preview truncated to the first 256 KiB.</p><pre>{{ crashes.preview.text }}</pre></section>
        <p v-if="crashes.error" role="alert">{{ crashes.error }}</p>
      </template>
      <div v-else class="gx-card gx-message" role="status">This Logs & Diagnostics page is unavailable in the offline preview.</div>
    </div>`,
}
