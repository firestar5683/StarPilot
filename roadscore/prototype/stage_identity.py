"""Prepare a selected generated identity for live scheduling; never reads routes."""
import argparse,json,shutil,time
from pathlib import Path
from rolling import anchor_options,INITIAL_END
R=Path('/data/roadscore');G=R/'generated';O=R/'results/unattended';p=argparse.ArgumentParser();p.add_argument('identity');p.add_argument('--original-events',action='store_true');a=p.parse_args();key=a.identity
for ext,suffix in [('wav','.wav'),('npy','_latents.npy')]:shutil.copy(O/f'{key}_seed.{ext}',R/f'assets/source_{key}{suffix}')
req={'id':int(time.time()*1000),'run_id':'stage-'+key,'identity':key,'conditioning':'base','seconds_total':180,'source_end':INITIAL_END,'latents':str(R/f'assets/source_{key}_latents.npy'),'seed':8501,**anchor_options(R,key)}
tmp=G/'request.tmp';tmp.write_text(json.dumps(req));tmp.replace(G/'request.json');f=G/f'result_{req["id"]}.json';deadline=time.monotonic()+120
while not f.exists():
 if time.monotonic()>deadline:raise TimeoutError('Prewarm')
 time.sleep(.1)
r=json.loads(f.read_text());assert 'error' not in r,r
shutil.copy(r['wav'],G/'job_-1.wav');shutil.copy(r['latents'],G/'job_-1.npy');(G/'warm_metadata.json').write_text(json.dumps(r));(O/(key+'_prewarm.json')).write_text(json.dumps(r,indent=2))
(R/'runtime.json').write_text(json.dumps({'identity':key,'musical':True,'rolling':True,'arrangement':True,'drive_events':True,'event_music':not a.original_events,'curve_handoff':not a.original_events,'phrase_runway':True}))
print(key,'ready',r['seconds'],flush=True)
