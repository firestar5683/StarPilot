import { reactive } from "../vendor/vue/vue.esm-browser.js"
import { GalaxySettingRow, settingControl } from "./galaxy-setting-row.js"
import { OnroadLayoutPage } from "./onroad-layout.js"
import { FavoritesPage } from "./favorites.js"
import { SoundPacks } from "./sound-packs.js"
import { CloudProviderPage } from "./cloud-provider.js"
import { GxNotice } from "./notice.js"

const post = (fetcher, path, body, signal) => fetcher(path, {
  method: "POST", credentials: "same-origin", cache: "no-store", signal,
  headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
})

export const SETTINGS_SECTIONS = Object.freeze([
  { id: "lateral", label: "Lateral (Steering)", icon: "bi-arrows-move", pages: ["aol", "lane_change", "torque", "lane"] },
  { id: "longitudinal", label: "Longitudinal (Speed & Following)", icon: "bi-speedometer2", pages: ["conditional", "curve", "profiles", "slc", "traffic", "aggressive", "standard", "relaxed"] },
  { id: "wheel", label: "Wheel Controls", icon: "bi-controller", pages: ["wheel"] },
  { id: "visual", label: "Visual (Display & UI)", icon: "bi-eye", pages: ["appearance", "ui_layout", "favorites", "pip"] },
  { id: "sounds", label: "Sounds & Alerts", icon: "bi-volume-up", pages: ["sounds"] },
  { id: "device", label: "Device & Data", icon: "bi-hdd", pages: ["display", "data"] },
  { id: "developer", label: "Developer", icon: "bi-code-slash", pages: ["developer"] },
])

// Crop numeric rows and the inline editor row are controlled from the dedicated
// Blind Spot Camera page; they stay writable through the settings API for the
// widget/VASM editor but must not surface in the generic toggles list.
export const isPipCropRow = (row) => row.label === "Visual camera crop editor" || /^Vehicle (left|right) crop/.test(row.label || "")

const SECTION_LINKS = {
  device: [{ label: "Display", page: "display" }, { label: "Data Uploads", page: "data" }],
  visual: [{ label: "Driving Screen Widgets", page: "appearance" }, { label: "Colors & Layout", page: "ui_layout" }, { label: "Quick Select", page: "favorites" }, { label: "Blind Spot Camera and Preview", page: "pip" }],
}

export class SettingsFeed {
  constructor({ publish, unauthorized = () => {}, fetcher = (...args) => fetch(...args),
                later = (fn, ms) => setTimeout(fn, ms), cancelTimer = (id) => clearTimeout(id) }) {
    Object.assign(this, { publish, unauthorized, fetcher, later, cancelTimer })
    this.active = false
    this.generation = 0
    this.request = null
    this.timer = null
    this.pollTimer = null
    this.polling = false
    this.saving = false
    this.page = "hub"
    this.data = null
    this.pending = null
  }

  stop() {
    this.active = false
    this.generation++
    this.request?.abort()
    if (this.timer !== null) this.cancelTimer(this.timer)
    if (this.pollTimer !== null) this.cancelTimer(this.pollTimer)
    this.request = this.timer = this.pollTimer = null
    this.polling = false
    this.saving = false
    this.data = null
    this.pending = null
    this.publish({ status: "idle", data: null, pending: null, error: "" })
  }

  start(page = "hub") {
    this.stop()
    this.active = true
    this.page = page
    return this.load(page)
  }

