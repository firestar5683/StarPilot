import fs from 'node:fs'
import vm from 'node:vm'
import assert from 'node:assert/strict'
import test from 'node:test'
const root = process.argv[2] || new URL('../../../../', import.meta.url).pathname
const js = root + '/starpilot/system/the_galaxy/assets/mobile/js/'
const source = fs.readFileSync(js + 'views/SystemTools.js', 'utf8')
const SHA = 'a'.repeat(40), HEAD = 'b'.repeat(40)
function fixture() {
  const calls = [], confirmations = [], messages = [], reads = []
  let confirm = async () => true
  const api = {
    setUpdateBranch: async branch => calls.push({legacy: branch}),
    installUpdateVersion: async (branch, commit) => calls.push({branch, commit}),
    getUpdateFastStatus: async () => ({running: false, isOnroad: false, versionPin: null}),
    getUpdateBranches: async () => ({branches: ['Dom', 'SunnyPilot', 'StarPilot', 'feature/new'], currentBranch: 'Dom'}),
    getUpdateVersions: async (branch, options) => {reads.push({branch, ...options}); return {branch, head: HEAD, page: options.page, hasMore: options.page === 1, commits: [{sha: options.page === 1 ? SHA : 'c'.repeat(40), date: '2026-09-10T12:00:00Z', subject: 'Fix launch'}]}},
  }
  const context = vm.createContext({api, AbortController, showSnackbar: (...args) => messages.push(args), GalaxySection: {}, GalaxySelect: {}, GxNotice: {}, GalaxyConfirm: async options => {confirmations.push(options); return confirm()}})
  vm.runInContext(fs.readFileSync(js + 'components/VersionHistoryPicker.js', 'utf8').replace(/export /g, ''), context)
  vm.runInContext(source.replace(/^import .*$/gm, '').replace('export const SystemTools =', 'globalThis.component =').replace('export const VersionTier =', 'globalThis.VersionTier ='), context)
  const component = context.component
  const instance = {...component.data(), ...component.methods, branches: ['Dom', 'SunnyPilot', 'StarPilot', 'feature/test'], currentBranch: 'feature/local', branchLoading: false}
  for (const [key, getter] of Object.entries(component.computed)) Object.defineProperty(instance, key, {get: () => getter.call(instance)})
  return {instance, calls, confirmations, messages, reads, api, tier: context.VersionTier, setConfirm: fn => {confirm = fn}}
}
test('pending summary names the destination branch and pinned version', () => {
  const {instance} = fixture()
  const setup = (overrides = {}) => Object.assign(instance, {
    currentBranch: 'StarPilot',
    fastStatus: {branch: 'StarPilot', localCommit: SHA, remoteCommit: HEAD, updateAvailable: false, versionPin: null},
    busy: '', rebootPending: false, versionMode: 'latest', selectedCommit: '', versionCommits: [],
  }, overrides)
  let state = setup({targetBranch: 'Dom'})
  assert.match(state.pendingSummary, /Currently StarPilot → will switch to Dom \(latest\)/)
  state = setup({targetBranch: 'Dom', versionMode: 'earlier', selectedCommit: SHA, versionCommits: [{sha: SHA, subject: 'Fix'}]})
  assert.match(state.pendingSummary, /Currently StarPilot → will install Dom @/)
  assert.match(state.pendingSummary, /pauses automatic updates/)
  state = setup({targetBranch: 'StarPilot', versionMode: 'earlier', selectedCommit: SHA, versionCommits: [{sha: SHA, version: '6.7.7'}]})
  assert.match(state.pendingSummary, /Currently StarPilot → will install StarPilot @ 6\.7\.7 \(pauses automatic updates\)/)
  state = setup({targetBranch: 'StarPilot'})
  assert.equal(state.pendingSummary, '')
})

