"""Optional external overlay on the existing normal UI; no public source modifications."""
import json,time,os
from overlay_view import draw_panel, overlay_view, EventPresentation, hud_bounds, startup_bounds
from pathlib import Path

def install():
 if os.environ.get('ROADSCORE_OVERLAY')!='1':return
 import pyray as rl
 from openpilot.system.ui.lib.application import gui_app,FontWeight
 original=gui_app.render;last=0.;state={};frames=0;captured=False;capture_ready_since=None;captured_events=set();alert_clear_after=0.;native_nav_visible=False;home_footer_right=None;home_rect=None;status_mtime=None;status_read_error=None;event_presentation=EventPresentation();alert_seen_at=None;alert_captured=False
 # Observe the actual native nav card; it keeps priority over this accessory.
 from openpilot.selfdrive.ui.onroad.starpilot.navigation_card import NavigationCardRenderer
 original_nav_render=NavigationCardRenderer._render
 def nav_render(widget,rect):
  nonlocal native_nav_visible
  result=original_nav_render(widget,rect)
  native_nav_visible=native_nav_visible or widget._valid
  return result
 NavigationCardRenderer._render=nav_render
 from openpilot.selfdrive.ui.mici.layouts.home import MiciHomeLayout
 original_home_render=MiciHomeLayout._render
 def home_render(widget,rect):
  nonlocal home_footer_right,home_rect
  result=original_home_render(widget,rect)
  home_rect=(widget.rect.x,widget.rect.y,widget.rect.width,widget.rect.height)
  if abs(widget.rect.x)<1 and abs(widget.rect.y)<1:
   home_footer_right=max((w.rect.x+w.rect.width for w in widget._status_bar_layout.widgets if w.is_visible),default=0)
  return result
 MiciHomeLayout._render=home_render
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
  nonlocal last,state,frames,captured,capture_ready_since,alert_clear_after,alert_seen_at,alert_captured,status_mtime,status_read_error
  now=time.monotonic()
  if now-last>.2:
   try:
    state=json.loads(path.read_text());status_mtime=path.stat().st_mtime;status_read_error=None
   except (OSError,ValueError) as error:status_read_error=type(error).__name__
   last=now
  from openpilot.selfdrive.ui.ui_state import ui_state
  # The native alert owns the display. Leave room for its existing fade-out too.
  for service in ('selfdriveState','starpilotSelfdriveState'):
   size=ui_state.sm[service].alertSize
   if int(size.raw)>0:alert_clear_after=now+1.
  frames+=1
  if frames==1:path.with_name('ui_capture_origin.json').write_text(json.dumps({'wall':time.monotonic(),'frame':0}))
  startup=home_footer_right is not None or not ui_state.started
  bounds=(startup_bounds(gui_app.width,gui_app.height,home_footer_right or 0) if startup else hud_bounds(gui_app.width,gui_app.height))
  def audit(visible,reason,presentation=None):
   evidence={'frame':frames-1,'frames':frames,'native_gpu_icon':False,'wall':now,'state':state,'overlay_visible':visible,'overlay_hidden_reason':reason,
             'started':bool(ui_state.started),'home_rect':home_rect,'home_footer_right':home_footer_right,
             'native_nav_visible':native_nav_visible,'overlay_bounds':bounds,'status_path':str(path),
             'status_age_seconds':max(0,time.time()-status_mtime) if status_mtime is not None else None,
             'status_read_error':status_read_error,'presentation':presentation}
   if os.environ.get('ROADSCORE_CAPTURE_TIMING')=='1':
    with path.with_name('ui_frames.jsonl').open('a') as log:log.write(json.dumps(evidence)+'\n')
   if frames%60==1:path.with_name('overlay_status.json').write_text(json.dumps(evidence))
  if now<alert_clear_after:
   audit(False,'native_alert')
   if alert_seen_at is None:alert_seen_at=now
   if os.environ.get('ROADSCORE_CAPTURE_EVENTS')=='1' and not alert_captured and now-alert_seen_at>.7 and os.environ.get('ROADSCORE_OVERLAY_CAPTURE'):
    capture_image(Path(os.environ['ROADSCORE_OVERLAY_CAPTURE']).with_name('overlay-native-alert.png'));alert_captured=True
   return
  alert_seen_at=None
  if native_nav_visible:
   audit(False,'native_navigation');return
  if not ui_state.started and home_footer_right is None:
   audit(False,'home_not_visible');return
  if home_rect and -home_rect[2]+1 < home_rect[0] < -1:
   audit(False,'home_transition');return
  if bounds is None:
   audit(False,'no_free_space');return
  presentation=event_presentation.update(overlay_view(state),now)
  view=draw_panel(rl,gui_app.font(FontWeight.NORMAL),state,gui_app.width,gui_app.height,gui_app.font(FontWeight.SEMI_BOLD),presentation,startup=startup,footer_right=home_footer_right or 0)
  ready=view['ready']
  audit(True,None,view)
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
  nonlocal native_nav_visible,home_footer_right,home_rect
  for should_render in original(*args,**kwargs):
   yield should_render
   if should_render:draw()
   native_nav_visible=False;home_footer_right=None;home_rect=None
 gui_app.render=render
