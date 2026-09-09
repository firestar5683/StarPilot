import { api } from "../api.js"

export const SystemMonitor = {
  name: "SystemMonitor",
  data() { return { snapshot: null, error: "", paused: false, loading: false, query: "", scope: "comma", sort: "cpu", descending: true, history: [], sensorNow: 0, receivedAt: 0, timer: null, stopped: false } },
  mounted() { this.visibility = () => { if (!document.hidden) this.refresh() }; document.addEventListener("visibilitychange", this.visibility); this.refresh() },
  beforeUnmount() { this.stopped = true; clearTimeout(this.timer); clearTimeout(this.sensorTimer); this.controller?.abort(); document.removeEventListener("visibilitychange", this.visibility) },
  computed: {
    rows() {
      const q = this.query.trim().toLowerCase()
      return (this.snapshot?.processes || []).filter(p => (this.scope === "all" || (this.scope === "comma" ? p.user === "comma" : !p.kernel)) &&
        (!q || `${p.name} ${p.pid} ${p.user} ${this.state(p.state)}`.toLowerCase().includes(q))).slice().sort((a,b) => {
          const av = a[this.sort], bv = b[this.sort]
          if (av == null) return bv == null ? a.pid - b.pid : 1
          if (bv == null) return -1
          const result = typeof av === "number" ? av - bv : String(av).localeCompare(String(bv))
          return (this.descending ? -result : result) || a.pid - b.pid
        })
    },
    captured() { return this.snapshot ? new Date(this.snapshot.sampledAt * 1000).toLocaleTimeString() : "—" },
    uptime() { const s = this.snapshot?.uptimeSeconds || 0; return `${Math.floor(s / 3600)}h ${Math.floor(s / 60) % 60}m` },
    vramUsed() { return this.sensor('memoryUsedBytes', 'memoryMaxAgeMs') },
    vramTotal() { return this.sensor('memoryTotalBytes', 'memoryMaxAgeMs') },
    graph() { return this.history.map((v,i) => `${i * 100 / 29},${40 - v * .4}`).join(" ") },
  },
  methods: {
    sensor(field, ageKey) {
      const vitals = this.snapshot?.vitals
      if (this.error || !vitals || !(vitals[ageKey] > 0) || (this.sensorNow - this.receivedAt >= vitals[ageKey])) return null
      return vitals[field] ?? null
    },
    expireSensors() {
      clearTimeout(this.sensorTimer)
      this.sensorNow = performance.now()
      if (this.stopped || this.paused) return
      const ages = ['onboardMaxAgeMs', 'maxAgeMs', 'memoryMaxAgeMs'].map(key => (this.snapshot?.vitals?.[key] || 0) - (this.sensorNow - this.receivedAt)).filter(age => age > 0)
      if (ages.length) this.sensorTimer = setTimeout(() => this.expireSensors(), Math.min(...ages) + 1)
    },
    number(value, suffix="") { return value == null ? "—" : Number(value).toFixed(1) + suffix },
    state(value) { return ({R:"Running", S:"Sleeping", D:"Waiting", T:"Stopped", t:"Tracing", Z:"Zombie", I:"Idle"})[value] || value },
    sortBy(key) { if (this.sort === key) this.descending = !this.descending; else { this.sort = key; this.descending = ["cpu", "memoryMiB"].includes(key) } },
    arrow(key) { return this.sort === key ? (this.descending ? " ↓" : " ↑") : "" },
    ariaSort(key) { return this.sort !== key ? "none" : this.descending ? "descending" : "ascending" },
    togglePause() { this.paused = !this.paused; this.expireSensors(); if (!this.paused) this.refresh() },
    async refresh() {
      clearTimeout(this.timer)
      if (this.stopped || this.loading) return
      if (!this.paused && !document.hidden) {
        this.loading = true
        this.controller = new AbortController()
        const timeout = setTimeout(() => this.controller.abort(), 8000)
        const requestStarted = performance.now()
        try {
          const data = await api.systemMonitor(this.controller.signal)
          if (this.stopped) return
          if (data.sampledAt !== this.snapshot?.sampledAt && data.cpuPercent != null) this.history = [...this.history, data.cpuPercent].slice(-30)
          this.snapshot = data; this.error = ""; this.receivedAt = requestStarted; this.expireSensors()
        } catch (e) { if (!this.stopped) this.error = "Cannot refresh system monitor. Showing the last captured values." }
        finally { clearTimeout(timeout); this.loading = false }
      }
      if (!this.stopped) this.timer = setTimeout(() => this.refresh(), 2000)
    },
  },
  template: `
    <div class="gx-monitor">
      <div class="gx-monitor__toolbar">
        <div><strong>System Monitor</strong><div class="gx-note">{{ paused ? 'Paused' : error ? 'Connection interrupted' : 'Updates every 2 seconds' }} · Captured {{ captured }}</div></div>
        <button class="gx-btn gx-btn--tonal" type="button" @click="togglePause">{{ paused ? 'Resume' : 'Pause' }}</button>
      </div>
      <p v-if="error" class="gx-note gx-note--danger" role="status">{{ error }}</p>
      <div v-if="!snapshot" class="gx-loading">{{ error ? 'Waiting for the device…' : 'Reading system activity…' }}</div>
      <template v-else>
        <div class="gx-monitor__summary">
          <section class="gx-card gx-monitor__metric"><span>CPU</span><strong>{{ number(snapshot.cpuPercent, '%') }}</strong><small>{{ snapshot.cores.length }} cores · overall usage</small>
            <svg viewBox="0 0 100 40" preserveAspectRatio="none" class="gx-monitor__graph" role="img" aria-label="Recent CPU usage"><polyline :points="graph" fill="none" stroke="currentColor" stroke-width="1.5" vector-effect="non-scaling-stroke"/></svg>
          </section>
          <section class="gx-card gx-monitor__metric"><span>Memory</span><strong>{{ number(snapshot.memory.percent, '%') }}</strong><small>{{ number(snapshot.memory.usedMiB / 1024) }} / {{ number(snapshot.memory.totalMiB / 1024) }} GiB</small><progress :value="snapshot.memory.percent" max="100" aria-label="Memory usage"></progress></section>
          <section class="gx-card gx-monitor__metric"><span>Processes</span><strong>{{ snapshot.processCount }}</strong><small>Uptime {{ uptime }}</small></section>
          <section class="gx-card gx-monitor__metric"><span>Storage</span><strong>{{ snapshot.storage.usedGiB }} GiB</strong><small>{{ snapshot.storage.totalGiB }} GiB total</small></section>
          <section class="gx-card gx-monitor__metric"><span>Onboard CPU temperature</span><strong>{{ number(sensor('cpuTempC', 'onboardMaxAgeMs'), ' °C') }}</strong></section>
          <section class="gx-card gx-monitor__metric"><span>Onboard GPU temperature</span><strong>{{ number(sensor('gpuTempC', 'onboardMaxAgeMs'), ' °C') }}</strong></section>
          <section class="gx-card gx-monitor__metric"><span>eGPU hotspot temperature</span><strong>{{ number(sensor('hotspotTempC', 'maxAgeMs'), ' °C') }}</strong></section>
          <section v-if="snapshot.vitals?.gpuEdgeTempC != null" class="gx-card gx-monitor__metric"><span>eGPU temperature</span><strong>{{ number(sensor('gpuEdgeTempC', 'maxAgeMs'), ' °C') }}</strong></section>
          <section class="gx-card gx-monitor__metric"><span>eGPU VRAM</span><strong>{{ vramUsed == null ? '—' : number(vramUsed / 1073741824) + ' GiB' }}</strong><small v-if="vramTotal != null">{{ number(vramTotal / 1073741824) }} GiB total · {{ number(100 * vramUsed / vramTotal, '%') }}</small><progress v-if="vramTotal > 0 && vramUsed != null" :value="vramUsed" :max="vramTotal" aria-label="eGPU VRAM usage"></progress></section>
        </div>
        <details class="gx-card gx-monitor__cores"><summary>CPU cores</summary><div><span v-for="core in snapshot.cores" :key="core.name">{{ core.name.toUpperCase() }} <b>{{ number(core.percent, '%') }}</b><progress :value="core.percent || 0" max="100" :aria-label="core.name + ' usage'"></progress></span></div></details>
        <div class="gx-monitor__filters"><input class="gx-field" type="search" v-model="query" aria-label="Search processes" placeholder="Search process, PID or user…"/><GalaxySelect class="gx-field" v-model="scope" aria-label="Process group"><option value="comma">Comma processes</option><option value="users">Apps and services</option><option value="all">All processes</option></GalaxySelect></div>
        <p class="gx-note">{{ rows.length }} processes shown. {{ snapshot.cpuPercent == null ? 'Collecting the first CPU sample…' : '' }}</p>
        <section class="gx-card gx-monitor__table" tabindex="0" aria-label="Process table; scroll horizontally for more columns">
          <table><thead><tr><th v-for="column in [['name','Process'],['pid','PID'],['cpu','CPU'],['memoryMiB','Memory'],['user','User'],['state','Status']]" :key="column[0]" :aria-sort="ariaSort(column[0])"><button type="button" @click="sortBy(column[0])">{{ column[1] }}{{ arrow(column[0]) }}</button></th></tr></thead>
          <tbody><tr v-for="process in rows" :key="process.pid"><td :title="process.name">{{ process.name }}</td><td>{{ process.pid }}</td><td>{{ number(process.cpu, '%') }}</td><td>{{ number(process.memoryMiB) }} MiB</td><td>{{ process.user }}</td><td><span class="gx-chip">{{ state(process.state) }}</span></td></tr><tr v-if="!rows.length"><td colspan="6" class="gx-empty">No matching processes.</td></tr></tbody></table>
        </section>
      </template>
    </div>`,
}
