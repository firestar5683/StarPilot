import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import { LongitudinalCurvesPage, savedCurve, curveGeometry } from "../web/js/longitudinal-curves.js"
import { SettingsFeed } from "../web/js/settings.js"

const rows = (first = 1) => [{ label: "Preset", value: "custom", choices: ["dom_default", "custom"], action: true, available: true },
  ...Array.from({ length: 10 }, (_, index) => ({ label: `${index * 10} mph point`, value: String(first + index * .05),
    unit: "m/s²", minimum: 0, maximum: 4, step: .05, available: true, action: true }))]
const points = savedCurve("standard/acceleration", rows())
assert.equal(points.length, 10)
assert.equal(points[0].speed, 0)
assert.equal(points[9].speed, 90)
assert.equal(points[0].index, 1)
assert.equal(curveGeometry(points).coords.length, 10)
assert.equal(savedCurve("standard/acceleration", rows().slice(0, -1)), null)
assert.equal(savedCurve("standard/acceleration", [{ label: "Preset", value: "dom_default" }]), null)
assert.equal(savedCurve("standard/acceleration", rows().map((row, index) => index === 3 ? { ...row, value: "NaN" } : row)), null)
assert.equal(savedCurve("standard/acceleration", rows().map((row, index) => index === 3 ? { ...row, label: "60 mph point" } : row)), null)
assert.equal(savedCurve("traffic/acceleration", rows()), null)

const calls = []
let saved = 1
const response = (body) => ({ ok: true, status: 200, json: async () => body })
const feed = new SettingsFeed({ publish: () => {}, fetcher: async (url, options) => {
  calls.push([url, options?.body && JSON.parse(options.body)])
  if (url.includes("/pages/")) return response({ page: "standard/acceleration", title: "Standard Acceleration", rows: rows(saved), view: "exact-view", parked: true })
  if (url.endsWith("/preview")) return response({ question: "Save 0 mph point?", intent: "one-use" })
  if (url.endsWith("/confirm")) { saved = 1.05; return response({ saved: true }) }
  throw new Error("unexpected request")
} })
await feed.start("standard/acceleration")
assert.equal(savedCurve(feed.data.page, feed.data.rows)[0].value, 1)
await feed.previewValue(1, 1.05)
assert.deepEqual(calls[1][1], { view: "exact-view", row: 1, value: 1.05 })
assert.equal(feed.pending, null)
assert.equal(calls.at(-2)[1].intent, "one-use")
assert.equal(calls.at(-1)[0], "./api/settings/pages/standard%2Facceleration")
assert.equal(savedCurve(feed.data.page, feed.data.rows)[0].value, 1.05)
feed.stop()

const page = { state: { profile: "standard", category: "acceleration" }, feed: { saving: false, load: (name) => calls.push(name) } }
Object.defineProperty(page, "page", { get: () => LongitudinalCurvesPage.computed.page.call(page) })
LongitudinalCurvesPage.methods.selectCategory.call(page, "following")
assert.equal(calls.at(-1), "standard/following")
LongitudinalCurvesPage.methods.selectProfile.call(page, "relaxed")
assert.equal(calls.at(-1), "relaxed/following")
LongitudinalCurvesPage.methods.selectProfile.call(page, "traffic")
assert.equal(calls.at(-1), "relaxed/following")

const app = readFileSync(new URL("../web/js/app.js", import.meta.url), "utf8")
const hub = readFileSync(new URL("../web/js/driving.js", import.meta.url), "utf8")
assert.match(app, /route\.path === '\/driving\/longitudinal-curves'/)
assert.match(hub, /go\('\/driving\/longitudinal-curves'\)/)
assert.match(LongitudinalCurvesPage.template, /state\.pending\.question/)
assert.match(LongitudinalCurvesPage.template, /feed\.confirm\(\)/)
