import assert from 'node:assert/strict'
import { installHelp, InstallApp } from '../web/js/install-app.js'
assert.match(installHelp({ secure: true, agent: 'iPhone' }), /Share.*Add to Home Screen/)
assert.match(installHelp({ secure: false, agent: 'Android' }), /https:\/\/galaxy.firestar.link/)
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
await InstallApp.methods.install.call(state)
assert.equal(prompted, 1)
assert.equal(state.prompt, null)
assert.equal(state.installed, false)
await InstallApp.methods.install.call(state)
assert.match(state.message, /Install app/)
events.get('appinstalled')()
assert.equal(state.installed, true)
mode.matches = true; modeListener()
assert.equal(state.installed, true)
InstallApp.beforeUnmount.call(state)
assert.equal(events.size, 0)
console.log('install app prompt and platform guidance passed')
