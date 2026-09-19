"""Play a recorded final score against original cereal time. Never imports a model."""
import argparse,json,time,signal,hashlib,sys
from pathlib import Path
import numpy as np
import soundfile as sf
import sounddevice as sd
from cereal import messaging

def main():
 p=argparse.ArgumentParser();p.add_argument('--score',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--duration',type=float,default=180);p.add_argument('--audible',action='store_true');p.add_argument('--device',default=None);a=p.parse_args();from audio_policy import allow_output;a.audible=allow_output(a.audible)
 meta=json.loads((a.score/'metadata.json').read_text())
 if meta.get('first_model_ns') is None or meta.get('audio_file_start_relative_first_model') is None:raise RuntimeError('Score lacks measured replay origin; cannot promise synchronized replay')
 if meta.get('capture_timing_clean') is False:print('Recorded output had timing interruptions; replay preserves rendered PCM, not hardware dropouts. See score metadata.',file=sys.stderr,flush=True)
 audio,rate=sf.read(a.score/'score.flac',dtype='float32',always_2d=True);sm=messaging.SubMaster(['modelV2'],poll='modelV2');anchor=None;count=0;flags=0;errors=[];end=False;position=None;digest=hashlib.sha256();first_frame=None;last_frame=None;max_error=0.;first_dac_wall=None;last_status=0.
 form_path=a.score/'song_form.json';form=json.loads(form_path.read_text()) if form_path.exists() else {}
 section_events=form.get('waveform_events',[]);section_decisions=form.get('decisions',[])
 from archived_music_state import ArchivedMusicState
 archived_music=ArchivedMusicState(a.score,rate)
 def callback(out,n,ti,status):
  nonlocal count,flags,end,position,first_frame,last_frame,max_error,first_dac_wall
  out.fill(0)
  if anchor is None:return
  if status:flags+=1
  mono,wall=anchor;dac=time.monotonic()+float(ti.outputBufferDacTime-ti.currentTime)
  t=(mono-meta['first_model_ns'])/1e9+dac-wall-meta['audio_file_start_relative_first_model'];expected=round(t*rate)
  if position is None:position=expected
  index=position;position+=n;max_error=max(max_error,abs(index-expected)/rate)
  lo=max(0,-index);hi=min(n,len(audio)-index)
  if hi>lo:
   chunk=audio[index+lo:index+hi];digest.update(chunk.tobytes())
   if first_frame is None:first_frame=index+lo;first_dac_wall=dac+lo/rate
   last_frame=index+hi
   if a.audible:out[lo:hi]=chunk
  count+=n
  if index>=len(audio):end=True
 def stop(*_):raise KeyboardInterrupt
 signal.signal(signal.SIGTERM,stop)
 started=None;initial=None
 try:
  with sd.OutputStream(device=a.device,samplerate=rate,channels=2,blocksize=480,dtype='float32',callback=callback):
   (a.out/'stored_ready').write_text('ready')
   while not end:
    sm.update(100)
    if sm.updated['modelV2']:
     now=time.monotonic();mono=sm.logMonoTime['modelV2']
     if initial is None:initial=(mono,now);anchor=initial;started=now
     drift=(mono-initial[0])/1e9-(now-initial[1])
     if abs(drift)>.75:raise RuntimeError('Stored-score replay paused, sought, or left 1x clock')
    if position is not None and time.monotonic()-last_status>.2:
     audio_t=position/rate-meta.get('audio_zero_host_seconds',0);past=[e for e in section_events if e['audio_s']<=audio_t];plans=[e for e in section_decisions if e.get('type')=='scheduled' and e['requested']<=audio_t<e['at']]
     state={'readiness':'READY','compute':'none','style':'Stored score','section':past[-1]['section'].upper() if past else 'ARCHIVED SCORE','next_section':plans[-1]['section'].upper() if plans else None,'buffered':max(0,(len(audio)-position)/rate),'archived_audio_s':audio_t}
     state.update(archived_music.at(audio_t))
     tmp=a.out/'roadscore_status.tmp';tmp.write_text(json.dumps(state));tmp.replace(a.out/'roadscore_status.json');last_status=time.monotonic()
    if started and time.monotonic()-started>=a.duration:break
 finally:
  (a.out/'stored_summary.json').write_text(json.dumps({'score':str(a.score),'first_dac_wall':first_dac_wall,'sample_rate':rate,'frames_presented':count,'portaudio_flags':flags,'muted':not a.audible,'first_model_ns':initial[0] if initial else None,'generation_invoked':False,'source_frame_start':first_frame,'source_frame_end':last_frame,'contiguous_samples_verified':first_frame is not None and digest.hexdigest()==hashlib.sha256(audio[first_frame:last_frame].tobytes()).hexdigest(),'max_clock_alignment_error_seconds':max_error,'synchronization':'original logMonoTime plus recorded host DAC/sample origin'},indent=2))
 if max_error>.05:raise RuntimeError('Stored-score audio clock drift exceeded 50ms')
if __name__=='__main__':main()
