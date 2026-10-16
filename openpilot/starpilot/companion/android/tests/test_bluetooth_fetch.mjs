import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import vm from 'node:vm'
import test from 'node:test'

const source = readFileSync(new URL('../app/src/main/assets/bluetooth-fetch.js', import.meta.url), 'utf8')
function environment() {
  const sent = [], canceled = []
  const scope = { Request, Response, URL, Uint8Array, Map, Promise, Error, DOMException, atob, btoa,
    location: { href: 'https://galaxy-app.invalid/', origin: 'https://galaxy-app.invalid' },
    StarPilotBLE: { request: (id, raw) => sent.push([id, JSON.parse(raw)]), cancel: id => canceled.push(id) },
    fetch: async () => new Response('asset'),
  }
  scope.window = scope
  vm.runInNewContext(source, scope)
  return { scope, sent, canceled }
}
const turn = () => new Promise(resolve => setImmediate(resolve))
test('BLE forwards POST bytes once, preserves HTTP failure, and keeps assets local', async () => {
  const { scope, sent } = environment()
  const pending = scope.fetch('https://galaxy-app.invalid/api/settings/preview', {method: 'POST', body: '{"value":"é"}', headers: {'Content-Type': 'application/json'}})
  await turn()
  assert.equal(sent.length, 1)
  assert.equal(Buffer.from(sent[0][1].body, 'base64').toString(), '{"value":"é"}')
  scope.__galaxyBleReply(sent[0][0], {status: 409, headers: {'content-type': 'application/json'}, body: btoa('{"error":"Park first"}')})
  assert.equal((await pending).status, 409)
  assert.equal(await (await scope.fetch('https://galaxy-app.invalid/data/catalog.json')).text(), 'asset')
  assert.equal(sent.length, 1)
  await assert.rejects(scope.fetch('https://evil.test/api/settings/preview'), /External/)
})
test('cancellation does not replay mutations and late replies cannot resolve them', async () => {
  const { scope, sent, canceled } = environment()
  const controller = new AbortController()
  const pending = scope.fetch('https://galaxy-app.invalid/api/settings/confirm', {method: 'POST', body: '{}', signal: controller.signal})
  await turn()
  controller.abort()
  await assert.rejects(pending, /Check whether the change applied/)
  assert.deepEqual(canceled, [sent[0][0]])
  scope.__galaxyBleReply(sent[0][0], {status: 200, headers: {}, body: btoa('{}')})
  assert.equal(sent.length, 1)
})

test('BLE reads live restart identity and refuses replay before sending a request', async () => {
  const { scope, sent } = environment()
  const pending = scope.fetch('https://galaxy-app.invalid/data/runtime.json')
  await turn()
  assert.equal(sent[0][1].path, '/api/companion/runtime')
  scope.__galaxyBleReply(sent[0][0], {status: 200, headers: {}, body: btoa('{"schemaVersion":1,"monitor":"local","instance":"boot-2"}')})
  assert.equal((await (await pending).json()).instance, 'boot-2')
  for (const path of ['/api/replay/start', '/api/replay/media?sequence=1', '/api/recordings/local', '/api/cameras/snapshot',
    '/api/android-auto/upload', '/api/navigation/map/tiles/1/0/0.png', '/api/companion/app.apk', '/api/companion/uplink']) {
    const blocked = await scope.fetch('https://galaxy-app.invalid' + path)
    assert.equal(blocked.status, 501)
    const body = await blocked.json()
    assert.equal(body.code, 'bluetooth_unavailable')
    assert.match(body.error, /not available over Bluetooth.*Wi-Fi or LAN/)
  }
  assert.equal(sent.length, 1)
})
