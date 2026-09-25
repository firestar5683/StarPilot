import assert from "node:assert/strict"
import { DevicePicker } from "../web/js/device-picker.js"

const slug = "CurrentComma1234", other = "OtherComma123456"
const reply = (status, data) => ({ status, ok: status >= 200 && status < 300, json: async () => data })
const context = () => ({ ...DevicePicker.data(), devices: [{ slug, name: "Comma 1" }], editing: slug, draft: "Road comma" })
let calls = []
globalThis.fetch = async (url, options) => { calls.push([url, options]); return reply(200, { name: "Road comma" }) }
const current = context()
await DevicePicker.methods.save.call(current)
assert.equal(calls[0][0], `/${slug}/api/galaxy/device-name`)
assert.equal(calls[0][1].method, "POST")
assert.equal(calls[0][1].credentials, "same-origin")
assert.deepEqual(JSON.parse(calls[0][1].body), { name: "Road comma" })
assert.equal(current.devices[0].name, "Road comma")
assert.equal(current.editing, "")

calls = []
globalThis.fetch = async (url, options) => { calls.push([url, options]); return calls.length === 1 ? reply(404, {}) : reply(200, { name: "Old comma" }) }
const legacy = context()
await DevicePicker.methods.save.call(legacy)
assert.deepEqual(calls.map(([url]) => url), [`/${slug}/api/galaxy/device-name`, `/_gateway/devices/${slug}/name`])
assert.equal(legacy.devices[0].name, "Old comma")

for (const status of [401, 403, 409, 503]) {
  calls = []
  globalThis.fetch = async (url, options) => { calls.push([url, options]); return reply(status, { error: "Denied" }) }
  const denied = context()
  await DevicePicker.methods.save.call(denied)
  assert.equal(calls.length, 1)
  assert.equal(denied.error, "Denied")
  assert.equal(denied.devices[0].name, "Comma 1")
}

calls = []
globalThis.fetch = async (url, options) => {
  calls.push([url, options])
  if (url === "/_gateway/devices") return reply(200, { activeSlug: slug, devices: [{ slug, name: "Comma 1" }, { slug: other, name: "Legacy" }, { slug: "../bad" }] })
  return url.includes(slug) ? reply(200, { name: "Road comma" }) : reply(404, {})
}
const loaded = context()
await DevicePicker.methods.load.call(loaded)
assert.deepEqual(loaded.devices, [{ slug, name: "Road comma" }, { slug: other, name: "Legacy" }])
assert.equal(calls.length, 3)
assert.equal(loaded.loading, false)

let inFlight = 0, maximum = 0
const many = Array.from({ length: 9 }, (_, index) => ({ slug: `Device${String(index).padStart(10, "0")}`, name: "Comma" }))
globalThis.fetch = async (url) => {
  if (url === "/_gateway/devices") return reply(200, { devices: many })
  inFlight++
  maximum = Math.max(maximum, inFlight)
  await new Promise(resolve => setTimeout(resolve, 1))
  inFlight--
  return reply(200, { name: url.split("/")[1] })
}
const bounded = context()
await DevicePicker.methods.load.call(bounded)
assert.equal(maximum, 4)
assert.deepEqual(bounded.devices.map(device => device.name), many.map(device => device.slug))
