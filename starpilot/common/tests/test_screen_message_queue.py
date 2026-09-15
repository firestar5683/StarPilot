"""Keep every button edge without adding a messaging reader or UI update frame."""
import ast
import os
from pathlib import Path
from types import SimpleNamespace
from typing import Optional

import capnp
import pytest
from cereal import log
from cereal.services import SERVICE_LIST

from test_screen_device_runtime import make_device

ROOT = Path(__file__).resolve().parents[3]


def packet(timestamp, pressed=None, *, valid=True, button_type='accelCruise'):
  message = log.Event.new_message(logMonoTime=timestamp, valid=valid)
  state = message.init('carState')
  if pressed is not None:
    buttons = state.init('buttonEvents', 1)
    buttons[0].type, buttons[0].pressed = button_type, pressed
  return message


def submaster_fixture():
  sockets = []

  class Poller:
    def __init__(self):
      self.sockets = []

    def poll(self, timeout):
      # Native Poller returns new wrapper objects around the same C++ socket.
      return [SocketView(sock) for sock in self.sockets if sock.queue]

  class SocketView:
    def __init__(self, sock):
      self.sock = sock

    def __getattr__(self, name):
      return getattr(self.sock, name)

  class Socket:
    def __init__(self, service, poller=None, conflate=False, **kwargs):
      self.service, self.conflate, self.queue = service, conflate, []
      sockets.append(self)
      if poller is not None:
        poller.sockets.append(self)

  class FrequencyTracker:
    def __init__(self, *args):
      self.times, self.valid = [], True

    def record_recv_time(self, now):
      self.times.append(now)

  def receive(sock):
    if not sock.queue:
      return None
    if sock.conflate:
      message, sock.queue[:] = sock.queue[-1], []
      return message
    return sock.queue.pop(0)

  def drain(sock):
    messages, sock.queue[:] = list(sock.queue), []
    return messages

  env = dict(List=list, Optional=Optional, Dict=dict, capnp=capnp, log=log, os=os, SERVICE_LIST=SERVICE_LIST,
             time=SimpleNamespace(monotonic=lambda: 100.0), Poller=Poller, sub_sock=Socket,
             FrequencyTracker=FrequencyTracker, recv_one_or_none=receive, drain_sock=drain)
  source = ROOT / 'cereal/messaging/__init__.py'
  nodes = [node for node in ast.parse(source.read_text()).body
           if isinstance(node, (ast.ClassDef, ast.FunctionDef)) and node.name in ('SubMaster', 'new_message')]
  exec(compile(ast.Module(body=nodes, type_ignores=[]), str(source), 'exec'), env)
  return env['SubMaster'], sockets


def test_default_submaster_keeps_existing_conflation():
  cls, sockets = submaster_fixture()
  sm = cls(['carState', 'deviceState'])
  assert len(sockets) == 2 and all(sock.conflate for sock in sockets)
  sockets[0].queue[:] = [packet(1, True), packet(2)]
  sm.update(0)
  assert sm.logMonoTime['carState'] == 2 and sm.frame == 0
  assert not sm['carState'].buttonEvents


@pytest.mark.parametrize('poll', [None, 'deviceState'])
def test_selected_reader_drains_edges_and_updates_latest_state_once(poll):
  cls, sockets = submaster_fixture()
  sm = cls(['carState', 'deviceState'], poll=poll, drain_services=['carState'])
  assert len(sockets) == 2
  assert sockets[0].conflate is False and sockets[1].conflate is True
  sockets[0].queue[:] = [packet(99_500_000_000, True), packet(99_600_000_000)]
  other = log.Event.new_message(logMonoTime=99_600_000_000, valid=True)
  other.init('deviceState')
  sockets[1].queue[:] = [other]
  sm.update(0)
  assert len(sm.drained['carState']) == 2 and sm.drained['carState'][0].carState.buttonEvents[0].pressed
  assert sm.logMonoTime['carState'] == 99_600_000_000 and not sm['carState'].buttonEvents
  assert sm.frame == 0 and all(sm.updated.values())
  assert sm.freq_tracker['carState'].times == sm.freq_tracker['deviceState'].times == [100.0]
  sm.update(0)
  assert sm.drained['carState'] == [] and not any(sm.updated.values()) and sm.frame == 1
  extended = sm.extend(['modelV2'])
  assert set(extended.drained) == {'carState'}
  assert extended.sock['carState'].conflate is False


@pytest.mark.parametrize('enabled', [False, True])
@pytest.mark.parametrize('brightness', [0, 101])
def test_ui_uses_queued_button_press_once_with_optional_wake(enabled, brightness):
  device, state, _ = make_device(StandbyWakeButton=enabled, ScreenBrightnessOnroad=brightness)
  device._last_car_button_frame = 99_000_000_000
  state.sm.drained = {'carState': [packet(99_500_000_000, True), packet(99_600_000_000)]}
  device._update_wakefulness()
  assert device.awake is enabled
  device._interaction_time = 90
  device._update_wakefulness()
  assert not device.awake
  assert state.params_memory.get('StandbyButtonPressTime') is None


def test_ui_rejects_invalid_unknown_release_future_stale_and_reordered_buttons():
  device, state, _ = make_device(StandbyWakeButton=True)
  device._last_car_button_frame = 97_000_000_000
  state.sm.drained = {'carState': [packet(97_500_000_000, True), packet(99_100_000_000, False),
                                 packet(99_200_000_000, True, valid=False), packet(99_300_000_000, True, button_type='unknown'),
                                 packet(100_100_000_000, True)]}
  device._update_wakefulness()
  assert not device.awake
  state.sm.drained = {'carState': [packet(99_800_000_000, True)]}
  device._update_wakefulness()
  assert device.awake
  device._interaction_time = 90
  state.sm.drained = {'carState': [packet(99_700_000_000, True)]}
  device._update_wakefulness()
  assert not device.awake


def test_vehicle_button_wake_adds_no_daemon_reader():
  source = (ROOT / 'starpilot/system/wheel_controls/wheel_controlsd.py').read_text()
  assert 'sub_sock(' not in source
  ui = ast.parse((ROOT / 'selfdrive/ui/ui_state.py').read_text())
  calls = [node for node in ast.walk(ui) if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == 'SubMaster']
  assert len(calls) == 1
  assert any(kw.arg == 'drain_services' and ast.literal_eval(kw.value) == ['carState'] for kw in calls[0].keywords)
