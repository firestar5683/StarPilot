"""Observe the unmodified normal UI's own update/draw calls. No custom drawing."""
import os,json,time,runpy
from pathlib import Path
from openpilot.selfdrive.ui.ui_state import UIState, device
from preparing_awake import PreparationWake
preparation_wake=PreparationWake(os.environ.get("ROADSCORE_STATUS_FILE"),Path("/TICI").exists())
from openpilot.selfdrive.ui.onroad.cameraview import CameraView
from openpilot.selfdrive.ui.mici.onroad.model_renderer import ModelRenderer
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
 preparation_wake.update(self,device)
 result=original_update(self,*args,**kw);now=time.monotonic()
 if now-last>=1:
  out.write(json.dumps({'wall':now,'started':bool(self.started),'speed':float(self.sm['carState'].vEgo),'model_mono_ns':self.sm.logMonoTime['modelV2'],'model_points':len(self.sm['modelV2'].position.x),**counts})+'\n');last=now
 return result
UIState.update=update;CameraView._accept_frame=accept;CameraView._render_textures=textures;ModelRenderer._draw_path=path;ModelRenderer._draw_lane_lines=lanes
from overlay import install
install()
runpy.run_path(str(Path(os.environ['BASEDIR'])/'selfdrive/ui/ui.py'),run_name='__main__')