  async run(operation, { saving = false, background = false } = {}) {
    if (!this.active) return null
    const generation = ++this.generation
    this.request?.abort()
    if (this.timer !== null) this.cancelTimer(this.timer)
    if (this.pollTimer !== null) this.cancelTimer(this.pollTimer)
    this.pollTimer = null
    const request = new AbortController()
    this.request = request
    this.saving = saving
    this.polling = background
    this.timer = this.later(() => {
      if (!this.active || generation !== this.generation || this.request !== request) return
      request.abort()
      this.generation++
      this.request = this.timer = null
      this.saving = false
      this.polling = false
      if (!background) this.data = this.pending = null
      else this.expireMonitorStatus()
      this.publish({ status: background && this.data ? "ready" : "unavailable", data: this.data, pending: this.pending,
        error: saving ? "Saving timed out. The result is unknown. Refresh saved values before trying again." :
                        "Reading settings timed out. Refresh to try again." })
    }, 4000)
    try {
      const response = await operation(request.signal)
      if (!this.active || generation !== this.generation || request.signal.aborted) return null
      const accessCode = response.status === 503 ? (await response.clone().json().catch(() => null))?.code : null
      if (!this.active || generation !== this.generation || request.signal.aborted) return null
      if (response.status === 401 || ["access_unavailable", "setup_required"].includes(accessCode)) {
        this.stop()
        this.unauthorized()
        return null
      }
      if (response.status === 409) {
        const error = new Error("Saved settings changed. Refresh this page.")
        error.stale = true
        throw error
      }
      if (!response.ok) throw new Error(response.status === 503 ? "Saved settings are unavailable." : "Settings request failed.")
      const data = await response.json().catch(() => { throw new Error("Galaxy could not load settings. Refresh to reconnect.") })
      if (!this.active || generation !== this.generation || request.signal.aborted) return null
      return data
    } catch (error) {
      if (this.active && generation === this.generation && !request.signal.aborted) {
        this.pending = null
        this.expireMonitorStatus()
        if (error?.stale) this.data = null
        this.publish({ status: this.data ? "ready" : "unavailable", data: this.data, pending: null,
          error: error?.message || "Settings request failed." })
      }
      return null
    } finally {
      if (this.request === request) {
        if (this.timer !== null) this.cancelTimer(this.timer)
        this.request = this.timer = null
        this.saving = false
        this.polling = false
      }
    }
  }

  expireMonitorStatus() {
    if (this.data?.page === "sentry") this.data = { ...this.data, subtitle: "Motion monitor status is unavailable. Refresh to check again." }
  }

  scheduleParkedRefresh() {
    if (!this.active || this.pending || this.request || this.saving || this.pollTimer !== null ||
        (this.data?.parked !== false && this.page !== "sentry") || this.data?.page !== this.page || typeof this.data.view !== "string" ||
        !Array.isArray(this.data.rows)) return
    const generation = this.generation
    this.pollTimer = this.later(() => {
      this.pollTimer = null
      if (this.active && this.generation === generation && !this.pending && !this.request && !this.saving && (this.data?.parked === false || this.page === "sentry"))
        this.load(this.page, { keepData: true, quiet: true })
    }, 1000)
  }

  async load(page = this.page, { keepData = page === this.page && this.data !== null, quiet = keepData } = {}) {
    if (!this.active || this.saving || (quiet && (this.pending || this.request))) return
    this.page = page
    this.pending = null
    if (!keepData) this.data = null
    this.publish({ status: quiet ? "ready" : keepData ? "saving" : "loading", data: this.data, pending: null, error: "" })
    const operation = this.run((signal) => this.fetcher(`./api/settings/pages/${encodeURIComponent(page)}`,
      { credentials: "same-origin", cache: "no-store", signal }), { background: quiet })
    const attempt = this.generation
    const data = await operation
    if (data && this.active && this.generation === attempt && this.page === page) {
      this.data = data
      this.publish({ status: "ready", data, pending: null, error: "" })
      this.scheduleParkedRefresh()
    }
  }

  async preview(row, direction, draft = null) {
    if (!this.active || !this.data?.view || this.pending || (this.request && !this.polling)) return
    const data = await this.run((signal) => post(this.fetcher, "./api/settings/preview",
      { view: this.data.view, row, direction, ...(draft === null ? {} : { draft }) }, signal))
    if (data) {
      this.pending = data
      this.publish({ status: "ready", data: this.data, pending: data, error: "" })
    }
  }

