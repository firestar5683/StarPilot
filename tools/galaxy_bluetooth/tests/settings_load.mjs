import assert from "node:assert/strict"
import { readFile } from "node:fs/promises"
import vm from "node:vm"

const web = new URL("../ios/GalaxyBluetooth/Resources/Web/", import.meta.url)
const { reactive, nextTick, watch } = await import(new URL("assets/vendor/vue/vue.esm-browser.js", web))
const source = (await readFile(new URL("assets/mobile/js/views/Settings.js", web), "utf8"))
  .replace(/import[\s\S]*?from [^\n]+\n/g, "")
  .replace("export const Settings", "const Settings") + "\nSettings"
let reads = 0
let developerMode = true
const components = Object.fromEntries(["SettingTree", "PersonalityProfiles", "GalaxyToggleCard", "GalaxySection",
  "DevModeBanner", "LongitudinalMode", "LanguageSelector"].map(name => [name, {}]))
const Settings = vm.runInNewContext(source, {
  ...components, GALAXY_DEVELOPER_MODE_KEY: "developerMode", longitudinalModeLayout: layout => layout,
  setLanguage() {}, showSnackbar(message) { throw new Error(message) },
  api: { getLayout: async () => [], getDefaults: async () => { throw new Error("Settings must not fetch unused defaults") },
    getSettingsParams: async () => { reads++; return { developerMode } } },
})
const model = reactive({ ...Settings.data(), ...Settings.methods, sections: [], $nextTick: nextTick })
const stop = watch(() => !!model.values.developerMode, () => Settings.watch.devModeOn.call(model))
await model.load()
await nextTick()
assert.equal(reads, 1, "Initial developer mode must not download Settings twice")
assert.equal(model.loading, false)
developerMode = false
model.values.developerMode = false
await nextTick()
while (model.loadPending) await nextTick()
assert.equal(reads, 2, "An actual developer mode change must refresh Settings once")
stop()

const api = (await import(new URL("assets/mobile/js/api.js", web))).api
const originalFetch = globalThis.fetch
const paths = []
globalThis.fetch = async path => { paths.push(path); return { ok: true, text: async () => "English\n", json: async () => ({ Metric: true }) } }
try {
  assert.equal(await api.getLanguage(), "English")
  assert.deepEqual(await api.getSettingsParams(), { Metric: true })
  assert.deepEqual(paths, ["/api/params?key=LanguageSetting", "/api/params/all?galaxy_ble_settings=1"])
} finally { globalThis.fetch = originalFetch }
console.log("Settings: one initial load, one developer-mode refresh, single-key language read passed")
