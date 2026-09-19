"""Private bench road-video presentation, using existing pyray/OpenCV. No inference."""
import json,time,signal,os
from pathlib import Path
import cv2,pyray as rl
ROOT=Path('/data/roadscore');os.chdir(ROOT/'results');run=ROOT/'results/current';cv2.setNumThreads(1);closed=False

def stop(*args):
 global closed
 closed=True
signal.signal(signal.SIGTERM,stop);signal.signal(signal.SIGINT,stop)
mode=Path('/sys/class/drm/card0-DSI-1/modes').read_text().splitlines()[0];dims=[int(x) for x in mode.split('x')];W,H=max(dims),min(dims);scale=W/536
rl.set_trace_log_level(rl.TraceLogLevel.LOG_WARNING);rl.init_window(W,H,'RoadScore private replay');rl.set_target_fps(20)
cap=cv2.VideoCapture(str(ROOT/'assets/demo.mp4'));texture=None;frame_index=-1;captured=False
log=(ROOT/'results/display_timing.jsonl').open('w',buffering=1)
try:
 while not closed and not rl.window_should_close():
  s={};clock={}
  try:s=json.loads((run/'status.json').read_text());clock=json.loads((run/'clock.json').read_text())
  except (FileNotFoundError,json.JSONDecodeError):pass
  active=s.get('route')==os.environ.get('ROADSCORE_CURVE_ROUTE','').split('/')[-1] and 110<=s.get('route_t',0)<210 and time.monotonic()-clock.get('wall',0)<2
  if active:
   # Never display later than the delivered replay clock. Frame-zero offset is in the prepared MP4.
   target=max(0,int((min(s['route_t'],clock['t'])-110)*20))
   if target<frame_index or target-frame_index>30:cap.set(cv2.CAP_PROP_POS_FRAMES,target);frame_index=target-1
   frame=None
   while frame_index<target:
    ok,frame=cap.read()
    if not ok:break
    frame_index+=1
   if frame is not None:
    rgb=cv2.cvtColor(frame,cv2.COLOR_BGR2RGB);image=rl.Image(rl.ffi.from_buffer(rgb),rgb.shape[1],rgb.shape[0],1,rl.PixelFormat.PIXELFORMAT_UNCOMPRESSED_R8G8B8)
    if texture is None:texture=rl.load_texture_from_image(image)
    else:rl.update_texture(texture,rl.ffi.cast("void *",rl.ffi.from_buffer(rgb)))
  rl.begin_drawing();rl.clear_background(rl.BLACK)
  if texture is not None and active:rl.draw_texture_pro(texture,rl.Rectangle(0,(texture.height-texture.width*H/W)/2,texture.width,texture.width*H/W),rl.Rectangle(0,0,W,H),rl.Vector2(0,0),0,rl.WHITE)
  rl.draw_rectangle(0,0,W,int(30*scale),rl.Color(8,14,22,225));rl.draw_text('RoadScore',int(10*scale),int(7*scale),int(18*scale),rl.Color(120,235,200,255))
  title=(s.get('playing_identity','legacy')+'  /  '+s.get('phase','waiting')).upper() if active else 'WAITING FOR PRIVATE REPLAY'
  rl.draw_text(title,int(140*scale),int(10*scale),int(12*scale),rl.WHITE)
  if active:
   lead=s.get('lead');text=f"Model: {s.get('kind','curve')} {lead:.1f}s ahead" if lead is not None and lead>0 else 'Following the recorded drive'
   rl.draw_rectangle(0,H-int(28*scale),W,int(28*scale),rl.Color(8,14,22,225));rl.draw_text(text,int(10*scale),H-int(19*scale),int(12*scale),rl.WHITE)
   rl.draw_text('CHESTNUT LIVE' if s.get('job_inflight') else 'LOCAL SCORE',int(405*scale),H-int(18*scale),int(10*scale),rl.Color(120,235,200,255))
   log.write(json.dumps({'wall':time.monotonic(),'source_route_t':s['route_t'],'video_route_t':110+frame_index/20,'lag':s['route_t']-(110+frame_index/20)})+'\n')
  rl.end_drawing()
  if active and not captured and s.get('phase')=='anticipation':rl.take_screenshot('native_display.png');captured=True
finally:
 cap.release();log.close()
 if texture is not None:rl.unload_texture(texture)
 rl.close_window()