  async resetDefault(row) {
    if (!this.active || !this.data?.view || !this.data.rows?.[row]?.resetAvailable ||
        this.pending || (this.request && !this.polling)) return
    const data = await this.run((signal) => post(this.fetcher, "./api/settings/reset-default",
      { view: this.data.view, row }, signal))
    if (data) {
      this.pending = data
      this.publish({ status: "ready", data: this.data, pending: data, error: "" })
    }
  }

  async previewValue(row, value) {
    if (!this.active || !this.data?.view || this.pending || (this.request && !this.polling)) return
    this.publish({ status: "updating", data: this.data, pending: null, error: "" })
    const data = await this.run((signal) => post(this.fetcher, "./api/settings/preview",
      { view: this.data.view, row, value }, signal))
    if (data) {
      this.pending = data
      await this.confirm()
    }
  }

  cancel() {
    this.pending = null
    if (this.active) this.publish({ status: "ready", data: this.data, pending: null, error: "" })
    this.scheduleParkedRefresh()
  }

  async confirm() {
    if (!this.active || !this.pending?.intent) return
    const intent = this.pending.intent
    this.pending = null
    this.publish({ status: "saving", data: this.data, pending: null, error: "" })
    const page = this.page
    const operation = this.run((signal) => post(this.fetcher, "./api/settings/confirm",
      { intent, confirmed: true }, signal), { saving: true })
    const attempt = this.generation
    const result = await operation
    if (this.active && this.generation === attempt) {
      const reload = this.load(page, { keepData: true, quiet: false })
      const refreshed = this.generation
      await reload
      if (result?.saved !== true && this.active && this.generation === refreshed && this.data) this.publish({ status: "ready", data: this.data, pending: null,
        error: "Save could not be confirmed. Current saved values are shown; review them before trying again." })
    }
  }
}

