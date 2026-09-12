"""Exercise physical event reads without a controller, native IPC, or vehicle actions."""
import ast
import os
from pathlib import Path
from types import SimpleNamespace

import pytest

from openpilot.starpilot.system.wheel_controls import wheel_controlsd
from test_wheel_controlsd import FakeParams, source


PRESS_PARAM = "StandbyButtonPressTime"


@pytest.fixture
def input_pipe():
  params = FakeParams({"ScreenManagement": True, "StandbyMode": True, "StandbyWakeButton": True})
  memory = FakeParams()
  daemon = wheel_controlsd.WheelControlsDaemon(params, memory)
  read_fd, write_fd = os.pipe()
  os.set_blocking(read_fd, False)
  daemon.sources[read_fd] = source()
  daemon.buffers[read_fd] = bytearray()

  def send(event_type, code, value):
    os.write(write_fd, wheel_controlsd.INPUT_EVENT.pack(0, 0, event_type, code, value))
    daemon._read_events(read_fd)

  yield daemon, params, memory, read_fd, send
  os.close(write_fd)
  daemon.close()


def test_unmapped_key_press_publishes_once_until_released(input_pipe, monkeypatch):
  _daemon, _params, memory, _fd, send = input_pipe
  now = [100]
  monkeypatch.setattr(wheel_controlsd.time, "monotonic_ns", lambda: now[0])

  send(wheel_controlsd.EV_KEY, 304, 1)
  assert memory.get_int(PRESS_PARAM) == 100
  now[0] = 200
  for value in (2, 1, 2, 0):
    send(wheel_controlsd.EV_KEY, 304, value)
    assert memory.get_int(PRESS_PARAM) == 100
  send(wheel_controlsd.EV_KEY, 304, 1)
  assert memory.get_int(PRESS_PARAM) == 200


def test_selected_joystick_buttons_wake_without_executing_mappings(input_pipe, monkeypatch):
  _daemon, params, memory, _fd, send = input_pipe
  wheel_controlsd.upsert_mapping(source(), 304, 0, params)
  wheel_controlsd.set_joystick_device(source().device_id, True, params)
  actions = []
  monkeypatch.setattr(wheel_controlsd, "execute_mapping_slot", lambda slot, *_args: actions.append(slot))
  monkeypatch.setattr(wheel_controlsd.time, "monotonic_ns", lambda: 123456789)

  send(wheel_controlsd.EV_KEY, 304, 1)
  assert memory.get_int(PRESS_PARAM) == 123456789
  assert actions == []


@pytest.mark.parametrize("disabled_key", ["ScreenManagement", "StandbyMode", "StandbyWakeButton"])
def test_button_wake_is_opt_in_and_enabling_it_while_held_does_not_create_a_press(input_pipe, monkeypatch, disabled_key):
  _daemon, params, memory, _fd, send = input_pipe
  params.put_bool(disabled_key, False)
  monkeypatch.setattr(wheel_controlsd.time, "monotonic_ns", lambda: 100)
  send(wheel_controlsd.EV_KEY, 304, 1)
  assert memory.get(PRESS_PARAM) is None
  params.put_bool(disabled_key, True)
  send(wheel_controlsd.EV_KEY, 304, 2)
  send(wheel_controlsd.EV_KEY, 304, 1)
  assert memory.get(PRESS_PARAM) is None
  send(wheel_controlsd.EV_KEY, 304, 0)
  send(wheel_controlsd.EV_KEY, 304, 1)
  assert memory.get_int(PRESS_PARAM) == 100


def test_dpad_direction_edges_wake_but_neutral_repeats_and_analog_axes_do_not(input_pipe, monkeypatch):
  _daemon, _params, memory, _fd, send = input_pipe
  now = [100]
  monkeypatch.setattr(wheel_controlsd.time, "monotonic_ns", lambda: now[0])

  send(wheel_controlsd.EV_ABS, 0, 32767)
  send(wheel_controlsd.EV_ABS, wheel_controlsd.ABS_HAT0X, 0)
  assert memory.get(PRESS_PARAM) is None
  send(wheel_controlsd.EV_ABS, wheel_controlsd.ABS_HAT0X, -1)
  assert memory.get_int(PRESS_PARAM) == 100
  now[0] = 200
  send(wheel_controlsd.EV_ABS, wheel_controlsd.ABS_HAT0X, -1)
  assert memory.get_int(PRESS_PARAM) == 100
  send(wheel_controlsd.EV_ABS, wheel_controlsd.ABS_HAT0X, 1)
  assert memory.get_int(PRESS_PARAM) == 200
  now[0] = 300
  send(wheel_controlsd.EV_ABS, wheel_controlsd.ABS_HAT0X, 0)
  assert memory.get_int(PRESS_PARAM) == 200
  send(wheel_controlsd.EV_ABS, wheel_controlsd.ABS_HAT0X, 1)
  assert memory.get_int(PRESS_PARAM) == 300


