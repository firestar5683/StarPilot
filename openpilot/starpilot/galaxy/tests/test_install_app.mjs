import assert from 'node:assert/strict'
import { androidInstallHelp, installHelp, InstallApp, rememberInstallPrompt, isIosDevice, isAndroidDevice } from '../web/js/install-app.js'
assert.match(installHelp({ secure: true, agent: 'iPhone' }), /Share.*Add to Home Screen/)
assert.match(installHelp({ secure: false, agent: 'Android' }), /web app.*https:\/\/galaxy\.firestar\.link/)
assert.match(installHelp({ secure: true, agent: 'Android' }), /Install app/)
assert.match(androidInstallHelp(), /download the Android app.*locally|locally.*download the Android app/i)
assert.match(installHelp({ secure: true, agent: 'Chrome' }), /Install app/)
const events = new Map()
let modeListener
const mode = { matches: false, addEventListener: (_, fn) => { modeListener = fn }, removeEventListener: () => {} }
globalThis.window = { isSecureContext: true, matchMedia: () => mode,
  addEventListener: (name, fn) => events.set(name, fn), removeEventListener: (name) => events.delete(name) }
Object.defineProperty(globalThis, 'navigator', { configurable: true, value: { userAgent: 'Chrome' } })
const state = { ...InstallApp.data() }
InstallApp.mounted.call(state)
assert.equal(state.installed, false)
let prevented = 0, prompted = 0
events.get('beforeinstallprompt')({ preventDefault: () => prevented++, prompt: async () => prompted++, userChoice: Promise.resolve({ outcome: 'dismissed' }) })
assert.equal(prevented, 1)
await InstallApp.methods.installWeb.call(state)
assert.equal(prompted, 1)
assert.equal(state.prompt, null)
assert.equal(state.installed, false)
await InstallApp.methods.installWeb.call(state)
assert.equal(state.message, '')
assert.match(InstallApp.template, /v-else-if="url" class="gx-btn" :href="url"/)
window.location = { hostname: 'galaxy.firestar.link' }
assert.equal(InstallApp.computed.onPublicGalaxy(), true)
events.get('appinstalled')()
assert.equal(state.installed, true)
mode.matches = true; modeListener()
assert.equal(state.installed, true)
InstallApp.beforeUnmount.call(state)
assert.equal(events.size, 0)
console.log('install app prompt and platform guidance passed')

// Browser can offer installation before the tool is mounted.
const early = {preventDefault(){}, prompt: async () => prompted++, userChoice: Promise.resolve({outcome:'dismissed'})}
rememberInstallPrompt(early)
const late = {...InstallApp.data()}
InstallApp.mounted.call(late)
assert.equal(late.prompt, early)
await InstallApp.methods.installWeb.call(late)
assert.equal(prompted, 2)
InstallApp.beforeUnmount.call(late)

// Android offers the local APK; tunnel pages explain how to connect locally.
navigator.userAgent = 'Android'
let apk
globalThis.location = { protocol: 'http:', assign: value => { apk = value } }
let nativeUpdates = 0
window.StarPilotApp = { installUpdate: () => nativeUpdates++ }
const nativeUpdate = { ...InstallApp.data(), updateAvailable: true }
InstallApp.methods.installAndroid.call(nativeUpdate)
assert.equal(nativeUpdates, 1)
assert.equal(apk, undefined, 'Native updates never hand the APK to a browser')
delete window.StarPilotApp
const android = { ...InstallApp.data() }
InstallApp.methods.installAndroid.call(android)
assert.equal(apk, './app.apk')
assert.match(InstallApp.template, /Install Galaxy/)
assert.match(InstallApp.template, /Install as offline app \(Android\)/)
assert.match(InstallApp.template, /Update offline app \(Android\)/)
assert.match(InstallApp.template, /android && !ios/)
location.protocol = 'https:'
InstallApp.methods.installAndroid.call(android)
assert.equal(android.help, true)
assert.match(android.message, /Android app.*locally|locally.*Android app/i)

// Choosing the web app on Android always keeps web-install guidance.
const webHelp = InstallApp.methods.installHelp.call(android)
assert.match(webHelp, /Install app/)
assert.doesNotMatch(webHelp, /download the Android app/i)

// iOS never sees the Android offline install; the web app install remains.
assert.equal(isIosDevice('iPhone'), true)
assert.equal(isIosDevice('iPad'), true)
assert.equal(isIosDevice('Android'), false)
assert.equal(isAndroidDevice('Android'), true)
assert.equal(isAndroidDevice('iPhone'), false)
navigator.userAgent = 'iPhone'
const ios = { ...InstallApp.data() }
assert.equal(ios.android, false)
assert.equal(ios.ios, true)
assert.match(InstallApp.methods.installHelp.call(ios), /Share.*Add to Home Screen/)
assert.match(InstallApp.template, /v-if="android && !ios/)
