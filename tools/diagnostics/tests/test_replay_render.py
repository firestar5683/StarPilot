from contextlib import contextmanager
from types import SimpleNamespace as NS
from unittest.mock import Mock
import gc
import json
import stat
import sys

import pytest

from tools.diagnostics import replay_render as diagnostic


def test_nested_timings_are_exclusive_and_failures_propagate(monkeypatch):
  trace = diagnostic.Trace()
  ticks = iter((100, 120, 150, 200))
  monkeypatch.setattr(diagnostic.time, 'monotonic_ns', lambda: next(ticks))
  monkeypatch.setattr(diagnostic.time, 'thread_time_ns', lambda: 0)
  with pytest.raises(ValueError, match='original error'), trace.span('outer'):
    with trace.span('inner'):
      raise ValueError('original error')
  inner, outer = trace.events
  assert inner['wall_ns'] == inner['exclusive_wall_ns'] == 30
  assert outer['wall_ns'] == 100 and outer['exclusive_wall_ns'] == 70
  assert inner['parent'] == outer['id']
  assert inner['error_type'] == outer['error_type'] == 'ValueError'


def test_records_are_bounded_and_missing_cpu_is_not_zero(monkeypatch):
  monkeypatch.setattr(diagnostic, 'MAX_EVENTS', 2)
  trace = diagnostic.Trace()
  for number in range(3):
    trace.record({'stage': 'gc', 'wall_ns': number})
  report = trace.report()
  assert len(report['events']) == 2 and report['overwritten_events'] == 1
  assert report['retained_window_stages']['gc']['cpu_ms']['p50'] is None
  json.dumps(report, allow_nan=False)


class Hooks:
  def update(self, *args): pass
  def sample(self): return NS(valid=True, epoch=2)
  def build(self, *args): pass
  def render(self, *args): pass
  def maintain(self, *args): pass
  def begin_frame(self, *args): pass
  def begin_texture_mode(self, *args): pass
  def end_texture_mode(self, *args): pass
  def measure_frame_phase(self, name, callback, *args, **kwargs): return callback(*args, **kwargs)


class CameraView:
  def __init__(self):
    self.client = NS(is_connected=lambda: True, frame_id=5, timestamp_sof=10, timestamp_eof=20)
    self.frame = NS(frame_id=5, idx=0, fd=10, width=4, height=2, stride=4, uv_offset=8)
    self.stream_type, self._switching = 0, False
  def _render(self): self._ensure_connection()
  def _ensure_connection(self): return True
  def _handle_switch(self): pass
  def _complete_switch(self): pass


class Pip(Hooks):
  generation = 1
  def poll(self, *args): pass


class Readback:
  def __init__(self):
    self.pending = False
    self.pixels = memoryview(b'pixels')
  def start(self): self.pending = True
  def ready(self): return self.pending
  def finish(self): return self.pixels
  def release(self): self.pending = False


class View(Hooks):
  def __init__(self): self.alert = Hooks()


class Compositor:
  def __init__(self):
    self.ui = Hooks()
    self.ui.replay_clock = Hooks()
    self.ui.replay_sample = NS(epoch=2, now_ns=100, boot_ns=100, valid=True, paused=False)
    self.ui.sm = Hooks()
    self.ui.sm.seen = self.ui.sm.valid = dict.fromkeys(diagnostic.STAMPS, False)
    self.ui.sm.logMonoTime = dict.fromkeys(diagnostic.STAMPS, 0)
    self.camera, self.pip_stream, self.pip, self.monitor = CameraView(), Pip(), Pip(), Hooks()
    self.adapter, self.placement, self.context, self.gui, self.rl = (Hooks() for _ in range(5))
    self.readback = Readback()
    self._new_view()
    self.rejection = None
  def _new_view(self): self.view = View()
  def update(self): return self.ui.replay_sample
  def _receive_primary(self): self.camera._render()
  def _draw_rejection(self, epoch): return self.rejection
  def _prepare(self): pass
  def reset_epoch(self, epoch): self.readback.release()
  def draw(self, *args):
    if self._draw_rejection(args[0]):
      return False
    self._receive_primary()
    self._prepare()
    self.gui.measure_frame_phase('model', lambda: None)
    self.readback.start()
    return True
  @contextmanager
  def finish(self):
    if not self.readback.ready():
      yield None
      return
    try:
      yield self.readback.finish(), (2, 0., 100)
    finally:
      self.readback.release()


class Output:
  def frame(self): pass
  def publish(self): pass


