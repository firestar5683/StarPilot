"""Capture transport fault frequency without doing logging in PortAudio's callback."""
from types import SimpleNamespace
from unittest.mock import Mock, patch

import numpy as np

from openpilot.selfdrive.ui import soundd


def test_underflow_counters_preserve_signal_and_log_on_service_thread():
  daemon = soundd.Soundd.__new__(soundd.Soundd)
  daemon.pending_stream_status = None
  daemon.stream_status_count = 0
  daemon.output_underflow_count = 0
  samples = np.array([0.5, -0.5, 0., 0.25], dtype=np.float32)
  daemon.get_sound_data = Mock(side_effect=lambda frames: samples[:frames])
  output = np.empty((4, 1), dtype=np.float32)
  underflow = SimpleNamespace(output_underflow=True)
  other = SimpleNamespace(output_underflow=False)
  with patch.object(soundd.cloudlog, "warning") as warning, patch.object(soundd.cloudlog, "info") as info:
    for status in (underflow, underflow, other, None):
      daemon.callback(output, 4, None, status)
      np.testing.assert_array_equal(output[:, 0], samples)
    warning.assert_not_called()
    info.assert_not_called()
    assert daemon.stream_status_count == 3
    assert daemon.output_underflow_count == 2
    daemon.log_pending_stream_status(SimpleNamespace(latency=0.2, cpu_load=0.01))
    warning.assert_called_once()
    info.assert_called_once_with("soundd stream diagnostics: status_callbacks=3 output_underflows=2 latency=0.2 cpu_load=0.01")
    daemon.log_pending_stream_status(SimpleNamespace(latency=0.2, cpu_load=0.01))
    assert info.call_count == 1
