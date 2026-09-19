"""Optional external overlay on the existing normal UI; no public source modifications."""
import json,time,os
from overlay_view import draw_panel
from pathlib import Path

def install():
 if os.environ.get('ROADSCORE_OVERLAY')!='1':return
 import pyray as rl
 from openpilot.system.ui.lib.application import gui_app,FontWeight
 original=gui_app.render;last=0.;state={};frames=0;captured=False;capture_ready_since=None
 path=Path(os.environ['ROADSCORE_STATUS_FILE'])
 def draw():
  nonlocal last,state,frames,captured,capture_ready_since
  now=time.monotonic()
  if now-last>.2:
   try:state=json.loads(path.read_text())
   except (OSError,ValueError):pass
   last=now
  view=draw_panel(rl,gui_app.font(FontWeight.NORMAL),state,gui_app.width,gui_app.height)
  ready=view['ready']
  frames+=1
  if frames==1:path.with_name('ui_capture_origin.json').write_text(json.dumps({'wall':time.monotonic(),'frame':0}))
  if os.environ.get('ROADSCORE_CAPTURE_TIMING')=='1':
   with path.with_name('ui_frames.jsonl').open('a') as audit:audit.write(json.dumps({'frame':frames-1,'wall':time.monotonic(),'state':state})+'\n')
  if frames%60==1:path.with_name('overlay_status.json').write_text(json.dumps({'frames':frames,'native_gpu_icon':False,'presentation':view,'state':state}))
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