def test_worker_hooks_preserve_delivery_lifetime_and_restore_after_failure():
  trace = diagnostic.Trace()
  module = NS(Compositor=Compositor, MediaMux=Output, MediaStore=Output, ReplayFramePublisher=Output,
              FRAME_INTERVAL=.05, time=diagnostic.time)
  original_draw, original_clock, callbacks = Compositor.draw, module.time, list(gc.callbacks)
  with pytest.raises(RuntimeError, match='encoder failed'), diagnostic.instrument(module, trace):
    core = Compositor()
    core.update()
    module.time.monotonic()
    assert core.draw(2, 0., 100)
    with core.finish() as value:
      assert value[0].tobytes() == b'pixels' and core.readback.pending
      raise RuntimeError('encoder failed')
  assert not core.readback.pending
  assert trace.pending_attempt is trace.submitted_ns is None
  assert Compositor.draw is original_draw and module.time is original_clock
  assert gc.callbacks == callbacks
  delivery = next(event for event in trace.events if event['stage'] == 'delivery_scope')
  assert delivery['attempt'] == 1 and delivery['error_type'] == 'RuntimeError'
  ready = next(event for event in trace.events if event['stage'] == 'readback_poll')
  assert ready['submit_to_observed_ready_ns'] >= 0
  assert trace.outcomes == {'accepted': 1}
  json.dumps(trace.report(), allow_nan=False)


def test_early_reason_is_recorded_without_preparation():
  trace = diagnostic.Trace()
  module = NS(Compositor=Compositor, MediaMux=Output, MediaStore=Output, ReplayFramePublisher=Output,
              FRAME_INTERVAL=.05, time=diagnostic.time)
  with diagnostic.instrument(module, trace):
    core = Compositor()
    core.rejection = 'camera_not_ready'
    assert not core.draw(2, 0., 100)
  assert trace.outcomes == {'camera_not_ready': 1}
  assert not any(event['stage'] == 'preparation_hooks' for event in trace.events)


def test_unchanged_worker_does_not_invent_rejection_reasons(monkeypatch):
  monkeypatch.delattr(Compositor, '_draw_rejection')
  monkeypatch.delattr(Compositor, '_prepare')
  monkeypatch.setattr(Compositor, 'draw', lambda *args: False)
  trace = diagnostic.Trace()
  module = NS(Compositor=Compositor, MediaMux=Output, MediaStore=Output, ReplayFramePublisher=Output,
              FRAME_INTERVAL=.05, time=diagnostic.time)
  with diagnostic.instrument(module, trace):
    assert not Compositor().draw(2, 0., 100)
  assert trace.capabilities == {'early_rejection_reason': False, 'preparation_hooks': False}
  assert trace.outcomes == {'unclassified_rejection': 1}


def test_scheduler_reports_pending_inhibition_and_seek_cancels_readback(monkeypatch):
  now = [10.]
  monkeypatch.setattr(diagnostic.time, 'monotonic', lambda: now[0])
  trace = diagnostic.Trace()
  module = NS(Compositor=Compositor, MediaMux=Output, MediaStore=Output, ReplayFramePublisher=Output,
              FRAME_INTERVAL=.05, time=diagnostic.time)
  with diagnostic.instrument(module, trace):
    core = Compositor()
    core.update()
    module.time.monotonic()
    assert core.draw(2, 0., 100)
    now[0] += .02
    core.update()
    module.time.monotonic()
    scheduled = [event for event in trace.events if event['stage'] == 'scheduler']
    assert scheduled[0]['deadline_lateness_ns'] is None
    assert scheduled[1]['deadline_lateness_ns'] == 20_000_000 and scheduled[1]['readback_pending']
    core.reset_epoch(3)
    assert trace.pending_attempt is trace.submitted_ns is None
    with core.finish() as value:
      assert value is None


def test_snapshot_does_not_dereference_disconnected_buffer():
  class InvalidBuffer:
    def __getattribute__(self, name):
      raise AssertionError('disconnected buffer was read')
  trace = diagnostic.Trace()
  core = trace.core = Compositor()
  core.camera.frame = InvalidBuffer()
  core.camera.client.is_connected = lambda: False
  assert trace.snapshot()['buffer']['frame_id'] is None


def test_cli_refuses_invalid_context_and_existing_output(tmp_path, monkeypatch):
  from openpilot.starpilot.replay import render
  output = tmp_path / 'trace.json'
  launch = Mock()
  monkeypatch.setattr(render, 'main', launch)
  with pytest.raises((OSError, ValueError)):
    diagnostic.main(['--output', str(output), '--', '--session-dir', str(tmp_path / 'missing')])
  assert not output.exists()
  launch.assert_not_called()
  monkeypatch.setattr(render, 'validate_context', lambda _: None)
  output.write_text('keep')
  with pytest.raises(FileExistsError):
    diagnostic.main(['--output', str(output), '--', '--session-dir', str(tmp_path)])
  assert output.read_text() == 'keep'
  launch.assert_not_called()


def test_cli_flushes_partial_report_on_worker_failure(tmp_path, monkeypatch):
  from openpilot.starpilot.replay import render
  output = tmp_path / 'trace.json'
  monkeypatch.setattr(render, 'validate_context', lambda _: None)
  monkeypatch.setattr(render, 'main', Mock(side_effect=SystemExit(1)))
  previous = sys.argv
  with pytest.raises(SystemExit):
    diagnostic.main(['--output', str(output), '--', '--session-dir', str(tmp_path)])
  assert sys.argv is previous
  assert stat.S_IMODE(output.stat().st_mode) == 0o600
  assert json.loads(output.read_text())['events'] == []
