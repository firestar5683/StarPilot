from unittest import mock
from types import SimpleNamespace

import pytest

from openpilot.selfdrive.controls import controlsd


@pytest.mark.parametrize("device", ("mici", "tizi", "tici", "pc", "unknown"))
def test_controls_main_priority_is_applied_after_initialization_and_affinity(device):
  calls = []
  controls = mock.Mock()
  controls.run.side_effect = lambda: calls.append(("run",))

  def priority_changed(tid, policy, param):
    calls.append(("priority", tid, policy, param.sched_priority))
  with (mock.patch.object(controlsd, "config_realtime_process", side_effect=lambda core, priority: calls.append(("configure", core, priority))),
        mock.patch.object(controlsd, "Controls", side_effect=lambda: calls.append(("construct",)) or controls),
        mock.patch.object(controlsd, "set_core_affinity", side_effect=lambda cores: calls.append(("affinity", cores))),
        mock.patch.object(controlsd.HARDWARE, "get_device_type", return_value=device),
        mock.patch.object(controlsd.os, "SCHED_FIFO", getattr(controlsd.os, "SCHED_FIFO", 1), create=True),
        mock.patch.object(controlsd.os, "sched_param", getattr(controlsd.os, "sched_param",
                          lambda priority: SimpleNamespace(sched_priority=priority)), create=True),
        mock.patch.object(controlsd.os, "sched_setscheduler", create=True, side_effect=priority_changed)):
    controlsd.main()
    fifo = controlsd.os.SCHED_FIFO
  expected = [("configure", 4, controlsd.Priority.CTRL_HIGH), ("construct",), ("affinity", [4, 5])]
  if device in ("tici", "tizi", "mici"):
    expected.append(("priority", 0, fifo, 52))
  assert calls == [*expected, ("run",)]


def test_constructor_failure_does_not_reprioritize_existing_threads():
  with (mock.patch.object(controlsd, "config_realtime_process"),
        mock.patch.object(controlsd, "Controls", side_effect=RuntimeError("initialization failed")),
        mock.patch.object(controlsd.os, "sched_setscheduler", create=True) as priority,
        pytest.raises(RuntimeError, match="initialization failed")):
    controlsd.main()
  priority.assert_not_called()


def test_scheduler_failure_does_not_start_controls():
  controls = mock.Mock()
  with (mock.patch.object(controlsd, "config_realtime_process"),
        mock.patch.object(controlsd, "Controls", return_value=controls),
        mock.patch.object(controlsd, "set_core_affinity"),
        mock.patch.object(controlsd.HARDWARE, "get_device_type", return_value="mici"),
        mock.patch.object(controlsd.os, "SCHED_FIFO", getattr(controlsd.os, "SCHED_FIFO", 1), create=True),
        mock.patch.object(controlsd.os, "sched_param", getattr(controlsd.os, "sched_param",
                          lambda priority: SimpleNamespace(sched_priority=priority)), create=True),
        mock.patch.object(controlsd.os, "sched_setscheduler", create=True, side_effect=PermissionError("priority denied")),
        pytest.raises(PermissionError, match="priority denied")):
    controlsd.main()
  controls.run.assert_not_called()
