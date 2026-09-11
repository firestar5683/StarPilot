let nextHistoryId = 0

function validDate(value) {
  const date = value ? new Date(value) : null
  return date && Number.isFinite(date.getTime()) ? date : null
}

function dateLabel(date) {
  return date.toLocaleDateString(undefined, { day: "numeric", month: "short", year: "numeric" })
}

export function groupVersionHistory(commits) {
  const groups = new Map()
  for (const commit of commits) {
    const date = validDate(commit.date)
    // Local calendar days match the local date/time displayed for each build.
    const key = date ? `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}` : "unknown"
    if (!groups.has(key)) groups.set(key, { key, label: date ? dateLabel(date) : "Unknown date", commits: [] })
    groups.get(key).commits.push(commit)
  }
  return [...groups.values()].sort((a, b) => a.key === "unknown" ? 1 : b.key === "unknown" ? -1 : b.key.localeCompare(a.key))
}

// History arrives newest first. Keep that exact build when older pages repeat a release.
export function releaseVersions(commits) {
  const versions = new Map()
  for (const commit of commits) {
    const key = commit.version || ""
    if (!versions.has(key)) versions.set(key, commit)
  }
  return [...versions.values()].sort((a, b) => {
    if (!a.version) return b.version ? 1 : 0
    if (!b.version) return -1
    const left = a.version.split(".").map(Number), right = b.version.split(".").map(Number)
    return right[0] - left[0] || right[1] - left[1] || right[2] - left[2]
  })
}

export function versionTitle(commit, releaseBranch) {
  const date = validDate(commit?.date)
  const when = date ? `${dateLabel(date)} · ${date.toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit", second: "2-digit" })}` : "Unknown date"
  return releaseBranch ? `${commit?.version || "Unnumbered version"} · ${when}` : `${commit?.subject || "Untitled change"} · ${when} · ${String(commit?.sha || "").slice(0, 10)}`
}

