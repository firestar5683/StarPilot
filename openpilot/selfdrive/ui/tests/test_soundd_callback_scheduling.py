"""Scheduling setup addresses only the calling audio thread and preserves playback."""

from threading import Thread
from types import SimpleNamespace
from unittest.mock import Mock

import numpy as np
import pytest

from openpilot.selfdrive.ui import soundd


def owner():
  obj = soundd.Soundd.__new__(soundd.Soundd)
  obj.callback_tid = None
  obj.callback_scheduling_tid = None
  obj.pending_callback_scheduling_status = None
  obj.current_alert = soundd.AudibleAlert.warningSoft
  obj.current_sound = obj.current_alert
  obj.current_volume = .6
  obj.current_sound_frame = 0
  obj.pending_stop = False
  obj.loaded_sounds = {obj.current_alert: np.linspace(-.5, .5, 32, dtype=np.float32)}
  obj.saved_volumes = {'WarningSoftVolume': 100}
  obj.pack_loader = Mock(is_builtin=Mock(return_value=False))
  obj.pending_stream_status = None
  obj.stream_status_count = obj.output_underflow_count = obj.reported_output_underflows = 0
  obj.stream_report_at = obj.last_callback_start_ns = obj.last_callback_work_ns = None
  obj.last_native_audio_time = obj.underflow_timing = None
  obj.callback_scheduler_history = soundd._CallbackSchedulerHistory()
  return obj


def setup_api(mocker, *, failure=None, policy=0):
  mocker.patch.object(soundd, 'PC', False)
  mocker.patch.object(soundd.os, 'SCHED_OTHER', 0, create=True)
  mocker.patch.object(soundd.os, 'SCHED_RR', 2, create=True)
  mocker.patch.object(soundd.os, 'sched_param', side_effect=lambda n: ('priority', n), create=True)
  read = mocker.patch.object(soundd.os, 'sched_getscheduler', return_value=policy, create=True)
  write = mocker.patch.object(soundd.os, 'sched_setscheduler', side_effect=failure, create=True)
  affinity = mocker.patch.object(soundd.os, 'sched_setaffinity', create=True)
  return read, write, affinity


def callback(obj, *, status=None):
  output = np.empty((64, 1), dtype=np.float32)
  obj.callback(output, 64, SimpleNamespace(currentTime=1., outputBufferDacTime=1.1), status)
  return output[:, 0]


def test_setup_and_logging_are_once_and_never_address_captured_tid(mocker):
  obj = owner()
  read, write, affinity = setup_api(mocker)
  mocker.patch.object(soundd, 'get_native_id', side_effect=(77, 77))
  info = mocker.patch.object(soundd.cloudlog, 'info')
  warning = mocker.patch.object(soundd.cloudlog, 'warning')
  expected = owner()
  np.testing.assert_array_equal(callback(obj), expected.get_sound_data(64))
  np.testing.assert_array_equal(callback(obj), expected.get_sound_data(64))
  assert obj.callback_tid == 77
  read.assert_called_once_with(0)
  write.assert_called_once_with(0, 2, ('priority', 1))
  affinity.assert_not_called()
  info.assert_not_called()
  warning.assert_not_called()
  obj.log_callback_scheduling_status()
  obj.log_callback_scheduling_status()
  info.assert_called_once()
  assert 'tid=77 result=configured' in info.call_args.args[0]


@pytest.mark.parametrize('observed_ids, attempts', [((77, 77, 88, 88), 2), ((77, 77, 77, 77), 1)])
def test_actual_thread_replacement_or_reuse_never_targets_a_cached_tid(mocker, observed_ids, attempts):
  obj = owner()
  read, write, _ = setup_api(mocker)
  mocker.patch.object(soundd, 'get_native_id', side_effect=observed_ids)
  failures = []
  def run():
    try:
      callback(obj)
      callback(obj)
    except BaseException as error:
      failures.append(error)
  for _ in range(2):
    thread = Thread(target=run)
    thread.start()
    thread.join(timeout=2.)
    assert not thread.is_alive()
  assert not failures
  assert read.call_count == write.call_count == attempts
  assert all(call.args == (0,) for call in read.call_args_list)
  assert all(call.args == (0, 2, ('priority', 1)) for call in write.call_args_list)


