"""Observe the unmodified normal UI's own update/draw calls. No custom drawing."""
import os,json,time,runpy
from pathlib import Path
from openpilot.selfdrive.ui.ui_state import UIState, device
from preparing_awake import PreparationWake
from replay_display_hold import ReplayDisplayHold
from replay_ui_controls import ReplayUIControls, ReplayStateView, isolated_replay, apply_turn_intent
replay_controls=ReplayUIControls(os.environ['ROADSCORE_STATUS_FILE'],enabled=isolated_replay(os.environ))
if replay_controls.enabled:
 from openpilot.selfdrive.ui.mici.onroad.hud_renderer import TurnIntent
 from openpilot.selfdrive.ui.ui_state import ui_state
 original_turn_intent=TurnIntent._update_state
 def replay_turn_intent(self):
  sm=ui_state.sm
  if isinstance(sm,ReplayStateView) and apply_turn_intent(self,sm.signal_mode):return
  return original_turn_intent(self)
 TurnIntent._update_state=replay_turn_intent
display_hold=ReplayDisplayHold(os.environ.get("ROADSCORE_AUDIO_DRAIN_FILE"), enabled=os.environ.get("OPENPILOT_PREFIX")=="roadscore_replay")
original_state=UIState._update_state
def replay_state(self,*args,**kwargs):
 result=original_state(self,*args,**kwargs)
 self.started=display_hold.apply(self.started)
 if isinstance(self.sm,ReplayStateView):self.sm.apply_native_mode(self)
 return result
UIState._update_state=replay_state
preparation_wake=PreparationWake(os.environ.get("ROADSCORE_STATUS_FILE"),Path("/TICI").exists())
from openpilot.selfdrive.ui.onroad.cameraview import CameraView
from openpilot.selfdrive.ui.mici.onroad.model_renderer import ModelRenderer
if os.environ.get('ROADSCORE_CLEAN_DEMO_UI')=='1':
 from openpilot.selfdrive.ui.mici.onroad.augmented_road_view import StandstillTimerOverlay
 from openpilot.selfdrive.ui.onroad.model_renderer import ModelRenderer as StandardModelRenderer
 from openpilot.selfdrive.ui.onroad.starpilot.widgets.stopped_timer import StoppedTimerWidget
 # Process-local presentation overrides; user settings and normal driving stay intact.
 ModelRenderer._draw_lead_info=lambda self,*args,**kwargs:None
 StandardModelRenderer._draw_lead_metrics=lambda self,*args,**kwargs:None
 StandstillTimerOverlay.render=lambda self,*args,**kwargs:False
 StoppedTimerWidget._update_timer=lambda self:0
counts={'accepted_camera_frames':0,'path_draw_calls':0,'lane_draw_calls':0,'nonempty_path_draws':0,'nonempty_lane_draws':0,'camera_texture_draws':0};last=0.;original_update=UIState.update;original_accept=CameraView._accept_frame;original_path=ModelRenderer._draw_path;original_lanes=ModelRenderer._draw_lane_lines;original_textures=CameraView._render_textures
out=Path(os.environ['ROADSCORE_UI_AUDIT']).open('w',buffering=1)
def accept(self,*args,**kw):
 value=original_accept(self,*args,**kw)
 if value:counts['accepted_camera_frames']+=1
 return value
def path(self,*args,**kw):
 counts['path_draw_calls']+=1
 if self._path.projected_points.size:counts['nonempty_path_draws']+=1
 return original_path(self,*args,**kw)
def lanes(self,*args,**kw):
 counts['lane_draw_calls']+=1
 if any(x.projected_points.size for x in self._lane_lines):counts['nonempty_lane_draws']+=1
 return original_lanes(self,*args,**kw)
def textures(self,*args,**kw):
 if self.frame is not None and self.texture_y is not None and self.texture_y.id and self.texture_uv is not None and self.texture_uv.id:counts['camera_texture_draws']+=1
 return original_textures(self,*args,**kw)
def update(self,*args,**kw):
 global last
 if replay_controls.enabled and not isinstance(self.sm,ReplayStateView):
  self.sm=ReplayStateView(self.sm,replay_controls)
 preparation_wake.update(self,device)
 result=original_update(self,*args,**kw);now=time.monotonic()
 if now-last>=1:
  out.write(json.dumps({'wall':now,'started':bool(self.started),'speed':float(self.sm['carState'].vEgo),'model_mono_ns':self.sm.logMonoTime['modelV2'],'model_points':len(self.sm['modelV2'].position.x),'replay_demo':self.sm.snapshot() if isinstance(self.sm,ReplayStateView) else None,'engaged':bool(self.engaged),'aol':bool(self.always_on_lateral_active),'ui_status':str(self.status),**counts})+'\n');last=now
 return result
UIState.update=update;CameraView._accept_frame=accept;CameraView._render_textures=textures;ModelRenderer._draw_path=path;ModelRenderer._draw_lane_lines=lanes
from overlay import install
install()
runpy.run_path(str(Path(os.environ['BASEDIR'])/'selfdrive/ui/ui.py'),run_name='__main__')
