from unittest.mock import patch
import os
import sys
import pytest

pytestmark = pytest.mark.skipif(sys.platform != "linux", reason="Diagnostic process uses Linux scheduling and pipe APIs")


def load():
  from openpilot.starpilot import planner_phase_timing
  return planner_phase_timing


def test_fixed_atomic_record_original_context_and_rate():
  module = load()
  now = [2_000_000_000]
  timing = module.PlannerPhaseTiming(spawn=False, clock=lambda: (now[0], now[0] // 2))
  read, write = os.pipe()
  timing.fd = write
  assert module.RECORD.size <= os.fpathconf(write, 'PC_PIPE_BUF')
  with patch.object(module.os, 'write', wraps=os.write) as writes:
    for _tick in range(10):
      timing.begin((10, 9, 8, 7))
      now[0] += 40_000_000
      timing.mark('slc_send_return')
      timing.finish(relevant=True, solver_s=.001)
    assert writes.call_count == 1
  row = module.RECORD.unpack(os.read(read, module.RECORD.size))
  assert row[:6] == (1, 10, 9, 8, 7, 0)
  assert row[6] == .001 and row[7] == 2
  timing.close()
  os.close(read)


def test_full_pipe_drops_without_waiting_or_disabling():
  module = load()
  now = [2_000_000_000]
  timing = module.PlannerPhaseTiming(spawn=False, clock=lambda: (now[0], 1))
  timing.fd = 99
  with patch.object(module.os, 'write', side_effect=BlockingIOError):
    timing.begin((1, 2, 3, 4))
    now[0] += 40_000_000
    timing.mark('slc_send_return')
    timing.finish(relevant=True, solver_s=.001)
  assert timing.dropped == 1 and timing.fd == 99 and timing.points == []
  timing.fd = None


def test_startup_failure_disables_only_observation():
  module = load()
  with patch.object(module.os, 'posix_spawn', side_effect=OSError):
    timing = module.PlannerPhaseTiming()
  timing.begin((1, 2, 3, 4))
  timing.mark('slc_send_return')
  timing.finish(relevant=True, solver_s=.001)
  assert timing.fd is None and timing.points == []
  timing.close()


def test_broken_pipe_and_pack_failure_are_optional():
  module = load()
  now = [2_000_000_000]
  timing = module.PlannerPhaseTiming(spawn=False, clock=lambda: (now[0], 1))
  read, write = os.pipe()
  os.close(read)
  timing.fd = write
  timing.begin((1, 2, 3, 4))
  now[0] += 40_000_000
  timing.mark('slc_send_return')
  timing.finish(relevant=True, solver_s=.001)
  assert timing.fd is None and timing.points == []
  timing.begin(('invalid', 2, 3, 4))
  assert timing.points == []
  timing.fd = 99
  timing.begin((1, 2, 3, 4))
  now[0] += 1_100_000_000
  timing.mark('slc_send_return')
  timing.finish(relevant=True, solver_s=object())
  assert timing.dropped == 1 and timing.points == []
  timing.fd = None


def test_shutdown_uses_only_bounded_nonblocking_reaping():
  module = load()
  timing = module.PlannerPhaseTiming(spawn=False)
  timing.pid = 123
  with patch.object(module.os, 'waitpid', return_value=(0, 0)) as waiting, \
       patch.object(module.os, 'kill') as killing, \
       patch.object(module.time, 'monotonic', side_effect=(0., 0., .2)), \
       patch.object(module.time, 'sleep'):
    timing.close()
  assert all(call.args[1] == os.WNOHANG for call in waiting.call_args_list)
  killing.assert_called_once_with(123, module.signal.SIGKILL)
  assert timing.pid == 123


def test_actual_spawned_worker_eof_and_cleanup():
  module = load()
  timing = module.PlannerPhaseTiming()
  assert timing.pid is not None and timing.fd is not None
  pid = timing.pid
  assert os.sched_getscheduler(pid) == os.SCHED_OTHER
  timing.close()
  assert timing.pid is None and timing.fd is None
  try:
    os.kill(pid, 0)
  except ProcessLookupError:
    pass
  else:
    raise AssertionError('Diagnostic child did not exit in bounded shutdown')


def test_spawn_failure_cleanup_close_errors_cannot_escape():
  module = load()
  with patch.object(module.os, 'pipe2', return_value=(88, 89)), \
       patch.object(module.os, 'set_blocking'), \
       patch.object(module.os, 'fpathconf', return_value=4096), \
       patch.object(module.os, 'posix_spawn', side_effect=OSError), \
       patch.object(module.os, 'close', side_effect=OSError) as closing:
    timing = module.PlannerPhaseTiming()
  assert timing.fd is None and timing.pid is None
  assert [call.args[0] for call in closing.call_args_list] == [88, 89]


def test_actual_child_cloudlog_transport_and_partial_malformed_record():
  import json
  import time
  import zmq
  from openpilot.common.hardware.hw import Paths
  from openpilot.common.prefix import OpenpilotPrefix

  module = load()
  with OpenpilotPrefix():
    context = zmq.Context()
    receiver = context.socket(zmq.PULL)
    receiver.setsockopt(zmq.LINGER, 0)
    receiver.bind(Paths.swaglog_ipc())
    now = [2_000_000_000]
    timing = module.PlannerPhaseTiming(clock=lambda: (now[0], now[0] // 2))
    try:
      assert timing.pid is not None and timing.pid != os.getpid()
      assert timing.fd is not None
      assert os.sched_getscheduler(timing.pid) == os.SCHED_OTHER
      invalid_points = [len(module.PHASES), 1, 1] + [0, 0, 0] * (len(module.PHASES) - 1)
      invalid = module.RECORD.pack(99, 10, 9, 8, 7, 0, .001, 1, *invalid_points)
      # Partial reads must accumulate; an out-of-range phase record is discarded.
      assert os.write(timing.fd, invalid[:17]) == 17
      assert os.write(timing.fd, invalid[17:]) == len(invalid) - 17
      timing.begin((10, 9, 8, 7))
      now[0] += 40_000_000
      timing.mark('slc_send_return')
      timing.finish(relevant=True, solver_s=.001)
      deadline = time.monotonic() + 5.
      record = None
      while time.monotonic() < deadline:
        if receiver.poll(100):
          wire = receiver.recv()
          decoded = json.loads(wire[1:].decode())
          message = decoded.get('msg', {})
          if isinstance(message, dict) and message.get('event') == 'plannerd.phase_timing':
            record = message
            break
      assert record is not None, 'Actual child must import cloudlog and emit the record'
      assert record['sequence'] == 1 and record['context'] == [10, 9, 8, 7]
      assert record['solver_seconds'] == .001 and record['dropped'] == 0
      assert record['points'] == [['model_received', 2_000_000_000, 1_000_000_000],
                                  ['slc_send_return', 2_040_000_000, 1_020_000_000]]
      assert record['context_columns'] == ['model_ns', 'car_state_ns', 'selfdrive_ns', 'car_control_ns']
      assert record['point_columns'] == ['phase', 'monotonic_ns', 'thread_cpu_ns']
      assert os.sched_getscheduler(timing.pid) == os.SCHED_OTHER
    finally:
      timing.close()
      receiver.close()
      context.term()


def test_interrupted_reaping_preserves_ownership_and_retries():
  module = load()
  timing = module.PlannerPhaseTiming(spawn=False)
  timing.pid = 123
  with patch.object(module.os, 'waitpid', side_effect=(InterruptedError(), (0, 0), (123, 0))), \
       patch.object(module.os, 'kill') as killing, \
       patch.object(module.time, 'monotonic', return_value=0.), \
       patch.object(module.time, 'sleep'):
    timing.close()
  killing.assert_called_once_with(123, module.signal.SIGKILL)
  assert timing.pid is None


def test_actual_hung_child_is_killed_and_reaped():
  import sys
  module = load()
  timing = module.PlannerPhaseTiming(spawn=False)
  timing.pid = os.posix_spawn(sys.executable, [sys.executable, '-c', 'import time; time.sleep(60)'],
                            os.environ.copy(), scheduler=(os.SCHED_OTHER, os.sched_param(0)))
  pid = timing.pid
  try:
    timing.close()
    assert timing.pid is None
    try:
      os.kill(pid, 0)
    except ProcessLookupError:
      pass
    else:
      raise AssertionError('Hung diagnostic child survived bounded close')
  finally:
    if timing.pid is not None:
      os.kill(timing.pid, module.signal.SIGKILL)
      os.waitpid(timing.pid, os.WNOHANG)
