import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import { webcrypto } from 'node:crypto'
import vm from 'node:vm'

const source = await readFile(new URL('../android/app/src/main/assets/native-bridge.js', import.meta.url), 'utf8')
const origin = 'https://appassets.androidplatform.net'
function page({ frame = false, remote = false, reply = true } = {}) {
  const sent = [], original = []
  const native = { postMessage(text) {
    const value = JSON.parse(text); sent.push(value)
    if (!value.cancel && reply) queueMicrotask(() => native.onmessage({ data: JSON.stringify({ id: value.id, ok: true,
      response: { status: value.method === 'HEAD' ? 204 : 200, headers: { 'content-type': 'application/json' },
        body: btoa(JSON.stringify({ received: value.path })) } }) }))
  } }
  const window = { GalaxyNative: native, fetch: async request => { original.push(request.url); return new Response('static') } }
  window.top = frame ? {} : window
  const context = { window, GalaxyNative: native, location: { origin: remote ? 'https://evil.example' : origin, href: origin + '/assets/mobile/index.html' },
    Request, Response, URL, DOMException, Uint8Array, btoa, atob, crypto: webcrypto, setTimeout, clearTimeout }
  vm.runInNewContext(source, context)
  return { window, native, sent, original }
}
const p = page()
const result = await p.window.fetch('/api/params/all?galaxy_ble_settings=1')
assert.deepEqual(await result.json(), { received: '/api/params/all?galaxy_ble_settings=1' })
assert.equal(p.sent[0].method, 'GET')
assert.equal(p.sent[0].body, '')
const body = JSON.stringify({ key: 'Metric', value: true, label: 'Galaxy ✨' })
await p.window.fetch('/api/params', { method: 'PUT', headers: { 'content-type': 'application/json' }, body })
assert.equal(Buffer.from(p.sent[1].body, 'base64').toString(), body)
assert.equal(p.sent[1].headers['content-type'], 'application/json')
await p.window.fetch('/assets/mobile/js/app.js')
assert.equal(p.sent.length, 2)
assert.equal(p.original.length, 1)
await p.window.fetch('https://outside.example/api/x')
assert.equal(p.sent.length, 2)
assert.equal(p.original.length, 2)
const head = await p.window.fetch('/api/params', { method: 'HEAD' })
assert.equal(await head.text(), '')
await assert.rejects(p.window.fetch('/api/params', { method: 'PUT', body: 'x'.repeat(1048577) }), /1 MiB/)
assert.equal(p.sent.filter(v => v.method === 'PUT').length, 1)
const controller = new AbortController(), quiet = page({ reply: false })
const aborted = quiet.window.fetch('/api/device/status', { signal: controller.signal })
while (quiet.sent.length === 0) await new Promise(resolve => setImmediate(resolve))
controller.abort()
await assert.rejects(aborted, error => error.name === 'AbortError')
assert.equal(quiet.sent.length, 2)
assert.equal(quiet.sent[1].cancel, true)
assert.equal(quiet.sent[0].id, quiet.sent[1].id)
for (const options of [{ frame: true }, { remote: true }]) {
  const other = page(options)
  await other.window.fetch('/api/params')
  assert.equal(other.sent.length, 0)
}
console.log('Android production fetch shim: fresh settings reads, UTF-8 writes, static/external routing, HEAD, upload bounds, abort without retry, frame/origin gating passed')
