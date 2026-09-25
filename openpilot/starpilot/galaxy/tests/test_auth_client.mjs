import assert from "node:assert/strict"
import { LocalAuth } from "../web/js/auth-client.js"
import { MonitorFeed } from "../web/js/monitor-feed.js"
import { readFileSync } from "node:fs"

const states = [], calls = []
const responses = [
  { ok: true, body: { state: "configured", authenticated: false } },
  { ok: false, status: 401 },
  { ok: true, body: { authenticated: true } },
  { ok: true, body: { authenticated: false } },
]
const auth = new LocalAuth({ publish: (state) => states.push(state), fetcher: async (url, options) => {
  calls.push({ url, options })
  const response = responses.shift()
  return { ok: response.ok, status: response.status ?? 200, json: async () => response.body }
} })
await auth.check()
assert.equal(states.at(-1).status, "login")
assert.equal(await auth.login("wrongpass"), false)
assert.equal(states.at(-1).error, "Sign in failed.")
assert.equal(await auth.login("correctpass"), true)
assert.equal(states.at(-1).status, "authenticated")
assert.equal(calls[2].options.credentials, "same-origin")
assert.equal(calls[2].options.headers["Content-Type"], "application/json")
assert.equal(await auth.logout(), true)
assert.equal(states.at(-1).status, "login")
assert.equal(calls[3].options.body, "{}")

const setup = new LocalAuth({ publish: (state) => states.push(state), fetcher: async () =>
  ({ ok: true, json: async () => ({ state: "setup_required", authenticated: false }) }) })
await setup.check()
assert.equal(states.at(-1).status, "setup_required")
const unavailable = new LocalAuth({ publish: (state) => states.push(state), fetcher: async () =>
  ({ ok: true, json: async () => ({ state: "unavailable", authenticated: false }) }) })
await unavailable.check()
assert.equal(states.at(-1).status, "unavailable")

let unauthorized = 0
const samples = []
const feed = new MonitorFeed({ mode: "local", publish: (state) => samples.push(state), unauthorized: () => unauthorized++,
  fetcher: async () => ({ ok: false, status: 401 }) })
feed.start()
for (let i = 0; i < 5; i++) await Promise.resolve()
assert.equal(unauthorized, 1)
assert.equal(samples.at(-1).snapshot, null)
assert.equal(feed.stopped, true)
assert.equal(feed.timer, null)

const accessLostStates = []
let accessLost = 0
const accessLostFeed = new MonitorFeed({ mode: "local", publish: (state) => accessLostStates.push(state),
  unauthorized: () => accessLost++, fetcher: async () => ({ ok: false, status: 503, json: async () => ({ code: "setup_required" }) }) })
accessLostFeed.start()
for (let i = 0; i < 5; i++) await Promise.resolve()
assert.equal(accessLost, 1)
assert.equal(accessLostStates.at(-1).snapshot, null)
assert.equal(accessLostFeed.stopped, true)

const lostLogoutStates = []
const lostLogout = new LocalAuth({ publish: (state) => lostLogoutStates.push(state), fetcher: async () => ({ ok: false, status: 401 }) })
assert.equal(await lostLogout.logout(), false)
assert.equal(lostLogoutStates.at(-1).status, "login")

const previewCalls = []
const preview = new MonitorFeed({ mode: "sample", publish: () => {}, fetcher: async (url) => {
  previewCalls.push(url)
  return { ok: false, status: 404 }
} })
preview.start()
for (let i = 0; i < 5; i++) await Promise.resolve()
assert.deepEqual(previewCalls, ["./data/system-monitor.sample.json"])
preview.stop()

const deferred = () => { let resolve; const promise = new Promise((done) => { resolve = done }); return { promise, resolve } }
const flush = async () => { for (let i = 0; i < 10; i++) await Promise.resolve() }

// A slow session check may not replace a completed sign-in.
const oldCheck = deferred(), raceStates = []
const race = new LocalAuth({ publish: (state) => raceStates.push(state), fetcher: (url) =>
  url.endsWith("session") ? oldCheck.promise : Promise.resolve({ ok: true, json: async () => ({ authenticated: true }) }) })
const checking = race.check()
assert.equal(await race.login("password123"), true)
oldCheck.resolve({ ok: true, json: async () => ({ state: "configured", authenticated: false }) })
await checking
assert.equal(raceStates.at(-1).status, "authenticated")

// Two successful sign-ins execute in order and only the latest publishes state.
const first = deferred(), second = deferred(), signStates = []
let loginNumber = 0
const sign = new LocalAuth({ publish: (state) => signStates.push(state), fetcher: (url) => {
  if (url.endsWith("login")) return ++loginNumber === 1 ? first.promise : second.promise
  return Promise.resolve({ ok: true })
} })
const firstLogin = sign.login("first-password")
const secondLogin = sign.login("second-password")
await flush()
assert.equal(loginNumber, 1)
first.resolve({ ok: true })
assert.equal(await firstLogin, false)
await flush()
assert.equal(loginNumber, 2)
second.resolve({ ok: true })
assert.equal(await secondLogin, true)
assert.equal(signStates.at(-1).status, "authenticated")

