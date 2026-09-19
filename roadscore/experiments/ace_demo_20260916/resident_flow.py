"""Focused verse→build→chorus→verse→bridge→chorus→outro via the real resident worker.
Standalone musical requests only. Own the replay session lock; never run beside replay.
"""
import time,json,fcntl,shutil
from pathlib import Path
import numpy as np,soundfile as sf
R=Path(__file__).resolve().parents[2];G=R/'generated';O=R/'results/ace_demo_20260916/resident_flow';O.mkdir(parents=True,exist_ok=True)
lock=open(G/'native_session.lock','w');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
state=json.loads((G/'ace_worker_state.json').read_text());assert state['profile']=='prism' and state['phase']=='READY';assert (G/'worker_ready').read_text()=='ace'
assert not (G/'request.json').exists() and not (G/'busy').exists(),'Worker must be idle'
base=R/'results/ace_demo_20260916/soak/section_00';source=base/'accepted.npy';audio,rate=sf.read(base/'accepted.wav',dtype='float32',always_2d=True);audio*=.65;rows=[]
for i,role in enumerate(['prechorus','chorus','verse','bridge','chorus','outro']):
 job=2**32*1000+41001+i;path=G/f'result_{job}.json';assert not path.exists(),'Preserve earlier flow; choose a new explicitly recorded experiment ID before rerunning'
 req={'id':job,'run_id':'standalone_demo_flow','composer':'ace','profile':'prism','identity':'kpop_control','conditioning':role,'latents':str(source),'experiment':'standalone musical flow, no driving inputs','nav_revision':0}
 (O/f'request_{i}.json').write_text(json.dumps(req,indent=2));temp=G/'request.tmp';temp.write_text(json.dumps(req));temp.replace(G/'request.json');deadline=time.monotonic()+150
 while not path.exists():
  if time.monotonic()>deadline or not (G/'worker_ready').exists():raise RuntimeError('Resident worker stopped or timed out; no automatic reset')
  time.sleep(.2)
 meta=json.loads(path.read_text());rows.append(meta);(O/'results.json').write_text(json.dumps(rows,indent=2))
 folder=O/f'section_{i:02d}_{role}';folder.mkdir(exist_ok=True)
 quality=G/'quality'/str(job)
 if quality.exists():shutil.move(str(quality),str(folder/'quality'))
 if meta.get('error') or meta.get('quality_rejected'):raise RuntimeError('Focused flow stopped at bounded rejection/failure; evidence retained')
 w,sr=sf.read(meta['wav'],dtype='float32',always_2d=True);assert sr==rate;prefix=meta['new_audio_start_frame'];n=meta['overlap_frames'];alpha=np.linspace(0,1,n,dtype=np.float32)[:,None];audio[-n:]=audio[-n:]*(1-alpha)+w[prefix-n:prefix]*alpha;audio=np.concatenate([audio,w[prefix:]])
 shutil.copy2(meta['wav'],folder/'accepted.wav');shutil.copy2(meta['latents'],folder/'accepted.npy');source=Path(meta['latents']);print('FLOW_ACCEPTED',role,meta['seconds'],meta['rerolls'],flush=True)
sf.write(O/'section_flow.wav',audio,rate,subtype='PCM_24');print('FLOW_COMPLETE',len(audio)/rate,flush=True)
