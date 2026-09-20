from collections import namedtuple
from types import SimpleNamespace
import unittest

from mac_showcase import parser
from showcase_fullscreen import FullscreenCanvas, install, viewport


class FullscreenTests(unittest.TestCase):
  def test_aspect_and_center_preserved_on_wide_and_tall_monitors(self):
    for width,height in ((1440,900),(1920,1080),(2560,1080),(900,1440)):
      x,y,w,h=viewport(width,height,536,240)
      self.assertAlmostEqual(w/h,536/240)
      self.assertAlmostEqual(x*2+w,width);self.assertAlmostEqual(y*2+h,height)
      self.assertGreaterEqual(x,0);self.assertGreaterEqual(y,0)
      self.assertLessEqual(w,width);self.assertLessEqual(h,height)

  def test_pointer_maps_canvas_corners_and_letterbox_stays_outside(self):
    app=SimpleNamespace(_scale=1.,_scaled_width=536,_scaled_height=240,width=536,height=240)
    canvas=FullscreenCanvas(None,app);canvas.rect=viewport(1440,900,536,240)
    Pos=namedtuple('Pos','x y');Event=namedtuple('Event','pos')
    x,y,w,h=canvas.rect
    self.assertEqual(canvas.map_event(Event(Pos(x,y))).pos,Pos(0.,0.))
    corner=canvas.map_event(Event(Pos(x+w,y+h))).pos
    self.assertAlmostEqual(corner.x,536.);self.assertAlmostEqual(corner.y,240.)
    self.assertLess(canvas.map_event(Event(Pos(0,0))).pos.y,0)

  def test_flag_defaults_and_device_gates(self):
    self.assertFalse(parser().parse_args([]).fullscreen)
    self.assertTrue(parser().parse_args(['--fullscreen']).fullscreen)
    env=dict(ROADSCORE_FULLSCREEN='1',ROADSCORE_PREPARED_SHOWCASE='1',SIMULATION='1',BIG='0')
    self.assertFalse(install(None,None,environ=env,platform='linux'))
    for patch in ({'ROADSCORE_FULLSCREEN':'0'},{'SIMULATION':'0'},{'BIG':'1'},{'ROADSCORE_PREPARED_SHOWCASE':'0'}):
      self.assertFalse(install(None,None,environ=env|patch,platform='darwin'))

  def test_resize_reallocates_canvas_and_escape_toggles_without_close(self):
    allocations=[];keys=set();toggles=[]
    rl=SimpleNamespace(KeyboardKey=SimpleNamespace(KEY_F11=11,KEY_F=70,KEY_ESCAPE=27),
      ConfigFlags=SimpleNamespace(FLAG_BORDERLESS_WINDOWED_MODE=1),
      TextureFilter=SimpleNamespace(TEXTURE_FILTER_BILINEAR=1),
      is_key_pressed=lambda key:key in keys,is_window_state=lambda flag:True,
      toggle_borderless_windowed=lambda:toggles.append(True),get_screen_width=lambda:1440,get_screen_height=lambda:900,
      get_render_width=lambda:2880,get_render_height=lambda:1800,unload_render_texture=lambda texture:None,
      load_render_texture=lambda w,h:allocations.append((w,h)) or SimpleNamespace(texture=1),set_texture_filter=lambda *args:None)
    app=SimpleNamespace(_scale=1.,_scaled_width=536,_scaled_height=240,width=536,height=240,
                        _render_texture=None,_patch_scissor_mode=lambda:None)
    canvas=FullscreenCanvas(rl,app);canvas.update();canvas.update()
    self.assertEqual(len(allocations),1)
    self.assertEqual(allocations[0][0],2880)
    self.assertAlmostEqual(app._pixel_scale_x,2880/536)
    keys.add(27);canvas.update();self.assertEqual(len(toggles),1)


if __name__=='__main__':unittest.main()
