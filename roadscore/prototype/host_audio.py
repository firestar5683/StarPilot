"""Host-owned bounded PCM presentation, scheduled from measured remote clock.
Capture stores exactly the final PCM with its target and observed host DAC timeline.
"""
import argparse,json,queue,subprocess,threading,time,signal
from pathlib import Path
import numpy as np
import soundfile as sf
import sounddevice as sd
from pcm_transport import read_packet
from jitter import overdue_frames

def main():
 p=argparse.ArgumentParser();p.add_argument('--bench',required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--clock',type=Path,required=True);p.add_argument('--audible',action='store_true');p.add_argument('--device',default=None);p.add_argument('--latency',type=float,default=.25);a=p.parse_args();from audio_policy import allow_output;a.audible=allow_output(a.audible)
 offset=json.loads(a.clock.read_text())['best']['bench_minus_host_seconds'];a.out.mkdir(exist_ok=True)
 packets=queue.Queue(maxsize=20);done=threading.Event();errors=[];stats={'max_absolute_timing_error_seconds':0.,'blocks':0,'late_frames':0,'starved_callbacks':0,'portaudio_flags':0,'max_queue':0,'muted':not a.audible,'target_added_latency_seconds':a.latency,'offset_seconds':offset};current=None;index=0;started=False;recovering=False
 remote=subprocess.Popen(['ssh',a.bench,'/usr/local/venv/bin/python -u /data/roadscore/prototype/pcm_transport.py /data/roadscore/results/current/pcm.sock'],stdout=subprocess.PIPE,stderr=(a.out/'pcm_ssh.log').open('w'))
 def receive():
  origin_target=None;expected_audio_s=None;expected_sequence=0;last_receive=None
  packet_log=(a.out/'transport_packets.jsonl').open('w',buffering=65536)
  try:
   while (packet:=read_packet(remote.stdout)) is not None:
    meta,raw=packet;meta['host_receive_wall']=time.monotonic()
    if meta.get('pcm_sequence',expected_sequence)!=expected_sequence:raise ValueError('PCM sequence loss or disorder')
    expected_sequence+=1
    meta['receive_gap_seconds']=0 if last_receive is None else meta['host_receive_wall']-last_receive;last_receive=meta['host_receive_wall']
    meta['transport_seconds']=meta['host_receive_wall']-(meta.get('export_wall',meta['callback_wall'])-offset)
    stats['max_transport_seconds']=max(stats.get('max_transport_seconds',0),meta['transport_seconds'])
    packet_log.write(json.dumps({k:meta.get(k) for k in ['pcm_sequence','audio_s','callback_wall','export_wall','host_receive_wall','receive_gap_seconds','transport_seconds']})+'\n')
    wave=np.frombuffer(raw,dtype='<f4').reshape(-1,2).copy()
    if expected_audio_s is not None and abs(meta['audio_s']-expected_audio_s)>1/48000:raise ValueError('PCM sample timeline discontinuity')
    if origin_target is None:origin_target=meta['callback_wall']-offset+a.latency-meta['audio_s']
    target=origin_target+meta['audio_s'];expected_audio_s=meta['audio_s']+len(wave)/48000
    status=meta.get('roadscore',{})
    if status:
     status.update(readiness=status.get('readiness') or ('DEGRADED' if status.get('worker_failed') else 'READY'),style=status.get('style') or status.get('identity',''),section=status.get('section') or ('OUTRO' if status.get('arrival_at') is not None else 'CONTINUATION'))
     tmp=a.out/'roadscore_status.tmp';tmp.write_text(json.dumps(status));tmp.replace(a.out/'roadscore_status.json')
    packets.put((meta,wave,target),timeout=3);stats['max_queue']=max(stats['max_queue'],packets.qsize())
  except Exception as e:errors.append(repr(e))
  finally:packet_log.close();done.set()
 receiver=threading.Thread(target=receive,daemon=True);receiver.start()
 recordings=queue.Queue(maxsize=400);record_stop=threading.Event()
 heard=sf.SoundFile(a.out/'host_heard.flac','w',samplerate=48000,channels=2,subtype='PCM_24');timeline=(a.out/'host_audio.jsonl').open('w',buffering=1)
 def record():
  while not record_stop.is_set() or not recordings.empty():
   try:
    wave,events=recordings.get(timeout=.1);heard.write(wave)
    for event in events:timeline.write(json.dumps(event)+'\n')
   except queue.Empty:pass
 writer=threading.Thread(target=record,daemon=True);writer.start();host_frames=0
 def callback(out,n,ti,status):
  nonlocal current,index,started,host_frames,recovering
  out.fill(0);wall=time.monotonic();dac=wall+float(ti.outputBufferDacTime-ti.currentTime)
  if status:stats['portaudio_flags']+=1
  cursor=0;events=[]
  if host_frames==0:stats['first_host_dac_wall']=dac
  while cursor<n:
   if current is None:
    try:current=packets.get_nowait();index=0
    except queue.Empty:
     if started and not done.is_set():stats['starved_callbacks']+=1;recovering=True
     break
   meta,wave,target=current
   wanted=target+index/48000;here=dac+cursor/48000
   if not started and wanted>here+1/48000:
    cursor+=min(n-cursor,max(1,round((wanted-here)*48000)));continue
   if recovering:
    skipped=overdue_frames(wanted,here,48000,len(wave)-index)
    if skipped:
     index+=skipped;stats['late_frames']+=skipped
     events.append({'type':'deadline_recovery','skipped_frames':skipped,'host_audio_s':(host_frames+cursor)/48000,'pcm_sequence':meta.get('pcm_sequence')})
    if index<len(wave):recovering=False
   if index>=len(wave):current=None;continue
   if index==0:
    stats['blocks']+=1;started=True;stats['max_absolute_timing_error_seconds']=max(stats['max_absolute_timing_error_seconds'],abs(here-target))
    events.append({**meta,'host_audio_s':(host_frames+cursor)/48000,'host_target_wall':target,'host_dac_wall':here,'host_lateness_seconds':here-target,'presentation_muted':not a.audible})
   count=min(n-cursor,len(wave)-index)
   out[cursor:cursor+count]=wave[index:index+count]
   cursor+=count;index+=count
   if index==len(wave):current=None
  try:recordings.put_nowait((out.copy(),events))
  except queue.Full:errors.append('Host capture queue full')
  host_frames+=n
  if not a.audible:out.fill(0)
 def stop(*_):raise KeyboardInterrupt
 signal.signal(signal.SIGTERM,stop)
 try:
  with sd.OutputStream(device=a.device,samplerate=48000,channels=2,blocksize=480,dtype='float32',callback=callback):
   (a.out/'host_audio_ready').write_text('ready')
   while not(done.is_set() and packets.empty() and current is None):time.sleep(.05)
 finally:
  if remote.poll() is None:remote.terminate()
  remote.wait(timeout=5);record_stop.set();writer.join(timeout=5);heard.close();timeline.close();stats['host_frames']=host_frames;
  if stats['max_absolute_timing_error_seconds']>.05:errors.append('Host DAC drift exceeded 50ms')
  stats['errors']=errors;(a.out/'host_audio_summary.json').write_text(json.dumps(stats,indent=2))
 if errors:raise RuntimeError(errors)
if __name__=='__main__':main()
