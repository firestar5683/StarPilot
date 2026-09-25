"""A missing desktop display must fail before monitor or render resource queries."""

import unittest
from unittest.mock import patch

from openpilot.system.ui.lib import application


class TestHostWindowFailure(unittest.TestCase):
  def test_auto_scale_does_not_query_uninitialized_monitor(self):
    app = object.__new__(application.GuiApplication)
    app._width, app._height = 536, 240
    with patch.object(application.rl, "init_window"), \
         patch.object(application.rl, "is_window_ready", return_value=False), \
         patch.object(application.rl, "get_monitor_width") as get_width:
      with self.assertRaisesRegex(RuntimeError, "active monitor"):
        app._calculate_auto_scale()
      get_width.assert_not_called()

  def test_normal_pc_window_does_not_load_render_resources(self):
    app = object.__new__(application.GuiApplication)
    app._scaled_width, app._scaled_height, app._scale = 536, 240, 1.0
    with patch.object(application, "PC", True), \
         patch.object(application.signal, "signal"), \
         patch.object(application.atexit, "register"), \
         patch.object(application.rl, "set_config_flags"), \
         patch.object(application.rl, "init_window"), \
         patch.object(application.rl, "is_window_ready", return_value=False), \
         patch.object(application.rl, "load_render_texture") as load_texture:
      with self.assertRaisesRegex(RuntimeError, "active monitor"):
        app.init_window("fixture")
      load_texture.assert_not_called()
