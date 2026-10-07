"""C4 native toggle behavior, including audio saves during Params contention."""

import fcntl
from pathlib import Path
from types import SimpleNamespace as NS
import tempfile
import threading
import time
import unittest
from unittest.mock import Mock, call, patch

import pyray as rl

from openpilot.common.params import Params
from openpilot.selfdrive.ui.layouts.settings import common
from openpilot.selfdrive.ui.mici.layouts.settings import toggles
from openpilot.selfdrive.ui.mici.widgets import button
from openpilot.system.ui.lib.application import gui_app, MousePos


class TestC4SafeMode(unittest.TestCase):
  def test_safe_mode_clears_experimental_choice_and_relaxes_personality(self):
    with tempfile.TemporaryDirectory() as directory:
      params = Params(directory)
      params.put_bool("SafeMode", True, block=True)
      params.put_bool("ExperimentalMode", True, block=True)
      params.put("LongitudinalPersonality", 0, block=True)
      panel = toggles.TogglesLayoutMici.__new__(toggles.TogglesLayoutMici)
      panel._safe_mode_btn = Mock()
      panel._experimental_btn = Mock()
      panel._personality_toggle = Mock()
      panel._metric_toggle = Mock()
      self.enterContext(patch.object(panel, "_slc_offsets", NS(_raw=lambda _key: b"0"), create=True))
      toggles_to_refresh = (("SafeMode", panel._safe_mode_btn), ("ExperimentalMode", panel._experimental_btn))
      self.enterContext(patch.object(panel, "_refresh_toggles", toggles_to_refresh, create=True))
      fake_ui = NS(params=params, CP=None, update_params=Mock())
      with patch.object(toggles, "ui_state", fake_ui):
        panel._update_toggles()
      self.assertFalse(params.get_bool("ExperimentalMode"))
      self.assertEqual(params.get("LongitudinalPersonality"), 2)
      panel._experimental_btn.set_enabled.assert_called_once_with(False)
      panel._personality_toggle.set_enabled.assert_called_once_with(False)
      panel._personality_toggle.set_value.assert_called_once_with("relaxed")


class TestC4AudioToggle(unittest.TestCase):
  def setUp(self):
    directory = tempfile.TemporaryDirectory()
    self.addCleanup(directory.cleanup)
    self.directory = directory.name
    self.params = Params(directory.name)
    self.params.put_bool("RecordAudio", False, block=True)
    self.ui = NS(params=self.params, CP=None, engaged=False, started=False,
                 add_engaged_transition_callback=Mock(), update_params=Mock())
    self.enterContext(patch.object(toggles, "ui_state", self.ui))
    self.enterContext(patch.object(common, "ui_state", self.ui))
    self.enterContext(patch.object(button, "Params", return_value=self.params))
    self.enterContext(patch.object(gui_app, "font", return_value=rl.Font()))
    self.enterContext(patch.object(gui_app, "texture", return_value=NS(width=64, height=64)))
    self.panel = toggles.TogglesLayoutMici()
    self.audio = next(item for key, item in self.panel._refresh_toggles if key == "RecordAudio")

  def test_release_queues_audio_before_restart_without_blocking_writes(self):
    with patch.object(self.params, "put_bool") as save:
      self.audio._handle_mouse_release(MousePos(0, 0))
      self.audio._handle_mouse_release(MousePos(0, 0))
    self.assertEqual(save.call_args_list, [call("RecordAudio", True), call("OnroadCycleRequested", True),
                                         call("RecordAudio", False), call("OnroadCycleRequested", True)])

  def test_release_returns_while_params_lock_is_held_then_persists_in_order(self):
    finished = threading.Event()
    errors = []

    def release():
      try:
        self.audio._handle_mouse_release(MousePos(0, 0))
      except Exception as error:
        errors.append(error)
      finally:
        finished.set()

    with (Path(self.directory) / ".lock").open("a") as lock:
      fcntl.flock(lock, fcntl.LOCK_EX)
      worker = threading.Thread(target=release, daemon=True)
      worker.start()
      try:
        self.assertTrue(finished.wait(1), "Audio touch handler waited for the Params filesystem lock")
        self.assertFalse(self.params.get_bool("RecordAudio"))
        self.assertFalse(self.params.get_bool("OnroadCycleRequested"))
      finally:
        fcntl.flock(lock, fcntl.LOCK_UN)
        worker.join(timeout=2)
    self.assertEqual(errors, [])
    deadline = time.monotonic() + 2
    while not self.params.get_bool("OnroadCycleRequested") and time.monotonic() < deadline:
      time.sleep(0.01)
    self.assertTrue(self.params.get_bool("OnroadCycleRequested"))
    self.assertTrue(self.params.get_bool("RecordAudio"))

  def test_audio_refresh_and_engaged_guard_remain_effective(self):
    self.params.put_bool("RecordAudio", True, block=True)
    self.panel._update_toggles()
    self.assertTrue(self.audio._checked)
    self.assertTrue(self.audio.enabled)
    self.ui.engaged = True
    self.assertFalse(self.audio.enabled)
