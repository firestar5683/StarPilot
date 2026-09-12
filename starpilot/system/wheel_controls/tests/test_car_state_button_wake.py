"""Preserve short carState button edges between UI refreshes, without vehicle actions."""
import ast
import sys
from pathlib import Path
from typing import Optional
from types import SimpleNamespace

import capnp
import pytest
from cereal import log

from openpilot.starpilot.system.wheel_controls import wheel_controlsd
from test_wheel_controlsd import FakeParams


def packet(timestamp, pressed=None, *, valid=True, button_type='accelCruise'):
  message = log.Event.new_message(logMonoTime=timestamp, valid=valid)
  state = message.init('carState')
  if pressed is not None:
    buttons = state.init('buttonEvents', 1)
    buttons[0].type, buttons[0].pressed = button_type, pressed
  return message


@pytest.fixture
def car_buttons(monkeypatch):
  params = FakeParams({'ScreenManagement': True, 'StandbyMode': True, 'StandbyWakeButton': True, 'IsOnroad': True})
  memory = FakeParams()
  daemon = wheel_controlsd.WheelControlsDaemon(params, memory)
  queued, subscriptions = [], []
  now_boot, now_mono = [10_000_000_000], [1_000_000_000]

  def subscribe(endpoint, *, conflate=False):
    assert endpoint == 'carState'
    assert conflate is False, 'Every published button edge must be read'
    sock = object()
    subscriptions.append(sock)
    return sock

  def drain(sock, wait_for_one=False):
    assert wait_for_one is False
    assert sock is subscriptions[-1]
    result, queued[:] = list(queued), []
    return result

  import cereal
  messaging = SimpleNamespace(sub_sock=subscribe, drain_sock=drain)
  monkeypatch.setitem(sys.modules, 'cereal.messaging', messaging)
  monkeypatch.setattr(cereal, 'messaging', messaging, raising=False)
  monkeypatch.setattr(wheel_controlsd.time, 'clock_gettime_ns', lambda _clock: now_boot[0])
  monkeypatch.setattr(wheel_controlsd.time, 'monotonic_ns', lambda: now_mono[0])
  yield daemon, params, memory, queued, subscriptions, now_boot, now_mono
  daemon.close()


def test_short_button_edge_survives_later_empty_frame_and_is_consumed_once(car_buttons):
  daemon, _params, memory, queued, subscriptions, _boot, now = car_buttons
  daemon._configure_car_buttons()
  now[0] += 100_000_000
  queued[:] = [packet(1_020_000_000, True), packet(1_030_000_000)]
  daemon._poll_car_buttons()
  assert memory.get_int('StandbyButtonPressTime') == 1_020_000_000
  daemon._poll_car_buttons()
  assert memory.get_int('StandbyButtonPressTime') == 1_020_000_000
  assert len(subscriptions) == 1


@pytest.mark.parametrize('disabled', ['ScreenManagement', 'StandbyMode', 'StandbyWakeButton', 'IsOnroad'])
def test_subscription_only_runs_when_needed_and_reopens_cleanly(car_buttons, disabled):
  daemon, params, memory, queued, subscriptions, _boot, now = car_buttons
  params.put_bool(disabled, False)
  daemon._configure_car_buttons()
  assert subscriptions == []
  params.put_bool(disabled, True)
  daemon._configure_car_buttons()
  assert len(subscriptions) == 1
  params.put_bool(disabled, False)
  daemon._configure_car_buttons()
  daemon._poll_car_buttons()
  assert memory.get('StandbyButtonPressTime') is None
  now[0] += 10_000_000
  params.put_bool(disabled, True)
  daemon._configure_car_buttons()
  queued[:] = [packet(1_005_000_000, True)]  # Retained message predates re-enable.
  daemon._poll_car_buttons()
  assert memory.get('StandbyButtonPressTime') is None
  assert len(subscriptions) == 2


def test_releases_invalid_unknown_future_and_stale_packets_cannot_wake(car_buttons):
  daemon, _params, memory, queued, _subscriptions, _boot, now = car_buttons
  daemon._configure_car_buttons()
  now[0] = 4_000_000_000
  queued[:] = [packet(1_500_000_000, True), packet(3_000_000_000, False), packet(3_100_000_000, True, valid=False),
              packet(3_200_000_000, True, button_type='unknown'), packet(4_100_000_000, True)]
  daemon._poll_car_buttons()
  assert memory.get('StandbyButtonPressTime') is None
  queued[:] = [packet(3_900_000_000, True)]
  daemon._poll_car_buttons()
  assert memory.get_int('StandbyButtonPressTime') == 3_900_000_000
  queued[:] = [packet(3_800_000_000, True), packet(3_900_000_000, True)]
  daemon._poll_car_buttons()
  assert memory.get_int('StandbyButtonPressTime') == 3_900_000_000


def test_python_car_state_clock_stays_monotonic_after_suspend(car_buttons):
  daemon, _params, memory, queued, _subscriptions, now_boot, now_mono = car_buttons
  # Execute the actual factory used by card.py, without opening native IPC.
  source = Path(__file__).resolve().parents[4] / 'cereal/messaging/__init__.py'
  factory = next(node for node in ast.parse(source.read_text()).body if isinstance(node, ast.FunctionDef) and node.name == 'new_message')
  env = dict(log=log, Optional=Optional, capnp=capnp, time=SimpleNamespace(monotonic=lambda: now_mono[0] / 1e9))
  exec(compile(ast.Module(body=[factory], type_ignores=[]), str(source), 'exec'), env)
  now_boot[0] = 10_000_000_000
  daemon._configure_car_buttons()
  now_boot[0] = 20_000_000_000
  now_mono[0] = 4_500_000_000
  message = env['new_message']('carState', valid=True)
  button = message.carState.init('buttonEvents', 1)[0]
  button.type, button.pressed = 'accelCruise', True
  queued[:] = [message]
  now_mono[0] = 5_000_000_000
  daemon._poll_car_buttons()
  assert memory.get_int('StandbyButtonPressTime') == 4_500_000_000
