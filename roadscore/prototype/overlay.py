"""Optional external overlay on the existing normal UI; no public source modifications."""
import json,time,os
from pathlib import Path

def install():
 if os.environ.get('ROADSCORE_OVERLAY')!='1':return
 import pyray as rl
 from openpilot.system.ui.lib.application import gui_app,FontWeight
 original=gui_app.render;last=0.;state={};icons={};frames=0;captured=False;capture_ready_since=None
 path=Path(os.environ['ROADSCORE_STATUS_FILE'])
 def draw():
  nonlocal last,state,frames,captured,capture_ready_since
  now=time.monotonic()
  if now-last>.2:
   try:state=json.loads(path.read_text())
   except (OSError,ValueError):pass
   last=now
  readiness=state.get('readiness','Preparing');ready=readiness=='READY'
  extra=bool(state.get('gesture_active') or state.get('gesture_queued') or state.get('turn_signal_music'));height=126 if extra else 104
  x=12;y=max(12,gui_app.height-height-12);width=min(320,gui_app.width*.55)
  rl.draw_rectangle_rounded(rl.Rectangle(x,y,width,height),.12,8,rl.Color(15,22,31,220))
  key='crossed' if state.get('compute')=='none' else ('green' if ready else 'loading')
  if key not in icons:
   try:icons[key]=gui_app.texture('icons_mici/egpu_'+key+'.png',24,18)
   except Exception:icons[key]=None
  if icons[key]:rl.draw_texture(icons[key],x+10,y+10,rl.WHITE)
  font=gui_app.font(FontWeight.NORMAL)
  lines=[f"RoadScore / {state.get('style','Preparing')}",state.get('section',readiness)]
  if state.get('next_section'):lines[1]+=' > '+state['next_section']
  lead=state.get('lead');detail=f'Curve {lead:.1f}s / ' if isinstance(lead,(int,float)) and lead>0 else ''
  detail+=f"{readiness} / Buffer {(state.get('buffered') or 0):.0f}s"
  elapsed=state.get('generation_elapsed_seconds')
  backend='ACE / CHESTNUT' if state.get('composer')=='ace' else str(state.get('composer','LOCAL')).upper()
  activity='GENERATING' if state.get('job_inflight') else readiness
  if state.get('job_inflight') and isinstance(elapsed,(int,float)):activity+=f' {elapsed:.1f}s'
  lines.append(f'{backend} / {activity}')
  lines.append(detail)
  if extra:
   active=state.get('gesture_active') or [];queued=state.get('gesture_queued') or []
   gesture='Signal percussion' if state.get('turn_signal_music') else (active[0] if active else ('Queued '+queued[0]['kind'] if queued else ''))
   lines.append(str(gesture).replace('_',' '))
  for i,line in enumerate(lines):rl.draw_text_ex(font,str(line),rl.Vector2(x+(42 if i==0 else 10),y+10+i*22),13,0,rl.WHITE)
  frames+=1
  if frames==1:path.with_name('ui_capture_origin.json').write_text(json.dumps({'wall':time.monotonic(),'frame':0}))
  if os.environ.get('ROADSCORE_CAPTURE_TIMING')=='1':
   with path.with_name('ui_frames.jsonl').open('a') as audit:audit.write(json.dumps({'frame':frames-1,'wall':time.monotonic(),'state':state})+'\n')
  if frames%60==1:path.with_name('overlay_status.json').write_text(json.dumps({'frames':frames,'native_gpu_icon':bool(icons[key]),'state':state}))
  from openpilot.selfdrive.ui.ui_state import ui_state
  if ready and ui_state.started and capture_ready_since is None:capture_ready_since=now
  if capture_ready_since is not None and now-capture_ready_since>=5 and ui_state.started and not captured and os.environ.get("ROADSCORE_OVERLAY_CAPTURE"):
   captured=True
   from PIL import Image
   rl.rl_draw_render_batch_active()
   image=rl.load_image_from_texture(gui_app._render_texture.texture) if gui_app._render_texture else rl.load_image_from_screen()
   try:
    data=bytes(rl.ffi.buffer(image.data,image.width*image.height*4))
    picture=Image.frombytes('RGBA',(image.width,image.height),data)
    if gui_app._render_texture:picture=picture.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
    picture.save(os.environ['ROADSCORE_OVERLAY_CAPTURE'])
   finally:rl.unload_image(image)
 def render(*args,**kwargs):
  for should_render in original(*args,**kwargs):
   yield should_render
   if should_render:draw()
 gui_app.render=render