test('single status button names and colors the pending action', () => {
  const {instance} = fixture()
  const setup = (overrides = {}) => Object.assign(instance, {
    currentBranch: 'StarPilot',
    fastStatus: {branch: 'StarPilot', localCommit: SHA, remoteCommit: HEAD, updateAvailable: false, versionPin: null},
    busy: '', rebootPending: false, versionMode: 'latest', selectedCommit: '', versionCommits: [],
  }, overrides)
  let state = setup({targetBranch: 'Dom'})
  assert.equal(state.pendingKind, 'switch')
  assert.equal(state.pendingLabel, 'Switch to Dom')
  assert.equal(state.pendingButtonClass, 'gx-btn gx-btn--switch')
  state = setup({targetBranch: 'StarPilot', fastStatus: {branch: 'StarPilot', localCommit: SHA, remoteCommit: HEAD, updateAvailable: true, versionPin: null}})
  assert.equal(state.pendingKind, 'update')
  assert.equal(state.pendingLabel, 'Update StarPilot')
  assert.equal(state.pendingButtonClass, 'gx-btn')
  state = setup({targetBranch: 'StarPilot', versionMode: 'earlier', selectedCommit: SHA, versionCommits: [{sha: SHA, version: '6.7.7'}]})
  assert.equal(state.pendingKind, 'version')
  assert.equal(state.pendingLabel, 'Install StarPilot @ 6.7.7')
  assert.equal(state.pendingButtonClass, 'gx-btn gx-btn--version')
  state = setup({targetBranch: 'Dom', versionMode: 'earlier', selectedCommit: SHA, versionCommits: [{sha: SHA, subject: 'Fix'}]})
  assert.equal(state.pendingLabel, 'Switch to Dom @ ' + SHA.slice(0, 7))
  assert.equal(state.pendingButtonClass, 'gx-btn gx-btn--version')
  state = setup({targetBranch: 'Dom', versionMode: 'earlier', selectedCommit: ''})
  assert.equal(state.pendingKind, 'none')
  assert.equal(state.pendingLabel, 'Select a version')
  state = setup({targetBranch: 'StarPilot'})
  assert.equal(state.pendingKind, 'current')
  assert.equal(state.pendingLabel, 'Up to date · Check again')
  state = setup({targetBranch: 'StarPilot', fastStatus: {branch: 'StarPilot', localCommit: SHA, remoteCommit: '', versionPin: null}})
  assert.equal(state.pendingKind, 'failed')
  assert.equal(state.pendingLabel, 'Check again')
})

test('status card waits for the first status attempt before showing the fallback', async () => {
  const {instance, api} = fixture()
  assert.equal(instance.statusChecked, false)
  api.getUpdateFastStatus = async () => ({running: false, isOnroad: false, versionPin: null, branch: 'Dom', localCommit: SHA, remoteCommit: HEAD})
  await instance.loadFastStatus()
  assert.equal(instance.statusChecked, true)
  assert.equal(instance.fastStatus.branch, 'Dom')

  const {instance: failed, api: failedApi} = fixture()
  failedApi.getUpdateFastStatus = async () => { throw new Error('offline') }
  await failed.loadFastStatus()
  assert.equal(failed.statusChecked, true)
  assert.equal(failed.statusUnavailable, true)
  assert.equal(failed.fastStatus, null)
})

test('local status paints the card immediately and the remote check fills in after', async () => {
  const {instance, api} = fixture()
  const calls = []
  api.getUpdateFastStatus = async ({local = false} = {}) => {
    calls.push(local)
    const base = {running: false, isOnroad: false, versionPin: null, branch: 'Dom', localCommit: SHA, automaticUpdates: false}
    return local ? {...base, remoteCommit: '', updateAvailable: false} : {...base, remoteCommit: HEAD, updateAvailable: true}
  }
  await instance.loadFastStatus({local: true})
  assert.equal(instance.statusChecked, true)
  assert.equal(instance.remoteChecked, false, 'a local response must not claim the remote check is done')
  assert.equal(instance.updateAvailable, false)
  assert.equal(instance.statusPollingNeeded, true, 'polling must continue until the remote check lands')

  await instance.loadFastStatus()
  assert.equal(instance.remoteChecked, true)
  assert.equal(instance.updateAvailable, true)
  assert.equal(instance.statusPollingNeeded, false)
  assert.deepEqual(calls, [true, false])
})

test('a late local response cannot overwrite a finished remote check', async () => {
  const {instance, api} = fixture()
  instance.remoteChecked = true
  instance.fastStatus = {running: false, isOnroad: false, versionPin: null, branch: 'Dom', remoteCommit: HEAD, updateAvailable: true}
  api.getUpdateFastStatus = async () => ({running: false, isOnroad: false, versionPin: null, branch: 'Dom', remoteCommit: '', updateAvailable: false})
  await instance.loadFastStatus({local: true})
  assert.equal(instance.fastStatus.remoteCommit, HEAD)
  assert.equal(instance.fastStatus.updateAvailable, true)
})

