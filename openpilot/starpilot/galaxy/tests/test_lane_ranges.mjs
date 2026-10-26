import assert from "node:assert/strict"
import { GalaxySettingRow, GalaxyRangeSettingRow, pairedSettingRows } from "../web/js/galaxy-setting-row.js"
import { SettingsPage } from "../web/js/settings.js"

function entries(group = "response", enabled = true) {
  const row = { minimum: 0, maximum: 1, step: .01, unit: "s", available: true, action: true, choices: [] }
  const pair = { group, enabled, label: "Correction response time", help: "Response speed" }
  return [
    { index: 4, row: { ...row, label: "Maximum response", value: ".35", rangePair: { ...pair, end: "max" } } },
    { index: 7, row: { ...row, label: "Minimum response", value: ".1", rangePair: { ...pair, end: "min" } } },
  ]
}

function control(entry) {
  const commits = []
  const vm = { ...GalaxySettingRow.data(), ...GalaxyRangeSettingRow.data(), ...entry, disabled: false, busy: false,
    $refs: {}, saveValue: async (...args) => commits.push(args) }
  for (const [key, method] of Object.entries({ ...GalaxySettingRow.methods, ...GalaxyRangeSettingRow.methods })) vm[key] = method.bind(vm)
  for (const [key, getter] of Object.entries({ ...GalaxySettingRow.computed, ...GalaxyRangeSettingRow.computed })) {
    Object.defineProperty(vm, key, { get: () => getter.call(vm) })
  }
  return { vm, commits }
}

// Combining rows must preserve the original scalar-setting indices for writes.
const source = entries()
const paired = pairedSettingRows(source)
assert.equal(paired.length, 1)
assert.equal(paired[0].index, 4)
assert.equal(paired[0].row.paired.lowerIndex, 7)
assert.equal(source[0].row.paired, undefined)
const { vm, commits } = control(paired[0])
vm.selectEndpoint("min")
await vm.flushSlider(.2)
vm.selectEndpoint("max")
await vm.flushSlider(.4)
assert.deepEqual(commits, [[7, .2], [4, .4]])
assert.equal(vm.boundedValue(.05), .1)
vm.selectEndpoint("min")
assert.equal(vm.boundedValue(.9), .35)
assert.equal(vm.boundedValue("invalid"), null)
vm.busy = true
await vm.flushSlider(.25)
vm.selectEndpoint("max")
assert.equal(vm.endpoint, "min")
assert.equal(commits.length, 2)

// Turning adaptation off exposes only the normal value; radius remains a disabled pair.
assert.equal(pairedSettingRows(entries("response", false))[0].row.paired, null)
const radius = control(pairedSettingRows(entries("radius", false))[0]).vm
radius.selectEndpoint("min")
assert.equal(radius.boundedValue(.9), .35 - .01)
radius.selectEndpoint("max")
assert.equal(radius.boundedValue(0), .1 + .01)
radius.row.available = false
assert.equal(radius.dimmed, true)

// Incomplete or malformed pairs stay independently visible for repair.
assert.equal(pairedSettingRows(source.slice(0, 1)).length, 1)
const broken = entries(); broken[1].row.value = "Invalid saved value"
assert.equal(pairedSettingRows(broken).length, 2)

// The real SettingsPage uses the combined row and keeps save indices after search.
const page = { initialPage: "lane", activeSection: {}, state: { query: "response", data: {
  page: "lane/preferences/smoothing", rows: source.map(item => item.row),
} } }
const visible = SettingsPage.computed.visibleRows.call(page)
assert.equal(visible.length, 1)
assert.equal(visible[0].row.label, "Correction response time")
assert.equal(visible[0].index, 0)
assert.equal(visible[0].row.paired.lowerIndex, 1)
console.log("Paired settings preserve scalar writes, bounds, disabled state, repair rows and page search")
