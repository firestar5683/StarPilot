import assert from "node:assert/strict"
import fs from "node:fs"
const text=fs.readFileSync(new URL("../web/js/route-leave.js", import.meta.url),"utf8")
const {createRouteLeave}=await import("data:text/javascript;base64,"+Buffer.from(text).toString("base64"))
let entries=[{path:"/",index:0}],at=0,shown="/",pending,queue=[]
const port={read:()=>entries[at],show:()=>{shown=entries[at].path},
 push:(path,index)=>{entries=entries.slice(0,at+1);entries.push({path,index});at++},
 replace:(path,index)=>{entries[at]={path,index}},
 go:delta=>queue.push(()=>{at+=delta;nav.changed();queue.push(()=>nav.changed())})}
const nav=createRouteLeave(port)
const flush=()=>{while(queue.length)queue.shift()()}
nav.navigate("/tools");nav.navigate("/theme_maker");nav.setGuard(callback=>{pending=callback})
port.go(-1);flush();assert.equal(shown,"/theme_maker");assert.equal(port.read().path,"/theme_maker")
nav.navigate("/settings");pending();assert.equal(shown,"/settings")
nav.setGuard(callback=>{pending=callback})
port.push("/logs",port.read().index);nav.changed();queue.push(()=>nav.changed());flush()
assert.equal(port.read().path,"/settings");assert.equal(shown,"/settings")
pending();flush();assert.equal(shown,"/logs")
port.go(-1);flush();assert.equal(shown,"/logs");pending();flush();assert.equal(shown,"/settings")
port.go(1);flush();assert.equal(shown,"/settings");pending();flush();assert.equal(shown,"/logs")
console.log("async Back/Forward, retained-state hash and canceled-then-new navigation passed")
