import assert from "node:assert/strict"
import { SoftwareStatusFeed, SoftwarePage, validSoftwareSnapshot } from "../web/js/software-status.js"

const flush = async () => { for (let i = 0; i < 12; i++) await Promise.resolve() }
const installed = { version: "fixture", branch: "Dom", commit: "a".repeat(40) }
const updater = { state: "idle", targetBranch: "Dom", lastSuccessAt: "2026-09-20T12:30:00Z", lastFetchAt: null,
  targetChangeFound: true, finalizedUpdateReady: false, failedCount: 0 }
const operations = { parked: true, availableBranches: ["Dom", "beta"], selectedTarget: "Dom",
  canCheck: true, canDownload: true, canSelect: true, canInstall: false, reason: null, request: null }
const snapshot = (changes = {}) => ({ schemaVersion: 1, installed, updater, operations, ...changes })
const request = (action, state = "pending", target = null, error = null) => ({ id: "one", action, target, state, error })
const response = (body, status = 200) => ({ ok: status >= 200 && status < 300, status, json: async () => body })

function fixture() {
  const requests = [], states = [], timers = new Map()
  let nextTimer = 0, unauthorized = 0
  const feed = new SoftwareStatusFeed({ publish: (state) => states.push(state), unauthorized: () => { unauthorized++ },
    later: (fn, ms) => { const id = ++nextTimer; timers.set(id, { fn, ms }); return id },
    cancelTimer: (id) => timers.delete(id),
    fetcher: (url, options) => new Promise((resolve, reject) => requests.push({ url, options, resolve, reject })) })
  async function reply(index, body, status = 200) { requests[index].resolve(response(body, status)); await flush() }
  async function fail(index) { requests[index].reject(new Error("Connection lost")); await flush() }
  function fire(ms) {
    const entry = [...timers.entries()].find(([, timer]) => timer.ms === ms)
    assert.ok(entry, `missing ${ms} ms timer`)
    timers.delete(entry[0]); entry[1].fn()
  }
  return { feed, requests, states, timers, reply, fail, fire, get unauthorized() { return unauthorized } }
}

assert.ok(validSoftwareSnapshot(snapshot()))
assert.ok(validSoftwareSnapshot(snapshot({ installed: { ...installed, displayVersion: "StarPilot 0.11.2" } })))
assert.equal(validSoftwareSnapshot(snapshot({ installed: { ...installed, displayVersion: 12 } })), false)
assert.ok(validSoftwareSnapshot({ schemaVersion: 1, installed, updater })) // Home can consume status-only responses.
assert.equal(validSoftwareSnapshot(snapshot({ operations: { ...operations, canInstall: "yes" } })), false)
assert.equal(validSoftwareSnapshot(snapshot({ operations: { ...operations, availableBranches: [42] } })), false)
assert.ok(validSoftwareSnapshot(snapshot({ operations: { ...operations, availableBranches: ["x".repeat(128)] } })))
assert.equal(validSoftwareSnapshot(snapshot({ operations: { ...operations, availableBranches: ["x".repeat(129)] } })), false)
assert.ok(validSoftwareSnapshot(snapshot({ operations: { ...operations,
  availableBranches: Array.from({ length: 76 }, (_, index) => `published-${index}`) } })))
assert.equal(validSoftwareSnapshot(snapshot({ operations: { ...operations,
  availableBranches: Array.from({ length: 257 }, (_, index) => `published-${index}`) } })), false)

const statusOnly = fixture()
statusOnly.feed.start()
await statusOnly.reply(0, { schemaVersion: 1, installed, updater })
assert.equal(statusOnly.states.at(-1).status, "ready")
assert.equal(statusOnly.states.at(-1).data.updater.finalizedUpdateReady, false)
assert.equal(statusOnly.states.at(-1).data.operations.canCheck, false)
statusOnly.feed.action("check")
assert.equal(statusOnly.requests.length, 1)
statusOnly.feed.stop()

const unavailable = fixture()
unavailable.feed.start()
assert.equal(unavailable.states.at(-1).status, "loading")
await unavailable.reply(0, { error: "Updater status is unavailable" }, 503)
assert.equal(unavailable.states.at(-1).status, "unavailable")
assert.match(unavailable.states.at(-1).error, /Updater status is unavailable/)
unavailable.fire(2000)
assert.equal(unavailable.states.at(-1).status, "unavailable")
assert.match(unavailable.states.at(-1).error, /Updater status is unavailable/)
await unavailable.reply(1, snapshot())
assert.equal(unavailable.states.at(-1).status, "ready")
assert.equal(unavailable.states.at(-1).error, "")
unavailable.feed.stop()

