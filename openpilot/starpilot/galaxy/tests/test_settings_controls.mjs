import assert from "node:assert/strict"
import { GalaxySettingRow, settingControl, numericBounds, snapNumeric, FINE_SCRUB_HOLD_MS, FINE_SCRUB_FACTOR } from "../web/js/galaxy-setting-row.js"
import { SettingsPage, SETTINGS_SECTIONS } from "../web/js/settings.js"

const numeric = { label: "Following time", value: "1.5", minimum: .5, maximum: 3, step: .05, unit: "s", available: true, action: true }
assert.equal(settingControl(numeric), "slider")
assert.equal(settingControl({ ...numeric, value: "Invalid saved value" }), "readout")
assert.equal(settingControl({ ...numeric, repairValue: "1.5" }), "action")
assert.equal(settingControl({ choices: ["Off", "On"], value: "Off" }), "switch")
assert.equal(settingControl({ choices: ["Off", "On"], value: "Invalid" }), "readout")
assert.equal(settingControl({ choices: ["Stock", "Custom"], value: "Stock" }), "select")
assert.equal(numericBounds({ ...numeric, maximum: Infinity }), null)
assert.equal(numericBounds({ ...numeric, step: 0 }), null)
assert.equal(snapNumeric(2.126, numericBounds(numeric)), 2.15)
assert.equal(snapNumeric(-99, numericBounds(numeric)), .5)
assert.equal(snapNumeric(99, numericBounds(numeric)), 3)
assert.equal(snapNumeric("invalid", numericBounds(numeric)), null)
assert.equal(snapNumeric("", numericBounds(numeric)), null)
assert.equal(snapNumeric(223.69, { min: 0, max: 223.69, step: 1 }), 223)
assert.equal(snapNumeric(999, { min: 0, max: 223.69, step: 1 }), 223)
assert.equal(snapNumeric(160.934, { min: 0, max: 160.934, step: 1 }), 160)
assert.equal(snapNumeric(20, { min: .5, max: 2.8, step: .5 }), 2.5)
assert.equal(snapNumeric(.6, { min: 0, max: .6, step: .2 }), .6)
assert.equal(snapNumeric(9999, { min: 183, max: 1161, step: 10 }), 1153)
assert.equal(FINE_SCRUB_HOLD_MS, 300)
assert.equal(FINE_SCRUB_FACTOR, 5)
assert.equal(settingControl({ ...numeric, choices: ['Auto'], value: 'Auto' }), 'slider')

function control(row = numeric) {
  const commits = []
  const vm = { ...GalaxySettingRow.data(), row, index: 7, disabled: false,
    saveValue: async (...args) => commits.push(args),
    $refs: { slider: { value: row.value, setPointerCapture() {}, releasePointerCapture() {}, getBoundingClientRect: () => ({ width: 250 }) } } }
  for (const [key, method] of Object.entries(GalaxySettingRow.methods)) vm[key] = method.bind(vm)
  for (const [key, getter] of Object.entries(GalaxySettingRow.computed)) Object.defineProperty(vm, key, { get: () => getter.call(vm) })
  const event = (x = 100, pointerId = 1) => ({ target: vm.$refs.slider, pointerId, clientX: x, preventDefault() {} })
  return { vm, commits, event }
}

// Drag previews remain local. Fine mode uses the held value and one fifth of normal travel.
const fine = control()
fine.vm.onSliderPointerDown(fine.event())
fine.vm.$refs.slider.value = 2
fine.vm.onSliderInput(fine.event())
assert.equal(fine.commits.length, 0)
fine.vm.activateFineScrub()
fine.vm.onSliderPointerMove(fine.event(150))
assert.equal(fine.vm.currentValue, 2.1)
fine.vm.$refs.slider.value = 3
fine.vm.onSliderInput(fine.event(150))
assert.equal(fine.vm.$refs.slider.value, 2.1) // Native range input cannot overwrite fine motion.
await fine.vm.onSliderPointerEnd(fine.event(150))
assert.deepEqual(fine.commits, [[7, 2.1]])
assert.equal(fine.vm.isFineScrubbing, false)
assert.equal(fine.vm._holdTimer, undefined)

const cancelled = control()
cancelled.vm.onSliderPointerDown(cancelled.event())
cancelled.vm.$refs.slider.value = 2.5
cancelled.vm.onSliderInput(cancelled.event())
cancelled.vm.onSliderCancel(cancelled.event())
await cancelled.vm.onSliderPointerEnd(cancelled.event())
assert.equal(cancelled.commits.length, 0)
assert.equal(cancelled.vm.currentValue, "1.5")

const keyboard = control()
keyboard.vm.$refs.slider.value = 1.55
keyboard.vm.onSliderInput(keyboard.event())
await keyboard.vm.onSliderCommit(keyboard.event())
assert.deepEqual(keyboard.commits, [[7, 1.55]])

