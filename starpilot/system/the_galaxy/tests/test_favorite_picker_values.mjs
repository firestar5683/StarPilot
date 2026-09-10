import assert from 'node:assert/strict'
import fs from 'node:fs'
import vm from 'node:vm'
import test from 'node:test'
const source = fs.readFileSync(new URL('../assets/mobile/js/components/FavoritesEditor.js', import.meta.url), 'utf8')
const speed = '__starpilot_controller_action__:set_speed'
function setup(api = {}) {
  const context = vm.createContext({api, showSnackbar() {}, openControllerActionPicker() {}})
  vm.runInContext(source.replace(/^import .*$/gm, '').replace('export const FavoritesEditor =', 'globalThis.component ='), context)
  const component = context.component
  const instance = {...component.data(), ...component.methods}
  for (const [name, getter] of Object.entries(component.computed)) Object.defineProperty(instance, name, {get: getter})
  return instance
}
test('loading and unrelated saves retain speed, assignment and visibility', async () => {
  const slot = {key: speed, label: 'Set Speed To', value: 42, enabled: true, show_onroad: true}
  let sent
  const instance = setup({getFavoritesSlots: async () => ({slots:[slot],options:[{key:speed,label:'Set Speed To',action:'controller'}],is_metric:true}),
    saveFavoritesSlots: async slots => { sent = slots; return {slots} }})
  await instance.load()
  assert.equal(instance.controlLabel(instance.slots[0]), 'Set Speed To 42 km/h')
  instance.updateSlot(1, {key: 'NewToggle', enabled:true})
  await new Promise(resolve => setTimeout(resolve,0))
  assert.deepEqual(JSON.parse(JSON.stringify(sent[0])),slot)
  assert.equal(instance.slots[0].value,42)
})
test('save failure restores accepted assignment and saved speed', async () => {
  const slot = {key:speed,label:'Set Speed To',value:42,enabled:true,show_onroad:true}
  const instance = setup({getFavoritesSlots:async()=>({slots:[slot]}),saveFavoritesSlots:async()=>{throw Error('No connection')}})
  await instance.load()
  instance.updateSlot(0,{value:55})
  await new Promise(resolve=>setTimeout(resolve,0))
  assert.equal(instance.slots[0].value,42)
  assert.equal(instance.slots[0].enabled,true)
})
test('activation forwards the chosen slot value', async () => {
  const sent=[]
  const instance=setup({activateFavoriteAction:async(...args)=>{sent.push(args);return {}}})
  await instance.runAction(speed,42)
  await instance.runAction(speed,55)
  assert.deepEqual(sent,[[speed,42],[speed,55]])
})
