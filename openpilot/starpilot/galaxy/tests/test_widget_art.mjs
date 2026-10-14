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
const flush=async()=>{for(let i=0;i<20;i++)await Promise.resolve()}
function fixture() {
  const updates=[],requests=[],timers=new Map(),revoked=[];let next=0,url=0,unauthorized=0
  const options={art:true,publish:value=>updates.push(value),unauthorized:()=>unauthorized++,
    fetcher:(address,options)=>new Promise(resolve=>requests.push({address,options,resolve})),
    later:(fn,delay)=>{timers.set(++next,{fn,delay});return next},cancelTimer:id=>timers.delete(id),
    urls:{createObjectURL:()=>`blob:${++url}`,revokeObjectURL:value=>revoked.push(value)}}
  const feed=new LayoutPreviewFeed(options)
  const tick=()=>{const [id,{fn}]=[...timers].at(-1);timers.delete(id);fn()}
  const answer=async(index,status=200,blob=image())=>{requests[index].resolve({status,ok:status===200,
    headers:{get:()=> 'image/png'},json:async()=>null,blob:async()=>blob});await flush()}
  return {feed,options,updates,requests,timers,revoked,tick,answer,get unauthorized(){return unauthorized}}
}
const {feed,updates,requests,timers,revoked,tick,answer}=fixture()
const document={version:6,layouts:{compact:{}},palette:{text:'#FFFFFFFF'}}
feed.start();feed.update(document,'compact','engaged');tick()
assert.equal(requests[0].address,'./api/ui/layout/preview');assert.equal(requests[0].options.credentials,'same-origin')
assert.equal(JSON.parse(requests[0].options.body).art,true)
await answer(0);assert.deepEqual(updates.at(-1).sprites,meta)
feed.update(document,'compact','engaged',true);assert.equal(feed.currentUrl,'blob:1','Drag retains mounted native art')
assert.equal(feed.pending,null,'Drag queues no native render');assert.equal(feed.timer,null,'Drag schedules no request timer')
assert.equal(requests.length,1,'Entering drag sends no native request')
feed.update(document,'compact','cem_stop_light');assert.equal(feed.currentUrl,'blob:1','Scene change retains art until its replacement arrives')
tick();feed.update(document,'large','cem_curve');assert.equal(requests[1].options.signal.aborted,true)
tick();await answer(1);assert.equal(requests.length,3);await answer(2);assert.equal(updates.at(-1).url,'blob:2')
feed.update(document,'compact','engaged')
assert.equal(feed.currentUrl,'blob:1','Returning to a profile restores its artwork immediately')
assert.equal(updates.at(-1).status,'ready');assert.equal(timers.size,0,'Unchanged cached artwork needs no request')
assert.deepEqual(revoked,[],'Switching profiles keeps both mounted sheets alive')
feed.update(document,'large','braking');tick();await answer(3,503)
assert.equal(feed.currentUrl,'blob:2','A transient failure retains visible artwork')
assert.equal(updates.at(-1).status,'updating','One transient failure does not flash the unavailable message')
assert.equal([...timers.values()][0].delay,600,'A transient failure retries promptly')
tick();tick();await answer(4,503)
assert.equal(updates.at(-1).status,'unavailable','Persistent failures still report an outage')
tick()
assert.equal(updates.findLast(update=>update.status)?.status,'unavailable','Retry does not flicker the outage message')
tick();await answer(5)
assert.equal(updates.at(-1).status,'ready');assert.equal(feed.currentUrl,'blob:3')
assert.deepEqual(revoked,['blob:2'],'Only a successfully replaced sheet is released')
feed.pause();assert.equal(feed.active,false);assert.equal(feed.currentUrl,'blob:3')
feed.start();feed.update(document,'large','braking')
assert.equal(feed.currentUrl,'blob:3');assert.equal(timers.size,0,'Returning to a profile reuses matching artwork')
const edited={...document,palette:{text:'#FF0000FF'}}
feed.update(edited,'large','braking');tick()
assert.equal(feed.currentUrl,'blob:3','Draft edits keep artwork while rendering the new colors')
feed.pause();feed.start();feed.update(document,'compact','engaged');await answer(6)
assert.equal(feed.currentUrl,'blob:1','A late response after switching views cannot replace cached art')
assert.equal(updates.at(-1).status,'ready')
feed.stop();assert.deepEqual(revoked,['blob:2','blob:1','blob:3'])
assert.equal(feed.artCache.size,0);assert.equal(updates.at(-1).url,null)

