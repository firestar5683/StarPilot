import ast
import json
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'roadscore/prototype'))
import overlay
from overlay_view import overlay_view


def native_scroller_home_rect():
  tree = ast.parse((ROOT/'system/ui/widgets/scroller.py').read_text())
  cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == '_Scroller')
  method = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == '_layout')
  namespace = {'DO_JELLO': False}
  exec(compile(ast.fix_missing_locations(ast.Module(body=[method], type_ignores=[])), '<native scroller layout>', 'exec'), namespace)
  class Item:
    is_visible = True
    def __init__(self): self.rect = NS(x=0,y=0,width=536,height=240)
    def set_position(self,x,y): self.rect.x=x;self.rect.y=y
    def set_parent_rect(self,rect): pass
  items = [Item(),Item(),Item()]
  scroller = NS(_items=items,_horizontal=True,_spacing=0,_pad=0,_rect=NS(x=0,y=0,width=536,height=240),
                _get_scroll=lambda *_:-536,_item_pos_filter=NS(update=lambda _:None),
                _do_move_animation=lambda item,x,y:(x,y))
  namespace['_layout'](scroller)
  return items[1].rect


class OverlayRenderOrderTests(unittest.TestCase):
  def test_real_scroller_moves_home_from_second_slot_to_screen_origin(self):
    rect = native_scroller_home_rect()
    self.assertEqual((rect.x,rect.y,rect.width,rect.height),(0,0,536,240))

  def test_home_hook_survives_application_yield_and_hidden_audit_is_honest(self):
    # The native application renders its nav widgets before yielding frame_ready.
    source=(ROOT/'system/ui/lib/application.py').read_text()
    self.assertLess(source.index('widget.render(rl.Rectangle(0, 0, self.width, self.height))'),source.index('yield True'))
    class Home:
      rect=native_scroller_home_rect()
      _status_bar_layout=NS(widgets=[NS(is_visible=True,rect=NS(x=x,width=48)) for x in (8,74,140)])
      def _render(self,rect): pass
    class Nav:
      _valid=True
      def _render(self,rect): pass
    home=Home();nav=Nav()
    def native_frames():
      home._render(home.rect)
      yield True
      home._render(home.rect)
      nav._render(None)
      yield True
    gui=NS(render=native_frames,width=536,height=240,font=lambda _:None)
    state=NS(started=True,sm={s:NS(alertSize=NS(raw=0)) for s in ('selfdriveState','starpilotSelfdriveState')})
    modules={'pyray':NS(), 'openpilot.system.ui.lib.application':NS(gui_app=gui,FontWeight=NS(NORMAL=0,SEMI_BOLD=1)),
             'openpilot.selfdrive.ui.mici.layouts.home':NS(MiciHomeLayout=Home),
             'openpilot.selfdrive.ui.onroad.starpilot.navigation_card':NS(NavigationCardRenderer=Nav),
             'openpilot.selfdrive.ui.ui_state':NS(ui_state=state)}
    with tempfile.TemporaryDirectory() as folder:
      path=Path(folder)/'roadscore_status.json';path.write_text(json.dumps({'readiness':'PREPARING','profile':'prism'}))
      os.utime(path,(time.time()-300,time.time()-300))
      with patch.dict(sys.modules,modules),patch.dict(os.environ,{'ROADSCORE_OVERLAY':'1','ROADSCORE_STATUS_FILE':str(path),'ROADSCORE_CAPTURE_TIMING':'1'}),patch.object(overlay,'draw_panel',return_value=overlay_view({'readiness':'PREPARING'})) as draw:
        overlay.install();list(gui.render())
      rows=[json.loads(line) for line in path.with_name('ui_frames.jsonl').read_text().splitlines()]
      self.assertTrue(rows[0]['overlay_visible'])
      self.assertEqual(rows[0]['home_rect'],[0,0,536,240])
      self.assertEqual(rows[0]['overlay_bounds'],[294,172,230,60])
      self.assertGreaterEqual(rows[0]['status_age_seconds'],299)
      self.assertFalse(rows[1]['overlay_visible'])
      self.assertEqual(rows[1]['overlay_hidden_reason'],'native_navigation')
      self.assertEqual(draw.call_count,1)
      self.assertTrue(path.with_name('overlay_status.json').exists())


if __name__ == '__main__': unittest.main()
