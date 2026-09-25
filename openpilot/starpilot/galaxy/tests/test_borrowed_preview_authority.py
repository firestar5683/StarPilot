import threading
from types import SimpleNamespace
from unittest.mock import Mock
from openpilot.starpilot.galaxy.settings import LiveContextSource
from openpilot.starpilot.parked_evidence import RESUME_SKEW_NS


def source():
  owner = LiveContextSource.__new__(LiveContextSource)
  owner.borrowed_messages, owner.closed = True, False
  owner.lock, owner.params = threading.Lock(), Mock()
  owner.messages = SimpleNamespace(updated={'deviceState': True}, logMonoTime={'deviceState': 200}, update=Mock())
  owner.device_after_mono_ns = 100
  owner.last_pair_offset_ns = owner.device_offset_ns = None
  owner.mono_clock, owner.boot_clock = lambda: 300, lambda: 400
  return owner


def test_borrowed_update_survives_the_throttled_preview_phase():
  owner = source()
  owner.observe_borrowed_device_clock()
  assert owner.device_offset_ns == 100
  owner.messages.updated['deviceState'] = False
  owner.observe_borrowed_device_clock()
  assert owner.device_offset_ns == 100
  assert owner.device_after_mono_ns == 100
  owner.messages.update.assert_not_called()
  assert owner.params.mock_calls == []


def test_startup_and_resume_require_new_publisher_update():
  owner = source()
  owner.messages.logMonoTime['deviceState'] = 100
  owner.observe_borrowed_device_clock()
  assert owner.device_offset_ns is None
  owner.messages.logMonoTime['deviceState'] = 200
  owner.observe_borrowed_device_clock()
  assert owner.device_offset_ns == 100
  owner.boot_clock = lambda: 400 + RESUME_SKEW_NS + 1
  owner.observe_borrowed_device_clock()
  assert owner.device_offset_ns is None
  assert owner.device_after_mono_ns == 300
  owner.messages.logMonoTime['deviceState'] = 301
  owner.observe_borrowed_device_clock()
  assert owner.device_offset_ns == 100 + RESUME_SKEW_NS + 1
  owner.messages.update.assert_not_called()
  assert owner.params.mock_calls == []


def test_ui_frame_observation_catches_update_between_preview_warmup_ticks():
  from unittest.mock import patch
  from openpilot.starpilot.ui.layout_preview_runtime import LayoutPreviewRuntime
  owner = source()
  owner.messages.updated['deviceState'] = False
  owner.parked = lambda: owner.device_offset_ns is not None
  runtime = LayoutPreviewRuntime.__new__(LayoutPreviewRuntime)
  runtime.authority, runtime.renderer, runtime.service = owner, Mock(), Mock()
  runtime.renderer.has_resources = False
  runtime._started, runtime._closed = True, False
  runtime._hint_was_offroad = runtime._warm = False
  runtime._warm_until = runtime._next_warm = runtime._next_authority_check = 0.0
  runtime._offroad_hint = lambda: True
  with patch('openpilot.starpilot.ui.layout_preview_runtime.time.monotonic', side_effect=[0.0, 0.05, 0.10]):
    runtime.poll()
    assert not runtime._warm
    owner.messages.updated['deviceState'] = True
    runtime.poll() # Publisher update arrives between the throttled checks.
    owner.messages.updated['deviceState'] = False
    runtime.poll()
  assert runtime._warm
  owner.messages.update.assert_not_called()
  assert owner.params.mock_calls == []
  assert runtime.service.poll.call_count == 3
