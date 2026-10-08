import assert from "node:assert/strict"
import { SoftwareStatusFeed, SoftwarePage, validSoftwareSnapshot, softwareProgress } from "../web/js/software-status.js"

const flush = async () => { for (let i = 0; i < 12; i++) await Promise.resolve() }
const installed = { version: "fixture", branch: "Dom", commit: "a".repeat(40) }
const updater = { state: "idle", targetBranch: "Dom", lastSuccessAt: "2026-09-20T12:30:00Z", lastFetchAt: null,
  targetChangeFound: true, finalizedUpdateReady: false, failedCount: 0 }
const operations = { parked: true, availableBranches: ["Dom", "beta"], selectedTarget: "Dom",
  canCheck: true, canDownload: true, canSelect: true, canInstall: false, reason: null, request: null }
const snapshot = (changes = {}) => ({ schemaVersion: 1, installed, updater, operations, ...changes })
const request = (action, state = "pending", target = null, error = null) => ({ id: "one", action, target, state, error })
const response = (body, status = 200) => ({ ok: status >= 200 && status < 300, status, json: async () => body })

function fixture(includeHistory = true) {
  const requests = [], states = [], timers = new Map()
  let nextTimer = 0, unauthorized = 0
  const feed = new SoftwareStatusFeed({ includeHistory, publish: (state) => states.push(state), unauthorized: () => { unauthorized++ },
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
    draftBranch: "", draftTouched: false, dialog: null }
  Object.defineProperty(state,"branchOptions",{get:()=>SoftwarePage.computed.branchOptions.call(state)})
  Object.defineProperty(state,"canStageBranch",{get:()=>SoftwarePage.computed.canStageBranch.call(state)})
  return state
}
const staged = page()
SoftwarePage.methods.syncDraftBranch.call(staged,"Dom")
assert.equal(staged.draftBranch,"Dom")
staged.draftBranch="beta"
SoftwarePage.methods.changeBranch.call(staged)
assert.equal(staged.draftTouched,true)
assert.equal(staged.canStageBranch,true)
SoftwarePage.methods.chooseBranch.call(staged)
assert.equal(staged.dialog.action,"select") // Normal updates can still stage a target without restarting.
assert.equal(staged.dialog.branch,"beta")
SoftwarePage.methods.askFastUpdate.call({...staged, operations:{...staged.operations,canFastUpdate:true}})
const switchPage={...staged,operations:{...staged.operations,canFastUpdate:true}}
SoftwarePage.methods.askFastUpdate.call(switchPage)
assert.equal(switchPage.dialog.action,"fast")
assert.equal(switchPage.dialog.branch,"beta")
assert.equal(switchPage.dialog.label,"Switch & update")
const alternateTarget=page("legacy",["StarPilot","Dom","beta"],"installed-only")
SoftwarePage.methods.syncDraftBranch.call(alternateTarget,"legacy")
assert.equal(alternateTarget.canStageBranch,false)
assert.equal(alternateTarget.draftBranch,"installed-only")
assert.deepEqual(alternateTarget.branchOptions.map(branch=>branch.name),["legacy","installed-only","StarPilot","Dom","beta"])
assert.equal(alternateTarget.branchOptions[0].available,false)
assert.equal(alternateTarget.branchOptions[1].available,true)
const sentinel = fixture()
sentinel.feed.start()
await sentinel.reply(0, snapshot({ operations: { ...operations, availableBranches: ["Dom", "other:"] } }))
sentinel.feed.action("select", "other:")
assert.equal(sentinel.requests.length, 1)
assert.deepEqual(page("Dom", ["Dom", "other:"]).branchOptions.map(branch=>branch.name), ["Dom"])
sentinel.feed.stop()

assert.equal(SoftwarePage.methods.branchLabel("StarPilot"), "StarPilot — Release")
assert.equal(SoftwarePage.methods.branchLabel("Dom"), "Dom — Development")
assert.match(SoftwarePage.template, /Check for updates/)
assert.match(SoftwarePage.template, /Normal Update/)
assert.match(SoftwarePage.template, /Restart &amp; install/)
assert.match(SoftwarePage.template, /displayVersion \?\? data\.installed\.version/)
assert.match(SoftwarePage.template, /@click="askRollback">Previous version/ )
assert.match(SoftwarePage.template, /operations\.canRollback !== true/)
assert.doesNotMatch(SoftwarePage.template, /historical version|status only/i)

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
assert.deepEqual(fastPage.dialog, { action: "fast", branch: "beta", title: "Switch branch", message: "Download latest version of beta and restart?", label: "Switch & update" })
assert.equal(validSoftwareSnapshot(snapshot({ operations: { ...operations, canFastUpdate: "yes" } })), false)
assert.equal(validSoftwareSnapshot(snapshot({ operations: { ...operations, request: { ...request("fast"), outcome: "invented" } } })), false)

const rollbackPage = { actionDisabled: false, operations: { canRollback: true }, data: { installed }, dialog: null }
SoftwarePage.methods.askRollback.call(rollbackPage)
assert.equal(rollbackPage.dialog.action, "rollback")
assert.equal(rollbackPage.dialog.branch, installed.branch)
assert.equal(rollbackPage.dialog.title, "Previous version")
assert.match(rollbackPage.dialog.message, /Automatic downloads will be turned off/)
const unavailableRollback = { ...rollbackPage, operations: { canRollback: false }, dialog: null }
SoftwarePage.methods.askRollback.call(unavailableRollback)
assert.equal(unavailableRollback.dialog, null)
assert.equal(validSoftwareSnapshot(snapshot({ operations: { ...operations, canRollback: "yes" } })), false)


// Recent-version selection pins both the installed revision and listed target.
{
  const h = fixture()
  h.feed.start()
  const selected = "b".repeat(40)
  const history = { installed: [], downloaded: [], currentReleaseNotes: null, downloadedReleaseNotes: null,
    recent: { branch: "Dom", head: "c".repeat(40), entries: [{ hash: selected, date: "2026-10-05", subject: "Older build" }] } }
  await h.reply(0, snapshot({ operations: { ...operations, canFastUpdate: true, history } }))
  assert.equal(h.feed.action("version", "Dom", { expectedCommit: "f".repeat(40), selectedCommit: selected }), null)
  assert.equal(h.feed.action("version", "Dom", { expectedCommit: installed.commit, selectedCommit: "f".repeat(40) }), null)
  const pending = h.feed.action("version", "Dom", { expectedCommit: installed.commit, selectedCommit: selected })
  assert.deepEqual(JSON.parse(h.requests[1].options.body), { action: "version", branch: "Dom", expectedCommit: installed.commit, selectedCommit: selected })
  await h.reply(1, snapshot({ operations: { ...operations, canFastUpdate: false, history,
    request: { ...request("version", "pending", "Dom"), selectedCommit: selected } } }))
  await pending
  assert.equal(h.feed.installBaseline.selectedCommit, selected)
  h.fire(1000)
  await h.reply(2, snapshot({ operations: { ...operations, history,
    request: { ...request("version", "complete", "Dom"), selectedCommit: "c".repeat(40), outcome: "up_to_date" } } }))
  assert.equal(h.feed.installBaseline.selectedCommit, selected)
  h.fire(1000)
  await h.reply(3, snapshot({ installed: { ...installed, commit: "c".repeat(40) }, operations: { ...operations, history } }))
  assert.equal(h.feed.installBaseline.selectedCommit, selected)
  assert.notEqual(h.feed.notice, "Installed build verified after reconnect.")
  h.fire(1000)
  await h.reply(4, snapshot({ installed: { ...installed, commit: selected }, operations: { ...operations, history } }))
  assert.equal(h.feed.installBaseline, null)
  assert.equal(h.feed.notice, "Installed build verified after reconnect.")
  h.feed.stop()
}

// Real stage progress remains indeterminate until measured numeric progress exists.
assert.equal(softwareProgress(updater), null)
assert.deepEqual(softwareProgress({...updater, state: "finalizing update..."}),
  {active: true, percent: null, label: "Finalizing update", detail: ""})
assert.equal(softwareProgress({...updater, state: "downloading..."}, {progress: {stage: "Downloading", detail: "", percent: 37}}).percent, 37)
for (const percent of [NaN, Infinity, -1, 101]) {
  assert.equal(validSoftwareSnapshot(snapshot({operations: {...operations, progress: {stage: "fetching", detail: "", percent}}})), false)
}
assert.equal(softwareProgress({...updater, state: "finalizing update..."}, {progress: {stage: "unavailable", detail: "Updater status unavailable", percent: null}}).active, false)
assert.ok(validSoftwareSnapshot(snapshot({updater: {...updater, lastCheckedAt: null}})))
assert.equal(validSoftwareSnapshot(snapshot({updater: {...updater, lastCheckedAt: 12}})), false)
assert.match(SoftwarePage.template, /<summary>Advanced options<\/summary>/)
assert.match(SoftwarePage.template, /<summary>Versions &amp; release notes<\/summary>/)
assert.match(SoftwarePage.template, /data\.updater\.lastCheckedAt/)

for (const progress of [{stage: "idle", detail: "", percent: null}, {stage: null, detail: null, percent: null}, {stage: "unknown", detail: "", percent: null}]) {
  assert.ok(validSoftwareSnapshot(snapshot({operations: {...operations, progress}})))
  assert.equal(softwareProgress(updater, {progress}), null)
}
for (const stage of ["complete", "error"]) {
  const state = {...updater, state: "updating...", fast: {stage, detail: "Finished"}}
  const progress = {stage, detail: "Finished", percent: null}
  assert.equal(softwareProgress(state, {progress}).active, false)
  assert.equal(softwareProgress(state, {progress}).percent, null)
}
assert.equal(softwareProgress({...updater, state: "finalizing update..."}, {progress: {stage: "finalizing", detail: null, percent: null}}).label, "Finalizing update")

const lightweight = fixture(false)
lightweight.feed.start()
assert.equal(lightweight.requests[0].url, './api/software/status?history=0')
await lightweight.reply(0, snapshot())
assert.equal(lightweight.states.at(-1).busy, false)
assert.equal(lightweight.states.at(-1).data.operations.canCheck, true)
SoftwarePage.methods.loadHistory.call({ operations, busy: false, feed: lightweight.feed }, { target: { open: true } })
assert.equal(lightweight.requests[1].url, './api/software/status')
await lightweight.reply(1, snapshot({ operations: { ...operations, history } }))
assert.deepEqual(lightweight.states.at(-1).data.operations.history, history)
lightweight.feed.stop()

const directBranch = fixture()
directBranch.feed.start()
await directBranch.reply(0,snapshot({operations:{...operations,availableBranches:['Dom','beta'],canFastUpdate:true}}))
const branchVm={actionDisabled:false,draftBranch:'beta',operations:directBranch.states.at(-1).data.operations,data:{installed},dialog:null,feed:directBranch.feed}
SoftwarePage.methods.askFastUpdate.call(branchVm)
assert.equal(branchVm.dialog.label,'Switch & update')
const acceptedSwitch=SoftwarePage.methods.confirmDialog.call(branchVm)
assert.deepEqual(JSON.parse(directBranch.requests[1].options.body),{action:'fast',branch:'beta'})
assert.equal(directBranch.requests.length,2,'switching uses one request and one confirmation')
await directBranch.reply(1,snapshot())
await acceptedSwitch
directBranch.feed.stop()
