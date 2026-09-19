"""Same saved latent/seed counterfactual for the output-scale gate; no route input."""
import fcntl,json,shutil,time
from pathlib import Path
R=Path(__file__).resolve().parents[2];G=R/'generated';O=R/'results/ace_demo_20260916/gain_reroll';O.mkdir(exist_ok=True)
lock=open(G/'native_session.lock','w');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
assert (G/'worker_ready').read_text()=='ace';assert not (G/'busy').exists() and not (G/'request.json').exists()
job=2**32*1001+2906845423;path=G/f'result_{job}.json';assert not path.exists()
req={'id':job,'run_id':'output_gain_regression','composer':'ace','profile':'prism','identity':'kpop_control','conditioning':'verse','latents':str(R/'results/ace_demo_20260916/curve_gain_source.npy'),'experiment':'same saved musical context/seed; no recorded driving input','playback_deadline_monotonic':time.monotonic()+90}
(O/'request.json').write_text(json.dumps(req,indent=2));temp=G/'request.tmp';temp.write_text(json.dumps(req));temp.replace(G/'request.json');deadline=time.monotonic()+140
while not path.exists():
 if time.monotonic()>deadline or not (G/'worker_ready').exists():raise RuntimeError('Worker stopped/timed out; evidence preserved, no reset')
 time.sleep(.25)
meta=json.loads(path.read_text());(O/'result.json').write_text(json.dumps(meta,indent=2));shutil.move(str(G/'quality'/str(job)),str(O/'quality'))
for key in ['wav','latents']:
 if meta.get(key):shutil.copy2(meta[key],O/('accepted'+Path(meta[key]).suffix))
print(json.dumps({k:meta.get(k) for k in ['quality_accepted','seconds','original_seed','accepted_seed','quality_rejections','rerolls']},indent=2))
assert meta.get('quality_accepted') and meta.get('quality_rejections',0)>=1,'Retain outcome and investigate; no forced pass'
