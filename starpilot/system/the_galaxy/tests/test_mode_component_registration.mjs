import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const source=readFileSync(new URL('../assets/mobile/js/components/LongitudinalMode.js',import.meta.url),'utf8').replace(/^import .*$/gm,'');
const stubs='const GalaxySelect={name:"GalaxySelect"},SettingTree={name:"SettingTree"};';
const {LongitudinalMode:c}=await import('data:text/javascript;base64,'+Buffer.from(stubs+source).toString('base64'));
assert.equal(c.components.GalaxySelect.name,'GalaxySelect');assert.equal(c.components.SettingTree.name,'SettingTree');
console.log('Standalone mode component dependencies registered');
