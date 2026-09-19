"""Remix an existing dry replay capture using only each then-current archived state.
This is a listening derivative, not a new onroad or fresh-generation acceptance run.
"""
from pathlib import Path
import sys,json
import numpy as np,soundfile as sf
P=Path(__file__).resolve().parent;R=P.parents[1];sys.path.insert(0,str(R/'prototype'))
from musical_gestures import MusicalGestures as V1
from musical_gestures_v2 import MusicalGestures as V2
O=R/'results/ace_chestnut_20260916/road_gestures';info=sf.info(O/'dry.wav');rate=info.samplerate
with sf.SoundFile(O/'dry.wav') as f:source=f.read(rate*8,dtype='float32',always_2d=True)
grid=json.loads((O/'gesture_grid.json').read_text());report={'kind':'archived dry replay + causally gated archived semantic state; no new replay/generation claim','sample_rate':rate,'frames':info.frames,'grid':grid,'versions':{}}
for version,cls in [('v1',V1),('v2',V2)]:
 g=cls(source,rate,grid['bpm'],grid['beat_phase']);trace=open(O/'trace.jsonl');pending=json.loads(next(trace));state={};frame=0;maxpeak=0.;clipped=0
 with sf.SoundFile(O/'dry.wav') as src,sf.SoundFile(O/(version+'.flac'),'w',samplerate=rate,channels=2,subtype='PCM_24') as out:
  while len(dry:=src.read(4800,dtype='float32',always_2d=True)):
   while pending is not None and pending['elapsed']<=frame/rate:
    state=pending;line=next(trace,None);pending=json.loads(line) if line else None
   if state:
    g.update(frame,left=bool(state.get('turn_signal_music')),road=state,nav=state.get('nav',{}),speed=state.get('speed',0),outro=bool(state.get('outro_intent')),arrived=state.get('arrival_at') is not None,input_ns=state.get('source_cutoff_ns',0))
   wet=g.render(dry);maxpeak=max(maxpeak,float(abs(wet).max()));clipped+=int(np.count_nonzero(abs(wet)>=.98));out.write(wet);frame+=len(dry)
 trace.close();r={'frames':frame,'max_peak':maxpeak,'clamp_samples':clipped,'late_events':sum(e.get('lateness_frames',0)>0 for e in g.events),'started_events':sum(e['type']=='started' for e in g.events),'signal_phrases':sum(e['type']=='started' and e.get('tag')=='signal' for e in g.events)};report['versions'][version]=r;(O/(version+'_events.json')).write_text(json.dumps(g.events,indent=2));assert frame==info.frames;print(version,r,flush=True)
(O/'review.json').write_text(json.dumps(report,indent=2))