@pytest.mark.parametrize('policy', [1, 2, 3, 5])
def test_backend_existing_policy_is_preserved(mocker, policy):
  obj = owner()
  read, write, _ = setup_api(mocker, policy=policy)
  expected = owner()
  np.testing.assert_array_equal(callback(obj), expected.get_sound_data(64))
  callback(obj)
  read.assert_called_once_with(0)
  write.assert_not_called()
  assert obj.pending_callback_scheduling_status[1:] == ('preserved', policy)


@pytest.mark.parametrize('failure', [PermissionError('permission'), ProcessLookupError('gone'),
                                     ValueError('policy'), AttributeError('unsupported')])
def test_setup_failure_preserves_samples_timing_and_error_retention(mocker, failure):
  obj = owner()
  _, write, _ = setup_api(mocker, failure=failure)
  warning = mocker.patch.object(soundd.cloudlog, 'warning')
  error = mocker.patch.object(soundd.cloudlog, 'error')
  mocker.patch.object(soundd, 'monotonic_ns', side_effect=(1_000_000_000, 1_000_100_000))
  expected = owner()
  samples = callback(obj, status=SimpleNamespace(output_underflow=True))
  np.testing.assert_array_equal(samples, expected.get_sound_data(64))
  assert obj.underflow_timing[1:6] == (1_000_000_000, None, 100_000, 64, None)
  assert obj.output_underflow_count == 1
  assert obj.current_sound_frame == expected.current_sound_frame
  warning.assert_not_called()
  error.assert_not_called()
  obj.log_callback_scheduling_status()
  obj.log_callback_scheduling_status()
  warning.assert_called_once()
  assert 'soundd callback scheduling unavailable:' in warning.call_args.args[0]
  obj.configure_current_callback_thread()
  write.assert_called_once()
  mocker.patch.object(soundd.time, 'monotonic', return_value=1.1)
  mocker.patch.object(soundd, '_callback_thread_snapshot', return_value={})
  obj.log_pending_stream_status()
  error.assert_called_once()
  assert 'output_underflows=1' in error.call_args.args[0]
  assert 'callback_work_ms=0.100' in error.call_args.args[0]


def test_scheduler_read_failure_is_contained_before_any_set(mocker):
  obj = owner()
  read, write, _ = setup_api(mocker)
  read.side_effect = PermissionError('query denied')
  expected = owner()
  np.testing.assert_array_equal(callback(obj), expected.get_sound_data(64))
  callback(obj)
  read.assert_called_once_with(0)
  write.assert_not_called()
  assert obj.pending_callback_scheduling_status[1] == 'unavailable'


def test_pc_callback_keeps_samples_and_performs_no_scheduler_syscall(mocker):
  obj = owner()
  read, write, _ = setup_api(mocker)
  mocker.patch.object(soundd, 'PC', True)
  expected = owner()
  np.testing.assert_array_equal(callback(obj), expected.get_sound_data(64))
  read.assert_not_called()
  write.assert_not_called()
  assert obj.pending_callback_scheduling_status is None


def test_successful_setup_preserves_existing_dismissal_tail(mocker):
  obj = owner()
  read, write, _ = setup_api(mocker)
  expected = owner()
  obj.current_sound_frame = expected.current_sound_frame = 7
  obj.update_alert(soundd.AudibleAlert.none)
  expected.update_alert(soundd.AudibleAlert.none)
  np.testing.assert_array_equal(callback(obj), expected.get_sound_data(64))
  assert obj.current_alert == expected.current_alert == soundd.AudibleAlert.none
  assert obj.pending_stop == expected.pending_stop is False
  read.assert_called_once_with(0)
  write.assert_called_once_with(0, 2, ('priority', 1))
