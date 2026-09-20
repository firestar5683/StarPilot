"""Render a timestamp-aligned road-camera/DSP comparison from archived inputs."""
import argparse,bisect,json,subprocess
from fractions import Fraction
from pathlib import Path
import av
from PIL import Image,ImageDraw,ImageFont

p=argparse.ArgumentParser();p.add_argument('review',type=Path);p.add_argument('camera',type=Path);p.add_argument('--camera-at-audio-zero',type=float,required=True);a=p.parse_args()
report=json.loads((a.review/'report.json').read_text());start=report['excerpt_start_audio_s'];duration=30.;states=json.loads((a.review/'motion_states.json').read_text());times=[v['audio_s'] for v in states]
fontpath='/System/Library/Fonts/Supplemental/Arial.ttf'
font=ImageFont.truetype(fontpath,24);large=ImageFont.truetype(fontpath,36);small=ImageFont.truetype(fontpath,18)
for variant in ('A','B'):
 source=av.open(str(a.camera));vs=source.streams.video[0];seek=a.camera_at_audio_zero+start;source.seek(max(0,int(seek/float(vs.time_base))),stream=vs);frames=source.decode(vs);previous=None;following=next(frames)
 temp=a.review/f'{variant}_picture.mp4';out=av.open(str(temp),'w');stream=out.add_stream('libx264',rate=20);stream.width=1280;stream.height=720;stream.pix_fmt='yuv420p';stream.options={'crf':'19','preset':'fast'}
 for i in range(round(duration*20)):
  t=i/20;target=seek+t
  while following is not None and float(following.pts*following.time_base)<=target:
   previous=following;following=next(frames,None)
  frame=previous or following
  if frame is None:raise RuntimeError('Camera ended before comparison')
  canvas=Image.new('RGB',(1280,720),(15,18,23));draw=ImageDraw.Draw(canvas)
  draw.text((28,22),'STOP / PULL AWAY',font=large,fill='white')
  draw.text((28,69),'Same recorded music and road events · offline DSP comparison',font=small,fill='#aab3bf')
  road=frame.to_image().resize((952,598));canvas.paste(road,(24,100))
  state=states[max(0,bisect.bisect_right(times,start+t)-1)];mix=state['rendered_open_mix'];speed=max(0,state.get('speed',0) or 0)
  draw.text((1000,115),f'{variant}  '+('BASELINE' if variant=='A' else 'STOP FILTER'),font=font,fill='white')
  draw.text((1000,178),f'{speed*3.6:.1f} km/h',font=large,fill='white')
  draw.text((1000,233),'STOPPED' if state['stopped'] else 'MOVING',font=font,fill='#ffbd67' if state['stopped'] else '#67e5bc')
  draw.text((1000,302),'Filter containment',font=small,fill='#aab3bf')
  strength=1-mix if variant=='B' else 0
  draw.rounded_rectangle((1000,335,1248,359),radius=8,fill='#323943')
  if strength>.001:draw.rounded_rectangle((1000,335,1000+248*strength,359),radius=8,fill='#ffbd67')
  draw.text((1000,387),('900 Hz low-pass' if strength>.98 else 'Opening / closing' if strength>.01 else 'Full bandwidth'),font=small,fill='white')
  draw.text((1000,445),'Listen at 6–15 s:',font=small,fill='#aab3bf');draw.text((1000,476),'muffled at stop,',font=small,fill='white');draw.text((1000,505),'bright on pullaway.',font=small,fill='white')
  draw.text((1000,650),f'{t:04.1f} / {duration:.0f} s',font=font,fill='#aab3bf')
  if variant=='B' and i==180:canvas.save(a.review/'preview.png')
  encoded=av.VideoFrame.from_image(canvas);encoded.pts=i;encoded.time_base=Fraction(1,20)
  for packet in stream.encode(encoded):out.mux(packet)
 for packet in stream.encode():out.mux(packet)
 out.close();source.close()
 audio=a.review/('A_baseline.wav' if variant=='A' else 'B_motion.wav');output=a.review/f'{variant}_road_comparison.mp4'
 subprocess.run(['/opt/homebrew/bin/ffmpeg','-v','error','-y','-i',str(temp),'-i',str(audio),'-t',str(duration),'-map','0:v','-map','1:a','-c:v','copy','-c:a','aac','-b:a','192k','-movflags','+faststart',str(output)],check=True);temp.unlink()
(a.review/'video_alignment.json').write_text(json.dumps({'audio_start':start,'duration':duration,'camera_at_audio_zero':a.camera_at_audio_zero,'type':'offline recorded-road review, not a native onroad UI capture','physical_bluetooth_sync':'not measured'},indent=2))
(a.review/'video.html').write_text('''<!doctype html><meta name="viewport" content="width=device-width,initial-scale=1"><title>RoadScore stop / pull-away</title><style>body{background:#101216;color:white;font:18px system-ui;max-width:1100px;margin:30px auto;padding:16px}video{width:100%}button{padding:14px;margin:6px;font:inherit}</style><h1>Stop / pull away</h1><p>Same music and recorded road events. Listen at 6–15 seconds: B should muffle at the stop and open on pullaway. This is an offline DSP review, not a native UI capture.</p><button onclick="swap('A')">A · Baseline</button><button onclick="swap('B')">B · Stop filter</button><video id="v" controls src="B_road_comparison.mp4"></video><script>const v=document.getElementById('v');function swap(letter){const t=v.currentTime,paused=v.paused;v.src=letter+'_road_comparison.mp4';v.onloadedmetadata=()=>{v.currentTime=t;if(!paused)v.play();};}</script>''')
print(a.review/'video.html')