test('primary and Other choices stage a target without installing or confirming', async () => {
  const {instance, calls, confirmations} = fixture()
  await instance.onPrimaryBranchSelect({target: {value: 'Dom'}})
  assert.equal(instance.targetBranch, 'Dom')
  await instance.onPrimaryBranchSelect({target: {value: 'other:'}})
  assert.equal(instance.otherBranchesOpen, true)
  await instance.onBranchSelect({target: {value: 'SunnyPilot'}})
  assert.equal(instance.targetBranch, 'SunnyPilot')
  assert.equal(instance.currentBranch, 'feature/local')
  assert.deepEqual(calls, [])
  assert.deepEqual(confirmations, [])
})
test('current custom branch remains visible when absent from remote', () => {
  const {instance} = fixture()
  assert.deepEqual(Array.from(instance.otherBranches), ['feature/local', 'SunnyPilot', 'feature/test'])
})
test('every remote branch can install latest only through explicit confirmation', async () => {
  for (const branch of ['StarPilot', 'Dom', 'SunnyPilot', 'feature/test']) {
    const {instance, calls, confirmations} = fixture()
    instance.selectTargetBranch(branch)
    await instance.installSelectedVersion()
    assert.deepEqual(calls, [{branch, commit: 'latest'}])
    assert.equal(confirmations.length, 1)
    assert.ok(confirmations[0].message.includes(branch))
    assert.ok(confirmations[0].message.includes('Latest'))
  }
})
test('historical install requires a loaded full SHA and cancellation writes nothing', async () => {
  const {instance, calls, confirmations, setConfirm} = fixture()
  instance.selectTargetBranch('Dom')
  await instance.onVersionModeSelect({target: {value: 'earlier'}})
  instance.selectedCommit = 'deadbeef'
  await instance.installSelectedVersion()
  assert.deepEqual(confirmations, [])
  instance.selectedCommit = SHA
  setConfirm(async () => false)
  await instance.installSelectedVersion()
  assert.deepEqual(calls, [])
  setConfirm(async () => true)
  await instance.installSelectedVersion()
  assert.deepEqual(calls, [{branch: 'Dom', commit: SHA}])
  assert.ok(confirmations.at(-1).message.includes(SHA))
})
test('pagination uses the original branch head and changing branch resets to Latest', async () => {
  const {instance, reads} = fixture()
  instance.selectTargetBranch('Dom')
  await instance.onVersionModeSelect({target: {value: 'earlier'}})
  instance.selectedCommit = SHA
  await instance.loadVersions(true)
  assert.equal(reads[1].page, 2)
  assert.equal(reads[1].head, HEAD)
  assert.equal(instance.versionCommits.length, 2)
  instance.selectTargetBranch('feature/test')
  assert.equal(instance.versionMode, 'latest')
  assert.equal(instance.selectedCommit, '')
  assert.equal(instance.versionCommits.length, 0)
  assert.equal(instance.versionHead, '')
})
test('late history response after branch change cannot repopulate history', async () => {
  const {instance, api} = fixture()
  let resolve, signal
  api.getUpdateVersions = (branch, options) => {signal = options.signal; return new Promise(done => {resolve = done})}
  instance.selectTargetBranch('Dom')
  const pending = instance.onVersionModeSelect({target: {value: 'earlier'}})
  instance.selectTargetBranch('StarPilot')
  assert.equal(signal.aborted, true)
  resolve({branch: 'Dom', head: HEAD, page: 1, hasMore: false, commits: [{sha: SHA}]})
  await pending
  assert.equal(instance.versionCommits.length, 0)
  assert.equal(instance.targetBranch, 'StarPilot')
  assert.equal(instance.versionLoading, false)
})
test('failed or missing history explains the issue and never enables historical install', async () => {
  const {instance, api} = fixture()
  instance.selectTargetBranch('Dom')
  api.getUpdateVersions = async () => {throw new Error('Branch no longer available')}
  await instance.onVersionModeSelect({target: {value: 'earlier'}})
  assert.equal(instance.versionError, 'Branch no longer available')
  assert.equal(instance.installVersionBlocked, true)
  api.getUpdateVersions = async () => ({branch: 'Dom', head: HEAD, page: 1, hasMore: false, commits: []})
  await instance.loadVersions()
  assert.match(instance.versionError, /No versions/)
})
test('driving, running, or busy state blocks install and is rechecked after confirmation', async () => {
  for (const state of [{isOnroad: true}, {fastStatus: {running: true}}, {busy: 'check'}]) {
    const {instance, calls, confirmations} = fixture()
    instance.selectTargetBranch('Dom')
    Object.assign(instance, state)
    await instance.installSelectedVersion()
    assert.deepEqual(calls, [])
    assert.deepEqual(confirmations, [])
  }
  const {instance, calls, api, setConfirm} = fixture()
  instance.selectTargetBranch('Dom')
  setConfirm(async () => {api.getUpdateFastStatus = async () => ({isOnroad: true}); return true})
  await instance.installSelectedVersion()
  assert.deepEqual(calls, [])
})
test('concurrent install confirmation and failed status refresh cannot submit', async () => {
  const {instance, calls, confirmations, api, setConfirm} = fixture()
  instance.selectTargetBranch('Dom')
  let release
  setConfirm(() => new Promise(resolve => {release = resolve}))
  const pending = instance.installSelectedVersion()
  await instance.installSelectedVersion()
  assert.equal(confirmations.length, 1)
  api.getUpdateFastStatus = async () => {throw new Error('offline')}
  release(true)
  await pending
  assert.deepEqual(calls, [])
})
test('return to Latest uses pinned branch and confirms without changing automatic update settings', async () => {
  const {instance, calls, confirmations} = fixture()
  instance.fastStatus = {versionPin: {branch: 'feature/test', commit: SHA, installedAt: '2026-09-10'}}
  await instance.returnToLatest()
  assert.deepEqual(calls, [{branch: 'feature/test', commit: 'latest'}])
  assert.ok(confirmations[0].message.includes('automatic-update setting is unchanged'))
})
test('API preserves branch encoding, pagination head, abort signal and confirmed install body', async () => {
  const calls = []
  const context = vm.createContext({URLSearchParams, fetch: async (url, init) => {calls.push({url, init}); return {ok: true, json: async () => ({})}}})
  vm.runInContext(fs.readFileSync(js + 'api.js', 'utf8').replace(/export /g, '') + '\nglobalThis.client = api', context)
  const signal = new AbortController().signal
  await context.client.getUpdateVersions('feature/a&b', {page: 2, head: HEAD, signal})
  const url = new URL(calls[0].url, 'https://example.test')
  assert.equal(url.searchParams.get('branch'), 'feature/a&b')
  assert.equal(url.searchParams.get('page'), '2')
  assert.equal(url.searchParams.get('head'), HEAD)
  assert.equal(calls[0].init.signal, signal)
  await context.client.installUpdateVersion('feature/a&b', SHA)
  assert.equal(calls[1].url, '/api/update/version')
  assert.equal(calls[1].init.method, 'POST')
  assert.deepEqual(JSON.parse(calls[1].init.body), {branch: 'feature/a&b', commit: SHA, confirmed: true})
})
test('GalaxySelect reads optional option descriptions without adding them to collapsed labels', () => {
  const context = vm.createContext({document: {getElementById() {}}})
  vm.runInContext(fs.readFileSync(js + 'components/GalaxySelect.js', 'utf8').replace('export const GalaxySelect =', 'globalThis.component ='), context)
  const native = {value: 'Dom', options: [{value: 'Dom', label: 'Dom', dataset: {description: 'Development description'}}, {value: 'StarPilot', label: 'StarPilot'}], selectedOptions: [{label: 'Dom'}]}
  const instance = {...context.component.data(), $refs: {native}, $attrs: {}, current: 'Dom'}
  context.component.methods.sync.call(instance)
  assert.equal(instance.items[0].description, 'Development description')
  assert.equal(instance.items[1].description, '')
  assert.equal(instance.label, 'Dom')
})

