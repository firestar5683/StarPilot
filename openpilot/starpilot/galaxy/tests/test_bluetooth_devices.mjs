import assert from 'node:assert/strict'
import { test } from 'node:test'
import { BluetoothDeviceList, hasBluetoothName } from '../web/js/bluetooth-devices.js'

test('hide address placeholders in discovery formats, retaining real names with model suffixes', () => {
  for (const name of ['', '  ', 'AA:bb:CC:dd:EE:ff', 'aa-bb-cc-dd-ee-ff', 'AABBCCDDEEFF',
    'aabb.ccdd.eeff', 'AA_BB_CC_DD_EE_FF', 'dev_AA_BB_CC_DD_EE_FF',
    '[AA:BB:CC:DD:EE:FF]', '(AA:BB:CC:DD:EE:FF)', '[dev_AA_BB_CC_DD_EE_FF]', ' AA BB CC DD EE FF ']) {
    assert.equal(hasBluetoothName({name}), false, name)
  }
  for (const name of ['IONIQ 6', 'AndroidAuto-8b83', 'Bose QC35 II', 'Tile A1:B2', 'Headphones AA:BB:CC:DD:EE:FF']) {
    assert.equal(hasBluetoothName({name}), true, name)
  }
  assert.equal(hasBluetoothName({name: null}), false)
})

test('stable rows follow addresses with live rename, flags, disappearance and discovery', () => {
  const list = new BluetoothDeviceList()
  const car = {address:'AA:BB:CC:DD:EE:01', name:' IONIQ 6 ', connected:false}
  const adapter = {address:'AA:BB:CC:DD:EE:02', name:'AndroidAuto-8b83'}
  const unnamed = {address:'AA:BB:CC:DD:EE:03', name:'AA-BB-CC-DD-EE-03'}
  assert.deepEqual(list.update([car, adapter, unnamed]).map(d => d.name), ['IONIQ 6', 'AndroidAuto-8b83'])
  assert.equal(car.name, ' IONIQ 6 ')
  assert.deepEqual(list.update([adapter]).map(d => d.address), [adapter.address])
  const current = list.update([adapter, {...car, name:'My IONIQ', connected:true}, {...unnamed, name:'Controller'}])
  assert.deepEqual(current.map(d => d.name), ['My IONIQ', 'AndroidAuto-8b83', 'Controller'])
  assert.equal(current[0].connected, true)
  assert.deepEqual(list.update([{...car, name:car.address}]), [])
  list.reset()
  assert.deepEqual(list.update([adapter, car]).map(d => d.address), [adapter.address, car.address])
})
