"""Optional external overlay on the existing normal UI; no public source modifications."""
import json,time,os
from overlay_view import draw_panel, overlay_view, EventPresentation
from pathlib import Path

def install():
 if os.environ.get('ROADSCORE_OVERLAY')!='1':return
 import pyray as rl
 from openpilot.system.ui.lib.application import gui_app,FontWeight
 original=gui_app.render;last=0.;state={};frames=0;captured=False;capture_ready_since=None;captured_events=set();alert_clear_after=0.;native_nav_visible=False;event_presentation=EventPresentation();alert_seen_at=None;alert_captured=False
 # Observe the actual native nav card; it keeps priority over this accessory.
 from openpilot.selfdrive.ui.onroad.starpilot.navigation_card import NavigationCardRenderer
 original_nav_render=NavigationCardRenderer._render
 def nav_render(widget,rect):
  nonlocal native_nav_visible
  result=original_nav_render(widget,rect)
  native_nav_visible=native_nav_visible or widget._valid
  return result
 NavigationCardRenderer._render=nav_render
 path=Path(os.environ['ROADSCORE_STATUS_FILE'])
 def capture_image(target):
  from PIL import Image
  rl.rl_draw_render_batch_active()
  image=rl.load_image_from_texture(gui_app._render_texture.texture) if gui_app._render_texture else rl.load_image_from_screen()
  try:
   data=bytes(rl.ffi.buffer(image.data,image.width*image.height*4))
   picture=Image.frombytes('RGBA',(image.width,image.height),data)
   if gui_app._render_texture:picture=picture.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
   picture.save(target)
  finally:rl.unload_image(image)
 def draw():
  nonlocal last,state,frames,captured,capture_ready_since,alert_clear_after,alert_seen_at,alert_captured
  now=time.monotonic()
  if now-last>.2:
   try:state=json.loads(path.read_text())
   except (OSError,ValueError):pass
   last=now
  from openpilot.selfdrive.ui.ui_state import ui_state
  # The native alert owns the display. Leave room for its existing fade-out too.
  for service in ('selfdriveState','starpilotSelfdriveState'):
   size=ui_state.sm[service].alertSize
   if int(size.raw)>0:alert_clear_after=now+1.
  frames+=1
  if frames==1:path.with_name('ui_capture_origin.json').write_text(json.dumps({'wall':time.monotonic(),'frame':0}))
  if os.environ.get('ROADSCORE_CAPTURE_TIMING')=='1':
   with path.with_name('ui_frames.jsonl').open('a') as audit:audit.write(json.dumps({'frame':frames-1,'wall':time.monotonic(),'state':state,'overlay_visible':not(now<alert_clear_after or native_nav_visible)})+'\n')
  if now<alert_clear_after:
   if alert_seen_at is None:alert_seen_at=now
   if os.environ.get('ROADSCORE_CAPTURE_EVENTS')=='1' and not alert_captured and now-alert_seen_at>.7 and os.environ.get('ROADSCORE_OVERLAY_CAPTURE'):
    capture_image(Path(os.environ['ROADSCORE_OVERLAY_CAPTURE']).with_name('overlay-native-alert.png'));alert_captured=True
   return
  alert_seen_at=None
  if native_nav_visible:return
  presentation=event_presentation.update(overlay_view(state),now)
  view=draw_panel(rl,gui_app.font(FontWeight.NORMAL),state,gui_app.width,gui_app.height,gui_app.font(FontWeight.SEMI_BOLD),presentation)
  ready=view['ready']
  if frames%60==1:path.with_name('overlay_status.json').write_text(json.dumps({'frames':frames,'native_gpu_icon':False,'presentation':view,'state':state}))
  from openpilot.selfdrive.ui.ui_state import ui_state
  if ready and ui_state.started and capture_ready_since is None:capture_ready_since=now
  capture_target=None
  capture_path=os.environ.get("ROADSCORE_OVERLAY_CAPTURE")
  if capture_path and ui_state.started:
   if capture_ready_since is not None and now-capture_ready_since>=5 and not captured:
    captured=True;capture_target=Path(capture_path)
   kind=view.get('event_kind')
   if os.environ.get('ROADSCORE_CAPTURE_EVENTS')=='1' and view.get('event_state')=='active' and kind and kind not in captured_events:
    captured_events.add(kind);capture_target=Path(capture_path).with_name('overlay-event-'+kind+'.png')
  if capture_target is not None:capture_image(capture_target)
 def render(*args,**kwargs):
  nonlocal native_nav_visible
  for should_render in original(*args,**kwargs):
   native_nav_visible=False
   yield should_render
   if should_render:draw()
 gui_app.render=render