export const VersionHistoryPicker = {
  name: "VersionHistoryPicker",
  inheritAttrs: false,
  props: { value: { default: "" }, commits: { type: Array, default: () => [] }, releaseBranch: Boolean, loading: Boolean, hasMore: Boolean, error: { default: "" }, notice: { default: "" }, disabled: Boolean },
  emits: ["change", "loadmore"],
  data() { return { uid: `gx-history-${++nextHistoryId}`, open: false, expanded: {} } },
  computed: {
    choices() { return this.releaseBranch ? releaseVersions(this.commits) : this.commits },
    groups() { return groupVersionHistory(this.choices) },
    selected() { return this.choices.find(commit => commit.sha === this.value) },
    label() { return this.selected ? versionTitle(this.selected, this.releaseBranch) : "Select an earlier version" },
    range() {
      if (this.releaseBranch) return `${this.choices.length} ${this.choices.length === 1 ? "release" : "releases"} · ${this.commits.length} builds checked`
      const known = this.groups.filter(group => group.key !== "unknown")
      if (!known.length) return this.commits.length ? `${this.commits.length} versions loaded` : "No history loaded yet"
      return `${this.commits.length} versions · ${known.at(-1).label}${known.length > 1 ? ` – ${known[0].label}` : ""}`
    },
  },
  watch: {
    commits: { immediate: true, handler() { this.syncDays() } },
    disabled(value) { if (value) this.close() },
  },
  methods: {
    versionTitle,
    syncDays() {
      const firstLoad = !Object.keys(this.expanded).length
      const expanded = {}
      for (const [index, group] of this.groups.entries()) expanded[group.key] = this.expanded[group.key] ?? (firstLoad && index === 0)
      this.expanded = expanded
    },
    async show() {
      if (this.disabled) return
      const selectedDay = this.groups.find(group => group.commits.some(commit => commit.sha === this.value))
      if (selectedDay) this.expanded[selectedDay.key] = true
      this.open = true
      await this.$nextTick()
      this.$refs.menu.showModal()
      this.position()
      ;(this.$refs.menu.querySelector('[aria-selected="true"]') || this.$refs.menu.querySelector('[data-day]') || this.$refs.close).focus()
    },
    close() {
      if (!this.open) return
      this.open = false
      this.$refs.menu?.close()
      if (this.$refs.button?.isConnected) this.$refs.button.focus({ preventScroll: true })
    },
    position() {
      if (!this.open) return
      const viewport = window.visualViewport
      const width = viewport?.width || window.innerWidth
      const height = viewport?.height || window.innerHeight
      const menu = this.$refs.menu
      const rect = this.$refs.button.getBoundingClientRect()
      let zoom = 1
      for (let node = menu; node; node = node.parentElement) zoom *= Number.parseFloat(getComputedStyle(node).zoom) || 1
      const menuWidth = Math.min(Math.max(rect.width, 420), width - 24)
      const menuHeight = Math.min(640, height - 24)
      menu.style.width = `${menuWidth / zoom}px`
      menu.style.height = `${menuHeight / zoom}px`
      menu.style.left = `${Math.max(12, Math.min(rect.left, width - menuWidth - 12)) / zoom}px`
      menu.style.top = `${Math.max(12, Math.min(rect.bottom + 6, height - menuHeight - 12)) / zoom}px`
    },
    select(sha) {
      if (this.disabled || !/^[a-f0-9]{40}$/.test(sha) || !(this.releaseBranch ? releaseVersions(this.commits) : this.commits).some(commit => commit.sha === sha)) return
      this.$emit("change", { target: { value: sha } })
      this.close()
    },
    loadMore() {
      if (this.disabled || this.loading || (!this.hasMore && !this.error)) return
      this.$emit("loadmore")
    },
    buttonKey(event) {
      if (["ArrowDown", "ArrowUp"].includes(event.key)) { event.preventDefault(); this.show() }
    },
    menuKey(event) {
      const target = event.target
      const day = target.closest("[data-day-group]")
      if (day && ["ArrowLeft", "ArrowRight"].includes(event.key)) {
        event.preventDefault()
        this.expanded[day.dataset.dayGroup] = event.key === "ArrowRight"
        day.querySelector("[data-day]").focus()
        return
      }
      const items = [...this.$refs.menu.querySelectorAll("button:not(:disabled)")].filter(button => button.getClientRects().length)
      const index = items.indexOf(target)
      let next
      if (event.key === "ArrowDown") next = items[(index + 1) % items.length]
      if (event.key === "ArrowUp") next = items[(index - 1 + items.length) % items.length]
      if (event.key === "Home") next = items[0]
      if (event.key === "End") next = items.at(-1)
      if (next) { event.preventDefault(); next.focus() }
    },
  },
  mounted() {
    window.addEventListener("resize", this.position)
    window.visualViewport?.addEventListener("resize", this.position)
  },
  beforeUnmount() {
    this.$refs.menu?.close()
    window.removeEventListener("resize", this.position)
    window.visualViewport?.removeEventListener("resize", this.position)
  },
  template: `
    <div class="gx-history-picker" style="min-width:0;">
      <span class="gx-select gx-field gx-field--full">
        <button ref="button" :id="$attrs.id || uid" class="gx-select__button" type="button" aria-haspopup="dialog" :aria-expanded="open" :aria-controls="uid + '-dialog'"
          :aria-label="'Earlier version: ' + label" :disabled="disabled" @click="show" @keydown="buttonKey">
          <span style="white-space:normal; overflow-wrap:anywhere;">{{ label }}</span><i class="bi bi-chevron-down" aria-hidden="true"></i>
        </button>
      </span>
      <p class="gx-note" style="margin:6px 0 0;">{{ range }}. {{ hasMore ? (releaseBranch ? 'Open the picker to load older versions.' : 'Open the picker to load older days.') : (commits.length && !error ? 'All available history loaded.' : 'Open the picker to browse history.') }}</p>
      <p v-if="notice" class="gx-note" role="status" style="margin:6px 0 0;">{{ notice }}</p>
      <dialog ref="menu" :id="uid + '-dialog'" class="gx-select-menu gx-history-menu" :aria-labelledby="uid + '-title'" :aria-describedby="uid + '-help'"
        style="padding:0; overflow:hidden;" @cancel.prevent="close" @click="event => { if (event.target === $refs.menu) close() }" @keydown="menuKey">
        <div style="height:100%; display:flex; flex-direction:column; min-height:0;">
          <div style="padding:14px 16px; border-bottom:1px solid var(--outline-variant);">
            <div style="display:flex; align-items:center; justify-content:space-between; gap:12px;">
              <strong :id="uid + '-title'">{{ releaseBranch ? 'Earlier StarPilot versions' : 'Earlier versions by day' }}</strong>
              <button ref="close" type="button" class="gx-btn gx-btn--tonal" aria-label="Close version history" style="min-width:44px; padding:8px;" @click="close">✕</button>
            </div>
            <p class="gx-note" style="margin:6px 0;" aria-live="polite">{{ range }}</p>
            <p v-if="notice" class="gx-note" role="status" style="margin:6px 0;">{{ notice }}</p>
            <p :id="uid + '-help'" class="gx-note" style="margin:0;">{{ releaseBranch ? 'Each version uses its newest build. Build dates are shown in your local time.' : 'Expand a day to choose a build. Build dates are shown in your local time.' }}</p>
          </div>
          <div ref="scroll" style="overflow-y:auto; overscroll-behavior:contain; min-height:0; flex:1; padding:6px;" :aria-busy="loading">
            <div v-if="releaseBranch" role="listbox" aria-label="StarPilot releases">
              <button v-for="commit in choices" :key="commit.sha" type="button" role="option" :data-value="commit.sha" :aria-selected="commit.sha === value" :disabled="disabled" @click="select(commit.sha)">
                <span style="min-width:0; overflow-wrap:anywhere;">{{ versionTitle(commit, true) }}</span>
                <i v-if="commit.sha === value" class="bi bi-check-lg" aria-hidden="true"></i>
              </button>
            </div>
            <template v-else>
            <section v-for="group in groups" :key="group.key" :data-day-group="group.key" style="border-bottom:1px solid var(--outline-variant);">
              <button type="button" class="gx-btn gx-btn--tonal" :data-day="group.key" :aria-expanded="expanded[group.key]" :aria-controls="uid + '-' + group.key"
                style="width:100%; display:flex; justify-content:space-between; gap:12px; text-align:left; padding:12px; border-radius:8px; margin:2px 0;"
                @click="expanded[group.key] = !expanded[group.key]">
                <span>{{ group.label }} <small style="opacity:.7;">· {{ group.commits.length }} {{ group.commits.length === 1 ? 'build' : 'builds' }}</small></span>
                <i :class="expanded[group.key] ? 'bi bi-chevron-up' : 'bi bi-chevron-down'" aria-hidden="true"></i>
              </button>
              <div v-if="expanded[group.key]" :id="uid + '-' + group.key" role="listbox" :aria-label="group.label + ' versions'">
                <button v-for="commit in group.commits" :key="commit.sha" type="button" role="option" :data-value="commit.sha" :aria-selected="commit.sha === value" :disabled="disabled" @click="select(commit.sha)">
                  <span style="min-width:0; overflow-wrap:anywhere;">
                    <span>{{ versionTitle(commit, releaseBranch) }}</span>
                  </span><i v-if="commit.sha === value" class="bi bi-check-lg" aria-hidden="true"></i>
                </button>
              </div>
            </section>
            </template>
          </div>
            <div style="padding:12px 16px; border-top:1px solid var(--outline-variant); flex-shrink:0;">
              <p v-if="error" class="gx-note gx-note--danger" role="alert" style="overflow-wrap:anywhere;">{{ error }}</p>
              <p v-if="loading" class="gx-note" role="status">Loading older history…</p>
              <button v-if="hasMore || error" type="button" class="gx-btn gx-btn--tonal" :aria-disabled="loading || disabled" style="width:100%; white-space:normal;" @click="loadMore">{{ error ? 'Retry history' : (releaseBranch ? 'Load older versions' : 'Load older days') }}</button>
              <p v-else-if="!loading" class="gx-note" role="status">{{ commits.length ? 'All available history loaded.' : 'No history available.' }}</p>
              <p v-if="hasMore && !error" class="gx-note" style="margin-bottom:0;">Keep loading to browse further back.</p>
            </div>
        </div>
      </dialog>
    </div>
  `,
}
