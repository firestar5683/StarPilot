from typing import Any
"""Cold rendering must not publish until the owning UI collector advances."""
import struct
import zlib
from unittest.mock import patch
from openpilot.starpilot.ui.layout_preview_transport import PreviewService, PreviewDenied, PreviewUnavailable, _Job


def png():
  def chunk(tag, data):
    return struct.pack('!I', len(data)) + tag + data + struct.pack('!I', zlib.crc32(tag + data))
  return (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('!IIBBBBB', 1, 1, 8, 6, 0, 0, 0)) +
          chunk(b'IDAT', zlib.compress(b'\0\0\0\0\xff')) + chunk(b'IEND', b''))


def scenario():
  state: dict[str, Any] = {'now': 0.0, 'parked': True, 'renders': 0}
  def render(payload):
    state['renders'] += 1
    state.update(now=.8, parked=False) # A cold render outlasts borrowed-message freshness.
    return png()
  service = PreviewService(render, lambda: state['parked'])
  job = _Job({}, 2.0)
  service._pending = job
  return service, job, state


def test_slow_render_completes_only_after_next_fresh_ui_frame():
  service, job, state = scenario()
  with patch('openpilot.starpilot.ui.layout_preview_transport.time.monotonic', side_effect=lambda: state['now']):
    assert service.poll()
    assert not job.done.is_set() and job.error is None and service._pending is job
    state.update(now=.81, parked=True)
    assert service.poll()
  assert job.done.is_set() and job.error is None and job.result == png()
  assert state['renders'] == 1 and service._pending is None


def test_next_frame_onroad_revocation_discards_retained_png():
  service, job, state = scenario()
  with patch('openpilot.starpilot.ui.layout_preview_transport.time.monotonic', side_effect=lambda: state['now']):
    service.poll()
    state['now'] = .81
    service.poll()
  assert job.done.is_set() and isinstance(job.error, PreviewDenied) and job.result is None


def test_result_expires_at_original_deadline():
  service, job, state = scenario()
  with patch('openpilot.starpilot.ui.layout_preview_transport.time.monotonic', side_effect=lambda: state['now']):
    service.poll()
    state.update(now=2.0, parked=True)
    service.poll()
  assert job.done.is_set() and isinstance(job.error, PreviewUnavailable) and job.result is None


def test_close_rejects_pending_result_and_cancelled_job_cannot_publish():
  service, job, state = scenario()
  with patch('openpilot.starpilot.ui.layout_preview_transport.time.monotonic', side_effect=lambda: state['now']):
    service.poll()
    service.close()
    assert not service.poll()
  assert job.done.is_set() and job.cancelled and isinstance(job.error, PreviewUnavailable)
  service, job, state = scenario()
  with patch('openpilot.starpilot.ui.layout_preview_transport.time.monotonic', side_effect=lambda: state['now']):
    service.poll()
    job.cancelled = True
    assert not service.poll()
  assert not job.done.is_set()


def test_invalid_png_is_rejected_before_result_retention():
  service, job, state = scenario()
  service.renderer = lambda payload: b'not PNG'
  with patch('openpilot.starpilot.ui.layout_preview_transport.time.monotonic', side_effect=lambda: state['now']):
    service.poll()
  assert job.done.is_set() and job.error is not None and job.result is None and service._pending is None
