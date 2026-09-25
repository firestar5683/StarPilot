import assert from 'node:assert/strict'
import {deflateSync} from 'node:zlib'
import {LayoutPreviewFeed} from '../web/js/layout-preview.js'
import {widgetArtMetadata} from '../web/js/widget-art.js'
import {LayoutWidgetPreview, OnroadLayoutPage} from '../web/js/onroad-layout.js'
function chunk(kind, bytes) {
  const body=Buffer.concat([Buffer.from(kind),bytes]);let crc=0xffffffff
  for(const byte of body){crc^=byte;for(let i=0;i<8;i++)crc=(crc>>>1)^(crc&1?0xedb88320:0)}
  const size=Buffer.alloc(4),sum=Buffer.alloc(4);size.writeUInt32BE(bytes.length);sum.writeUInt32BE((crc^0xffffffff)>>>0)
  return Buffer.concat([size,body,sum])
}
const meta={version:1,width:2,height:1,sprites:{conditional_mode:{x:0,y:0,width:2,height:1}}}
function image(metadata=meta){
  const header=Buffer.alloc(13);header.writeUInt32BE(2);header.writeUInt32BE(1,4);header[8]=8;header[9]=6
  return new Blob([Buffer.concat([Buffer.from([137,80,78,71,13,10,26,10]),chunk('IHDR',header),
    chunk('tEXt',Buffer.from('starpilot-widget-art\0'+JSON.stringify(metadata))),
    chunk('IDAT',deflateSync(Buffer.from([0,255,255,255,255,0,0,0,0]))),chunk('IEND',Buffer.alloc(0))])],{type:'image/png'})
}
assert.deepEqual(await widgetArtMetadata(image()),meta)
for(const bad of [{...meta,width:3},{...meta,sprites:{conditional_mode:{x:1,y:0,width:2,height:1}}},
 {...meta,sprites:{conditional_mode:{x:0,y:0,width:NaN,height:1}}},
 {...meta,sprites:{conditional_mode:{x:0,y:0,width:2,height:1,offsetX:1}}}])await assert.rejects(widgetArtMetadata(image(bad)))
await assert.rejects(widgetArtMetadata(new Blob(['not PNG'])))
const updates=[],requests=[],timers=new Map(),revoked=[];let next=0,url=0
const feed=new LayoutPreviewFeed({art:true,publish:value=>updates.push(value),
 fetcher:(address,options)=>new Promise(resolve=>requests.push({address,options,resolve})),
 later:fn=>{timers.set(++next,fn);return next},cancelTimer:id=>timers.delete(id),
 urls:{createObjectURL:()=>`blob:${++url}`,revokeObjectURL:value=>revoked.push(value)}})
const flush=async()=>{for(let i=0;i<20;i++)await Promise.resolve()}
const tick=()=>{const [id,fn]=[...timers].at(-1);timers.delete(id);fn()}
const answer=async(index,status=200)=>{requests[index].resolve({status,ok:status===200,
 headers:{get:()=> 'image/png'},blob:async()=>image()});await flush()}
const document={version:6,layouts:{compact:{}},palette:{text:'#FFFFFFFF'}}
feed.start();feed.update(document,'compact','engaged');tick()
assert.equal(requests[0].address,'./api/ui/layout/preview');assert.equal(requests[0].options.credentials,'same-origin')
assert.equal(JSON.parse(requests[0].options.body).art,true)
await answer(0);assert.deepEqual(updates.at(-1).sprites,meta)
feed.update(document,'compact','engaged',true);assert.equal(feed.currentUrl,'blob:1','Drag retains mounted native art')
assert.equal(feed.pending,null,'Drag queues no native render');assert.equal(feed.timer,null,'Drag schedules no request timer')
assert.equal(requests.length,1,'Entering drag sends no native request')
feed.update(document,'compact','cem_stop_light');assert.equal(feed.currentUrl,null,'Scene change clears stale CEM art')
tick();feed.update(document,'large','cem_curve');assert.equal(requests[1].options.signal.aborted,true)
tick();await answer(1);assert.equal(requests.length,3);await answer(2);assert.equal(updates.at(-1).url,'blob:2')
feed.update(document,'large','braking');tick();await answer(3,503);assert.equal(feed.currentUrl,null)
assert.equal(updates.at(-1).status,'unavailable');feed.stop();assert(revoked.includes('blob:1')&&revoked.includes('blob:2'))
assert.equal(OnroadLayoutPage.methods.runtimeWidget.call({profile:{runtimePreviewWidgets:['conditional_mode']}},'conditional_mode'),true)
assert.equal(OnroadLayoutPage.methods.runtimeWidget.call({profile:{}},'conditional_mode'),false)
assert.match(LayoutWidgetPreview.template,/data-preview-source="runtime"/)
assert.match(LayoutWidgetPreview.template,/data-preview-source="placeholder"/)
assert.doesNotMatch(LayoutWidgetPreview.template,/scene === 'experimental' \? 'E' : 'C'/)
assert.doesNotMatch(LayoutWidgetPreview.template,/M38 78 Q96 107 154 78/)
console.log('Canonical widget art: metadata bounds, authenticated request, race, drag retention, neutral error, selection passed')
