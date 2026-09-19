"""Bounded final SA3 control: fresh identity, extreme roles, generated transitions/outro.
Research only. No route access or audio device access. Existing worker stays unchanged.
"""
import argparse,json,time,shutil,os
from pathlib import Path
R=Path('/data/roadscore');O=R/'results/composition_20260916/sa3';G=R/'generated'
BASE='Polished instrumental K-pop and electronic game-score hybrid, 128 BPM, four-four time, D minor. Tight compressed electronic drums, syncopated electric and synth bass, pulsing synths, bright arpeggiators, catchy recurring four-note synth hook, glossy modern pop production, playful electronic fills. One coherent instrumental song, strong rhythmic and harmonic identity. No vocals, singing, chanting or speech. '
ROLES={
'base':'Restrained verse groove with dry drums and bass, a small plucked hook, sparse accompaniment and plenty of space for a later huge chorus.',
'verse':'VERSE ONLY. Deliberately STRIPPED arrangement: dry kick, rim snare, closed hats, syncopated bass and tiny plucked motif. Minimal lead and no wide pads. Obvious empty space. Controlled quiet energy, not a full chorus.',
'prechorus':'PRECHORUS BUILD. Unmistakable rising motion throughout the phrase: accelerating snare subdivisions, opening synth filters, rising arpeggio sequence, suspended harmony and bass movement pointing forward. Strong crescendo of orchestration. Finish with a dramatic pickup into the next downbeat, not a static verse.',
'chorus':'MASSIVE CHORUS. Explosive full drums and electric bass, very wide layered synth stack, soaring recurring hook doubled in octaves, bright counter-melody and driving arpeggios. Strong harmonic lift. Clearly the largest most exuberant arrangement, dramatically fuller than the restrained verse, not merely louder.',
'bridge':'CONTRASTING BRIDGE. New borrowed major/modal harmonic color within the same song. Initially half-time tom groove and a new expressive glassy lead timbre; retain bass pulse and the recurring motif. Then rebuild with stronger drum fills and rising harmony. Do not fall into silence.',
'outro':'ACTUAL CONCLUDING OUTRO lasting a complete phrase. Bring back the recognizable hook one final time. Progressively remove counterlines, simplify drums and bass, resolve harmonic tension through a clear final melodic answer. Finish with an intentional tonic D minor chord and naturally ringing instruments. Prepare and complete a real ending. No abrupt interruption, no endless loop.',
'verse_to_chorus':'GENERATE THE TRANSITION, not a static section: begin in the existing restrained verse. Over the next two bars add subdivisions, rising arpeggios and harmonic tension. On the following downbeat EXPLODE into the massive full chorus with wide synths, full drums and the recurring hook. Preserve tempo, drums, key and motif through the transition. Continue the chorus.',
'chorus_to_bridge':'GENERATE THE TRANSITION: finish the existing chorus phrase, use one intentional drum fill, then enter a clearly contrasting bridge with borrowed/modal color and a new playful lead over the same bass pulse. The harmonic change is prepared, not an unrelated song or random splice. Rebuild after the contrast.',
'song_to_outro':'GENERATE THE SONG ENDING TRANSITION: complete the current energetic phrase, recall the main hook, then spend the remaining four to eight bars concluding the composition. Counterlines drop out, the hook gives a final answer, bass and harmony resolve to the tonic. End the drums purposefully, let the final chord ring naturally. This is an actual final outro, not an ordinary verse with a fade.'}
def encode():
 import section_experiment as e
 e.O=O;e.BASE=BASE;e.ROLES=ROLES;os.environ['ROADSCORE_CONDITION_ID']='kpop_control';e.encode()
def job(name,role,source,fresh=False,context=22,seed=12601):
 import numpy as np,soundfile as sf
 dest=O/name
 if dest.with_suffix('.json').exists():return json.loads(dest.with_suffix('.json').read_text())
 req={'id':int(time.time()*1000),'run_id':'composition-control-20260916','identity':'kpop_control','conditioning':role,'seconds_total':30 if fresh else 120,'source_end':302,'latents':str(source),'fresh':fresh,'context_frames':context,'anchor_frames':0,'seed':seed}
 tmp=G/'request.tmp';tmp.write_text(json.dumps(req));tmp.replace(G/'request.json');result=G/f'result_{req["id"]}.json';deadline=time.monotonic()+240
 while not result.exists():
  if time.monotonic()>deadline:raise TimeoutError(name)
  time.sleep(.1)
 meta=json.loads(result.read_text());assert 'error' not in meta,meta
 wave,sr=sf.read(meta['wav'],dtype='float32',always_2d=True);start=0 if fresh else context*4096
 sf.write(dest.with_suffix('.wav'),wave[start:],sr);shutil.copy(meta['latents'],dest.with_suffix('.npy'))
 meta.update(request=req,artifact=str(dest.with_suffix('.wav')),duration=len(wave[start:])/sr,rms=float(np.sqrt(np.mean(wave[start:]**2))),role=role,human_musical_acceptance='pending');dest.with_suffix('.json').write_text(json.dumps(meta,indent=2));print(name,meta['seconds'],meta['duration'],flush=True);return meta
def probe():
 deadline=time.monotonic()+600
 while not (G/'worker_ready').exists():
  if time.monotonic()>deadline:raise TimeoutError('Worker readiness')
  time.sleep(1)
 seed=job('identity','base',R/'assets/source_songform_latents.npy',fresh=True)
 for role in ['verse','prechorus','chorus','bridge','outro']:job(role,role,O/'identity.npy')
 job('verse_to_chorus','verse_to_chorus',O/'verse.npy',context=44,seed=12602)
 job('chorus_to_bridge','chorus_to_bridge',O/'chorus.npy',context=44,seed=12603)
 job('song_to_outro','song_to_outro',O/'chorus.npy',context=44,seed=12604)
if __name__=='__main__':
 O.mkdir(parents=True,exist_ok=True);p=argparse.ArgumentParser();p.add_argument('mode',choices=['encode','probe']);a=p.parse_args();globals()[a.mode]()