const normal = fixture()
normal.feed.start()
assert.equal(normal.requests[0].url, "./api/software/status")
assert.equal(normal.requests[0].options.credentials, "same-origin")
await normal.reply(0, snapshot())
assert.equal(normal.states.at(-1).busy, false)
assert.deepEqual([...normal.timers.values()].map((timer) => timer.ms), [5000])
normal.feed.load()
assert.equal(normal.states.at(-1).status, "ready")
assert.deepEqual(normal.states.at(-1).data.installed, installed) // Refresh keeps the visible build.
assert.equal(normal.states.at(-1).busy, false) // Background reads do not dim the controls.
await normal.reply(1, snapshot({ updater: { ...updater, targetChangeFound: false } }))
assert.equal(normal.states.at(-1).data.updater.targetChangeFound, false)
normal.feed.stop()
assert.equal(normal.timers.size, 0)

const interruptPoll = fixture()
interruptPoll.feed.start()
await interruptPoll.reply(0, snapshot())
interruptPoll.fire(5000)
assert.equal(interruptPoll.states.at(-1).busy, false)
interruptPoll.feed.action("check")
assert.equal(interruptPoll.requests.length, 3)
assert.equal(interruptPoll.requests[1].options.signal.aborted, true)
assert.deepEqual(JSON.parse(interruptPoll.requests[2].options.body), { action: "check" })
assert.equal(interruptPoll.states.at(-1).busy, true)
interruptPoll.feed.action("check")
interruptPoll.feed.load()
assert.equal(interruptPoll.requests.length, 3)
await interruptPoll.reply(2, snapshot({ operations: { ...operations, request: request("check") } }))
await interruptPoll.reply(1, snapshot({ operations: { ...operations, parked: false } }))
assert.equal(interruptPoll.states.at(-1).data.operations.parked, true)
assert.equal(interruptPoll.states.at(-1).data.operations.request.state, "pending")
interruptPoll.feed.stop()

const branch = fixture()
branch.feed.start()
await branch.reply(0, snapshot())
branch.feed.action("select", "unknown")
assert.equal(branch.requests.length, 1)
branch.feed.action("select", "beta")
assert.equal(branch.requests[1].url, "./api/software/action")
assert.deepEqual(JSON.parse(branch.requests[1].options.body), { action: "select", branch: "beta" })
branch.feed.action("check")
assert.equal(branch.requests.length, 2) // In-flight mutation is never duplicated.
await branch.reply(1, snapshot({ operations: { ...operations, selectedTarget: "beta", request: request("select", "complete", "beta") } }))
assert.equal(branch.states.at(-1).busy, false)
assert.equal(branch.requests.length, 2) // Staging does not start a check or download.
branch.feed.action("download", "Dom")
assert.equal(branch.requests.length, 2)
branch.feed.action("check")
assert.deepEqual(JSON.parse(branch.requests[2].options.body), { action: "check" })
await branch.reply(2, snapshot({ operations: { ...operations, selectedTarget: "beta", request: request("check", "pending", "beta") } }))
assert.equal(branch.timers.size, 1)
branch.fire(1000)
assert.equal(branch.requests[3].url, "./api/software/status")
await branch.reply(3, snapshot({ operations: { ...operations, selectedTarget: "beta", request: request("check", "complete", "beta") } }))
assert.deepEqual([...branch.timers.values()].map((timer) => timer.ms), [5000])
branch.feed.action("download", "beta")
assert.deepEqual(JSON.parse(branch.requests[4].options.body), { action: "download", branch: "beta" })
await branch.reply(4, snapshot({ operations: { ...operations, selectedTarget: "beta", request: request("download", "failed", "beta", "Download failed") } }))
assert.equal(branch.states.at(-1).data.operations.request.error, "Download failed")
assert.equal(branch.states.at(-1).busy, false)
branch.feed.stop()

const parked = fixture()
parked.feed.start()
await parked.reply(0, snapshot({ operations: { ...operations, parked: false, canCheck: false, canDownload: false, canSelect: false } }))
parked.feed.action("check")
assert.equal(parked.requests.length, 1)
parked.fire(1000)
assert.equal(parked.states.at(-1).status, "ready")
await parked.reply(1, snapshot())
assert.equal(parked.states.at(-1).data.operations.parked, true)
assert.deepEqual([...parked.timers.values()].map((timer) => timer.ms), [5000])
parked.feed.stop()

