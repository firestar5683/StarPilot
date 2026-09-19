"""Bounded on-bench quality experiments. No route reads or external access."""
import json,time,shutil
from pathlib import Path
ROOT=Path('/data/roadscore');OUT=ROOT/'results/quality';OUT.mkdir(exist_ok=True)
if (OUT/'trim_batch.json').exists():raise SystemExit('Preserved experiment already exists; use a new output directory for a deliberate rerun.')
generated=ROOT/'generated';serial=910000;results=[]
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
 (OUT/'trim_batch.json').write_text(json.dumps(results,indent=2));print(name,round(meta['seconds'],3),flush=True)
 return meta['latents']
entries=json.loads((OUT/'batch.json').read_text())
latent=next(x['latents'] for x in entries if x['experiment']=='nocturne_initial')
for i in range(3):
 latent=request(f'nocturne_trim_{i}',identity='nocturne',seconds_total=120,source_end=301,latents=latent)
print('TRIM COMPLETE',flush=True)
