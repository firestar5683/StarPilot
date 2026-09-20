"""Offline same-PCM build/cut/drop audition from an archived rhythm assessment."""
import argparse
import hashlib
import json
from pathlib import Path
import time

import numpy as np
import soundfile as sf

from curve_build_drop import CurveBuildDrop
from signal_shaker import ShakerGrid


def main():
  p=argparse.ArgumentParser(description=__doc__)
  p.add_argument('source',type=Path);p.add_argument('output',type=Path)
  p.add_argument('--timeline',type=Path)
  p.add_argument('--build-start',type=float,required=True);p.add_argument('--apex',type=float,required=True)
  p.add_argument('--start',type=float);p.add_argument('--end',type=float)
  a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
  wave,rate=sf.read(a.source,dtype='float32',always_2d=True)
  timeline_path=a.timeline or a.source.with_name('rhythm_timeline.json')
  timeline=json.loads(timeline_path.read_text());apex=round(a.apex*rate)
  entry=next(e for e in reversed(timeline) if e['start_frame']<=apex<e['end_frame'])
  grid=ShakerGrid(**entry['grid'])
  if not grid.usable:raise ValueError('The archived apex grid is not usable; no guessed pulse')
  step=rate*60/grid.bpm/2;origin=grid.beat_phase*rate
  payoff=round(origin+round((apex-origin)/step)*step)
  build=round(a.build_start*rate)
  first=max(0,round((a.start if a.start is not None else a.build_start-2)*rate))
  end=min(len(wave),round((a.end if a.end is not None else a.apex+3)*rate))
  fx=CurveBuildDrop(rate);blocks=[];timings=[]
  for frame in range(0,end,4800):
    x=wave[frame:min(frame+4800,end)];started=time.perf_counter()
    blocks.append(fx.process(x,frame,grid,build,payoff,enabled=True))
    timings.append(time.perf_counter()-started)
  after=np.concatenate(blocks)[first:end];before=wave[first:end]
  report=dict(source=str(a.source),source_sha256=hashlib.sha256(a.source.read_bytes()).hexdigest(),
    rhythm_source=str(timeline_path),rhythm_sha256=hashlib.sha256(timeline_path.read_bytes()).hexdigest(),
    grid=entry['grid'],build_audio_s=build/rate,requested_apex_audio_s=a.apex,actual_payoff_audio_s=payoff/rate,
    apex_quantization_offset_ms=1000*(payoff/rate-a.apex),clip_start_audio_s=first/rate,
    clip_end_audio_s=end/rate,clip_build_s=(build-first)/rate,clip_drop_s=(payoff-first)/rate,
    scope='Explicit staged presentation from supplied real-event timing; no generation or runtime changes. Component only; root bass-removal build is not included.',
    common_gain='Source unchanged; no normalization, resampling or source attenuation',
    hardware_validated=False,work_mean_ms=float(np.mean(timings)*1000),work_max_ms=max(timings)*1000,
    pulse_frames=fx.pulse_frames,status=fx.snapshot(),files={})
  for name,audio in (('before-core.wav',before),('after-build-drop.wav',after)):
    target=a.output/name;sf.write(target,audio,rate,subtype='FLOAT')
    report['files'][name]=dict(seconds=len(audio)/rate,peak=float(abs(audio).max()),
      samples_above_full_scale=int(np.count_nonzero(abs(audio)>1)),sha256=hashlib.sha256(target.read_bytes()).hexdigest())
  (a.output/'comparison.json').write_text(json.dumps(report,indent=2)+'\n')
  print(json.dumps({key:report[key] for key in ('clip_build_s','clip_drop_s','apex_quantization_offset_ms','work_mean_ms','work_max_ms','files')},indent=2))


if __name__=='__main__':main()