test('GalaxySelect extracts current branch status and badge for stand-out rendering', () => {
  const context = vm.createContext({document: {getElementById() {}}})
  vm.runInContext(fs.readFileSync(js + 'components/GalaxySelect.js', 'utf8').replace('export const GalaxySelect =', 'globalThis.component ='), context)
  const native = {value: 'feature', options: [{value: 'main', label: 'main'}, {value: 'feature', label: 'feature', dataset: {current: 'true', badge: 'current'}}], selectedOptions: [{label: 'feature'}]}
  const instance = {...context.component.data(), $refs: {native}, $attrs: {}, current: 'feature'}
  context.component.methods.sync.call(instance)
  assert.equal(instance.items[1].label, 'feature')
  assert.equal(instance.items[1].current, true)
  assert.equal(instance.items[1].badge, 'current')
  assert.equal(instance.items[0].current, false)
  assert.equal(instance.label, 'feature')
})

test('GalaxySelect ignores a second open request while its menu is open', async () => {
  const context = vm.createContext({document: {getElementById() {}}})
  vm.runInContext(fs.readFileSync(js + 'components/GalaxySelect.js', 'utf8').replace('export const GalaxySelect =', 'globalThis.component ='), context)
  const instance = {...context.component.data(), open: true, disabled: false, sync() { throw new Error('menu reopened') }}
  await context.component.methods.show.call(instance)
  assert.equal(instance.open, true)
})

