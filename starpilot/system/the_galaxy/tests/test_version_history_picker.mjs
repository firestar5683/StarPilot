import fs from 'node:fs'
import vm from 'node:vm'
import assert from 'node:assert/strict'
import test from 'node:test'
const root = process.argv[2] || new URL('../../../../', import.meta.url).pathname
const file = root + '/starpilot/system/the_galaxy/assets/mobile/js/components/VersionHistoryPicker.js'
const context = vm.createContext({Date, Map, Set})
if (fs.existsSync(file)) vm.runInContext(fs.readFileSync(file, 'utf8').replace(/export /g, '') + '\nglobalThis.picker = VersionHistoryPicker; globalThis.group = groupVersionHistory; globalThis.title = versionTitle; globalThis.releases = releaseVersions;', context)
const row = (sha, date, version = '6.7.7') => ({sha: sha.repeat(40), date, version, subject: 'Correct launch behavior'})
test('history groups every loaded local day and merges nonadjacent page entries', () => {
  assert.equal(typeof context.group, 'function', 'date-grouped history is available')
  const groups = context.group([row('a', '2026-09-11T12:00:00'), row('b', '2026-09-10T13:00:00'), row('c', '2026-09-11T09:00:00'), row('d', '2024-01-02T10:00:00')])
  assert.deepEqual(Array.from(groups, g => g.key), ['2026-09-11', '2026-09-10', '2024-01-02'])
  assert.deepEqual(Array.from(groups[0].commits, c => c.sha), ['a'.repeat(40), 'c'.repeat(40)])
})
test('StarPilot uses version numbers with time to distinguish builds and never a hash headline', () => {
  assert.equal(typeof context.title, 'function', 'friendly version labels are available')
  const a = context.title(row('a', '2026-09-11T12:00:00'), true)
  const b = context.title(row('b', '2026-09-11T13:00:00'), true)
  assert.match(a, /6\.7\.7/)
  assert.notEqual(a, b)
  assert.ok(!a.includes('aaaaaaaaaa'))
  assert.match(context.title(row('c', '2026-09-11T12:00:00', ''), true), /Unnumbered version/)
  assert.match(context.title(row('a', '2026-09-11T12:00:00'), false), /Correct launch behavior/)
})
test('bad dates remain selectable in an unknown-date day without hiding history', () => {
  assert.equal(typeof context.group, 'function')
  const groups = context.group([row('a', 'not a date'), row('b', '2026-09-10T12:00:00')])
  assert.equal(groups.length, 2)
  assert.equal(groups[1].label, 'Unknown date')
  assert.equal(groups[1].commits[0].sha, 'a'.repeat(40))
})
test('newly appended days stay collapsed while the current day keeps its state', () => {
  assert.ok(context.picker, 'history picker is available')
  const instance = {...context.picker.data(), groups: [{key:'2026-09-11'}, {key:'2026-09-10'}]}
  context.picker.methods.syncDays.call(instance)
  assert.deepEqual({...instance.expanded}, {'2026-09-11':true, '2026-09-10':false})
  instance.expanded['2026-09-10'] = true
  instance.groups.push({key:'2026-09-09'})
  context.picker.methods.syncDays.call(instance)
  assert.equal(instance.expanded['2026-09-10'], true)
  assert.equal(instance.expanded['2026-09-09'], false)
})
test('selection emits only an available exact SHA and disabled selection emits nothing', () => {
  assert.ok(context.picker)
  const calls = []
  const instance = {commits: [row('a', '2026-09-11')], disabled:false, close:()=>{}, $emit:(...args)=>calls.push(args)}
  context.picker.methods.select.call(instance, 'b'.repeat(40))
  assert.equal(calls.length, 0)
  context.picker.methods.select.call(instance, 'a'.repeat(40))
  assert.equal(calls[0][0], 'change')
  assert.equal(calls[0][1].target.value, 'a'.repeat(40))
  instance.disabled = true
  context.picker.methods.select.call(instance, 'a'.repeat(40))
  assert.equal(calls.length, 1)
})

test('release numbers appear once across pages, retaining the first newest build and numeric ordering', () => {
 const rows=[row('a','2026-09-11','6.7.7'),row('b','2026-09-10','6.7.7'),row('c','2026-09-09','6.7.6'),row('d','2026-09-08','6.7.7')]
 assert.deepEqual(Array.from(context.releases(rows),r=>r.sha),['a'.repeat(40),'c'.repeat(40)])
 assert.deepEqual(Array.from(context.releases([row('a','2026-09-11','6.9.0'),row('b','2026-09-10','6.10.0')]),r=>r.version),['6.10.0','6.9.0'])
 assert.equal(context.releases([row('a','2026-09-11',null),row('b','2026-09-10',null)]).length,1)
 assert.equal(context.group(rows).reduce((n,g)=>n+g.commits.length,0),4)
})

test('release picker cannot emit a hidden duplicate build', () => {
 const calls=[]
 const instance={releaseBranch:true,commits:[row('a','2026-09-11'),row('b','2026-09-10')],disabled:false,close:()=>{},$emit:(...args)=>calls.push(args)}
 context.picker.methods.select.call(instance,'b'.repeat(40));assert.equal(calls.length,0)
 context.picker.methods.select.call(instance,'a'.repeat(40));assert.equal(calls[0][1].target.value,'a'.repeat(40))
})
