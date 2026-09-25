import assert from 'node:assert/strict'
import { compile } from '../web/vendor/vue/vue.esm-browser.js'
import { GalaxyHotspot, validHotspot } from '../web/js/hotspot.js'
const value = { version: 1, revision: 'a'.repeat(64), editable: true, active: false, state: 'disabled', reason: '',
  url: 'http://172.31.254.1:8082/', config: { enabled: false, ssid: 'TheGalaxy-6b86', password: '' } }
assert.equal(validHotspot(value), true)
assert.equal(validHotspot({ ...value, config: { ...value.config, ssid: 'Custom network' } }), false)
assert.ok(!GalaxyHotspot.template.includes('v-model="draft.ssid"'))
assert.ok(GalaxyHotspot.template.includes('Broadcast hotspot automatically'))
assert.equal(validHotspot({ ...value, url: 'javascript:alert(1)' }), false)
assert.equal(validHotspot({ ...value, config: { ...value.config, password: 'bad\npassword' } }), false)
compile(GalaxyHotspot.template, { decodeEntities: value => value })
function instance() {
  const vm = { ...GalaxyHotspot.data(), mode: 'local', unauthorized() {} }
  for (const [name, fn] of Object.entries(GalaxyHotspot.methods)) vm[name] = fn.bind(vm)
  Object.defineProperty(vm, 'dirty', { get: () => GalaxyHotspot.computed.dirty.call(vm) })
  return vm
}
const vm = instance()
vm.adopt(value)
assert.equal(vm.dirty, false)
vm.draft.password = 'my-own-password'
vm.adopt({ ...value, revision: 'b'.repeat(64), config: { ...value.config, password: 'another-password' } })
assert.equal(vm.draft.password, 'my-own-password')
assert.equal(vm.revision, value.revision) // Polls must not bless a stale draft.
vm.adopt(value, true)
assert.equal(vm.dirty, false)
let requests = 0, resolve
globalThis.fetch = (_url, options) => { requests++; return new Promise(done => { resolve = done }) }
vm.mode = 'sample'; vm.start()
assert.equal(requests, 0)
vm.active = true
const reading = vm.refresh()
vm.stop()
resolve({ ok: true, json: async () => value })
await reading
assert.equal(vm.snapshot, null)
assert.equal(vm.draft, null)
let auth = 0
vm.unauthorized = () => auth++
globalThis.fetch = async () => ({ ok: false, status: 401, json: async () => ({ error: 'Sign in' }) })
vm.active = true
await vm.refresh()
assert.equal(auth, 1)
assert.equal(vm.active, false)
assert.equal(vm.timer, null)
console.log('Hotspot: schema, Vue template, preview exclusion, stale drafts, unmount race, credential clearing and authentication passed')
