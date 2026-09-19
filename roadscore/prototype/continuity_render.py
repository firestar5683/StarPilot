"""Local review export. Same two-second retained-context splice as runtime; no gap repair."""
import json,wave
from pathlib import Path
import numpy as np
R=Path(__file__).resolve().parents[1];O=R/'results/continuity'
def read(p):
 with wave.open(str(p)) as f:
  assert f.getsampwidth()==2
  return np.frombuffer(f.readframes(f.getnframes()),'<i2').reshape(-1,f.getnchannels()).astype(np.float32)/32768,f.getframerate()
def write(p,x,sr):
 with wave.open(str(p),'wb') as f:f.setnchannels(2);f.setsampwidth(2);f.setframerate(sr);f.writeframes((np.clip(x,-1,1)*32767).astype('<i2').tobytes())
def envelope(x,sr):
 n=sr//10;e=np.sqrt(np.mean(x[:len(x)//n*n].reshape(-1,n,2)**2,axis=(1,2)))
 return np.maximum(-90,20*np.log10(np.maximum(e,1e-9))).tolist()
def splice(a,b,retained,sr):
 b=b[round((retained-2)*sr):];n=2*sr;t=np.linspace(0,1,n)[:,None]
 return np.concatenate([a[:-n],a[-n:]*(1-t)+b[:n]*t,b[n:]]).astype(np.float32)
plots=[]
for name in ['horizon_initial','horizon_base','horizon_approach','horizon_journey','nocturne_trim_journey']:
 x,sr=read(R/'results/quality'/f'{name}.wav');plots.append({'name':'Rejected: '+name,'file':'../quality/'+name+'.wav','db':envelope(x,sr),'joins':[30,52.0123356,74.0246712] if name=='horizon_journey' else ([27.9568254,47.9259864,67.8951474] if name=='nocturne_trim_journey' else ([86*4096/44100] if name in ['horizon_base','horizon_approach'] else [])),'anchors':[]})
metrics={}
if (O/'probe.json').exists():
 m=json.loads((O/'probe.json').read_text());x,sr=read(R/'results/quality/horizon_initial.wav');x=x[:m['initial_end']*4096];joins=[];anchors=[];jobs=[]
 for r in m['jobs']:
  b,br=read(O/f'{r["name"]}.wav');assert br==sr
  plots.append({'name':'Raw: '+r['name'],'file':r['name']+'.wav','db':envelope(b,sr),'joins':[r['retained_seconds']],'anchors':[[len(b)/sr-r['anchor_frames']*4096/sr,len(b)/sr]] if r['anchor_frames'] else []})
  if not r['name'].startswith('anchor_'):continue
  join=len(x)/sr;joins.append(join);x=splice(x,b,r['retained_seconds'],sr);anchors.append([len(x)/sr-r['anchor_frames']*4096/sr,len(x)/sr]);jobs.append(r)
 if jobs:
  write(O/'horizon_anchored_journey.wav',x,sr);plots.insert(0,{'name':'Candidate: Horizon anchored rolling journey','file':'horizon_anchored_journey.wav','db':envelope(x,sr),'joins':joins,'anchors':anchors})
  unique=[r['new_seconds'] for r in jobs];usable=[r['playable_new_seconds'] for r in jobs];times=[r['seconds'] for r in jobs]
  metrics={'duration':len(x)/sr,'boundaries_seconds':joins,'anchor_ranges':anchors,'generation_seconds':times,'newly_generated_seconds_per_job':unique,'playable_new_seconds_per_job':usable,'rtf_playable':[a/b for a,b in zip(times,usable)],'rtf_unique':[a/b for a,b in zip(times,unique)],'net_buffer_gain_per_job':[b-a for a,b in zip(times,usable)],'note':'Reused four-second identity anchor explicitly included in playable duration. Two-second crossfade only over retained common context. No silence removal, level matching, stretching, or offline repairs. Human acceptance pending.'}
 (O/'metrics.json').write_text(json.dumps(metrics,indent=2))
# Live captures use exactly the playback audio, with actual append boundaries.
for name,label in [('live_curve','Live curve — Horizon'),('live_arrival','Live arrival — generated closing and local resolution'),('live_development','Live continuity and development — 210 seconds')]:
 run=O/name
 if not (run/'summary.json').exists():continue
 x,sr=read(run/'heard.wav');bounds=[json.loads(t) for t in (run/'boundaries.jsonl').read_text().splitlines()]
 joins=[r['new_material_audio_s'] for r in bounds if r['new_material_audio_s']<len(x)/sr]
 anchors=[[t-44*4096/44100,t] for t in joins[1:]]
 summary=json.loads((run/'summary.json').read_text())
 stages=[{'t':joins[i+1] if i+1<len(joins) else None,'intent':j.get('trajectory')} for i,j in enumerate(summary['generation'])]
 plots.insert(0,{'name':label,'file':name+'/heard.wav','db':envelope(x,sr),'joins':joins,'anchors':anchors,'stages':stages,'ending':json.loads((run/'ending.json').read_text()) if (run/'ending.json').exists() else None,'primary':True})
