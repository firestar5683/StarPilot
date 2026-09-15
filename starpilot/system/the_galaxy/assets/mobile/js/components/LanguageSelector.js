import { api, showSnackbar } from "../api.js"
import { GxNotice } from "./GxNotice.js"
import { LANGUAGE_OPTIONS, languageState, normalizeLanguage, setLanguage, t } from "../i18n.js"

export const LanguageSelector = {
  name: "LanguageSelector",
  components: { GxNotice },
  props: { deviceValue: { type: String, default: "" } },
  data() {
    return { languages: LANGUAGE_OPTIONS, selected: languageState.code, saving: false, error: "" }
  },
  computed: {
    languageCode() { return languageState.code },
  },
  watch: {
    languageCode(value) { this.selected = value },
    deviceValue: {
      immediate: true,
      handler(value) {
        if (!value) return
        this.selected = setLanguage(value)
      },
    },
  },
  methods: {
    tr(key, fallback = key) { return t(key, fallback) },
    async change(event) {
      const next = normalizeLanguage(event.target.value)
      const previous = languageState.code
      this.selected = next
      this.error = ""
      setLanguage(next)
      this.saving = true
      try {
        // LanguageSetting is shared with the native UI, which stores the
        // language catalog values as main_<locale>.
        await api.updateParam({ key: "LanguageSetting", value: `main_${next}` })
        showSnackbar(t("Language updated.", "Language updated."))
      } catch (err) {
        setLanguage(previous)
        this.selected = previous
        this.error = err?.message || t("Unable to save language.", "Unable to save language.")
        showSnackbar(this.error, "error")
      } finally {
        this.saving = false
      }
    },
  },
  template: `
    <div class="gx-card">
      <div class="gx-section__header">
        <i class="bi bi-translate"></i>
        <span class="gx-section__title">{{ tr("Language") }}</span>
      </div>
      <div class="gx-row gx-row--stack">
        <div class="gx-row__info">
          <span class="gx-row__label">{{ tr("Select language") }}</span>
          <span class="gx-row__desc">{{ tr("Galaxy uses English when no language is selected.") }}</span>
        </div>
        <GalaxySelect class="gx-field" :value="selected" :disabled="saving" @change="change">
          <option v-for="option in languages" :key="option.value" :value="option.value">{{ tr(option.label, option.label) }}</option>
        </GalaxySelect>
      </div>
      <GxNotice v-if="error" tone="danger" :text="error" style="margin: 0 var(--sp-4) var(--sp-4);" />
    </div>
  `,
}
