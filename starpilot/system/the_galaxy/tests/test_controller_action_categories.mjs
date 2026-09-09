// Run with node; optional source-derived full option fixture from browser test.
import assert from 'node:assert/strict'
import fs from 'node:fs'
import { actionCategory, actionCategories, filterActions } from '../assets/components/tools/controller_action_picker.js'

const layout = JSON.parse(fs.readFileSync(new URL('../../../common/assets/device_settings_layout.json', import.meta.url)))
const mapping = new Map(layout.flatMap(s => s.params.map(p => [p.key, s.name])))
const options = process.argv[2] ? JSON.parse(fs.readFileSync(process.argv[2])) :
  [...mapping].map(([key, section]) => ({ key, section, label: key }))
const before = JSON.stringify(options)
for (const option of options) {
  const expected = mapping.get(option.key) ?? (option.section === 'Actions' ? 'Controller Actions' : option.section || 'Other')
  assert.equal(actionCategory(option, layout), expected, option.key)
  assert.ok(filterActions(options, option.key, '', layout).includes(option))
  if (mapping.has(option.key)) assert.equal(actionCategory({ ...option, section: 'Incorrect API label' }, layout), expected)
}
const available = new Set(options.map(o => mapping.get(o.key) ?? (o.section === 'Actions' ? 'Controller Actions' : o.section || 'Other')))
const expectedOrder = [...new Set([...layout.map(s => s.name).filter(n => available.has(n)), ...available])]
assert.deepEqual(actionCategories(options, layout), expectedOrder)
const collected = expectedOrder.flatMap(c => filterActions(options, '', c, layout))
assert.equal(collected.length, options.length)
assert.equal(new Set(collected.map(o => o.key)).size, options.length)
assert.deepEqual(new Set(collected), new Set(options))
assert.deepEqual(filterActions(options, '', '', layout), options)
assert.equal(JSON.stringify(options), before, 'Presentation must not mutate catalogue')
assert.equal(actionCategory({ key: 'RemapCancelToDistance' }, layout), 'Wheel Controls')
assert.equal(actionCategory({ key: 'SLCMapboxFiller' }, layout), 'Visual (Display & UI)')
assert.equal(actionCategory({ key: 'unknown', section: 'Future section' }, layout), 'Future section')
assert.equal(actionCategory({ key: 'unknown' }, layout), 'Other')
assert.deepEqual(filterActions(options), options, 'Missing layout must retain every eligible option')
assert.deepEqual(actionCategories([], layout), [])
assert.deepEqual(actionCategories([{ key: 'virtual', section: 'Actions' }, { key: 'command', section: 'Controller Actions' }], layout), ['Controller Actions'])
console.log(JSON.stringify({ result: 'PASS', options: options.length, categories: expectedOrder, duplicateOwnership: 'PASS', mutation: 'NONE' }, null, 2))
