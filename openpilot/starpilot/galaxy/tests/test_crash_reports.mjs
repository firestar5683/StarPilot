import assert from "node:assert/strict"
import { CrashReportsFeed } from "../web/js/crash-reports.js"

const flush = async () => { for (let i = 0; i < 8; i++) await Promise.resolve() }
function fixture() {
  const requests = [], states = []
  let unauthorized = 0
  const feed = new CrashReportsFeed({ publish: (state) => states.push(state), unauthorized: () => { unauthorized++ },
    fetcher: (url, options) => new Promise((resolve) => requests.push({ url, signal: options.signal, resolve })) })
  const reply = async (index, body, status = 200) => {
    requests[index].resolve({ ok: status === 200, status, json: async () => body })
    await flush()
  }
  return { feed, requests, states, reply, get unauthorized() { return unauthorized } }
}

const listing = { schemaVersion: 1, scanIncomplete: true, listLimited: false, reports: [
  { id: "first", name: "report-one", size: 10, modifiedAt: 100 },
  { id: "second", name: "report-two", size: 20, modifiedAt: 90 },
] }

const normal = fixture()
normal.feed.start()
assert.equal(normal.requests[0].url, "./api/crash-reports")
await normal.reply(0, listing)
assert.equal(normal.states.at(-1).scanIncomplete, true)
normal.feed.open(listing.reports[0])
assert.equal(normal.requests[1].url, "./api/crash-reports/first")
normal.feed.open(listing.reports[1])
assert.equal(normal.requests[1].signal.aborted, true)
await normal.reply(2, { schemaVersion: 1, name: "report-two", text: "current", truncated: false })
assert.equal(normal.states.at(-1).preview.text, "current")
const count = normal.states.length
await normal.reply(1, { schemaVersion: 1, name: "report-one", text: "stale", truncated: false })
assert.equal(normal.states.length, count)
normal.feed.stop()
assert.equal(normal.states.at(-1).preview, null)
assert.deepEqual(normal.states.at(-1).reports, [])

const exited = fixture()
exited.feed.start()
exited.feed.stop()
await exited.reply(0, listing)
assert.deepEqual(exited.states.at(-1).reports, [])

const revoked = fixture()
revoked.feed.start()
await revoked.reply(0, { error: "Sign in" }, 401)
assert.equal(revoked.unauthorized, 1)
assert.deepEqual(revoked.states.at(-1).reports, [])

const failure = fixture()
failure.feed.start()
await failure.reply(0, listing)
failure.feed.open(listing.reports[0])
await failure.reply(1, { error: "Report changed" }, 409)
assert.equal(failure.states.at(-1).preview, null)
assert.equal(failure.states.at(-1).selected, null)
assert.equal(failure.states.at(-1).previewStatus, "unavailable")
failure.feed.open(listing.reports[0])
await failure.reply(2, { schemaVersion: 1, name: "report-one", text: "sample", truncated: true })
assert.equal(failure.states.at(-1).preview.truncated, true)
failure.feed.stop()

console.log("Crash report client lifecycle checks passed")
