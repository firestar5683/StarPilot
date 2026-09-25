from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

from openpilot.starpilot.galaxy.settings import LiveContextSource


class Messages:
  def __init__(self):
    self.frame = 7
    self.data: dict = {
      'deviceState': SimpleNamespace(started=False),
      'pandaStates': [SimpleNamespace(pandaType='uno', ignitionLine=False, ignitionCan=False,
                                     safetyModel='noOutput', controlsAllowed=False)],
      'carState': SimpleNamespace(canValid=True, canTimeout=False, standstill=True, gearShifter='park'),
      'selfdriveState': SimpleNamespace(enabled=False, active=False),
    }
    self.seen = dict.fromkeys(self.data, True)
    self.alive = dict.fromkeys(self.data, True)
    self.valid = dict.fromkeys(self.data, True)
    self.updated = dict.fromkeys(self.data, True)
    self.logMonoTime = dict.fromkeys(self.data, 2_000_000_000)
    self.logMonoTime['pandaStates'] = 12_000_000_000
    self.recv_time = dict.fromkeys(self.data, 2.0)
    self.update = Mock(side_effect=AssertionError('Borrowed collector advanced'))
    self.sock = {'carState': SimpleNamespace(close=Mock(side_effect=AssertionError('Borrowed socket closed')))}

  def __getitem__(self, key):
    return self.data[key]


class Params:
  def __init__(self):
    self.offroad = b'1'

  def get(self, key):
    assert key == 'IsOffroad'
    return self.offroad


def test_borrowed_ui_authorities_preserve_fresh_gates_and_collector_lifecycle(tmp_path):
  from openpilot.common.params import Params as NativeParams
  messages, params = Messages(), NativeParams(str(tmp_path))
  params.put_bool("IsOffroad", True, block=True)
  now = [1_000_000_000]
  authorities = [LiveContextSource(params, messages=messages, borrowed_messages=True, evidence_wait_ms=0,
                                  mono_clock=lambda: now[0], boot_clock=lambda: now[0] + 10_000_000_000)
                 for _ in range(2)]
  now[0] = 2_100_000_000
  with patch('openpilot.cereal.messaging.SubMaster', side_effect=AssertionError('Duplicate subscriber created')):
    for authority in authorities:
      assert authority.parked()
    authority = authorities[0]
    params.put_bool("IsOffroad", False, block=True)
    messages.data['pandaStates'][0].ignitionLine = True
    messages.data['pandaStates'][0].safetyModel = 'hyundai'
    messages.data['deviceState'].started = True
    assert not authority.configuration_allowed()  # First observer requires a new physical sample.
    now[0] += 200_000_000
    for service in messages.data:
      messages.logMonoTime[service] = now[0] - 100_000_000 + (10_000_000_000 if service == 'pandaStates' else 0)
      messages.recv_time[service] = (now[0] - 100_000_000) / 1e9
    assert authority.configuration_allowed()
    for target, field, value in [(messages.data['carState'], 'standstill', False),
                                 (messages.data['carState'], 'gearShifter', 'drive'),
                                 (messages.data['selfdriveState'], 'enabled', True),
                                 (messages.data['selfdriveState'], 'active', True)]:
      old = getattr(target, field)
      setattr(target, field, value)
      assert not authority.configuration_allowed()
      setattr(target, field, old)
    messages.valid['carState'] = False
    assert not authority.configuration_allowed()
    messages.valid['carState'] = True
    fresh_now = now[0]
    now[0] += 1_000_000_000
    assert not authority.configuration_allowed()
    now[0] = fresh_now
    authority.close()
    assert not authority.configuration_allowed()
    params.put_bool("IsOffroad", True, block=True)
    messages.data['pandaStates'][0].ignitionLine = False
    messages.data['pandaStates'][0].safetyModel = 'noOutput'
    messages.data['deviceState'].started = False
    authorities[1].close()
  assert messages.frame == 7
  messages.update.assert_not_called()
  messages.sock['carState'].close.assert_not_called()


def test_owned_collector_cleanup_is_preserved():
  messages = Messages()
  messages.sock['carState'].close = Mock()
  authority = LiveContextSource(Params(), messages=messages)
  authority.close()
  messages.sock['carState'].close.assert_called_once()
  with pytest.raises(ValueError, match='Borrowed authority'):
    LiveContextSource(Params(), borrowed_messages=True)


def test_actual_ui_constructor_borrows_one_collector_for_both_runtimes():
  import ast
  from pathlib import Path
  import sys

  import openpilot

  source = Path(openpilot.__file__).parent / 'selfdrive/ui/ui.py'
  tree = ast.parse(source.read_text())
  main = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == 'main')
  messages = Messages()
  layout = SimpleNamespace(star=SimpleNamespace(_favorite_actions=(),
                           favorites_owner=SimpleNamespace(snapshot=Mock(), invoke=Mock())), close=Mock())
  created = []

  def runtime(*args, **kwargs):
    authority = kwargs['authority']
    created.append(authority)
    assert authority.messages is messages and authority.borrowed_messages
    return SimpleNamespace(close=authority.close)

  modules = {
    'openpilot.starpilot.ui.runtime_app': SimpleNamespace(StarMainLayout=lambda: layout, StarMiciMainLayout=lambda: layout),
    'openpilot.starpilot.controllers.runtime': SimpleNamespace(ControllerRuntime=runtime),
    'openpilot.starpilot.ui.layout_preview_runtime': SimpleNamespace(LayoutPreviewRuntime=runtime),
  }
  scope: dict = {
    'COMMA_HARDWARE': False,
    'config_realtime_process': Mock(),
    'Priority': SimpleNamespace(UI=0),
    'select_ui': lambda *args: SimpleNamespace(custom=True, reason='test'),
    'os': SimpleNamespace(environ={}),
    'sys': sys,
    'Profile': SimpleNamespace(LARGE=SimpleNamespace(value='large'), COMPACT=SimpleNamespace(value='compact')),
    'gui_app': SimpleNamespace(init_window=Mock(), render=lambda **kwargs: iter(())),
    'ui_state': SimpleNamespace(params=Params(), sm=messages, is_offroad=lambda: True, replay_clock=None),
    'messaging': SimpleNamespace(PubMaster=Mock()),
    'update_frame': Mock(),
  }
  exec(compile(ast.Module(body=[main], type_ignores=[]), str(source), 'exec'), scope)
  with patch.dict(sys.modules, modules), patch('openpilot.cereal.messaging.SubMaster',
                                             side_effect=AssertionError('Duplicate subscriber created')):
    for big in (False, True):
      scope['BIG_UI'] = big
      scope['main']()
  assert len(created) == 4 and all(authority.closed for authority in created)
  assert messages.frame == 7
  messages.update.assert_not_called()
  messages.sock['carState'].close.assert_not_called()
