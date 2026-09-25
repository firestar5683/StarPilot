import assert from 'node:assert/strict'
import { MapOperationsClient, MapOperationsPanel, validSetup } from '../web/js/map-operations.js'
const setup = { schemaVersion: 1, packageReady: false, packageState: 'invalid_package', snapshotReady: true,
  selectedGeneration: 'a'.repeat(64), parked: true, freeDiskBytes: 2147483648,
  maxTransferBytes: 8589934592, maxNewDiskBytes: 17179869184 }
assert.equal(validSetup(setup), true)
assert.equal(validSetup({ ...setup, packageReady: true }), false)
assert.equal(validSetup({ ...setup, snapshotReady: false }), false)
assert.equal(validSetup({ ...setup, freeDiskBytes: -1 }), false)
assert.match(MapOperationsPanel.template, /Saved map selection is retained/)
assert.match(MapOperationsPanel.template, /available storage/)
let calls = [], updates = [], resolveSetup
const client = new MapOperationsClient({ publish: state => updates.push(state),
  fetcher: (url, options) => {
    calls.push({ url, options })
    return new Promise(resolve => { resolveSetup = resolve })
  }, later: () => 1, cancelTimer: () => {} })
client.active = true
const loading = client.loadSetup()
resolveSetup({ ok: true, status: 200, json: async () => setup })
await loading
assert.equal(client.setup.selectedGeneration, setup.selectedGeneration)
assert.equal(client.setup.packageReady, false)
assert.equal(client.busy, false)
assert.deepEqual(calls.map(c => c.url), ['./api/maps/setup'])
assert.equal(calls[0].options.method, undefined)
assert.equal(client.catalog, null)
// A delayed setup JSON cannot resurrect data after authentication/navigation stop.
let resolveJSON
const late = client.loadSetup()
resolveSetup({ ok: true, status: 200, json: () => new Promise(resolve => { resolveJSON = resolve }) })
await Promise.resolve(); await Promise.resolve()
client.stop()
resolveJSON(setup)
await late
assert.equal(client.setup, null)
assert.equal(updates.at(-1).setup, null)
console.log('Map setup prerequisite, retained selection, read-only request and stale-response tests passed')
