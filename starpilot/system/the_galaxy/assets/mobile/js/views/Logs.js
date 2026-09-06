import { api, showSnackbar } from "../api.js"
import { useLogStream, useTabRouting } from "../composables.js"
import { GalaxyConfirm } from "../components/GalaxyModal.js"
import { TroubleshootPanel } from "../components/TroubleshootPanel.js"
import { GalaxyTabs } from "../components/GalaxyTabs.js"

const TABS = {
  errors: "Error Logs",
  tmux: "Tmux Live Log",
  troubleshoot: "Troubleshoot",
}

function parseLogDate(filename) {
  const m = filename.match(/(\d{4})-(\d{2})-(\d{2})[T_]?(\d{2})-?(\d{2})-?(\d{2})?/)
  if (!m) return new Date()
  const date = new Date(Number(m[1]), Number(m[2]) - 1, Number(m[3]), Number(m[4] || 0), Number(m[5] || 0), Number(m[6] || 0))
  return isNaN(date.getTime()) ? new Date() : date
}

export const Logs = {
  name: "Logs",
  components: { TroubleshootPanel, GalaxyTabs },
  data() {
    return {
      TABS,
      errorFiles: [],
      errorsLoading: true,
      selectedLog: "",
      logContent: "",
      logLoading: false,
      tmuxFiles: [],
      tmuxLoading: true,
      searchFilter: "",
      tmuxAutoScroll: true,
    }
  },
  setup() {
    return useTabRouting("/logs", { errors: "errors", tmux: "tmux", troubleshoot: "troubleshoot" })
  },
  created() {
    this.stream = useLogStream({ endpoint: "/api/tmux_log/live", snapshotFn: () => api.tmuxSnapshot(), interval: 2000 })
  },
  watch: {
    "stream.state.log"() {
      this.$nextTick(() => {
        if (this.stream.state.paused || !this.tmuxAutoScroll) return
        const el = this.$refs.tmuxtail
        if (el) el.scrollTop = el.scrollHeight
      })
    },
  },
  mounted() {
    this.loadErrorLogs()
    this.loadTmuxLogs()
    this.stream.start()
  },
  beforeUnmount() { this.stream.destroy() },
  computed: {
    filteredErrorFiles() {
      if (!this.searchFilter) return this.errorFiles
      const q = this.searchFilter.toLowerCase()
      return this.errorFiles.filter((f) => f.filename.toLowerCase().includes(q))
    },
  },
  methods: {
    async loadErrorLogs() {
      try {
        const files = await api.getErrorLogs()
        this.errorFiles = files.map((f) => {
          const date = parseLogDate(f)
          return { filename: f, date: date.toLocaleString() }
        })
      } catch (e) {
        showSnackbar("Failed to load error logs.", "error")
      } finally {
        this.errorsLoading = false
      }
    },
    async viewLog(file) {
      this.selectedLog = file.filename
      this.logLoading = true
      try {
        this.logContent = await api.getErrorLog(file.filename)
      } catch (e) {
        this.logContent = "Could not load this log."
      } finally {
        this.logLoading = false
        this.$nextTick(() => {
          const el = this.$refs.logview
          if (el) el.scrollTop = el.scrollHeight
        })
      }
    },
    async deleteLog(file) {
      if (!(await GalaxyConfirm({ title: "Delete log?", message: `Delete ${file.filename}?`, confirmLabel: "Delete", danger: true }))) return
      await api.deleteErrorLog(file.filename)
      this.errorFiles = this.errorFiles.filter((f) => f.filename !== file.filename)
      if (this.selectedLog === file.filename) this.selectedLog = ""
      showSnackbar("Log deleted!")
    },
    async deleteAllLogs() {
      if (!(await GalaxyConfirm({ title: "Delete all error logs?", message: "This cannot be undone.", confirmLabel: "Delete All", danger: true }))) return
      try {
        const ok = await api.deleteAllErrorLogs()
        if (!ok) throw new Error("Delete failed")
        this.errorFiles = []
        this.selectedLog = ""
        showSnackbar("All error logs deleted!")
      } catch (e) {
        showSnackbar("Delete all failed.", "error")
      }
    },
    copyLog() {
      const text = this.logContent
      if (navigator.clipboard && window.isSecureContext) navigator.clipboard.writeText(text)
      else { const ta = document.createElement("textarea"); ta.value = text; document.body.appendChild(ta); ta.select(); document.execCommand("copy"); ta.remove() }
      showSnackbar("Copied to clipboard!")
    },
    async loadTmuxLogs() {
      try {
        const files = await api.getTmuxLogs()
        this.tmuxFiles = files.map((f) => {
          const date = new Date(f.timestamp * 1000)
          return { filename: f.filename, date: date.toLocaleString() }
        })
      } catch (e) {
        this.tmuxFiles = []
      } finally {
        this.tmuxLoading = false
      }
    },
    async captureTmux() {
      const ok = await api.tmuxCapture()
      showSnackbar(ok ? "Current session captured!" : "Capture failed.", ok ? "info" : "error")
      this.tmuxLoading = true
      await this.loadTmuxLogs()
    },
    async deleteTmux(file) {
      if (!(await GalaxyConfirm({ title: "Delete log?", message: `Delete ${file.filename}?`, confirmLabel: "Delete", danger: true }))) return
      const ok = await api.deleteTmuxLog(file.filename)
      showSnackbar(ok ? "Deleted!" : "Delete failed.", ok ? "info" : "error")
      this.tmuxFiles = this.tmuxFiles.filter((f) => f.filename !== file.filename)
    },
    async deleteAllTmux() {
      if (!(await GalaxyConfirm({ title: "Delete all logs?", message: "This cannot be undone.", confirmLabel: "Delete All", danger: true }))) return
      const ok = await api.deleteAllTmuxLogs()
      showSnackbar(ok ? "All logs deleted!" : "Delete failed.", ok ? "info" : "error")
      this.tmuxFiles = []
    },
    onTmuxScroll(e) {
      const el = e.target
      this.tmuxAutoScroll = el.scrollHeight - el.scrollTop - el.clientHeight < 40
    },
  },
  template: `
    <div class="gx-view">
      <h2 style="margin-top:0;">Logs & Diagnostics</h2>

      <GalaxyTabs :items="TABS" :active="tab" @select="selectTab" />

      <template v-if="tab === 'errors'">
        <div style="display:flex; gap:8px; margin-bottom:8px; align-items:center;">
          <input class="gx-field" style="flex:1;" type="search" v-model="searchFilter" placeholder="Search logs..." />
          <button v-if="errorFiles.length" type="button" class="gx-btn gx-btn--danger" @click="deleteAllLogs()">Delete All</button>
        </div>
        <section class="gx-card">
          <div v-if="errorsLoading" class="gx-loading">Loading...</div>
          <div v-else-if="!filteredErrorFiles.length" class="gx-empty">No error logs!</div>
          <div v-for="f in filteredErrorFiles" :key="f.filename" class="gx-row" style="cursor:pointer;" @click="viewLog(f)">
            <div class="gx-row__info">
              <span class="gx-row__label">{{ f.date }}</span>
              <span class="gx-row__desc">{{ f.filename }}</span>
            </div>
            <div style="display:flex; gap:6px;">
              <a class="gx-btn gx-btn--tonal" :href="'/api/error_logs/' + encodeURIComponent(f.filename)" download><i class="bi bi-download"></i></a>
              <button type="button" class="gx-btn gx-btn--danger" @click.stop="deleteLog(f)"><i class="bi bi-trash"></i></button>
            </div>
          </div>
        </section>
        <div v-if="selectedLog" class="gx-card" style="margin-top:12px;">
          <div class="gx-section__header">
            <i class="bi bi-file-text"></i>
            <span class="gx-section__title">{{ selectedLog }}</span>
            <button type="button" class="gx-btn gx-btn--tonal" @click="copyLog"><i class="bi bi-clipboard"></i> Copy</button>
          </div>
          <pre ref="logview" style="max-height:60vh; overflow:auto; padding:var(--sp-3); font-size:12px; line-height:1.5; white-space:pre-wrap;">{{ logLoading ? 'Loading...' : logContent }}</pre>
        </div>
      </template>

      <template v-else-if="tab === 'tmux'">
        <section class="gx-card">
          <div class="gx-section__header">
            <i class="bi bi-terminal"></i>
            <span class="gx-section__title">Tmux Live Log</span>
            <span class="gx-chip" :style="stream.state.transport === 'streaming' ? 'background:var(--success);' : ''">{{ stream.state.transport }}</span>
          </div>
          <pre ref="tmuxtail" class="gx-terminal" @scroll.passive="onTmuxScroll">{{ stream.state.log || '(waiting for log output…)' }}</pre>
          <div style="display:flex; gap:8px; padding: var(--sp-3); flex-wrap:wrap;">
            <button type="button" class="gx-btn gx-btn--tonal" @click="stream.togglePause()"><i class="bi" :class="stream.state.paused ? 'bi-play-fill' : 'bi-pause-fill'"></i> {{ stream.state.paused ? 'Resume' : 'Pause' }}</button>
            <button type="button" class="gx-btn gx-btn--tonal" @click="captureTmux">Capture Log</button>
            <button type="button" class="gx-btn gx-btn--tonal" @click="deleteAllTmux">Delete All</button>
          </div>
        </section>
        <section class="gx-card" style="margin-top:12px;">
          <div class="gx-section__header">
            <i class="bi bi-collection"></i>
            <span class="gx-section__title">Saved Session Logs</span>
          </div>
          <div v-if="tmuxLoading" class="gx-loading">Loading...</div>
          <div v-else-if="!tmuxFiles.length" class="gx-empty">No tmux logs found.</div>
          <div v-for="f in tmuxFiles" :key="f.filename" class="gx-row">
            <div class="gx-row__info">
              <span class="gx-row__label">{{ f.filename }}</span>
              <span class="gx-row__desc">{{ f.date }}</span>
            </div>
            <div style="display:flex; gap:6px;">
              <a class="gx-btn gx-btn--tonal" :href="'/api/tmux_log/download/' + encodeURIComponent(f.filename)" download><i class="bi bi-download"></i></a>
              <button type="button" class="gx-btn gx-btn--danger" @click="deleteTmux(f)"><i class="bi bi-trash"></i></button>
            </div>
          </div>
        </section>
      </template>

      <template v-else>
        <TroubleshootPanel />
      </template>
    </div>
  `,
}
