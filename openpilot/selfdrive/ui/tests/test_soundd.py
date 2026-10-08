import threading
from unittest.mock import mock_open
import numpy as np

from openpilot.common.test import OpenpilotTestCase
from openpilot.cereal import log, messaging
from openpilot.cereal.messaging import SubMaster, PubMaster
from openpilot.selfdrive.ui.soundd import SELFDRIVE_STATE_TIMEOUT, Soundd, check_selfdrive_timeout_alert

AudibleAlert = log.SelfdriveState.AudibleAlert


class TestSoundd(OpenpilotTestCase):
  def test_callback_defers_and_bounds_stream_status_logging(self, mocker):
    scheduler_read = mocker.patch("openpilot.selfdrive.ui.soundd._read_callback_schedstat", side_effect=AssertionError("callback I/O"))
    thread_snapshot = mocker.patch("openpilot.selfdrive.ui.soundd._callback_thread_snapshot", side_effect=AssertionError("callback I/O"))
    soundd = Soundd.__new__(Soundd)
    soundd.current_alert = AudibleAlert.none
    soundd.current_volume = 0.1
    soundd.loaded_sounds = {}
    soundd.saved_volumes = {}
    soundd.pending_stream_status = None
    soundd.stream_status_count = 0
    soundd.output_underflow_count = 0
    soundd.reported_output_underflows = 0
    soundd.stream_report_at = None
    soundd.last_callback_start_ns = None
    soundd.underflow_timing = None
    warning = mocker.patch("openpilot.selfdrive.ui.soundd.cloudlog.warning")
    error = mocker.patch("openpilot.selfdrive.ui.soundd.cloudlog.error")
    output = np.empty((8, 1), dtype=np.float32)

    soundd.callback(output, 8, None, "first underflow")
    soundd.callback(output, 8, None, "latest underflow")
    assert np.array_equal(output, np.zeros_like(output))
    warning.assert_not_called()
    error.assert_not_called()
    scheduler_read.assert_not_called()
    thread_snapshot.assert_not_called()

    soundd.log_pending_stream_status()
    warning.assert_called_once_with("soundd stream diagnostics: status=latest underflow status_callbacks=2 output_underflows=0")
    soundd.log_pending_stream_status()
    warning.assert_called_once()
    error.assert_not_called()

  def test_check_selfdrive_timeout_alert(self, mocker):
    sm = SubMaster(['selfdriveState'])
    pm = PubMaster(['selfdriveState'])

    cs = messaging.new_message('selfdriveState')
    cs.selfdriveState.enabled = True
    threading.Timer(0.01, pm.send, args=("selfdriveState", cs)).start()
    sm.update(100)
    assert sm.updated['selfdriveState']

    sm.recv_time['selfdriveState'] = 0
    clock = mocker.patch("openpilot.selfdrive.ui.soundd.time.monotonic", return_value=SELFDRIVE_STATE_TIMEOUT)
    assert not check_selfdrive_timeout_alert(sm)

    clock.return_value = SELFDRIVE_STATE_TIMEOUT + 0.1
    assert check_selfdrive_timeout_alert(sm)

    clock.return_value = SELFDRIVE_STATE_TIMEOUT + 10
    assert not check_selfdrive_timeout_alert(sm)

  # TODO: add test with micd for checking that soundd actually outputs sounds


def scheduler_sample(history, mocker, begin, counters, *, tid=7, duration=1):
  mocker.patch("openpilot.selfdrive.ui.soundd.monotonic_ns", side_effect=(begin, begin + duration))
  mocker.patch("openpilot.selfdrive.ui.soundd._read_callback_schedstat", return_value=counters)
  history.sample(tid)