(O/'energy.json').write_text(json.dumps(plots))
page='''<!doctype html><meta charset="utf-8"><title>RoadScore continuity — listening gate</title><style>body{background:#111722;color:#e2e9f2;font:16px system-ui;max-width:1100px;margin:36px auto;padding:16px}canvas{width:100%;height:160px;background:#182130}audio{width:100%}section{margin:32px 0}small{color:#aec0d4}button{margin:4px}</style><h1>Horizon: rolling continuity experiment</h1><p>The prior trimming pass failed human review. This candidate conditions SA3 on active music at both ends of each generated window. Purple bands are reused four-second identity anchors; orange lines mark where new generated material begins. These are disclosed musical repeats, not newly generated seconds.</p><p>No silence removal, gain repair, time stretching or post-hoc arrangement. The splice is the runtime's two-second overlap of shared retained context. This page makes no musical-success claim. Listen across the marked boundaries.</p><p>Energy is 100 ms RMS in dBFS; it is diagnostic, not a musical score. Click a plot to seek.</p><p><a href="curve_review.html">Synchronized curve video</a> · <a href="arrival_review.html">Synchronized arrival video</a> · <a href="live_metrics.json">Measurements</a></p><p>Orange marks include every transition into newly generated material. Listen for a continuous musical phrase, not merely a nonzero waveform. The long live capture includes establish → explore → develop → build → release prompt intent; these names do not prove those musical effects.</p><div id="plots"></div><details><summary>Controlled probe and rejected baseline diagnostics</summary><div id="diagnostics"></div></details><script>const DATA=__DATA__;for(const p of DATA){const s=document.createElement('section');s.innerHTML='<h2>'+p.name+'</h2><audio controls preload="metadata" src="'+p.file+'"></audio><canvas width="1100" height="160"></canvas><small></small>';document.querySelector(p.primary?'#plots':'#diagnostics').append(s);const a=s.querySelector('audio'),c=s.querySelector('canvas'),ctx=c.getContext('2d'),dur=p.db.length/10;s.querySelector('small').textContent='New-material boundaries: '+p.joins.map(t=>t.toFixed(3)+' s').join(', ')+(p.stages?' | Intent: '+p.stages.filter(v=>v.t!=null).map(v=>v.intent+' at '+v.t.toFixed(1)+' s').join(', '):'')+(p.ending?' | Final resolution at route '+p.ending.route_t.toFixed(3)+' s':'');function draw(){ctx.clearRect(0,0,1100,160);for(const [lo,hi] of p.anchors){ctx.fillStyle='#7956b355';ctx.fillRect(lo/dur*1100,0,(hi-lo)/dur*1100,160)}ctx.font='12px system-ui';for(const db of [-20,-40,-60,-80]){const y=-db/90*140;ctx.strokeStyle='#354355';ctx.beginPath();ctx.moveTo(0,y);ctx.lineTo(1100,y);ctx.stroke();ctx.fillStyle='#a5b6cc';ctx.fillText(db+' dB',5,y-3)}ctx.strokeStyle='#63d4bb';ctx.beginPath();p.db.forEach((v,i)=>{const x=i/p.db.length*1100,y=-v/90*140;i?ctx.lineTo(x,y):ctx.moveTo(x,y)});ctx.stroke();for(const t of p.joins){ctx.strokeStyle='#ffb35e';ctx.beginPath();ctx.moveTo(t/dur*1100,0);ctx.lineTo(t/dur*1100,160);ctx.stroke();ctx.fillStyle='#ffb35e';ctx.fillText(t.toFixed(1)+'s',t/dur*1100+3,12)}ctx.strokeStyle='white';ctx.beginPath();ctx.moveTo(a.currentTime/dur*1100,0);ctx.lineTo(a.currentTime/dur*1100,160);ctx.stroke()}c.onclick=e=>{a.currentTime=(e.clientX-c.getBoundingClientRect().left)/c.clientWidth*dur};a.ontimeupdate=draw;draw()}</script>'''
(O/'listen.html').write_text(page.replace('__DATA__',json.dumps(plots)));print(json.dumps(metrics,indent=2))
