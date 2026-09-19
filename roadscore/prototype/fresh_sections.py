"""Text-only control comparison; deliberately tests the loss-of-identity tradeoff."""
import json,time,shutil
from pathlib import Path
R=Path('/data/roadscore');G=R/'generated';O=R/'results/overnight/fresh';O.mkdir(exist_ok=True)
for role in ['verse','chorus','bridge']:
 dest=O/role;assert not dest.with_suffix('.json').exists()
 req={'id':int(time.time()*1000),'run_id':'fresh-role-control','identity':'songform2','conditioning':role,'seconds_total':30,'fresh':True,'latents':str(R/'assets/source_songform_latents.npy'),'seed':9501}
 p=G/'request.tmp';p.write_text(json.dumps(req));p.replace(G/'request.json');f=G/f'result_{req["id"]}.json';end=time.monotonic()+150
 while not f.exists():
  if time.monotonic()>end:raise TimeoutError(role)
  time.sleep(.1)
 r=json.loads(f.read_text());assert 'error' not in r,r;shutil.copy(r['wav'],dest.with_suffix('.wav'));r['request']=req;dest.with_suffix('.json').write_text(json.dumps(r,indent=2));print(role,r['seconds'],flush=True)