for(const status of [429,503]){
  const cold=fixture();cold.feed.start();cold.feed.update(document,'compact','engaged');cold.tick();await cold.answer(0,status)
  assert.equal(cold.updates.at(-1).status,'updating','Cold-start transient failures also retry without flashing a warning')
  cold.tick();cold.tick();await cold.answer(1)
  assert.equal(cold.updates.some(update=>update.status==='unavailable'),false)
  assert.equal(cold.updates.at(-1).status,'ready');cold.feed.stop()
}
for(const status of [401,403]){
  const denied=fixture();denied.feed.start();denied.feed.update(document,'compact','engaged');denied.tick();await denied.answer(0)
  denied.feed.update(edited,'compact','engaged');denied.tick();await denied.answer(1,status)
  assert.equal(denied.feed.currentUrl,null,'Access denial releases retained artwork immediately')
  assert.equal(denied.feed.artCache.size,0)
  if(status===401){assert.equal(denied.unauthorized,1);assert.equal(denied.feed.active,false)}
  else assert.equal(denied.updates.at(-1).status,'unavailable')
  denied.feed.stop()
}

const stalled=fixture();stalled.feed.start();stalled.feed.update(document,'compact','engaged');stalled.tick();await stalled.answer(0)
stalled.feed.update(edited,'compact','engaged');stalled.tick();stalled.tick();await flush()
assert.equal(stalled.requests[1].options.signal.aborted,true)
assert.equal(stalled.feed.currentUrl,'blob:1','A timed-out refresh retains artwork')
assert.equal(stalled.updates.at(-1).status,'updating')
stalled.tick();stalled.tick();await stalled.answer(2)
assert.equal(stalled.updates.at(-1).status,'ready','A hung renderer can recover without discarding the last sheet')
stalled.feed.update(document,'compact','engaged');stalled.tick();await stalled.answer(3,200,new Blob(['invalid PNG']))
assert.equal(stalled.feed.currentUrl,'blob:2','Malformed replacement art cannot displace the last good sheet')
stalled.feed.stop()

// Exercise the real page watchers when changing preview modes and parked authority.
const page=OnroadLayoutPage.setup({mode:'local',projection:false,unauthorized(){}})
Object.assign(page.backdropFeed,{start(){},update(){},stop(){}})
const pageFeed=fixture()
Object.assign(page.artFeed,pageFeed.options,{publish:update=>{Object.assign(page.state.art,update);pageFeed.updates.push(update)}})
page.state.data={editable:true,revision:1,metadata:{profiles:{large:{widgets:{conditional_mode:{}}},compact:{widgets:{conditional_mode:{}}}}}}
page.state.draft=document
pageFeed.tick();await pageFeed.answer(0)
const artUrl=page.state.art.url
assert(artUrl)
page.state.data.editable=false
assert.equal(page.artFeed.active,false);assert.equal(page.state.art.url,null,'Parked authority changes clear artwork')
page.artFeed.stop()
assert.equal(OnroadLayoutPage.methods.runtimeWidget.call({profile:{runtimePreviewWidgets:['conditional_mode']}},'conditional_mode'),true)
assert.equal(OnroadLayoutPage.methods.runtimeWidget.call({profile:{}},'conditional_mode'),false)
assert.match(LayoutWidgetPreview.template,/data-preview-source="runtime"/)
assert.match(LayoutWidgetPreview.template,/data-preview-source="placeholder"/)
assert.doesNotMatch(LayoutWidgetPreview.template,/scene === 'experimental' \? 'E' : 'C'/)
assert.doesNotMatch(LayoutWidgetPreview.template,/M38 78 Q96 107 154 78/)
console.log('Canonical widget art: metadata, races, retained refreshes, profile/mode switches, retries, auth and cleanup passed')