const lateUpdater = fixture()
lateUpdater.feed.start()
await lateUpdater.reply(0, snapshot({ operations: { ...operations, canCheck: false, canDownload: false,
  canSelect: false, reason: "Updater is not running" } }))
assert.deepEqual([...lateUpdater.timers.values()].map((timer) => timer.ms), [5000])
lateUpdater.fire(5000)
assert.equal(lateUpdater.requests[1].url, "./api/software/status")
assert.equal(lateUpdater.states.at(-1).data.operations.canCheck, false) // Keep the visible status during refresh.
await lateUpdater.reply(1, snapshot())
assert.equal(lateUpdater.states.at(-1).data.operations.canCheck, true)
assert.deepEqual([...lateUpdater.timers.values()].map((timer) => timer.ms), [5000])
lateUpdater.feed.stop()
assert.equal(lateUpdater.timers.size, 0)

const uncertain = fixture()
uncertain.feed.start()
await uncertain.reply(0, snapshot({ operations: { ...operations, request: { ...request("check", "complete", "Dom"), id: "old" } } }))
uncertain.feed.action("check")
await uncertain.fail(1)
assert.equal(uncertain.states.at(-1).uncertain, true)
assert.equal(uncertain.states.at(-1).data.installed.commit, installed.commit)
uncertain.feed.action("check")
assert.equal(uncertain.requests.length, 2)
uncertain.fire(2000)
await uncertain.reply(2, snapshot({ operations: { ...operations, request: { ...request("check", "complete", "Dom"), id: "old" } } }))
assert.equal(uncertain.states.at(-1).uncertain, true) // A retained older request does not resolve the new one.
uncertain.feed.action("check")
assert.equal(uncertain.requests.length, 3)
uncertain.fire(1000)
await uncertain.reply(3, snapshot({ operations: { ...operations, request: request("check", "pending", "Dom") } }))
assert.equal(uncertain.states.at(-1).uncertain, false)
assert.equal(uncertain.timers.size, 1)
uncertain.feed.stop()
assert.equal(uncertain.timers.size, 0)

const serverError = fixture()
serverError.feed.start()
await serverError.reply(0, snapshot())
serverError.feed.action("check")
await serverError.reply(1, { error: "Status unavailable after signal" }, 503)
assert.equal(serverError.states.at(-1).uncertain, true) // A server error does not prove the POST had no effect.
assert.equal(serverError.states.at(-1).busy, false)
serverError.feed.action("check")
assert.equal(serverError.requests.length, 2)
serverError.feed.stop()

const uncertainSelect = fixture()
uncertainSelect.feed.start()
await uncertainSelect.reply(0, snapshot())
uncertainSelect.feed.action("select", "beta")
await uncertainSelect.fail(1)
assert.equal(uncertainSelect.states.at(-1).uncertain, true)
uncertainSelect.fire(2000)
await uncertainSelect.reply(2, snapshot({ operations: { ...operations, selectedTarget: "beta" } }))
assert.equal(uncertainSelect.states.at(-1).uncertain, false) // Select stages target without a request record.
uncertainSelect.feed.stop()

const install = fixture()
install.feed.start()
await install.reply(0, snapshot({ operations: { ...operations, canInstall: true } }))
install.feed.action("install", "Dom")
assert.deepEqual(JSON.parse(install.requests[1].options.body), { action: "install", branch: "Dom" })
await install.reply(1, snapshot({ operations: { ...operations, canInstall: false, request: request("install", "pending", "Dom") } }))
assert.match(install.states.at(-1).notice, /Waiting to reconnect/)
install.fire(1000)
await install.fail(2)
assert.equal(install.states.at(-1).data.installed.commit, installed.commit)
assert.equal(install.timers.size, 1)
install.fire(2000)
await install.reply(3, snapshot({ installed: { ...installed, commit: "b".repeat(40) },
  operations: { ...operations, canInstall: false } }))
assert.match(install.states.at(-1).notice, /verified after reconnect/)
assert.deepEqual([...install.timers.values()].map((timer) => timer.ms), [5000])
install.feed.stop()

