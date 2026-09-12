"""Compare wake policy with real renderer methods without constructing widgets."""
import ast
from enum import IntEnum
from pathlib import Path
from types import SimpleNamespace

import pytest

from openpilot.starpilot.common.screen_settings import alert_wake_key, standby_alert_wake_key


class ProtoEnum(IntEnum):
  @property
  def raw(self):
    return int(self)


class Size(ProtoEnum):
  none = 0
  small = 1
  mid = 2
  full = 3


class Status(ProtoEnum):
  normal = 0
  userPrompt = 1
  critical = 2
  starpilot = 3


def message():
  return SimpleNamespace(enabled=True, alertSize=Size.none, alertStatus=Status.normal,
                         alertText1='', alertText2='', alertType='', alertHudVisual=0)


def renderer_method(mici, state, sm, tici):
  root = Path(__file__).resolve().parents[3]
  source = root / ('selfdrive/ui/mici/onroad/alert_renderer.py' if mici else 'selfdrive/ui/onroad/alert_renderer.py')
  tree = ast.parse(source.read_text())
  constants = {'ALERT_STARTUP_PENDING', 'ALERT_CRITICAL_TIMEOUT', 'ALERT_CRITICAL_REBOOT',
               'SELFDRIVE_STATE_TIMEOUT', 'SELFDRIVE_UNRESPONSIVE_TIMEOUT'}
  body = [node for node in tree.body if isinstance(node, ast.Assign) and any(
    isinstance(target, ast.Name) and target.id in constants for target in node.targets)]
  renderer = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == 'AlertRenderer')
  body.append(next(node for node in renderer.body if isinstance(node, ast.FunctionDef) and node.name == 'get_alert'))
  namespace = dict(Alert=SimpleNamespace, AlertSize=Size, AlertStatus=Status,
                   custom=SimpleNamespace(StarPilotSelfdriveState=SimpleNamespace(AlertSize=Size)),
                   messaging=SimpleNamespace(SubMaster=object), tr=lambda text: text, ui_state=state,
                   time=SimpleNamespace(monotonic=lambda: 100), TICI=tici)
  exec(compile(ast.Module(body=body, type_ignores=[]), str(source), 'exec'), namespace)
  return namespace['get_alert'](SimpleNamespace(), sm)


@pytest.mark.parametrize('mici', [False, True])
@pytest.mark.parametrize('scenario', [
  'startup', 'startup_boundary', 'takeover', 'timeout_boundary', 'reboot', 'reboot_boundary', 'reboot_disengaged',
  'nonhardware', 'updated_old_timestamp', 'info', 'warning', 'critical', 'no_size', 'secondary',
  'primary_precedence', 'hidden_normal', 'visible_starpilot', 'hidden_generated_startup',
])
def test_wake_category_matches_actual_renderer_alert(mici, scenario):
  class Messages(dict):
    pass
  sm = Messages(selfdriveState=message(), starpilotSelfdriveState=message())
  sm.updated = {'selfdriveState': True}
  sm.recv_frame = {'selfdriveState': 6}
  sm.recv_time = {'selfdriveState': 100}
  state = SimpleNamespace(started_time=90, started_frame=5, starpilot_toggles={})
  tici = True
  primary = sm['selfdriveState']
  secondary = sm['starpilotSelfdriveState']
  if scenario in ('startup', 'startup_boundary', 'hidden_generated_startup'):
    sm.updated['selfdriveState'] = False
    sm.recv_frame['selfdriveState'] = 4
    if scenario == 'startup_boundary':
      state.started_time = 95
    if scenario == 'hidden_generated_startup':
      state.starpilot_toggles['hide_alerts'] = True
  elif scenario in ('takeover', 'timeout_boundary', 'reboot', 'reboot_boundary', 'reboot_disengaged', 'nonhardware', 'updated_old_timestamp'):
    sm.updated['selfdriveState'] = scenario == 'updated_old_timestamp'
    sm.recv_time['selfdriveState'] = {'timeout_boundary': 95, 'reboot': 84, 'reboot_boundary': 85}.get(scenario, 94)
    primary.enabled = scenario != 'reboot_disengaged'
    tici = scenario != 'nonhardware'
  elif scenario == 'secondary':
    secondary.alertSize = Size.small
  elif scenario == 'visible_starpilot':
    secondary.alertSize, secondary.alertStatus = Size.small, Status.starpilot
    state.starpilot_toggles['hide_alerts'] = True
  else:
    primary.alertSize = Size.none if scenario == 'no_size' else Size.small
    primary.alertStatus = (Status.userPrompt if scenario == 'warning' else
                           Status.critical if scenario in ('critical', 'no_size', 'primary_precedence') else Status.normal)
    if scenario == 'primary_precedence':
      secondary.alertSize = Size.small
    if scenario == 'hidden_normal':
      state.starpilot_toggles['hide_alerts'] = True
  rendered = renderer_method(mici, state, sm, tici)
  expected = alert_wake_key(SimpleNamespace(alertSize=rendered.size, alertStatus=rendered.status)) if rendered else None
  actual = standby_alert_wake_key(primary, secondary, now=100,
    started_time=state.started_time, started_frame=state.started_frame,
    updated=sm.updated['selfdriveState'], recv_frame=sm.recv_frame['selfdriveState'], recv_time=sm.recv_time['selfdriveState'],
    primary_fresh=True, secondary_fresh=True, tici=tici, mici=mici, hide_alerts=state.starpilot_toggles.get('hide_alerts', False))
  assert actual == expected


@pytest.mark.parametrize('primary_stale', [False, True])
def test_stale_raw_alert_is_ignored_before_generated_timeout(primary_stale):
  primary, secondary = message(), message()
  alert = primary if primary_stale else secondary
  alert.alertStatus, alert.alertSize = Status.critical, Size.full
  assert standby_alert_wake_key(primary, secondary, now=100, started_time=90, started_frame=5,
    updated=False, recv_frame=6, recv_time=99, primary_fresh=not primary_stale, secondary_fresh=primary_stale,
    tici=True, mici=True) is None
