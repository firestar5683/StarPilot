import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { deleteRecords, storedSize } from '../web/js/record-deletion.js'

const empty = { schemaVersion: 1, reports: [], reportCount: 0, storageBytes: 0, more: false }
function fixture(replies = [empty]) {
  const states = [], requests = []
  const feed = { active: true, generation: 0, request: null, deleting: false,
    poller: { stop() {}, start() {} }, later: () => 1, cancel: () => {},
    publish: state => states.push(state), stop() { this.active = false; this.generation++; this.request?.abort() }, unauthorized() {},
    fetcher: async (url, options) => { requests.push({ url, options }); return { ok: true, status: 200, json: async () => replies.shift() } } }
  const accept = data => states.push(data)
  const valid = data => data?.schemaVersion === 1 && Array.isArray(data.reports)
  return { feed, requests, states, options: { accept, valid, subject: 'crash reports' } }
}
const cancel = fixture()
assert.equal(await deleteRecords(cancel.feed, '/delete', { all: true, confirmed: true }, { ...cancel.options, confirm: () => false }), false)
assert.equal(cancel.requests.length, 0)
const individual = fixture()
assert.equal(await deleteRecords(individual.feed, '/delete', { id: 'selected' }, individual.options), true)
assert.equal(individual.requests[0].options.method, 'POST')
assert.deepEqual(JSON.parse(individual.requests[0].options.body), { id: 'selected' })
assert.equal(individual.states.find(state => state.storageBytes === 0).reportCount, 0)
assert.equal(individual.states[0].preview, null)
assert.equal(individual.feed.deleting, false)
const batches = fixture([{ ...empty, more: true, storageBytes: 5 }, empty])
let message
assert.equal(await deleteRecords(batches.feed, '/delete', { all: true, confirmed: true }, {
  ...batches.options, confirm: value => { message = value; return true },
}), true)
assert.match(message, /Delete all crash reports.*cannot be undone/)
assert.equal(batches.requests.length, 2)
assert.deepEqual(batches.states.filter(state => state.storageBytes !== undefined).map(state => state.storageBytes), [5, 0])
const stale = fixture()
let reply
stale.feed.fetcher = () => new Promise(resolve => { reply = resolve })
const pending = deleteRecords(stale.feed, '/delete', { id: 'selected' }, stale.options)
stale.feed.stop()
reply({ ok: true, status: 200, json: async () => empty })
assert.equal(await pending, false)
assert.equal(stale.states.some(state => state.reports), false)
assert.equal(storedSize(7), '7 B')
assert.equal(storedSize(2048), '2.0 KB')
for (const file of ['sentry.js', 'logs.js']) {
  const source = readFileSync(new URL('../web/js/' + file, import.meta.url), 'utf8')
  assert.match(source, /Delete All/)
  assert.match(source, />Delete<\/button>/)
  assert.match(source, /storageBytes/)
  assert.match(source, /:disabled="(?:deleting|crashes.deleting)"/)
  assert.doesNotMatch(source, /v-html/)
}
console.log('record deletion confirmation, refresh, lifecycle and UI hooks passed')

const { SentryEventsFeed } = await import('../web/js/sentry.js')
const { CrashReportsFeed } = await import('../web/js/crash-reports.js')
for (const kind of ['sentry', 'crash']) {
  const eventId = 'a'.repeat(32)
  let inventory = kind === 'sentry'
    ? { schemaVersion: 1, source: 'local', scanIncomplete: false, capacity: 512, storageBytes: 10, storageIncomplete: false,
      events: [{ eventId, kind: 'warning', systemTimeMs: 1700000000000 }] }
    : { schemaVersion: 1, reports: [{ id: 'opaque-id', name: 'report', size: 10, modifiedAt: 1 }], reportCount: 1,
      storageBytes: 10, storageIncomplete: false, scanIncomplete: false, listLimited: false }
  const updates = [], calls = []
  const Feed = kind === 'sentry' ? SentryEventsFeed : CrashReportsFeed
  const feed = new Feed({ publish: update => updates.push(update), later: () => 1, cancel: () => {}, cancelTimer: () => {},
    fetcher: async (url, options) => {
      calls.push({ url, options })
      if (options.method === 'POST') inventory = { ...inventory, events: [], reports: [], reportCount: 0, storageBytes: 0, more: false }
      return { ok: true, status: 200, json: async () => inventory }
    } })
  await feed.start()
  assert.equal(await feed.remove(kind === 'sentry' ? eventId : 'opaque-id'), true)
  assert.equal(calls.at(-1).url, kind === 'sentry' ? './api/sentry/events/delete' : './api/crash-reports/delete')
  assert.equal(kind === 'sentry' ? feed.data.events.length : feed.reports.length, 0)
  assert.equal(kind === 'sentry' ? feed.data.storageBytes : updates.find(update => update.storageBytes === 0).storageBytes, 0)
  feed.stop()
  assert.equal(feed.deleting, false)
}