export const SettingsPage = {
  components: { GalaxySettingRow, OnroadLayoutPage, FavoritesPage, SoundPacks, CloudProviderPage, GxNotice },
  props: { mode: { type: String, required: true }, unauthorized: { type: Function, required: true },
    initialPage: { type: String, default: "hub" }, title: { type: String, default: "Toggles" },
    initialSection: { type: String, default: null }, returnTo: { type: Function, default: null } },
  setup(props) {
    const state = reactive({ status: "idle", data: null, pending: null, error: "", query: "", searchOpen: false, section: "lateral", layoutOpen: false, favoritesOpen: false, soundChoicesDirty: false, developerOpen: props.initialSection === "developer" })
    const feed = new SettingsFeed({ publish: (update) => Object.assign(state, update), unauthorized: props.unauthorized })
    return { state, feed, sections: SETTINGS_SECTIONS }
  },
  computed: {
    busy() { return ["updating", "saving"].includes(this.state.status) || !!this.state.pending },
    activeSection() {
      if (this.state.developerOpen) return this.sections.at(-1)
      const page = (this.state.data?.page || "hub").split("/")[0]
      return this.sections.find((section) => page === "hub" ? section.id === this.state.section : section.pages.includes(page)) || this.sections[0]
    },
    atSectionRoot() {
      if (this.state.developerOpen) return true
      return this.state.data?.page === "hub" ||
        (this.activeSection.pages.length === 1 && this.state.data?.page === this.activeSection.pages[0])
    },
    visibleRows() {
      const needle = this.state.query.trim().toLocaleLowerCase()
      const rows = this.state.data?.rows || []
      const inHub = this.initialPage === "hub" && this.state.data?.page === "hub"
      const section = this.activeSection
      const entries = inHub && SECTION_LINKS[section.id]
        ? SECTION_LINKS[section.id].map((row, index) => ({ row: { ...row, available: true, action: false, value: "" }, index }))
        : rows.map((row, index) => ({ row, index })).filter(({ row }) => !inHub || section.pages.includes(row.page))
      return entries.filter(({ row }) => !isPipCropRow(row)).filter(({ row, index }) => {
        const previous = rows[index - 1]
        return !(["sounds", "display"].includes(this.state.data?.page) && row.repairValue === "Auto" &&
          previous?.choices?.includes("Auto") && settingControl(previous) === "slider" && row.label === `Use Auto ${previous.label}`)
      }).filter(({ row }) =>
        !needle || `${row.label} ${row.value} ${row.reason}`.toLocaleLowerCase().includes(needle))
    },
  },
  watch: {
    "state.pending"() { this.flushSoundChoices() },
    "state.status"(status, previous) {
      if (previous === "saving" && status === "ready") this.state.soundChoicesDirty = false
      else this.flushSoundChoices()
    },
  },
  mounted() { if (this.mode === "local" && !this.state.developerOpen) this.feed.start(this.initialPage) },
  beforeUnmount() { this.feed.stop() },
  methods: {
    open(page) {
      this.state.query = ""
      if (page === "ui_layout") { this.feed.stop(); this.state.layoutOpen = true }
      else if (page === "favorites") { this.feed.stop(); this.state.favoritesOpen = true }
      else this.feed.load(page)
    },
    togglePageSearch() {
      this.state.searchOpen = !this.state.searchOpen
      if (this.state.searchOpen) this.$nextTick(() => this.$refs.pageSearch?.focus())
      else this.state.query = ""
    },
    async openCropEditor() { (await import("./router.js")).navigate("/cameras/pip") },
    rowKey(row, index) { return JSON.stringify([this.state.data.page, index, row.revision ?? this.state.data.view, row]) },
    closeLayout() { this.state.layoutOpen = false; this.state.section = "visual"; this.feed.start(this.initialPage) },
    closeFavorites() { this.state.favoritesOpen = false; this.state.section = "visual"; this.feed.start("hub") },
    selectSection(section) {
      if (this.busy) return
      this.state.section = section.id
      this.state.developerOpen = section.id === "developer"
      if (this.state.developerOpen) { this.feed.stop(); return }
      if (!this.feed.active) { this.feed.start(section.pages.length === 1 ? section.pages[0] : "hub"); return }
      this.state.query = ""
      const page = section.pages.length === 1 ? section.pages[0] : "hub"
      if (this.state.data?.page !== page) this.feed.load(page, { keepData: true, quiet: true })
    },
    requestRouteLeave(proceed) {
      if (this.busy) return
      if (this.state.layoutOpen) this.$refs.layoutEditor.requestLeave(proceed)
      else proceed()
    },
    navigateBack() {
      if (this.state.pending) { this.feed.cancel(); return true }
      if (this.busy) return true
      if (this.state.layoutOpen) { this.$refs.layoutEditor.requestLeave("back"); return true }
      if (this.state.favoritesOpen) { if (!this.$refs.favoritesEditor?.busy) this.closeFavorites(); return true }
      if (this.state.developerOpen) return false
      const nested = this.initialPage === "hub" ? !this.atSectionRoot : this.state.data?.page !== this.initialPage
      if (!nested) return false
      this.back()
      return true
    },
    back() {
      if (this.state.developerOpen) return
      const page = this.state.data?.page || this.initialPage
      this.state.section = this.activeSection?.id || this.state.section
      this.state.query = ""
      if (page === this.initialPage && this.returnTo) { this.returnTo(); return }
      if (this.initialPage !== "hub") { this.feed.load(this.initialPage); return }
      this.feed.load(page.includes("/") ? page.split("/")[0] :
        ["aggressive", "standard", "relaxed"].includes(page) ? "profiles" : "hub")
    },
    refreshSoundChoices() {
      this.state.soundChoicesDirty = true
      this.flushSoundChoices()
    },
    flushSoundChoices() {
      if (!this.state.soundChoicesDirty || this.state.data?.page !== "sounds" || this.feed.saving || this.state.pending) return
      this.state.soundChoicesDirty = false
      this.feed.load("sounds", { keepData: true })
    },
  },
  template: `
    <OnroadLayoutPage ref="layoutEditor" v-if="state.layoutOpen" :mode="mode" :unauthorized="unauthorized" @close="closeLayout" />
    <FavoritesPage ref="favoritesEditor" v-else-if="state.favoritesOpen" :mode="mode" :unauthorized="unauthorized" @close="closeFavorites" />
    <section v-else class="gx-settings" :aria-label="title">
      <div class="gx-settings__header"><div><h2>{{ title }}</h2></div></div>
      <GxNotice v-if="state.data && state.data.page !== 'hub' && !state.data.parked && state.data.rows.some(row => !row.available)" tone="warn">Turn the vehicle off to change these settings.</GxNotice>
      <GxNotice v-if="initialPage === 'pip'" tone="info">Choose when to show the camera and adjust its saved crop. Use the crop editor for a live preview.</GxNotice>
      <GxNotice v-else-if="(state.data?.page || initialPage) === 'sounds'" tone="info">Adjust alert and chime volumes. Immediate warnings keep their safety volume ramp.</GxNotice>
      <GxNotice v-else-if="(state.data?.page || initialPage) === 'display'" tone="info">Adjust brightness and screen timing when custom display settings are on.</GxNotice>
      <GxNotice v-else-if="initialPage === 'appearance'" tone="info">Choose which driving information to show. Use Colors &amp; Layout to arrange widgets and change colors.</GxNotice>
      <GxNotice v-else-if="initialPage === 'lane_change'" tone="info">Close gap adjusts following distance during a lane change when StarPilot controls acceleration and braking. It is Off by default.</GxNotice>
      <GxNotice v-else-if="state.data?.page === 'conditional' || state.data?.page.startsWith('conditional/')" tone="info">Choose when to switch between Chill and Experimental. Applies on supported vehicles when StarPilot controls acceleration and braking.</GxNotice>
      <GxNotice v-else-if="state.data?.page === 'profiles'" tone="info">Braking response works without saved personality curves. A selected personality braking preset or Traffic takes priority.</GxNotice>
      <GxNotice v-else-if="state.data?.page === 'traffic'" tone="info">Traffic follow and jerk blend toward saved Relaxed values at higher speeds. Saved curves require Use saved profiles and the Traffic profile switch.</GxNotice>
      <GxNotice v-else-if="state.data?.page === 'aol'" tone="info">Keep StarPilot lateral control active without holding the steering wheel.</GxNotice>
      <GxNotice v-else-if="state.data?.page === 'torque'" tone="info">Tune how StarPilot applies steering torque.</GxNotice>
      <GxNotice v-else-if="state.data?.page === 'lane'" tone="info">Choose lane-centering behavior and alerts.</GxNotice>
      <GxNotice v-else-if="state.data?.page === 'curve'" tone="info">Set how the vehicle slows for curves ahead.</GxNotice>
      <GxNotice v-else-if="state.data?.page === 'slc'" tone="info">Control how speed limits change your set speed.</GxNotice>
      <GxNotice v-else-if="state.data?.page === 'wheel'" tone="info">Assign what the steering-wheel controls do.</GxNotice>
      <GxNotice v-else-if="state.data?.page === 'data'" tone="info">Choose what uploads when the vehicle uses mobile data.</GxNotice>
      <GxNotice v-else-if="['aggressive','standard','relaxed'].includes(state.data?.page)" tone="info">Saved personality curve for this driving style.</GxNotice>
      <GxNotice v-else-if="initialPage === 'sentry'" tone="info">{{ state.data?.subtitle || "Checking motion monitor…" }}</GxNotice>
      <div v-if="mode !== 'local'" class="gx-card gx-message" role="status">Local settings are unavailable in preview.</div>
      <template v-else>
        <div v-if="initialPage === 'hub'" class="gx-settings-tabs" aria-label="Settings sections">
          <button v-for="section in sections" :key="section.id" type="button" class="gx-chip" :aria-pressed="section.id === activeSection.id" :disabled="busy" @click="selectSection(section)">{{ section.label }}</button>
        </div>
        <section v-if="state.developerOpen" class="gx-card gx-settings__section gx-settings__developer" aria-label="Developer">
          <div class="gx-section__header"><i class="bi bi-code-slash" aria-hidden="true"></i><span class="gx-section__title">Developer</span></div>
          <div class="gx-settings__developer-body"><CloudProviderPage :mode="mode" :unauthorized="unauthorized" /></div>
        </section>
        <p v-if="state.status === 'saving' || state.status === 'updating'" class="gx-settings__save-status" role="status">Saving preference…</p>
        <div v-if="state.status === 'loading'" class="gx-card gx-message" role="status">Loading saved settings…</div>
        <div v-else-if="state.status === 'unavailable'" class="gx-card gx-message" role="alert">Saved settings are unavailable.</div>
        <div v-if="state.error" class="gx-card gx-message" role="alert">{{ state.error }}
          <button type="button" class="gx-btn gx-btn--tonal" :disabled="busy" @click="feed.load()">Refresh</button></div>
        <div v-if="state.data" class="gx-settings__body">
          <div v-if="state.data.page === 'appearance' || state.data.page === 'pip'" class="gx-settings__actions">
            <button v-if="state.data.page === 'appearance'" type="button" class="gx-btn gx-btn--tonal" :disabled="busy" @click="open('ui_layout')"><i class="bi bi-palette" aria-hidden="true"></i> Open Colors &amp; Layout</button>
            <button v-if="state.data.page === 'pip'" type="button" class="gx-btn gx-btn--tonal" :disabled="busy" @click="openCropEditor"><i class="bi bi-crop" aria-hidden="true"></i> Open crop editor</button>
          </div>
          <section class="gx-card gx-settings__section">
            <div class="gx-section__header"><i class="bi" :class="activeSection.icon" aria-hidden="true"></i><span class="gx-section__title">{{ state.data.page === 'hub' ? activeSection.label : state.data.title }}</span>
              <button v-if="state.data.page !== 'hub' && state.data.rows.length" type="button" class="gx-icon-btn" :aria-label="state.searchOpen ? 'Close page search' : 'Search within this page'" :aria-pressed="state.searchOpen" @click="togglePageSearch"><i class="bi" :class="state.searchOpen ? 'bi-x-lg' : 'bi-search'" aria-hidden="true"></i></button>
              <button v-if="state.data.page === 'hub'" type="button" class="gx-icon-btn" aria-label="Refresh settings" :disabled="busy" @click="feed.load()"><i class="bi bi-arrow-clockwise" aria-hidden="true"></i></button></div>
            <div v-if="state.searchOpen" class="gx-settings__search"><input ref="pageSearch" v-model="state.query" class="gx-field" type="search" aria-label="Search within this page" placeholder="Search within…"></div>
            <GalaxySettingRow v-for="{ row, index } in visibleRows" :key="rowKey(row, index)" :row="row" :index="index"
              :disabled="busy || !row.available" :save-value="(index, value) => feed.previewValue(index, value)"
              @open="open" @review="(index, direction) => feed.preview(index, direction)" @reset-default="index => feed.resetDefault(index)" />
            <div v-if="!visibleRows.length" class="gx-empty">No matching settings.</div>
          </section>
          <SoundPacks v-if="state.data.page === 'sounds'" :unauthorized="unauthorized" :disabled="busy" @installed="refreshSoundChoices" />
        </div>
        <Teleport to="body"><div v-if="state.pending" class="gx-settings__modal" role="dialog" aria-modal="true" aria-label="Confirm saved setting">
          <div class="gx-card gx-settings__dialog"><h3>Confirm Saved Preference</h3><p>{{ state.pending.question }}</p>
            <div class="gx-settings__controls"><button type="button" class="gx-btn gx-btn--tonal" @click="feed.cancel()">Cancel</button>
              <button type="button" class="gx-btn" @click="feed.confirm()">Save</button></div></div>
        </div></Teleport>
      </template>
    </section>`,
}
