"""Identical-request comparisons after JIT capture; no musical/audio output."""
import json,time,hashlib,argparse
from pathlib import Path
R=Path('/data/roadscore');G=R/'generated';rows=[]
p=argparse.ArgumentParser();p.add_argument('--roles',default='base,base');a=p.parse_args()
for i,role in enumerate(a.roles.split(',')):
 req={'id':int(time.time()*1000),'run_id':'cache-equivalence','identity':'songform','conditioning':role,'seconds_total':120,'source_end':236,'latents':str(R/'assets/source_songform_latents.npy'),'seed':1999,'context_frames':44,'anchor_frames':44,'anchor_end':108,'anchor_latents':str(R/'assets/source_songform_latents.npy')}
 p=G/'request.tmp';p.write_text(json.dumps(req));p.replace(G/'request.json');f=G/f'result_{req["id"]}.json';end=time.monotonic()+150
 while not f.exists():
  if time.monotonic()>end:raise TimeoutError('worker')
  time.sleep(.1)
 r=json.loads(f.read_text());assert 'error' not in r,r;r['hashes']={k:hashlib.sha256(Path(r[k]).read_bytes()).hexdigest() for k in ['wav','latents']};rows.append(r);print(json.dumps(r),flush=True)
if len(set(a.roles.split(',')))==1:print('IDENTICAL',all(r['hashes']==rows[0]['hashes'] for r in rows),flush=True)
