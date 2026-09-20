"""Offline same-generation motion A/B from an immutable captured demo."""
import argparse,hashlib,json,time
from pathlib import Path
import numpy as np
import soundfile as sf
from motion_presentation import MotionPresentation


def sha(path):
  h=hashlib.sha256()
  with path.open('rb') as handle:
    for chunk in iter(lambda:handle.read(1024*1024),b''):h.update(chunk)
  return h.hexdigest()


def render(locked,out):
  source=locked/'render/heard.wav';tracepath=locked/'render/trace.jsonl';blockpath=locked/'render/audio_blocks.jsonl'
  protected={str(p):sha(p) for p in (source,tracepath,blockpath)}
  rows=[json.loads(line) for line in tracepath.read_text().splitlines()]
  blocks=[json.loads(line) for line in blockpath.read_text().splitlines()]
  out.mkdir(parents=True,exist_ok=False)
  info=sf.info(source);rate=info.samplerate
  if rate!=48000 or info.channels!=2:raise ValueError('Expected archived48k stereo PCM')
  dsp=MotionPresentation(rate,enabled=True);index=-1;times=[];states=[]
  with sf.SoundFile(source) as src,sf.SoundFile(out/'full_motion.wav','w',samplerate=rate,channels=2,subtype='FLOAT') as dst:
    for i,block in enumerate(blocks):
      start=round(block['audio_s']*rate);end=round(blocks[i+1]['audio_s']*rate) if i+1<len(blocks) else info.frames
      if src.tell()!=start:raise ValueError('Captured audio blocks are not contiguous')
      pcm=src.read(end-start,dtype='float32',always_2d=True)
      while index+1<len(rows) and rows[index+1]['command_wall']<=block['callback_wall']:index+=1
      row=rows[index] if index>=0 else {}
      fresh=bool(block.get('signal_fresh') and row and 0<=block['callback_wall']-row['command_wall']<=.5)
      open_mix=row.get('engagement_presentation',{}).get('rendered_open_mix',0.) if block.get('engagement_active') and block.get('engagement_fresh') else 0.
      before=time.perf_counter()
      y=dsp.process(pcm,speed=row.get('speed',0.),source_fresh=fresh,engagement_open_mix=open_mix)
      times.append(time.perf_counter()-before);dst.write(y)
      states.append(dict(audio_s=start/rate,route_t=row.get('route_t'),source_age_seconds=block['callback_wall']-row.get('command_wall',block['callback_wall']),signal_fresh=block.get('signal_fresh'),steering=row.get('steering'),speed=row.get('speed'),fresh=fresh,**dsp.snapshot()['motion_presentation']))
  transitions=[state for previous,state in zip(states,states[1:]) if previous['stopped'] and not state['stopped'] and state['fresh'] and state.get('speed',0)>=.8]
  event=transitions[0] if transitions else min(states,key=lambda x:x['rendered_open_mix'])
  start=max(0.,min(info.duration-45,event['audio_s']-15));end=min(info.duration,start+45)
  for name,path in [('A_baseline.wav',source),('B_motion.wav',out/'full_motion.wav')]:
    with sf.SoundFile(path) as audio:
      audio.seek(round(start*rate));pcm=audio.read(round((end-start)*rate),dtype='float32',always_2d=True)
    sf.write(out/name,pcm,rate,subtype='FLOAT')
  after={str(p):sha(p) for p in (source,tracepath,blockpath)}
  if protected!=after:raise RuntimeError('Protected source changed during review')
  report=dict(source_sha256=protected,source_unchanged=True,excerpt_start_audio_s=start,excerpt_end_audio_s=end,
              selection='45 seconds around first causal stopped-to-moving transition; no manual event triggers',
              cpu_host='Mac offline; not a device benchmark',dsp_median_ms=float(np.median(times)*1000),dsp_p95_ms=float(np.quantile(times,.95)*1000),dsp_max_ms=max(times)*1000,dsp_rtf=sum(times)/info.duration,
              input_alignment='Latest recorded trace command_wall at or before callback_wall; recorded carState freshness; no interpolation/future rows',
              output='Post-process exact archived heard.wav; preserve existing engagement/cues, motion filter has unity gain/width; existing engagement remains present',
              physical_bluetooth_latency='Not measured; these files compare musical processing, not speaker/video synchronization',
              settings=dsp.snapshot(),sample_frames=info.frames)
  (out/'report.json').write_text(json.dumps(report,indent=2));(out/'motion_states.json').write_text(json.dumps(states))
  (out/'index.html').write_text('''<!doctype html><meta name="viewport" content="width=device-width,initial-scale=1"><title>RoadScore motion A/B</title><style>body{background:#101016;color:#eee;font:18px system-ui;max-width:760px;margin:40px auto;padding:20px}audio{width:100%;margin:12px 0}p{line-height:1.5;color:#bbb}</style><h1>Stop / pullaway presentation A/B</h1><p>Same accepted recording and same 45-second excerpt. B uses a strong 900 Hz low-pass while stopped and opens as the car starts moving. No regeneration, new melody, gain normalization or event samples.</p><h2>A · Locked baseline</h2><audio controls src="A_baseline.wav"></audio><h2>B · Optional motion containment</h2><audio controls src="B_motion.wav"></audio><p>Default remains off. This is a musical comparison, not Bluetooth/video synchronization. Existing engagement processing remains intact. This cannot isolate a lead instrument from a stereo mix.</p>''')
  return report

if __name__=='__main__':
  p=argparse.ArgumentParser();p.add_argument('locked',type=Path);p.add_argument('output',type=Path);a=p.parse_args();print(json.dumps(render(a.locked,a.output),indent=2))
