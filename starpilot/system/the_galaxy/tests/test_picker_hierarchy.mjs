import assert from 'node:assert/strict'
import fs from 'node:fs'
import { actionCategory, actionHierarchy, actionGroups, filterActions } from '../assets/components/tools/controller_action_picker.js'
const layout=JSON.parse(fs.readFileSync(new URL('../../../common/assets/device_settings_layout.json',import.meta.url)))
const mode={key:'ConditionalExperimental',label:'Conditional Experimental'}
const personality={key:'__starpilot_controller_action__:cycle_driving_personality',label:'Cycle Driving Personality'}
assert.deepEqual(actionHierarchy(mode,layout).map(p=>p.label),['Longitudinal control mode'])
assert.deepEqual(actionHierarchy(personality,layout).map(p=>p.label),['Driving Personalities'])
assert.equal(actionCategory(personality,layout),'Longitudinal (Speed & Following)')
const options=layout.flatMap(s=>s.params.map(p=>({...p,section:s.name}))).concat(mode,personality)
const groups=actionGroups(options,layout)
const collect=node=>node.items.concat(...node.groups.map(collect))
assert.deepEqual(collect(groups).map(o=>o.key).sort(),options.map(o=>o.key).sort())
for(const o of options) assert.ok(filterActions(options,o.key,'',layout).includes(o))
assert.ok(filterActions(options,'driving personalities','',layout).includes(personality))
assert.ok(filterActions(options,'longitudinal control mode','',layout).includes(mode))
const cyclic=[{name:'Test',params:[{key:'a',parent_key:'b'},{key:'b',parent_key:'a'}]}]
assert.ok(actionHierarchy({key:'a'},cyclic).length<=2)
assert.deepEqual(actionGroups([{key:'missing'}],[]).items,[{key:'missing'}])
console.log('Nested settings hierarchy, virtual actions, search, lossless fallback and cycle guard passed.')
