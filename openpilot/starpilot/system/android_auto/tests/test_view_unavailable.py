from unittest.mock import Mock
from openpilot.starpilot.system.android_auto.frame_source import FrameRequest
from openpilot.starpilot.system.android_auto.view import ViewSource


def request():
  return FrameRequest(1280, 720, 0, 0, 33_333)


def test_uninstalled_mirror_source_never_consumes_a_stale_frame():
  source = ViewSource('mirror', request(), lambda *_a, **_k: None)
  assert source.view == 'unavailable'
  assert 'mirror source is not installed' in source.label
  assert source.source.latest() is None
  source.demand()
  source.release_demand()
  source.close()


def test_failed_car_renderer_withdraws_frames_and_reports_unavailable():
  class OldSource:
    def __init__(self): self.closed = False
    def close(self): self.closed = True

  old = OldSource()
  source = ViewSource.__new__(ViewSource)
  source.view = 'car'
  source.fallback_reason = ''
  source.frames = 3
  source.source = Mock(wraps=old)
  source.process = None
  source.touch = None
  source.log = lambda *_a, **_k: None
  source.fallback('renderer exited')
  assert old.closed
  assert source.view == 'unavailable' and source.source.latest() is None
  assert 'renderer exited' in source.label
  source.close()


def crashing_view(tmp_path, events, script="import sys; print('Traceback: boom', flush=True); sys.exit(1)"):
  import sys
  return ViewSource('car', request(), lambda event, **fields: events.append((event, fields)),
                    car_path=str(tmp_path / 'frame'), touch_path=str(tmp_path / 'touch'),
                    renderer_command=[sys.executable, '-c', script], renderer_log=tmp_path / 'car_ui.log')


def test_crashed_renderer_is_restarted_and_its_output_is_logged(tmp_path):
  events = []
  source = crashing_view(tmp_path, events)
  try:
    source.process.wait(timeout=10)
    source.check(100.0)
    assert source.view == 'car' and not source.fallback_reason
    assert source.waiting_for_first_frame
    output = [fields for event, fields in events if event == 'car_view_output']
    assert output == [{'reason': 'renderer exited with 1', 'lines': ['Traceback: boom']}]
    assert ('car_view_restart', {'reason': 'renderer exited with 1', 'attempt': 1}) in events
    assert sum(event == 'car_view_started' for event, _ in events) == 2
  finally:
    source.close()


def test_renderer_restarts_are_bounded_then_fall_back(tmp_path):
  from openpilot.starpilot.system.android_auto import view
  events = []
  source = crashing_view(tmp_path, events)
  try:
    for attempt in range(view.MAX_RESTARTS + 1):
      source.process.wait(timeout=10)
      source.check(100.0 + attempt)
    assert source.view == 'unavailable' and 'renderer exited with 1' in source.label
    assert [event for event, _ in events].count('car_view_restart') == view.MAX_RESTARTS
    assert [event for event, _ in events].count('car_view_output') == view.MAX_RESTARTS + 1
  finally:
    source.close()


def test_restart_budget_recovers_after_the_window(tmp_path):
  from openpilot.starpilot.system.android_auto import view
  events = []
  source = crashing_view(tmp_path, events)
  try:
    for attempt in range(view.MAX_RESTARTS):
      source.process.wait(timeout=10)
      source.check(100.0 + attempt)
    source.process.wait(timeout=10)
    source.check(100.0 + view.RESTART_WINDOW + 1)
    assert source.view == 'car'
  finally:
    source.close()


def test_stalled_renderer_output_is_captured_before_restart(tmp_path):
  events = []
  source = crashing_view(tmp_path, events, "import time; print('stuck', flush=True); time.sleep(60)")
  try:
    import time
    deadline = time.monotonic() + 10
    while not (tmp_path / 'car_ui.log').read_text() and time.monotonic() < deadline:
      time.sleep(0.05)
    source.check(source.started_at + 30.0)
    assert ('car_view_output', {'reason': 'no frames after 25 s', 'lines': ['stuck']}) in events
    assert source.view == 'car'
  finally:
    source.close()


def test_unavailable_frame_draws_the_logo():
  from openpilot.starpilot.system.android_auto.supervisor import Supervisor
  req = request()
  frame = Supervisor._unavailable_frame(req, 'Starting StarPilot')
  assert len(frame) == req.width * req.height * 4
  # The logo is purple; without it the frame is only the dark background and white text.
  pixels = memoryview(frame).cast('B')
  purple = sum(1 for i in range(0, len(frame), 4 * 97) if pixels[i + 2] > 120 and pixels[i + 2] > pixels[i + 1] + 60)
  assert purple > 100