const branchSwitch = fixture()
branchSwitch.feed.start()
await branchSwitch.reply(0, snapshot({ operations: { ...operations, selectedTarget: "beta", canInstall: true } }))
branchSwitch.feed.action("install", "beta")
await branchSwitch.reply(1, snapshot({ operations: { ...operations, selectedTarget: "beta", canInstall: false,
  request: request("install", "pending", "beta") } }))
branchSwitch.fire(1000)
await branchSwitch.reply(2, snapshot({ installed: { ...installed, branch: "beta" },
  operations: { ...operations, selectedTarget: "beta", canInstall: false } }))
assert.match(branchSwitch.states.at(-1).notice, /verified after reconnect/)
assert.equal(branchSwitch.states.at(-1).busy, false)
branchSwitch.feed.stop()

const revoked = fixture()
revoked.feed.start()
await revoked.reply(0, { error: "Sign in" }, 401)
assert.equal(revoked.unauthorized, 1)
assert.equal(revoked.states.at(-1).status, "idle")

const page = (selectedTarget = "Dom", availableBranches = ["StarPilot", "Dom", "beta"], installedBranch = "Dom") => {
  const state = { operations: { ...operations, selectedTarget, availableBranches }, data: {
    installed: { ...installed, branch: installedBranch } }, actionDisabled: false,
    primaryChoice: "", draftBranch: "", draftTouched: false, dialog: null }
  Object.defineProperty(state, "otherBranches", { get: () => SoftwarePage.computed.otherBranches.call(state) })
  Object.defineProperty(state, "canStageBranch", { get: () => SoftwarePage.computed.canStageBranch.call(state) })
  return state
}
const staged = page()
SoftwarePage.methods.syncDraftBranch.call(staged, "Dom")
assert.equal(staged.primaryChoice, "Dom")
assert.equal(SoftwarePage.computed.primaryBranchHelp.call(staged), "Latest features and fixes under development. Updates regularly and may introduce bugs.")
staged.primaryChoice = "other:"
SoftwarePage.methods.onPrimaryBranchChange.call(staged)
assert.equal(staged.draftBranch, "") // Other is navigation, never a draft target.
assert.equal(staged.canStageBranch, false)
staged.draftBranch = "beta"
SoftwarePage.methods.onOtherBranchChange.call(staged)
assert.equal(staged.primaryChoice, "other:")
assert.equal(staged.canStageBranch, true)
SoftwarePage.methods.chooseBranch.call(staged)
assert.equal(staged.dialog.action, "select")
assert.equal(staged.dialog.branch, "beta")
assert.match(staged.dialog.message, /only stages the choice/i)
staged.dialog = null
staged.draftBranch = "other:"
assert.equal(staged.canStageBranch, false)
SoftwarePage.methods.chooseBranch.call(staged)
assert.equal(staged.dialog, null)

const alternateTarget = page("legacy", ["StarPilot", "Dom", "beta"], "installed-only")
SoftwarePage.methods.syncDraftBranch.call(alternateTarget, alternateTarget.operations.selectedTarget)
assert.equal(alternateTarget.primaryChoice, "other:")
assert.equal(alternateTarget.draftBranch, "legacy")
assert.deepEqual(alternateTarget.otherBranches.map(({ name, listed, current }) => ({ name, listed, current })), [
  { name: "legacy", listed: false, current: false },
  { name: "installed-only", listed: false, current: true },
  { name: "beta", listed: true, current: false },
])
assert.equal(alternateTarget.canStageBranch, false) // A missing target remains visible but cannot be staged.
alternateTarget.draftBranch = "beta"
assert.equal(alternateTarget.canStageBranch, true)
const unavailablePrimary = page("Dom", ["Dom"])
unavailablePrimary.primaryChoice = "StarPilot"
SoftwarePage.methods.onPrimaryBranchChange.call(unavailablePrimary)
assert.equal(unavailablePrimary.canStageBranch, false)

const sentinel = fixture()
sentinel.feed.start()
await sentinel.reply(0, snapshot({ operations: { ...operations, availableBranches: ["Dom", "other:"] } }))
sentinel.feed.action("select", "other:")
assert.equal(sentinel.requests.length, 1)
assert.deepEqual(page("Dom", ["Dom", "other:"]).otherBranches, [])
sentinel.feed.stop()

