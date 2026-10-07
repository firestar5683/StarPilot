"""Capture transport fault frequency without doing logging in PortAudio's callback."""
from types import SimpleNamespace
from unittest.mock import Mock, patch

import numpy as np

from openpilot.selfdrive.ui import soundd


def make_daemon():
  daemon = soundd.Soundd.__new__(soundd.Soundd)
  daemon.pending_stream_status = None
  daemon.stream_status_count = 0
  daemon.output_underflow_count = 0
  daemon.reported_output_underflows = 0
  daemon.stream_report_at = None
  samples = np.array([0.5, -0.5, 0., 0.25], dtype=np.float32)
  daemon.get_sound_data = Mock(side_effect=lambda frames: samples[:frames])
  return daemon, samples


def test_underflow_counters_preserve_signal_and_log_on_service_thread():
  daemon, samples = make_daemon()
  output = np.empty((4, 1), dtype=np.float32)
  underflow = SimpleNamespace(output_underflow=True)
  other = SimpleNamespace(output_underflow=False)
  with patch.object(soundd.cloudlog, "warning") as warning, patch.object(soundd.cloudlog, "error") as error:
    for status in (underflow, underflow, other, None):
      daemon.callback(output, 4, None, status)
      np.testing.assert_array_equal(output[:, 0], samples)
    warning.assert_not_called()
    error.assert_not_called()
    assert daemon.stream_status_count == 3
    assert daemon.output_underflow_count == 2
    daemon.log_pending_stream_status(SimpleNamespace(latency=0.2, cpu_load=0.01))
    warning.assert_not_called()
    error.assert_called_once_with(f"soundd stream diagnostics: status={other} status_callbacks=3 output_underflows=2 latency=0.2 cpu_load=0.01")
    daemon.log_pending_stream_status(SimpleNamespace(latency=0.2, cpu_load=0.01))
    assert error.call_count == 1


def test_underflow_reports_coalesce_without_losing_the_last_dropout():
  daemon, _ = make_daemon()
  output = np.empty((4, 1), dtype=np.float32)
  underflow = SimpleNamespace(output_underflow=True)
  with patch.object(soundd.cloudlog, "error") as error, patch.object(soundd.time, "monotonic") as clock:
    clock.return_value = 0.
    daemon.callback(output, 4, None, underflow)
    daemon.log_pending_stream_status()
    for now in (0.1, 1., 4.9):
      clock.return_value = now
      daemon.callback(output, 4, None, underflow)
      daemon.log_pending_stream_status()
    assert error.call_count == 1
    clock.return_value = 5.
    daemon.log_pending_stream_status()
    assert error.call_count == 2
    assert "output_underflows=4" in error.call_args.args[0]
    clock.return_value = 10.
    daemon.log_pending_stream_status()
    assert error.call_count == 2


def test_other_status_stays_a_warning_and_underflow_counter_survives_status_clear():
  daemon, _ = make_daemon()
  output = np.empty((4, 1), dtype=np.float32)
  with patch.object(soundd.cloudlog, "error") as error, patch.object(soundd.cloudlog, "warning") as warning, \
       patch.object(soundd.time, "monotonic", return_value=0.) as clock:
    daemon.callback(output, 4, None, SimpleNamespace(output_underflow=False))
    daemon.log_pending_stream_status()
    warning.assert_called_once()
    error.assert_not_called()
    daemon.callback(output, 4, None, SimpleNamespace(output_underflow=True))
    daemon.pending_stream_status = None
    clock.return_value = 5.
    daemon.log_pending_stream_status()
    error.assert_called_once()
    assert "output_underflows=1" in error.call_args.args[0]