def test_wake_only_listener_does_not_reactivate_disabled_mappings(input_pipe, monkeypatch):
  _daemon, params, memory, _fd, send = input_pipe
  wheel_controlsd.upsert_mapping(source(), 30, 2, params)
  params.put_bool("WheelControlsEnabled", False)
  actions = []
  monkeypatch.setattr(wheel_controlsd, "execute_mapping_slot", lambda slot, *_args: actions.append(slot))
  monkeypatch.setattr(wheel_controlsd.time, "monotonic_ns", lambda: 999)

  send(wheel_controlsd.EV_KEY, 30, 1)
  assert actions == []
  assert memory.get_int(PRESS_PARAM) == 999


def test_enabled_mapping_still_executes_once_on_press_with_wake_timestamp(input_pipe, monkeypatch):
  _daemon, params, memory, _fd, send = input_pipe
  wheel_controlsd.upsert_mapping(source(), 30, 2, params)
  actions = []
  monkeypatch.setattr(wheel_controlsd, "execute_mapping_slot", lambda slot, *_args: actions.append(slot))
  monkeypatch.setattr(wheel_controlsd.time, "monotonic_ns", lambda: 777)

  for value in (1, 2, 0):
    send(wheel_controlsd.EV_KEY, 30, value)
  assert actions == [2]
  assert memory.get_int(PRESS_PARAM) == 777


def test_wake_timestamp_failure_does_not_interrupt_mapped_button_actions(input_pipe, monkeypatch):
  _daemon, params, memory, _fd, send = input_pipe
  wheel_controlsd.upsert_mapping(source(), 30, 2, params)
  actions = []
  monkeypatch.setattr(wheel_controlsd, "execute_mapping_slot", lambda slot, *_args: actions.append(slot))

  def fail_write(key, value):
    raise OSError("memory Params unavailable")

  monkeypatch.setattr(memory, "put_int", fail_write)
  send(wheel_controlsd.EV_KEY, 30, 1)
  assert actions == [2]


def test_disconnected_device_does_not_suppress_next_press_on_reused_descriptor(input_pipe, monkeypatch):
  daemon, _params, memory, fd, send = input_pipe
  now = [100]
  monkeypatch.setattr(wheel_controlsd.time, "monotonic_ns", lambda: now[0])
  send(wheel_controlsd.EV_KEY, 304, 1)
  assert memory.get_int(PRESS_PARAM) == 100

  # Keep this test's pipe open while exercising the real per-device cleanup.
  with monkeypatch.context() as patch:
    patch.setattr(wheel_controlsd.os, "close", lambda _fd: None)
    daemon._remove(fd)
  daemon.sources[fd] = source()
  daemon.buffers[fd] = bytearray()
  now[0] = 200
  send(wheel_controlsd.EV_KEY, 304, 1)
  assert memory.get_int(PRESS_PARAM) == 200


@pytest.mark.parametrize("started", [False, True])
@pytest.mark.parametrize("mapping,management,standby,button,expected", [
  (False, False, False, False, False),
  (False, True, True, True, True),
  (False, False, True, True, False),
  (False, True, False, True, False),
  (False, True, True, False, False),
  (True, False, False, False, True),
])
def test_manager_runs_listener_for_enabled_mappings_or_selected_standby_wake(started, mapping, management, standby, button, expected):
  # The manager module creates native processes at import, so load its real predicate only.
  path = Path(__file__).resolve().parents[4] / "system/manager/process_config.py"
  tree = ast.parse(path.read_text())
  node = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "wheel_controls_enabled")
  namespace = {"Params": object, "car": SimpleNamespace(CarParams=object), "SimpleNamespace": SimpleNamespace}
  exec(compile(ast.Module(body=[node], type_ignores=[]), str(path), "exec"), namespace)
  params = FakeParams({"WheelControlsEnabled": mapping, "ScreenManagement": management,
                       "StandbyMode": standby, "StandbyWakeButton": button})
  assert namespace["wheel_controls_enabled"](started, params, None, SimpleNamespace()) is expected
