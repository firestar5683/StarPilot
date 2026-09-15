import { api, showSnackbar } from "../api.js"
import { LANGUAGE_OPTIONS, languageState, normalizeLanguage, setLanguage, t } from "../i18n.js"
import { GalaxySelect } from "./GalaxySelect.js"

export const LanguageSelector = {
  name: "LanguageSelector",
  components: { GalaxySelect },
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
    <div class="gx-card gx-language-card">
      <div class="gx-section__header">
        <i class="bi bi-translate"></i>
        <span class="gx-section__title">{{ tr("Language") }}</span>
      </div>
      <div class="gx-language-card__row">
        <label class="gx-language-card__label">
          <span>{{ tr("Select language") }}</span>
          <GalaxySelect class="gx-field gx-language-card__select" :value="selected" :disabled="saving" @change="change">
            <option v-for="option in languages" :key="option.value" :value="option.value">{{ tr(option.label, option.label) }}</option>
          </GalaxySelect>
        </label>
        <small class="gx-row__desc gx-language-card__hint">{{ tr("Galaxy uses English when no language is selected.") }}</small>
      </div>
      <p v-if="error" class="gx-row__desc" style="color:var(--danger); margin:8px 0 0;">{{ error }}</p>
    </div>
  `,
}
