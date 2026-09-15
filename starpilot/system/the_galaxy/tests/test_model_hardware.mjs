import assert from 'node:assert/strict';
import {readHardwareFilter,saveHardwareFilter,matchesHardware,hardwareLabel,fileSizeText} from '../assets/components/tools/model_hardware.js';
assert.equal(readHardwareFilter(),'both');
const stored=new Map();globalThis.localStorage={getItem:k=>stored.get(k),setItem:(k,v)=>stored.set(k,v)};
for (const value of ['both','gpu','comma']) {assert.equal(saveHardwareFilter(value),value);assert.equal(readHardwareFilter(),value);}
assert.equal(saveHardwareFilter('invalid'),'both');
assert.equal(matchesHardware({},'gpu'),false);assert.equal(matchesHardware({},'comma'),false);assert.equal(matchesHardware({},'both'),true);
assert.equal(matchesHardware({requiresGpu:true},'gpu'),true);assert.equal(matchesHardware({requiresGpu:false},'comma'),true);
assert.equal(hardwareLabel({}),'Hardware unknown');
assert.equal(fileSizeText({modelSize:'big'}),'Unavailable');
assert.equal(fileSizeText({fileSizeBytes:1500000000}),'1.50 GB');
assert.equal(fileSizeText({declaredSizeBytes:1200000}),'1.2 MB · declared');
assert.equal(fileSizeText({fileSizeBytes:1500000000,declaredSizeBytes:1000000000}),'1.50 GB · size mismatch');
assert.equal(fileSizeText({partial:true,downloadedBytes:1200000,declaredSizeBytes:3000000}),'Partial: 1.2 MB / 3.0 MB');
for(const size of [-1,0,NaN,Infinity,'123',true])assert.equal(fileSizeText({fileSizeBytes:size}),'Unavailable');
globalThis.localStorage={getItem:()=>{throw Error('blocked')},setItem:()=>{throw Error('blocked')}};assert.equal(readHardwareFilter(),'both');assert.equal(saveHardwareFilter('gpu'),'gpu');
console.log('PASS: hardware filtering, persistence, unknown/mismatch/partial/declared sizes');
