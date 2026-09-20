"""Render the same PCM through two presentation policies; no playback or inference."""
import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import time

import numpy as np
import soundfile as sf

from engagement_presentation import EngagementPresentation, PresentationConfig
from presentation_policy import effective_config
from rhythm_timeline import RhythmTimeline
from signal_shaker import SignalShaker


def render(wave, rate, policy):
  config=effective_config({}, {'ROADSCORE_PRESENTATION_POLICY':policy})
  settings=PresentationConfig.read(config['engagement_presentation'])
  dsp=EngagementPresentation(rate,cutoff_hz=settings.cutoff_hz,width=settings.width,gain=settings.gain)
  timeline=RhythmTimeline(rate,128.);timeline.add(wave,0)
  shaker=SignalShaker(timeline.at(0),rate,True,peak=config['signal_shaker']['peak'])
  after=config['signal_shaker'].get('after_containment',False)
  blocks=[];timings=[];snapshots=[]
  for frame in range(0,len(wave),4800):
    t=frame/rate;x=wave[frame:frame+4800]
    active=not (4<=t<8 or 16<=t<20)
    direction='left' if 10<=t<14 else 'right' if 14<=t<18 else 'off'
    started=time.perf_counter()
    shaker.set_grid(timeline.at(frame),frame)
    if not after:x=shaker.process(x,frame,direction!='off',True)
    output=dsp.process(x,active,settings)
    if after:
      contained=config['signal_shaker']['contained_gain']
      output=shaker.process(output,frame,direction!='off',True,sequence_key=direction,
                            presentation_gain=contained+(1-contained)*dsp.mix)
    timings.append(time.perf_counter()-started)
    blocks.append(output)
    snapshots.append(dict(seconds=t,active=active,direction=direction,shaker=shaker.snapshot()))
  return np.concatenate(blocks),dict(policy=policy,config=config,grid=timeline.snapshot(),
    sequence_events=shaker.events,pulse_frames=shaker.pulse_frames,
    block_work_mean_ms=float(np.mean(timings)*1000),block_work_max_ms=max(timings)*1000,
    frames_unchanged=True,added_timing_delay_samples=0,snapshots=snapshots)


def main():
  parser=argparse.ArgumentParser(description=__doc__)
  parser.add_argument('source',type=Path);parser.add_argument('output',type=Path)
  args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=False)
  wave,rate=sf.read(args.source,dtype='float32',always_2d=True)
  if rate!=48000 or wave.shape[1]!=2 or len(wave)!=26*rate:
    raise ValueError('Use the exact 26-second 48kHz stereo native baseline')
  report=dict(source=str(args.source),source_sha256=hashlib.sha256(args.source.read_bytes()).hexdigest(),
    source_preserved=True,common_gain='Exact source gain; no normalization, resampling or limiter',
    event_source='Synthetic manual-controls rehearsal, not route telemetry; moving throughout',
    timeline=[dict(seconds=0,event='Engaged/open'),dict(seconds=4,event='Simulate disengage'),
      dict(seconds=8,event='Simulate engage'),dict(seconds=10,event='Left signal'),
      dict(seconds=14,event='Right signal'),dict(seconds=16,event='Simulate disengage'),
      dict(seconds=18,event='Signals off; natural release'),dict(seconds=20,event='Simulate engage')],
    scope='Signal and engagement comparison only; curves/alerts/motion not active in this fixture',
    hardware_validated=False,files={})
  for filename,policy in [('before-v3.wav','conservative-v3'),('after-v4.wav','conservative-v4')]:
    audio,details=render(wave,rate,policy)
    target=args.output/filename;sf.write(target,audio,rate,subtype='FLOAT')
    report['files'][filename]=dict(sha256=hashlib.sha256(target.read_bytes()).hexdigest(),
      seconds=len(audio)/rate,peak=float(abs(audio).max()),rms=float(np.sqrt(np.mean(audio*audio))),
      samples_above_full_scale=int(np.count_nonzero(abs(audio)>1)),**details)
  sf.write(args.output/'unchanged-core.wav',wave,rate,subtype='FLOAT')
  report['core_sample_identical']=bool(np.array_equal(sf.read(args.output/'unchanged-core.wav',dtype='float32')[0],wave))
  (args.output/'comparison.json').write_text(json.dumps(report,indent=2)+'\n')
  summary={name:{key:value[key] for key in ('seconds','peak','rms','samples_above_full_scale','block_work_mean_ms','block_work_max_ms','sequence_events')} for name,value in report['files'].items()}
  print(json.dumps(summary,indent=2))


if __name__=='__main__':main()
