"""Audit retained new music and render exact first five linked sections, file only."""
import sys,json
from pathlib import Path
import numpy as np,soundfile as sf
from bundle import OUT
plan_path=OUT/sys.argv[1];plan=json.loads(plan_path.read_text());results=[];flow=None;all_energy=[]
for number,j in enumerate(plan):
 p=OUT/'cases'/j['case'];o=p/j['output'];f=o/'pcm.npy'
 if not (o/'audio.wav').exists():continue
 a=np.load(f) if f.exists() else sf.read(o/'audio.wav',dtype='float32',always_2d=True)[0]/.65
 prefix=int(np.flatnonzero(np.load(p/'mask.npy')[0])[0])/25 if (p/'mask.npy').exists() else 0
 endpoint=json.loads((o/'endpoint.json').read_text()) if (o/'endpoint.json').exists() else {};end=endpoint.get('committed_seconds',j['commit_seconds']);fresh=a[round(prefix*48000):round(end*48000)];n=4800;e=np.sqrt(np.mean(fresh[:len(fresh)//n*n].reshape(-1,n,2)**2,axis=(1,2)));q=e<.003;all_energy.extend(e.tolist());spans=[];start=None
 for i,v in enumerate(list(q)+[False]):
  if v and start is None:start=i
  if not v and start is not None:spans.append([start/10,i/10]);start=None
 report=json.loads((o/'report.json').read_text());entry={'endpoint':endpoint,'number':number,'case':j['case'],'output':j['output'],'prefix_seconds':prefix,'committed_seconds':end,'new_seconds':end-prefix,'quiet_spans_new_seconds':spans,'longest_quiet_seconds':max([b-a for a,b in spans],default=0),'rms_last_committed_2s':float(np.sqrt(np.mean(a[round((end-2)*48000):round(end*48000)]**2))),'wall_seconds_including_cold_warmup':report.get('wall_seconds'),'cold_shape_warmup_seconds':report.get('warmup_seconds',[]),'warm_full_job_rtf':report['wall_seconds']/(end-prefix) if 'wall_seconds' in report and not report.get('warmup_seconds') else None,'generation_seconds':report['generation_seconds'],'decode_seconds':report['decode_seconds'],'rtf_retained_new':(report['generation_seconds']+report['decode_seconds'])/(end-prefix),'finite':bool(np.isfinite(a).all())}
 if (o/'input_source.npy').exists():
  source=np.load(o/'input_source.npy');z=np.load(o/'latents.npy');count=round(prefix*25)-12;entry['preserved_prefix_exact']=bool(np.array_equal(source[:,:count].astype(z.dtype),z[:,:count]))
 results.append(entry)
 if number<5:
  if flow is None:flow=a[:round(end*48000)].copy()
  else:
   n=96000;alpha=np.linspace(0,1,n)[:,None];flow[-n:]=flow[-n:]*(1-alpha)+a[round(prefix*48000)-n:round(prefix*48000)]*alpha;flow=np.concatenate([flow,fresh])
whole=np.asarray(all_energy);run=longest=0
for quiet in whole<.003:run=run+1 if quiet else 0;longest=max(longest,run)
name=plan_path.stem
(OUT/(name+'_joined_energy.json')).write_text(json.dumps({'seconds':len(whole)/10,'max_contiguous_quiet_seconds_across_joins':longest/10,'rms_100ms':all_energy},indent=2))
(OUT/(name+'_audit.json')).write_text(json.dumps(results,indent=2))
if flow is not None:sf.write(OUT/(name+'_flow.wav'),flow*.65,48000,subtype='PCM_24')
print('completed',len(results),'worst quiet',max([x['longest_quiet_seconds'] for x in results],default=0),'RTF range',[min([x['rtf_retained_new'] for x in results],default=0),max([x['rtf_retained_new'] for x in results],default=0)])