test('unavailable branch and navigation values cannot become install targets', async () => {
  const {instance, calls, confirmations} = fixture()
  for (const branch of ['other:', '', 'deleted-branch']) instance.selectTargetBranch(branch)
  await instance.installSelectedVersion()
  assert.equal(instance.targetBranch, '')
  assert.deepEqual(calls, [])
  assert.deepEqual(confirmations, [])
})
test('mismatched paginated history cannot mix another branch head into the selected version', async () => {
  const {instance, api} = fixture()
  instance.selectTargetBranch('Dom')
  await instance.onVersionModeSelect({target: {value: 'earlier'}})
  api.getUpdateVersions = async () => ({branch: 'Dom', head: 'd'.repeat(40), page: 2, hasMore: false, commits: [{sha: 'e'.repeat(40)}]})
  await instance.loadVersions(true)
  assert.equal(instance.versionCommits.length, 1)
  assert.equal(instance.versionHead, HEAD)
  assert.match(instance.versionError, /history changed/)
})
test('switching back to Latest invalidates history and selected revision', async () => {
  const {instance, api} = fixture()
  let reject
  api.getUpdateVersions = async () => new Promise((resolve, fail) => {reject = fail})
  instance.selectTargetBranch('Dom')
  const pending = instance.onVersionModeSelect({target: {value: 'earlier'}})
  await instance.onVersionModeSelect({target: {value: 'latest'}})
  reject(new Error('Old network failure'))
  await pending
  assert.equal(instance.versionMode, 'latest')
  assert.equal(instance.versionError, '')
  assert.equal(instance.versionLoading, false)
  assert.equal(instance.installVersionBlocked, false)
})

test('release confirmation shows a friendly version and the exact installation SHA', async () => {
  const {instance, calls, confirmations} = fixture()
  instance.selectTargetBranch('StarPilot')
  await instance.onVersionModeSelect({target: {value: 'earlier'}})
  instance.versionCommits[0].version = '6.7.7'
  instance.selectedCommit = SHA
  await instance.installSelectedVersion()
  assert.match(confirmations[0].message, /Version: 6\.7\.7/)
  assert.ok(confirmations[0].message.includes('Commit: ' + SHA))
  assert.deepEqual(calls, [{branch: 'StarPilot', commit: SHA}])
})

test('saved history is labelled and retained across pagination, then reset on branch change', async () => {
  const {instance,api,calls} = fixture()
  const normal=api.getUpdateVersions
  api.getUpdateVersions=async (...args)=>({...await normal(...args), cached:true, cachedAt:'2026-09-11T12:00:00Z'})
  instance.selectTargetBranch('Dom')
  await instance.onVersionModeSelect({target:{value:'earlier'}})
  assert.match(instance.versionNotice,/saved history/i)
  assert.match(instance.versionNotice,/online check/i)
  api.getUpdateVersions=normal
  await instance.loadVersions(true)
  assert.match(instance.versionNotice,/saved history/i)
  assert.deepEqual(calls,[])
  instance.selectTargetBranch('StarPilot')
  assert.equal(instance.versionNotice,'')
})
test('fresh history does not show a saved-history notice', async () => {
  const {instance} = fixture()
  instance.selectTargetBranch('Dom')
  await instance.onVersionModeSelect({target:{value:'earlier'}})
  assert.equal(instance.versionNotice,'')
})

