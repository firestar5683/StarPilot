import assert from 'node:assert/strict'
import { retireLegacyPhone } from '../web/js/connection-migration.js'

const oldKeys = ['galaxy-companion-link', 'galaxy-companion-ble-device', 'galaxy-connection-preference', 'galaxy-offline', 'galaxy-home-screen-added']
const storage = new Map([...oldKeys, 'galaxy-auth', 'map-downloads', 'unrelated'].map(key => [key, 'keep']))
const fetch = () => { throw new Error('migration must not make LAN requests') }
let updates = 0
const target = {
  location: { href: 'https://galaxy.example/device/#/galaxy' },
  localStorage: { removeItem: key => storage.delete(key) },
  fetch,
  navigator: { serviceWorker: { getRegistration: async url => ({
    active: { scriptURL: url }, update: async () => { updates++ },
  }) } },
}
await retireLegacyPhone(target)
assert.deepEqual([...storage.keys()], ['galaxy-auth', 'map-downloads', 'unrelated'])
assert.equal(target.fetch, fetch)
assert.equal(updates, 1)
target.navigator.serviceWorker.getRegistration = async () => ({
  active: { scriptURL: 'https://galaxy.example/another-worker.js' },
  update: async () => { throw new Error('unrelated worker touched') },
})
await retireLegacyPhone(target)
target.localStorage.removeItem = () => { throw new Error('storage denied') }
target.navigator.serviceWorker.getRegistration = async () => { throw new Error('worker denied') }
await retireLegacyPhone(target)
await retireLegacyPhone({})
