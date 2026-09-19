"""Bounded on-bench quality experiments. No route reads or external access."""
import json,time,shutil
from pathlib import Path
ROOT=Path('/data/roadscore');OUT=ROOT/'results/quality';OUT.mkdir(exist_ok=True)
if (OUT/'batch.json').exists():raise SystemExit('Preserved experiment already exists; use a new output directory for a deliberate rerun.')
generated=ROOT/'generated';serial=900000;results=[]
def request(name,**args):
 global serial
 serial+=1;req={'id':serial,'run_id':'quality','latents':str(ROOT/'assets/source_latents.npy'),'seed':12345,**args}
 assert (generated/'worker_ready').exists()
 p=generated/'request.tmp';p.write_text(json.dumps(req));p.replace(generated/'request.json')
 deadline=time.monotonic()+90;f=generated/f'result_{serial}.json'
 while not f.exists():
  if time.monotonic()>deadline:raise RuntimeError('Worker timed out')
  time.sleep(.1)
 meta=json.loads(f.read_text());assert 'error' not in meta,meta
 meta['experiment']=name;results.append(meta)
 shutil.copy(meta['wav'],OUT/f'{name}.wav')
 (OUT/'batch.json').write_text(json.dumps(results,indent=2));print(name,round(meta['seconds'],3),flush=True)
 return meta['latents']
request('legacy_30',fresh=True,seconds_total=30)
fresh=request('legacy_120',fresh=True,seconds_total=120)
request('legacy_120_continue',latents=fresh,seconds_total=120)
request('old_tail_120',seconds_total=120)
request('earlier_tail_120',seconds_total=120,source_end=248)
# Four distinct identities, each followed by base, development and closing material.
for identity in ['nocturne','horizon','orbit','canopy']:
 latent=request(identity+'_initial',identity=identity,fresh=True,seconds_total=120)
 for intent in ['base','approach','closing']:
  latent=request(identity+'_'+intent,identity=identity,conditioning=intent,seconds_total=30 if intent=='closing' else 120,latents=latent)
print('BATCH COMPLETE',flush=True)