const locked = control({ ...numeric, available: false })
locked.vm.onSliderPointerDown(locked.event())
await locked.vm.commit(2)
assert.equal(locked.vm.fineScrub, null)
assert.equal(locked.commits.length, 0)

const switched = control({ ...numeric, choices: ["Off", "On"], value: "Off", step: 0 })
await switched.vm.onSwitch({ target: { checked: true } })
assert.deepEqual(switched.commits, [[7, "On"]])

// Auto is an explicit labeled endpoint, never a fabricated numeric setting.
const automatic = control({ ...numeric, label: 'Screen brightness', minimum: 0, maximum: 100,
  step: 1, unit: '%', choices: ['Auto'], value: 'Auto' })
assert.equal(automatic.vm.sliderValue, 101)
assert.equal(automatic.vm.displayValue, 'Auto')
assert.equal(automatic.commits.length, 0, 'rendering Auto saves nothing')
await automatic.vm.flushSlider(101)
assert.equal(automatic.commits.length, 0, 'keeping the Auto endpoint saves nothing')
await automatic.vm.flushSlider(60)
assert.deepEqual(automatic.commits, [[7, 60]])
const fixed = control({ ...automatic.vm.row, value: '60' })
await fixed.vm.flushSlider(101)
assert.deepEqual(fixed.commits, [[7, 'Auto']])
const autoCancelled = control(automatic.vm.row)
autoCancelled.vm.onSliderPointerDown(autoCancelled.event())
autoCancelled.vm.$refs.slider.value = 50
autoCancelled.vm.onSliderInput(autoCancelled.event())
autoCancelled.vm.onSliderCancel(autoCancelled.event())
assert.equal(autoCancelled.vm.$refs.slider.value, 101)
assert.equal(autoCancelled.commits.length, 0)
const warning = control({ ...automatic.vm.row, minimum: 35, maximum: 100, step: 5, value: '70' })
await warning.vm.flushSlider(0)
assert.deepEqual(warning.commits, [[7, 35]], 'the owner-provided warning floor is retained')
const audioRows = [{ ...automatic.vm.row, value: '60' },
  { label: 'Use Auto Screen brightness', value: 'Fixed level saved', repairValue: 'Auto' },
  { label: 'Sound Pack', value: 'stock', choices: ['stock', 'custom'] }]
assert.deepEqual(SettingsPage.computed.visibleRows.call({ initialPage: 'sounds', activeSection: {},
  state: { query: '', data: { page: 'sounds', rows: audioRows } } }).map(({ index }) => index), [0, 2],
  'the redundant native Auto action is hidden without renumbering owner rows')

const lateral = SETTINGS_SECTIONS[0]
const page = { initialPage: "hub", activeSection: lateral, state: { query: "", data: { page: "hub", rows: [
  { label: "SLC", page: "slc" }, { label: "AOL", page: "aol" }, { label: "Lane", page: "lane" },
] } } }
assert.deepEqual(SettingsPage.computed.visibleRows.call(page).map(({ index }) => index), [1, 2])
page.state.query = "lane"
assert.deepEqual(SettingsPage.computed.visibleRows.call(page).map(({ index }) => index), [2])

// Single-page sections open their controls in one tap, including when moving
// from another section's child page. Multi-page sections still use the hub.
const destinations = []
const navigation = { busy: false, state: { query: "old", section: "lateral", data: { page: "lane" } },
  feed: { active: true, load: (target) => destinations.push(target) } }
for (const id of ["wheel", "sounds", "device", "visual"]) {
  const section = SETTINGS_SECTIONS.find((item) => item.id === id)
  SettingsPage.methods.selectSection.call(navigation, section)
  assert.equal(navigation.state.section, id)
  assert.equal(navigation.state.query, "")
}
assert.deepEqual(destinations, ["wheel", "sounds", "hub", "hub"])
navigation.busy = true
SettingsPage.methods.selectSection.call(navigation, lateral)
assert.equal(destinations.length, 4, "a save cannot be retired by section navigation")
for (const id of ["wheel", "sounds"]) {
  const section = SETTINGS_SECTIONS.find((item) => item.id === id)
  assert.equal(SettingsPage.computed.atSectionRoot.call({ activeSection: section,
    state: { data: { page: section.pages[0] } } }), true)
}

const deviceData = SETTINGS_SECTIONS.find((item) => item.id === "device")
assert.deepEqual(deviceData.pages, ["display", "data"])
assert.equal(SettingsPage.computed.atSectionRoot.call({ activeSection: deviceData,
  state: { data: { page: "hub" } } }), true)
assert.equal(SettingsPage.computed.atSectionRoot.call({ activeSection: deviceData,
  state: { data: { page: "display" } } }), false)

const dataLinks = SettingsPage.computed.visibleRows.call({ initialPage: "hub", activeSection: deviceData,
  state: { query: "", data: { page: "hub", rows: [] } } })
assert.deepEqual(dataLinks.map(({ row }) => row.page), ["display", "data"])
