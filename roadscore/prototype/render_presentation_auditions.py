"""Offline same-generation auditions. Synthetic events never claimed as route data."""
import argparse,json,time,hashlib
from pathlib import Path
from dataclasses import replace,asdict
import numpy as np
import soundfile as sf
from signal_shaker import SignalShaker,assess_grid
from core_apex import CoreApex
from alert_accent import AlertAccent
from engagement_presentation import EngagementPresentation,PresentationConfig

def main():
 p=argparse.ArgumentParser();p.add_argument('source',type=Path);p.add_argument('output',type=Path);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
 wave,rate=sf.read(a.source,dtype='float32',always_2d=True);assert rate==48000
 estimated,analysis=assess_grid(wave,rate,128.)
 # Explicit audition hypothesis only: never written into runtime configuration.
 audition=replace(estimated,bpm=128.,beat_phase=estimated.beat_phase,confirmed=True,reason='OFFLINE PROVISIONAL128BPM hypothesis; NOT human verified or runtime authorized')
 shaker=SignalShaker(audition,rate,True);safe=SignalShaker(estimated,rate,True);apex=CoreApex(audition,rate,True);engage=EngagementPresentation(rate)
 alerts=AlertAccent(estimated,rate,True)
 arms={k:[] for k in ['core','alerts_confidence_gated','shaker_provisional128','shaker_confidence_gated','engagement_separate','apex_separate_provisional128']};timings=[]
 for frame in range(0,len(wave),4800):
  x=wave[frame:frame+4800];t=frame/rate
  signal=any(start<=t<end for start,end in [(8.,14.),(32.,38.)]) and int(t*2)%2==0
  active=16<=t<28 or 42<=t<56
  # Synthetic model-style anticipation for two explicitly marked apexes.
  target=22. if t<28 else 46.;lead=target-t
  state={'kind':'curve','phase':'anticipation' if .0<lead<2 else 'neutral','lead':lead,'activation':target}
  started=time.perf_counter()
  arms['core'].append(x);arms['alerts_confidence_gated'].append(alerts.process(x,frame,'synthetic_user_prompt',3<=t<6,True));arms['shaker_provisional128'].append(shaker.process(x,frame,signal,True));arms['shaker_confidence_gated'].append(safe.process(x,frame,signal,True));arms['engagement_separate'].append(engage.process(x,active,PresentationConfig(enabled=True)));arms['apex_separate_provisional128'].append(apex.process(x,frame,state));timings.append(time.perf_counter()-started)
 records={}
 for name,blocks in arms.items():
  output=np.concatenate(blocks);path=a.output/(name+'.wav');sf.write(path,output,rate,subtype='FLOAT');records[name]={'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'peak':float(abs(output).max()),'difference_rms':float(np.sqrt(np.mean((output-wave)**2)))}
 records['core']['sample_identical_to_source']=bool(np.array_equal(sf.read(a.output/'core.wav',dtype='float32')[0],wave))
 report={'source':str(a.source),'source_sha256':hashlib.sha256(a.source.read_bytes()).hexdigest(),'seconds':len(wave)/rate,'common_gain':'source unchanged; no normalization, limiter, secondgain or resampling','events_source':'SYNTHETIC OFFLINE timeline; not route telemetry','synthetic_signal_windows_seconds':[[8,14],[32,38]],'synthetic_engaged_windows_seconds':[[16,28],[42,56]],'synthetic_apex_seconds':[22,46],'estimated_grid':asdict(estimated),'grid_analysis':analysis,'provisional_audition_grid':asdict(audition),'shaker':shaker.snapshot(),'shaker_sequence_events':shaker.events,'shaker_pulse_frames':shaker.pulse_frames,'apex_events':apex.events,'engagement_config':asdict(PresentationConfig(enabled=True)),'callback_work_allarms_mean_ms':float(np.mean(timings)*1000),'callback_work_allarms_max_ms':max(timings)*1000,'timing_scope':'Mac offline sequential5arms, not native callback deadline validation','files':records,'alert_events':alerts.events,'hardware_validated':False}
 (a.output/'report.private.json').write_text(json.dumps(report,indent=2));print(json.dumps({'output':str(a.output),'grid':asdict(estimated),'files':records},indent=2))
if __name__=='__main__':main()
