import assert from 'node:assert/strict'
import fs from 'node:fs'
import vm from 'node:vm'
import test from 'node:test'
import { api } from '../assets/mobile/js/api.js'
import { vehicleSpeedUnit } from '../assets/mobile/js/params.js'

const source = fs.readFileSync(new URL('../assets/components/tools/device_settings.js', import.meta.url), 'utf8')
const extract = (start, end) => source.slice(source.indexOf(start), source.indexOf(end, source.indexOf(start)))
const speed = '__starpilot_controller_action__:set_speed'
const savedSpeed = {enabled: true, show_onroad: true, key: speed, label: 'Set Speed To', value: 42}

function setup() {
  const requests = [], messages = []
  const snapshot = {locked: false, action_expires_at: 123, values: {ExperimentalMode: false, ConditionalExperimental: false, ConditionalChill: false}}
  const state = {favoriteSlots: [structuredClone(savedSpeed)], favoriteFilters: ['', '', ''], favoriteOptions: [
    {key: speed, label: 'Set Speed To', action: 'controller', value_type: 'speed'},
    {key: 'FeatureToggle', label: 'Feature Toggle'},
  ], favoriteValues: {}, values: {}}
  const fetch = async (url, init = {}) => {
    requests.push({url, init})
    return {ok: true, json: async () => url === '/api/longitudinal_mode' ? snapshot : {slots: state.favoriteSlots}}
  }
  const context = vm.createContext({state, api, fetch, performance, Number, messages,
    FAVORITE_OPTION_COLLATOR: new Intl.Collator(), FAVORITE_ACTION_PREFIX: '__starpilot_favorite_action__:',
    showParamSnackbar: (...args) => messages.push(args), scheduleSyncInputs() {},
    window: {setTimeout() {}, location: {pathname: '/device_settings'}},
    vehicleSpeedUnit, html: (strings, ...values) => ({strings, values}),
  })
  vm.runInContext(extract('function defaultFavoriteSlots()', 'function populateFavoriteSelect(') +
    extract('async function saveFavoriteSlots(', 'function updateFavoriteFilter(') +
    extract('async function activateFavoriteAction(', 'function stepPrecision(') +
    extract('function renderFavoriteSlotsPanel()', 'function renderSettingRow('), context)
  return {context, state, requests, messages, snapshot, fetch}
}

test('classic unrelated saves preserve configured speed and other slot metadata', async () => {
  const {context, state, requests} = setup()
  state.favoriteSlots[0].futureMetadata = {unit: 'current'}
  const slots = context.normalizeFavoriteSlots(state.favoriteSlots)
  slots[1] = {enabled: false, show_onroad: true, key: 'FeatureToggle', label: 'Feature Toggle'}
  await context.saveFavoriteSlots(slots)
  const sent = JSON.parse(requests[0].init.body).slots
  assert.equal(sent[0].value, 42)
  assert.deepEqual(sent[0].futureMetadata, {unit: 'current'})
  assert.equal(sent[1].show_onroad, true)
})

test('classic keeps configured speed selectable but cannot create one without its required value', () => {
  const {context, state} = setup()
  assert(context.filteredFavoriteOptions(0).some(option => option.key === speed))
  assert(!context.filteredFavoriteOptions(1).some(option => option.key === speed))
  context.updateFavoriteSlot(1, {key: speed})
  assert.equal(state.favoriteSlots[1]?.key ?? null, null)
})

test('classic Set Speed activation sends the saved speed', async () => {
  const {context, requests, fetch} = setup()
  const previous = globalThis.fetch
  try {
    globalThis.fetch = fetch
    await context.activateFavoriteAction(speed, 42)
    assert.deepEqual(JSON.parse(requests[0].init.body), {key: speed, value: 42})
  } finally { globalThis.fetch = previous }
})

test('classic rendered speed buttons show current units and dispatch each slot value', async () => {
  const {context, state, requests, fetch} = setup()
  state.favoriteSlots.push({...savedSpeed, value: 55})
  const buttons = []
  function renderText(node) {
    if (Array.isArray(node)) return node.map(renderText).join('')
    if (node?.strings) {
      return node.strings.map((part, index) => {
        const value = node.values[index]
        if (part.includes('ds-favorite-action-card') && typeof value === 'function') buttons.push(value)
        return part + (typeof value === 'function' ? '' : renderText(value))
      }).join('')
    }
    return node == null ? '' : String(node)
  }
  for (const [metric, unit] of [[false, 'mph'], [true, 'km/h']]) {
    state.values.IsMetric = metric
    buttons.length = 0
    const output = renderText(context.renderFavoriteSlotsPanel())
    assert(output.includes(`Set Speed To 42 ${unit}`))
    assert(output.includes(`Set Speed To 55 ${unit}`))
    assert.equal(buttons.length, 2)
  }
  const previous = globalThis.fetch
  try {
    globalThis.fetch = fetch
    for (const click of buttons) await click()
    assert.deepEqual(requests.map(request => JSON.parse(request.init.body).value), [42, 55])
  } finally { globalThis.fetch = previous }
})
