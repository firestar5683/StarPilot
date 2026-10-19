import assert from 'node:assert/strict'
import { createRenderer, h, nextTick } from '../web/vendor/vue/vue.esm-browser.js'
import { LocalRecordingsPage, validLocalHistory } from '../web/js/record-history.js'

const node = (type, text = '') => ({ type, text, props: {}, children: [], parent: null, style: {},
  addEventListener() {}, removeEventListener() {} })
const renderer = createRenderer({
  createElement: type => node(type), createText: text => node('text', text), createComment: text => node('comment', text),
  setText: (item, text) => { item.text = text }, setElementText: (item, text) => { item.text = text },
  patchProp: (item, key, before, after) => { item.props[key] = after },
  insert(item, parent, anchor = null) {
    if (item.parent) { const index = item.parent.children.indexOf(item); if (index >= 0) item.parent.children.splice(index, 1) }
    item.parent = parent
    const index = parent.children.indexOf(anchor)
    parent.children.splice(index < 0 ? parent.children.length : index, 0, item)
  },
  remove(item) { const index = item.parent?.children.indexOf(item); if (index >= 0) item.parent.children.splice(index, 1) },
  parentNode: item => item.parent, nextSibling(item) { const siblings = item.parent?.children || []; return siblings[siblings.indexOf(item) + 1] || null },
})
const text = item => (item.type === 'comment' ? '' : item.text) + item.children.map(text).join('')
const inventory = { schemaVersion: 1, source: 'local', partialHistory: true, scanIncomplete: false, routes: [] }
const notice = 'Older StarPilot recordings also use device storage.'
const entities = /&(?:#[xX][0-9a-fA-F]+|#[0-9]+|[A-Za-z][A-Za-z0-9]*)/
// Render the actual page template and notice component. Network lifecycle and
// unrelated interactive select behavior are outside this presentation test.
const View = { ...LocalRecordingsPage, created: undefined, mounted: undefined, beforeUnmount: undefined,
  components: { ...LocalRecordingsPage.components,
    GalaxySelect: { render() { return h('select', null, this.$slots.default?.()) } } },
  data: () => ({ ...LocalRecordingsPage.data(), status: 'ready', data: { ...inventory, legacyRecordingsPresent: true } }),
}
const host = node('host')
const app = renderer.createApp(View, { mode: 'local', unauthorized() {} })
app.config.compilerOptions.decodeEntities = raw => { assert.doesNotMatch(raw, entities); return raw }
const vm = app.mount(host)
await nextTick()
assert.equal(validLocalHistory(vm.data), true)
assert.ok(text(host).includes(notice), 'legacy notice renders even when there are no current-root routes')
assert.ok(text(host).includes('No saved drives found on this device.'), 'notice does not inject false route entries')
vm.data = { ...inventory, legacyRecordingsPresent: false }
await nextTick()
assert.ok(!text(host).includes(notice), 'no notice without admitted legacy recordings')
vm.data = { ...inventory }
await nextTick()
assert.ok(!text(host).includes(notice), 'old server responses remain supported')
vm.data = { ...inventory, legacyRecordingsPresent: 'true' }
await nextTick()
assert.ok(!text(host).includes(notice), 'an invalid truthy value does not display the notice')
vm.data = { ...inventory, legacyRecordingsPresent: true, scanIncomplete: true }
await nextTick()
assert.ok(text(host).includes(notice))
assert.ok(text(host).includes('This scan was incomplete.'), 'existing incomplete-scan notice remains independent')
app.unmount()
console.log('Legacy storage notice: actual Vue render/update with empty inventory, absent/false/invalid field and incomplete-scan coexistence passed')
