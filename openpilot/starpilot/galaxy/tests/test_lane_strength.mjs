import assert from "node:assert/strict"
import { presentedSetting, laneStrengthDisplay, laneStrengthSaved, GalaxySettingRow } from "../web/js/galaxy-setting-row.js"
const row = { displayScale: "lane-strength", minimum: 33, maximum: 200, step: 1, value: "100", defaultValue: "100", unit: "%", available: true }
assert.deepEqual([33, 100, 200].map(v => laneStrengthDisplay(v, row)), [1, 5, 10])
assert.deepEqual([1, 5, 10].map(v => laneStrengthSaved(v, row)), [33, 100, 200])
const display = presentedSetting(row)
assert.equal(display.minimum, 1); assert.equal(display.maximum, 10); assert.equal(display.step, 1)
assert.equal(display.value, 5); assert.equal(display.defaultValue, 5); assert.equal(display.unit, "")
for (let value = 33; value <= 200; value++) assert.equal(laneStrengthSaved(laneStrengthDisplay(value, row), row), value)
assert.equal(laneStrengthSaved(0, row), null); assert.equal(laneStrengthSaved(11, row), null)
assert.equal(presentedSetting({ value: "100" }).value, "100")
const saves = []
const context = { row, presentedRow: display, locked: false, saveValue: async (index, value) => saves.push(value), index: 0 }
await GalaxySettingRow.methods.commit.call(context, 5)
assert.deepEqual(saves, [])
await GalaxySettingRow.methods.commit.call(context, 10)
assert.deepEqual(saves, [200])
assert.equal(row.value, "100")
console.log("Lane strength presentation and unchanged raw transport verified")

// Mount the actual shared component with Vue's renderer, including its template.
const { createRenderer, nextTick } = await import('../web/vendor/vue/vue.esm-browser.js')
const node = (type, text = '') => ({ type, text, props: {}, children: [], parent: null })
const renderer = createRenderer({
  createElement: type => node(type), createText: text => node('text', text), createComment: text => node('comment', text),
  setText: (item, text) => { item.text = text }, setElementText: (item, text) => { item.text = text },
  patchProp: (item, key, before, after) => { item.props[key] = after },
  insert: (item, parent, anchor = null) => { item.parent = parent; const i = parent.children.indexOf(anchor); parent.children.splice(i < 0 ? parent.children.length : i, 0, item) },
  remove: item => { const i = item.parent?.children.indexOf(item); if (i >= 0) item.parent.children.splice(i, 1) },
  parentNode: item => item.parent, nextSibling: () => null,
})
// Vue's browser compiler defaults to a document-backed HTML entity decoder.
// This exact template contains no entity references: reject any future named or
// numeric reference (including optional-semicolon forms), then preserve its text.
// The actual Vue compiler and actual component template still run unchanged.
const entityReference = /&(?:#[xX][0-9a-fA-F]+|#[0-9]+|[A-Za-z][A-Za-z0-9]*)/
assert.doesNotMatch(GalaxySettingRow.template, entityReference)
const mountActualRow = (props, host) => {
  const app = renderer.createApp(GalaxySettingRow, props)
  app.config.compilerOptions.decodeEntities = raw => {
    assert.doesNotMatch(raw, entityReference)
    return raw
  }
  return app.mount(host)
}
const all = item => [item, ...item.children.flatMap(all)]
for (const surface of ['desktop-sidebar', 'mobile']) {
  const host = node(surface), commits = []
  const vm = mountActualRow({ row: { ...row, label: 'Lane Centering Strength', action: true }, index: 3,
    saveValue: async (index, value) => commits.push([index, value]) }, host)
  await nextTick()
  const slider = all(host).find(item => item.type === 'input' && item.props.type === 'range')
  assert.ok(slider, `${surface} renders actual slider`)
  assert.equal(Number(slider.props.min), 1); assert.equal(Number(slider.props.max), 10)
  assert.equal(Number(slider.props.step), 1); assert.equal(Number(slider.props.value), 5)
  assert.equal(commits.length, 0, 'mount never rewrites old bytes')
  for (const invalid of [0, 11, NaN]) await vm.commit(invalid)
  assert.equal(commits.length, 0, "invalid actual component commits have no effect")
  await vm.commit(5); assert.equal(commits.length, 0)
  await vm.commit(10); assert.deepEqual(commits, [[3, 200]])
  vm.$.appContext.app.unmount()
}
const disabledHost = node('disabled')
const disabledCommits = []
const disabledVm = mountActualRow({ row: { ...row, available: false, action: false, label: 'Lane Centering Strength' },
  index: 0, saveValue: async value => disabledCommits.push(value) }, disabledHost)
await disabledVm.commit(10)
assert.equal(disabledCommits.length, 0, 'unavailable setting has no effect')
disabledVm.$.appContext.app.unmount()