test('release pagination searches duplicate pages for the next version and installs only its newest build', async () => {
 const {instance,api,calls}=fixture(), pages=[]
 api.getUpdateVersions=async(branch,{page})=>{pages.push(page);return {branch,head:HEAD,page,hasMore:page<5,commits:[{sha:String(page).repeat(40),version:page<4?'6.7.7':'6.7.6',date:'2026-09-11T12:00:00Z',subject:'Build'}]}}
 instance.selectTargetBranch('StarPilot');await instance.onVersionModeSelect({target:{value:'earlier'}})
 await instance.loadVersions(true)
 assert.deepEqual(pages,[1,2,3,4])
 assert.deepEqual(Array.from(instance.versionChoices,c=>c.sha),['1'.repeat(40),'4'.repeat(40)])
 instance.selectedCommit='2'.repeat(40);assert.equal(instance.installVersionBlocked,true)
 instance.selectedCommit='4'.repeat(40);await instance.installSelectedVersion()
 assert.deepEqual(calls,[{branch:'StarPilot',commit:'4'.repeat(40)}])
})
test('a release search has a bounded request budget and preserves progress when older history is unavailable', async () => {
 const {instance,api}=fixture();let requests=0
 api.getUpdateVersions=async(branch,{page})=>{requests++;return {branch,head:HEAD,page,hasMore:true,commits:[{sha:page.toString(16).repeat(40),version:'6.7.7',date:'2026-09-11T12:00:00Z',subject:'Build'}]}}
 instance.selectTargetBranch('StarPilot');await instance.onVersionModeSelect({target:{value:'earlier'}})
 await instance.loadVersions(true);assert.equal(requests,5);assert.equal(instance.versionPage,5)
 api.getUpdateVersions=async()=>{throw Error('GitHub rate limit')}
 await instance.loadVersions(true)
 assert.equal(instance.versionPage,5);assert.equal(instance.versionChoices.length,1);assert.match(instance.versionError,/rate limit/)
})

test('changing branch during a multi-page release search cancels remaining pages and rejects stale results', async () => {
 const {instance,api}=fixture();let finish,requests=0
 api.getUpdateVersions=async(branch,{page})=>{requests++;return {branch,head:HEAD,page,hasMore:true,commits:[{sha:'1'.repeat(40),version:'6.7.7',date:'2026-09-11T12:00:00Z',subject:'Build'}]}}
 instance.selectTargetBranch('StarPilot');await instance.onVersionModeSelect({target:{value:'earlier'}})
 api.getUpdateVersions=(branch,{page})=>{requests++;return new Promise(resolve=>{finish=()=>resolve({branch,head:HEAD,page,hasMore:true,commits:[{sha:'2'.repeat(40),version:'6.7.7',date:'2026-09-11T12:00:00Z',subject:'Build'}]})})}
 const pending=instance.loadVersions(true)
 instance.selectTargetBranch('Dom');finish();await pending
 assert.equal(requests,2);assert.equal(instance.versionCommits.length,0);assert.equal(instance.versionLoading,false)
})

test('Latest explains normal OS handling and local-edit behavior; historical confirmation keeps recovery details', async () => {
  const {instance, confirmations} = fixture()
  instance.selectTargetBranch('Dom')
  await instance.installSelectedVersion()
  assert.match(confirmations[0].message, /normal branch updater/)
  assert.match(confirmations[0].message, /required OS update/)
  assert.match(confirmations[0].message, /Local code changes may be overwritten/)
  assert.doesNotMatch(confirmations[0].message, /code changes are backed up/)
  instance.rebootPending = false
  instance.rebootStartedAt = 0
  await instance.onVersionModeSelect({target:{value:'earlier'}})
  instance.selectedCommit=SHA
  await instance.installSelectedVersion()
  assert.match(confirmations[1].message, /updates will be paused/)
  assert.match(confirmations[1].message, /code changes are backed up/)
})

test('refreshBranches updates remote branch list and resets fallback notice', async () => {
  const {instance, messages} = fixture()
  instance.branchListFallback = true
  await instance.refreshBranches()
  assert.equal(instance.branchRefreshing, false)
  assert.equal(instance.branchListFallback, false)
  assert.ok(instance.branches.includes('feature/new'))
  assert.equal(messages.length, 1)
  assert.match(messages[0][0], /refreshed/i)
})

