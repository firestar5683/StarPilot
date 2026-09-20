"""Render a measured replay curve over unchanged archived core PCM, offline."""
import argparse
import hashlib
import json
from pathlib import Path
import time
import numpy as np
import soundfile as sf
from curve_reaction import CurveReaction
from demo_curve_plan import ReplayCurvePlan
from rhythm_timeline import RhythmTimeline
from signal_shaker import ShakerGrid


def main():
 parser=argparse.ArgumentParser(description=__doc__)
 parser.add_argument('archive',type=Path);parser.add_argument('plan',type=Path);parser.add_argument('output',type=Path)
 args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=False)
 plan=ReplayCurvePlan(json.loads(args.plan.read_text()));event=plan.value['curves'][0]
 rows=[json.loads(line) for line in (args.archive/'audio_blocks.jsonl').read_text().splitlines()]
 timeline=RhythmTimeline(48000,128.)
 timeline.entries=tuple((row['start_frame'],row['end_frame'],ShakerGrid(**row['grid'])) for row in json.loads((args.archive/'rhythm_timeline.json').read_text()))
 start=int(event['build_start'])-4;end=int(event['end'])+4;rate=48000
 with sf.SoundFile(args.archive/'dry.wav') as source:
  if source.samplerate!=rate or source.channels!=2:raise ValueError('Expected native 48kHz stereo core')
  source.seek(start*rate);wave=source.read((end-start)*rate,dtype='float32',always_2d=True)
 lookup={round(row['audio_s']*10):row for row in rows}
 report={'source':str(args.archive/'dry.wav'),'source_sha256':hashlib.sha256((args.archive/'dry.wav').read_bytes()).hexdigest(),
         'plan':plan.value,'clip_audio_start':start,'clip_seconds':len(wave)/rate,
         'camera_start_s':lookup[start*10]['route_t'],
         'scope':'Same native core PCM and gain. Curve layer only; other presentation effects omitted. No regeneration.',
         'files':{}}
 for name,staged in [('before-curve.wav',False),('after-curve.wav',True)]:
  dsp=CurveReaction(timeline.at(start*rate),rate,enabled=True,bass_build=staged);output=[];events=[];timings=[]
  for offset in range(0,len(wave),4800):
   frame=start*rate+offset;row=lookup[round(frame/rate*10)]
   state={key:row.get(key) for key in ('kind','phase','amount','activation','predicted_peak')}
   if staged:state=plan.state(row['route_t'],plan.value['route'],state)
   dsp.grid=timeline.at(frame)
   target=frame+round((state.get('predicted_peak',row['route_t'])-row['route_t'])*rate) if state.get('demo_build_drop') else frame
   began=time.perf_counter();output.append(dsp.process(wave[offset:offset+4800],frame,state,route_time=row['route_t'],payoff_grid=timeline.at(target)));timings.append(time.perf_counter()-began)
   events.append({'audio_s':frame/rate,'route_s':row['route_t'],**dsp.snapshot()['curve_reaction']})
  audio=np.concatenate(output);sf.write(args.output/name,audio,rate,subtype='FLOAT')
  report['files'][name]={'peak':float(abs(audio).max()),'over_full_scale':int(np.count_nonzero(abs(audio)>1)),
                       'work_mean_ms':float(np.mean(timings)*1000),'work_max_ms':float(max(timings)*1000),'states':events}
 sf.write(args.output/'unchanged-core.wav',wave,rate,subtype='FLOAT')
 (args.output/'comparison.json').write_text(json.dumps(report,indent=2)+'\n')
 print(json.dumps({name:{k:v for k,v in row.items() if k!='states'} for name,row in report['files'].items()},indent=2))


if __name__=='__main__':main()