const waitingLogin = deferred(), waitingLogout = deferred(), logoutStates = [], logoutCalls = []
const serialized = new LocalAuth({ publish: (state) => logoutStates.push(state), fetcher: (url) => {
  logoutCalls.push(url)
  return url.endsWith("login") ? waitingLogin.promise : waitingLogout.promise
} })
const pendingSignIn = serialized.login("password123")
const pendingSignOut = serialized.logout()
await flush()
assert.deepEqual(logoutCalls, ["./api/auth/login"])
waitingLogin.resolve({ ok: true })
await pendingSignIn
await flush()
assert.deepEqual(logoutCalls, ["./api/auth/login", "./api/auth/logout"])
waitingLogout.resolve({ ok: true })
assert.equal(await pendingSignOut, true)
assert.equal(logoutStates.at(-1).status, "login")

// A login requested while logout waits must run after logout's cookie mutation.
const queuedLogin1 = deferred(), queuedLogout = deferred(), queuedLogin2 = deferred()
const orderedCalls = [], orderedStates = []
let orderedLoginNumber = 0
const ordered = new LocalAuth({ publish: (state) => orderedStates.push(state), fetcher: (url) => {
  orderedCalls.push(url)
  if (url.endsWith("login")) return ++orderedLoginNumber === 1 ? queuedLogin1.promise : queuedLogin2.promise
  return queuedLogout.promise
} })
const orderedFirst = ordered.login("first-password")
const orderedSignOut = ordered.logout()
const orderedSecond = ordered.login("second-password")
await flush()
assert.deepEqual(orderedCalls, ["./api/auth/login"])
queuedLogin1.resolve({ ok: true })
assert.equal(await orderedFirst, false)
await flush()
assert.deepEqual(orderedCalls, ["./api/auth/login", "./api/auth/logout"])
queuedLogout.resolve({ ok: true })
assert.equal(await orderedSignOut, false)
await flush()
assert.deepEqual(orderedCalls, ["./api/auth/login", "./api/auth/logout", "./api/auth/login"])
queuedLogin2.resolve({ ok: true })
assert.equal(await orderedSecond, true)
assert.deepEqual(orderedStates, [{ status: "authenticated", error: "", localAccess: false }])

const localStates = [], localCalls = []
let localSession = { state: "configured", authenticated: true, localAccess: true }
const local = new LocalAuth({ publish: (state) => localStates.push(state), fetcher: async (url) => {
  localCalls.push(url)
  return { ok: true, json: async () => localSession }
} })
await local.check()
assert.deepEqual(localStates.at(-1), { status: "authenticated", error: "", localAccess: true })
assert.equal(await local.login("unused"), false)
assert.equal(await local.logout(), false)
assert.deepEqual(localCalls, ["./api/auth/session"])
assert.equal(localStates.at(-1).status, "authenticated")
local.expired()
assert.deepEqual(localStates.at(-1), { status: "checking", error: "", localAccess: false })
await local.check()
assert.equal(localStates.at(-1).localAccess, true)
assert.equal(localStates.at(-1).status, "authenticated")
localSession = { state: "configured", authenticated: false, localAccess: false }
await local.check()
assert.deepEqual(localStates.at(-1), { status: "login", error: "", localAccess: false })
localSession = { state: "configured", authenticated: false, localAccess: true }
await local.check()
assert.equal(localStates.at(-1).status, "login")
assert.equal(localStates.at(-1).localAccess, false)
localSession = { state: "configured", authenticated: true, localAccess: "true" }
await local.check()
assert.equal(localStates.at(-1).localAccess, false)

const app = readFileSync(new URL("../web/js/app.js", import.meta.url), "utf8")
assert.match(app, /authState\.status === 'authenticated' && !authState\.localAccess/)
assert.match(app, /state\.monitorMode === 'local' && authState\.status !== 'authenticated'/)
assert.match(app, /sessionExpired\(\) \{ auth\.expired\(\); auth\.check\(\) \}/)

const oldMonitor = deferred(), nextMonitor = deferred(), lateStates = []
let lateUnauthorized = 0, monitorRequests = 0
const lateFeed = new MonitorFeed({ mode: "local", publish: (state) => lateStates.push(state),
  unauthorized: () => lateUnauthorized++, fetcher: () => ++monitorRequests === 1 ? oldMonitor.promise : nextMonitor.promise })
lateFeed.start()
lateFeed.stop()
lateFeed.start()
oldMonitor.resolve({ ok: false, status: 401 })
await flush()
assert.equal(lateUnauthorized, 0)
assert.equal(lateFeed.stopped, false)
assert.equal(lateStates.length, 0)
lateFeed.stop()
console.log("Galaxy browser auth, expiry and static-preview isolation checks passed")

const gatewayStates = [], gatewayCalls = []
let gatewayAuthenticated = true
const gateway = new LocalAuth({ publish: value => gatewayStates.push(value), fetcher: async (path) => {
  gatewayCalls.push(path)
  return { ok: true, json: async () => ({ state: "configured", authenticated: gatewayAuthenticated, gatewayAccess: true }) }
} })
await gateway.check()
assert.equal(gatewayStates.at(-1).status, "authenticated")
assert.equal(gatewayStates.at(-1).gatewayAccess, true)
assert.equal(await gateway.login("never-submit-to-device"), false)
assert.equal(await gateway.logout(), false)
assert.deepEqual(gatewayCalls, ["./api/auth/session"])
gatewayAuthenticated = false
await gateway.check()
assert.equal(gatewayStates.at(-1).status, "gateway_login")
