import fs from 'node:fs'
import vm from 'node:vm'
import assert from 'node:assert/strict'
const source = fs.readFileSync('../../galaxy/web/js/toggle-search.js', 'utf8').replace(/^import .*\n/gm, '').replaceAll('export ', '')
const settings = fs.readFileSync('../../galaxy/web/js/settings.js', 'utf8')
const sections = settings.slice(settings.indexOf('export const SETTINGS_SECTIONS'), settings.indexOf('\n\n// Crop')).replace('export ', '')
const adapter = fs.readFileSync('GalaxyBluetooth/LoopbackServer.swift', 'utf8').match(/static let nativeSearchScript = #"""\n([\s\S]*?)    """#/)[1]
function probe(timeout = 20000) {
  const context = vm.createContext({ window: { __galaxyNative: true }, AbortController, DOMException,
    setTimeout: (fn, ms) => setTimeout(fn, ms === 20000 ? timeout : ms), clearTimeout })
  vm.runInContext(sections + '\nconst isPipCropRow = () => false;\n' + source + '\n' + adapter + '\nglobalThis.api = {SettingsSearchIndex, ToggleSearch, searchSettings};', context)
  return context.api
}
const tick = () => new Promise(resolve => setImmediate(resolve))
async function until(condition) { for (let i = 0; i < 100; i++) { if (condition()) return; await tick() }; assert.fail('Expected search progress') }
const response = (page, rows = []) => ({ ok: true, status: 200, json: async () => ({ page, title: page, rows }) })
{
  const api = probe(), updates = []
  let active = 0, maximum = 0, release
  const index = new api.SettingsSearchIndex({ publish: value => updates.push(value), fetcher: async (url, options) => {
    assert.equal(options.method, undefined, 'Search must only read settings')
    active++; maximum = Math.max(maximum, active)
    const page = decodeURIComponent(url.split('/').at(-1))
    if (page === 'lane_change') await new Promise(resolve => { release = resolve })
    active--
    return response(page, page === 'aol' ? [{ label: 'Always On Lateral', value: 'On' }]
      : page === 'lane_change' ? [{label: 'Nested', page: 'lane_change/nested'}]
      : page === 'lane_change/nested' ? [{label: 'Lane change delay', value: '2 seconds'}] : [])
  }})
  const loading = index.load()
  await until(() => typeof release === 'function')
  assert(updates.some(update => update.status === 'loading' && update.entries.some(row => row.label === 'Always On Lateral')), 'Show matches before the whole scan finishes')
  release(); await loading
  assert.equal(maximum, 1, 'Bluetooth search must not enqueue four parallel page reads')
  assert.equal(index.status, 'ready')
  assert.equal(api.searchSettings(index.entries, 'always lateral').length, 1)
  assert(index.entries.some(row => row.label === 'Lane change delay'), 'Include nested settings')
}
{
  const api = probe(); let calls = 0
  const index = new api.SettingsSearchIndex({ fetcher: (url, options) => {
    calls++
    return new Promise((resolve, reject) => options.signal.addEventListener('abort', () => reject(new DOMException('Closed', 'AbortError'))))
  }})
  const loading = index.load()
  await until(() => calls === 1)
  api.ToggleSearch.methods.close.call({ index, state: {} })
  await loading
  assert.equal(calls, 1, 'Closing must cancel the rest of the index scan')
  assert.equal(index.status, 'idle')
  assert.equal(index.entries.length, 0)
}
{
  const api = probe(5); let calls = 0
  const index = new api.SettingsSearchIndex({ fetcher: async url => {
    calls++
    const page = decodeURIComponent(url.split('/').at(-1))
    if (calls === 1) return new Promise(() => {}) // Simulate a response that ignores cancellation.
    return response(page, [{label: 'Working later setting'}])
  }})
  await index.load()
  assert.equal(index.status, 'partial')
  assert(index.entries.length > 0, 'One timed-out page must not prevent later results')
}
{
  const api = probe(); let unauthorized = 0, calls = 0
  const index = new api.SettingsSearchIndex({ unauthorized: () => unauthorized++, fetcher: async () => { calls++; return {status: 401} } })
  await index.load()
  assert.equal(unauthorized, 1); assert.equal(calls, 1); assert.equal(index.status, 'idle')
}
console.log('Toggle search: incremental matches, serial reads, nested pages, close cancellation, bounded timeout and expired sessions passed')
