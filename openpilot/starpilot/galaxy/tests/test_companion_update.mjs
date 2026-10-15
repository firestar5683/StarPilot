import assert from 'node:assert/strict'
import { createRenderer, nextTick } from '../web/vendor/vue/vue.esm-browser.js'
import { GalaxyPage } from '../web/js/galaxy.js'
import { newerCompanionVersion } from '../web/js/companion.js'

assert.equal(newerCompanionVersion('1.1.5', '1.1.4'), true)
assert.equal(newerCompanionVersion('1.1.10', '1.1.9'), true)
assert.equal(newerCompanionVersion('1.2', '1.1.99'), true)
for (const [available, installed] of [['1.1.5', '1.1.5'], ['1.1.4', '1.1.5'], ['1.1', '1.1.0'],
  ['', '1.1.4'], ['1.1.5', ''], ['unknown', '1.1.4'], ['1.1.5', null]]) {
  assert.equal(newerCompanionVersion(available, installed), false)
}

const storage = new Map()
globalThis.localStorage = { getItem: key => storage.get(key) ?? null, setItem: (key, value) => storage.set(key, value) }
globalThis.window = { StarPilotApp: { version: () => '1.1.4', uplinkState: () => '{}' } }
globalThis.document = { activeElement: null }
const status = { protocol: 1, enabled: false, connected: false, active: false, appAvailable: true, updateAvailable: false,
  bytes: 0, shippedVersion: '1.1.5', version: null, state: 'disabled' }
globalThis.fetch = async url => ({ ok: true, json: async () => url.includes('/api/companion/status') ? status : { paired: false } })

const node = (type, text = '') => ({ type, text, props: {}, children: [], parent: null,
  addEventListener() {}, removeEventListener() {} })
const renderer = createRenderer({
  createElement: type => node(type), createText: text => node('text', text), createComment: text => node('comment', text),
  setText: (item, text) => { item.text = text }, setElementText: (item, text) => { item.text = text; item.children = [] },
  patchProp: (item, key, before, after) => { item.props[key] = after },
  insert: (item, parent, anchor = null) => {
    if (item.parent) item.parent.children.splice(item.parent.children.indexOf(item), 1)
    item.parent = parent
    const index = parent.children.indexOf(anchor)
    parent.children.splice(index < 0 ? parent.children.length : index, 0, item)
  },
  remove: item => { const index = item.parent?.children.indexOf(item); if (index >= 0) item.parent.children.splice(index, 1) },
  parentNode: item => item.parent,
  nextSibling: item => item.parent?.children[item.parent.children.indexOf(item) + 1] ?? null,
})
const all = item => [item, ...item.children.flatMap(all)]
const text = item => [item.text, ...item.children.map(text)].join(' ')
const banner = host => all(host).find(item => item.type === 'div' && text(item).includes('Android app update available') && item.props.role === 'status')
async function mount() {
  const host = node('host')
  const app = renderer.createApp({ ...GalaxyPage,
    // The real companion child still polls and emits metadata to the real page.
    components: { ...GalaxyPage.components, GalaxyHotspot: { template: '<div />' }, InstallApp: { props: ['updateAvailable'], template: '<div class="install-state">{{ updateAvailable }}</div>' } },
  }, { mode: 'local', unauthorized() { assert.fail('Unexpected authentication failure') } })
  app.config.compilerOptions.decodeEntities = raw => raw.replaceAll('&amp;', '&')
  const vm = app.mount(host)
  await new Promise(resolve => setImmediate(resolve))
  await nextTick()
  return { host, app, vm }
}

let mounted = await mount()
try {
  const { host, vm } = mounted
  const notice = banner(host)
  assert.ok(notice, 'A native app without an internet-sharing lease still gets an update notice')
  assert.match(text(notice), /Version 1.1.5 is available.*Installed: 1.1.4/s)
  assert.ok(all(notice).some(item => item.type === 'a' && item.props.href === './app.apk' && text(item).includes('Update app')))
  assert.ok(all(host).some(item => item.type === 'div' && item.props.class === 'install-state' && text(item).includes('true')),
    'The main install action is told to render as an update')
  const root = host.children.find(item => item.type === 'div')
  assert.ok(root.children.indexOf(notice) < root.children.findIndex(item => item.type === 'section'), 'Notice precedes all page sections')
  const install = all(host).find(item => item.type === 'section' && text(item).includes('Install Galaxy'))
  assert.match(text(install), /Android app version:.*1.1.5.*Installed.*1.1.4/s)
  const dismiss = all(notice).find(item => item.type === 'button' && item.props['aria-label'] === 'Dismiss app update notice')
  dismiss.props.onClick()
  await nextTick()
  assert.equal(banner(host), undefined)
  vm.companionStatus = { ...status }
  await nextTick()
  assert.equal(banner(host), undefined, 'Polling does not undo dismissal')
} finally { mounted.app.unmount() }

let nativeInstalls = 0
window.StarPilotApp.installUpdate = () => nativeInstalls++
mounted = await mount()
try {
  assert.equal(banner(mounted.host), undefined, 'Dismissal survives leaving and returning to the page')
  mounted.vm.companionStatus = { ...status, shippedVersion: '1.1.6' }
  await nextTick()
  const nativeNotice = banner(mounted.host)
  assert.ok(nativeNotice, 'A later available release gets a new notice')
  const nativeUpdate = all(nativeNotice).find(item => item.type === 'button' && text(item).includes('Update app'))
  assert.ok(nativeUpdate, 'A current native app uses the in-app installer')
  nativeUpdate.props.onClick()
  assert.equal(nativeInstalls, 1)
  mounted.vm.companionStatus = { ...status, shippedVersion: '1.1.3', updateAvailable: true }
  await nextTick()
  assert.equal(banner(mounted.host), undefined, 'A server mismatch flag cannot suggest downgrading this phone')
  mounted.vm.companionStatus = { ...status, shippedVersion: '1.1.6', appAvailable: false }
  await nextTick()
  assert.equal(banner(mounted.host), undefined, 'Missing APK never advertises a dead update link')
  mounted.vm.companionStatus = { ...status, shippedVersion: '1.1.6' }
  localStorage.setItem = () => { throw new Error('Storage unavailable') }
  mounted.vm.dismissAppUpdate()
  await nextTick()
  assert.equal(banner(mounted.host), undefined, 'Dismiss still works when persistent storage is unavailable')
} finally { mounted.app.unmount() }

delete window.StarPilotApp
storage.clear()
mounted = await mount()
try {
  assert.equal(banner(mounted.host), undefined, 'A browser cannot infer an installed version without a connected phone')
  const install = all(mounted.host).find(item => item.type === 'section' && text(item).includes('Install Galaxy'))
  assert.match(text(install), /Android app version:.*1.1.5/s)
  assert.doesNotMatch(text(install), /Installed:/)
} finally { mounted.app.unmount() }

console.log('Companion install version, in-app update, browser fallback, version ordering and persistent dismissal passed')
