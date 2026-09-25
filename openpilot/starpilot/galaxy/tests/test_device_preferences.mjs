import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { DEVICE_PAGES, DevicePreferencesPage, devicePage } from "../web/js/device-preferences.js"
import { DriveStatePanel } from "../web/js/drive-state.js"
assert.deepEqual(Object.keys(DEVICE_PAGES), [])
for (const path of ["/device-preferences", "/device-preferences/sounds", "/device-preferences/display", "/device-preferences/alpha"]) assert.equal(devicePage(path), null)
assert.equal(DevicePreferencesPage.components.DriveStatePanel, DriveStatePanel)
assert.match(DevicePreferencesPage.template, /<DriveStatePanel v-if="mode === 'local'"/)
assert.match(DevicePreferencesPage.template, /Force Drive State/)
assert.doesNotMatch(DevicePreferencesPage.template, /sounds|display|SettingsPage/)
const app = readFileSync(new URL("../web/js/app.js", import.meta.url), "utf8")
assert.match(app, /<DevicePreferencesPage v-else-if="route\.path === '\/device-preferences'"/)