class TestSounddSchedulerHistory(OpenpilotTestCase):
  def test_scheduler_history_reports_only_explicit_bracket(self, mocker):
    from openpilot.selfdrive.ui.soundd import _CallbackSchedulerHistory
    history = _CallbackSchedulerHistory()
    for tick in range(8):
      scheduler_sample(history, mocker, tick * 50_000_000, (tick * 1_000_000, tick * 3_000_000, tick))
    bracket = history.bracket(7, 320_000_000, 270_000_000)
    assert bracket == {"available": True, "tid": 7,
                       "event_gap_start_ns": 50_000_000, "event_gap_end_ns": 320_000_000,
                       "sample_before_begin_ns": 0, "sample_before_end_ns": 1,
                       "sample_after_begin_ns": 350_000_000, "sample_after_end_ns": 350_000_001,
                       "runtime_delta_ns": 7_000_000, "runqueue_delta_ns": 21_000_000,
                       "timeslices_delta": 7, "max_sample_gap_ns": 50_000_001, "sample_count": 8}
    assert history.bracket(8, 320_000_000, 270_000_000) == {"available": False}
    assert history.bracket(7, 320_000_000, None) == {"available": False}
    assert history.bracket(7, 320_000_000, 0) == {"available": False}
    assert history.bracket(7, 400_000_000, 270_000_000) == {"available": False}
    assert history.bracket(7, 320_000_000, 400_000_000) == {"available": False}

  def test_scheduler_history_never_bridges_missing_or_reset_samples(self, mocker):
    for failure in ("gap", "slow_read", "read_error", "counter_reset", "tid_reset"):
      with self.subTest(failure=failure):
        from openpilot.selfdrive.ui.soundd import _CallbackSchedulerHistory
        history = _CallbackSchedulerHistory()
        scheduler_sample(history, mocker, 0, (100, 100, 1))
        if failure == "gap":
          scheduler_sample(history, mocker, 200_000_000, (200, 200, 2))
        elif failure == "slow_read":
          scheduler_sample(history, mocker, 50_000_000, (200, 200, 2), duration=101_000_000)
        elif failure == "read_error":
          mocker.patch("openpilot.selfdrive.ui.soundd.monotonic_ns", return_value=50_000_000)
          mocker.patch("openpilot.selfdrive.ui.soundd._read_callback_schedstat", side_effect=OSError("missing proc"))
          history.sample(7)
        elif failure == "counter_reset":
          scheduler_sample(history, mocker, 50_000_000, (1, 1, 1))
        else:
          scheduler_sample(history, mocker, 50_000_000, (200, 200, 2), tid=8)
        scheduler_sample(history, mocker, 250_000_000, (300, 300, 3), tid=8 if failure == "tid_reset" else 7)
        assert history.bracket(7, 220_000_000, 210_000_000) == {"available": False}

  def test_scheduler_history_is_capped_and_has_no_regular_logging(self, mocker):
    from openpilot.selfdrive.ui.soundd import _CallbackSchedulerHistory
    warning = mocker.patch("openpilot.selfdrive.ui.soundd.cloudlog.warning")
    error = mocker.patch("openpilot.selfdrive.ui.soundd.cloudlog.error")
    history = _CallbackSchedulerHistory()
    for tick in range(140):
      scheduler_sample(history, mocker, tick * 50_000_000, (tick, tick, tick))
    assert len(history.samples) == 128
    warning.assert_not_called()
    error.assert_not_called()
    history.sample(None)
    assert not history.samples

  def test_scheduler_reader_rejects_malformed_counters(self, mocker):
    for raw in ("1 2", "1 2 3 4", "-1 2 3", "1 bad 3"):
      with self.subTest(raw=raw):
        from openpilot.selfdrive.ui.soundd import _read_callback_schedstat
        opened = mocker.patch("pathlib.Path.open", mock_open(read_data=raw))
        with self.assertRaises(ValueError):
          _read_callback_schedstat(7)
        opened().read.assert_called_once_with(128)

  def test_underflow_log_contains_scheduler_bracket_without_callback_io(self, mocker):
    from types import SimpleNamespace
    from openpilot.selfdrive.ui.soundd import _CallbackSchedulerHistory
    owner = Soundd.__new__(Soundd)
    owner.current_alert, owner.current_volume = AudibleAlert.none, 0.1
    owner.loaded_sounds, owner.saved_volumes = {}, {}
    owner.pending_stream_status = None
    owner.stream_status_count = owner.output_underflow_count = owner.reported_output_underflows = 0
    owner.stream_report_at = owner.underflow_timing = None
    owner.last_callback_start_ns = 25_000_000
    owner.callback_tid = 7
    owner.callback_scheduler_history = _CallbackSchedulerHistory()
    for tick in range(4):
      scheduler_sample(owner.callback_scheduler_history, mocker, tick * 50_000_000, (tick, tick * 10, tick))
    reader = mocker.patch("openpilot.selfdrive.ui.soundd._read_callback_schedstat", side_effect=AssertionError("callback I/O"))
    snapshot = mocker.patch("openpilot.selfdrive.ui.soundd._callback_thread_snapshot", return_value={})
    error = mocker.patch("openpilot.selfdrive.ui.soundd.cloudlog.error")
    mocker.patch("openpilot.selfdrive.ui.soundd.monotonic_ns", side_effect=(125_000_000, 125_001_000))
    mocker.patch("openpilot.selfdrive.ui.soundd.time.monotonic", return_value=0.2)
    output = np.empty((8, 1), dtype=np.float32)
    owner.callback(output, 8, None, SimpleNamespace(output_underflow=True))
    assert np.array_equal(output, np.zeros_like(output))
    reader.assert_not_called()
    snapshot.assert_not_called()
    error.assert_not_called()
    owner.log_pending_stream_status()
    error.assert_called_once()
    message = error.call_args.args[0]
    assert 'callback_scheduler_bracket={"available":true,' in message
    assert '"runqueue_delta_ns":30' in message
    assert '"event_gap_start_ns":25000000' in message
    owner.log_pending_stream_status()
    error.assert_called_once()
