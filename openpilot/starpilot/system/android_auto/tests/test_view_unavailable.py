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