assert.match(SoftwarePage.template, /StarPilot — Release/)
assert.match(SoftwarePage.template, /Dom — Development/)
assert.match(SoftwarePage.template, /Other branches…/)
assert.match(SoftwarePage.template, /Additional branches from this installation's repository/)
assert.match(SoftwarePage.template, /Check for updates/)
assert.match(SoftwarePage.template, /Download update/)
assert.match(SoftwarePage.template, /Restart &amp; install/)
assert.match(SoftwarePage.template, /displayVersion \?\? data\.installed\.version/)
assert.doesNotMatch(SoftwarePage.template, /Rollback|historical version|status only/i)

const preferences = fixture()
preferences.feed.start()
await preferences.reply(0, snapshot({ operations: { ...operations, automaticDownloads: true, canConfigure: true } }))
preferences.feed.configureAutomaticDownloads(false)
assert.deepEqual(JSON.parse(preferences.requests[1].options.body), {
  action: 'preferences', automaticDownloads: false, expectedAutomaticDownloads: true,
})
await preferences.fail(1)
assert.equal(preferences.states.at(-1).uncertain, true)
preferences.feed.configureAutomaticDownloads(true)
assert.equal(preferences.requests.length, 2)
preferences.fire(2000)
await preferences.reply(2, snapshot({ operations: { ...operations, automaticDownloads: false, canConfigure: true } }))
assert.equal(preferences.states.at(-1).uncertain, false)
assert.equal(preferences.states.at(-1).data.operations.automaticDownloads, false)
preferences.feed.stop()

const history = { installed: [{ hash: 'a'.repeat(40), date: '2026-09-29T12:30:00Z', subject: '<script>plain text</script>' }],
  downloaded: [], currentReleaseNotes: '<script>also plain text</script>', downloadedReleaseNotes: null }
assert(validSoftwareSnapshot(snapshot({ operations: { ...operations, automaticDownloads: true, canConfigure: true, history } })))
assert(!validSoftwareSnapshot(snapshot({ operations: { ...operations, history: { ...history, installed: [{ hash: '--help' }] } } })))
assert(!validSoftwareSnapshot(snapshot({ operations: { ...operations, automaticDownloads: 'true' } })))
assert.doesNotMatch(SoftwarePage.template, /v-html/)

const fast = fixture()
fast.feed.start()
await fast.reply(0, snapshot({ operations: { ...operations, availableBranches: [], selectedTarget: "beta", canFastUpdate: true } }))
fast.feed.action("fast", "beta")
assert.equal(fast.requests.length, 1)
fast.feed.action("fast", installed.branch)
assert.deepEqual(JSON.parse(fast.requests[1].options.body), { action: "fast", branch: installed.branch })
await fast.reply(1, snapshot({ operations: { ...operations, canFastUpdate: false, request: request("fast", "pending", installed.branch) }, updater: { ...updater, state: "updating..." } }))
fast.feed.action("fast", installed.branch)
assert.equal(fast.requests.length, 2)
fast.fire(1000)
await fast.reply(2, snapshot({ operations: { ...operations, canFastUpdate: true, request: { ...request("fast", "complete", installed.branch), outcome: "up_to_date" } } }))
assert.equal(fast.feed.installBaseline, null)
assert.match(fast.feed.notice, /already up to date/)
fast.feed.stop()

const fastLost = fixture()
fastLost.feed.start()
await fastLost.reply(0, snapshot({ operations: { ...operations, canFastUpdate: true } }))
fastLost.feed.action("fast", installed.branch)
await fastLost.fail(1)
assert.equal(fastLost.feed.uncertain, true)
fastLost.feed.action("fast", installed.branch)
assert.equal(fastLost.requests.length, 2)
fastLost.fire(2000)
await fastLost.reply(2, snapshot({ installed: { ...installed, commit: "b".repeat(40) }, operations: { ...operations, canFastUpdate: true } }))
assert.equal(fastLost.feed.installBaseline, null)
assert.equal(fastLost.feed.uncertain, false)
assert.match(fastLost.feed.notice, /verified after reconnect/)
fastLost.feed.stop()

const fastPage = { actionDisabled: false, operations: { canFastUpdate: true, selectedTarget: "beta" }, data: { installed }, dialog: null }
SoftwarePage.methods.askFastUpdate.call(fastPage)
assert.deepEqual(fastPage.dialog, { action: "fast", branch: "Dom", title: "Fast Update", message: "Download latest version of Dom and restart?", label: "Fast Update" })
assert.equal(validSoftwareSnapshot(snapshot({ operations: { ...operations, canFastUpdate: "yes" } })), false)
assert.equal(validSoftwareSnapshot(snapshot({ operations: { ...operations, request: { ...request("fast"), outcome: "invented" } } })), false)
