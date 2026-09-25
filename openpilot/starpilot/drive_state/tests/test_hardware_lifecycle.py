"""Portable regression checks of the current hardware transition and power branches."""

import ast
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import Mock, patch

from openpilot.starpilot.drive_state.resolver import Mode
from openpilot.system.hardware.power_monitoring import PowerMonitoring
from openpilot.starpilot.power.offroad_preferences import PowerPolicy

ROOT = Path(__file__).parents[4]


def hardware_body():
  tree = ast.parse((ROOT / 'openpilot/system/hardware/hardwared.py').read_text())
  function = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == 'hardware_thread')
  return next(node for node in function.body if isinstance(node, ast.While)).body


def executable(nodes):
  return compile(ast.fix_missing_locations(ast.Module(body=nodes, type_ignores=[])), 'current-hardware', 'exec')


def test_forced_modes_poll_at_nominal_cadence_without_repeated_edges_and_observe_physical_changes():
  from openpilot.starpilot.drive_state.resolver import effective_onroad

  body = hardware_body()
  start = next(i for i, node in enumerate(body) if isinstance(node, ast.Assign) and ast.unparse(node.targets[0]) == 'physical_ignition')
  end = next(i for i, node in enumerate(body) if isinstance(node, ast.Assign) and ast.unparse(node.targets[0]) == 'ign_edge')
  code = executable(body[start : end + 1])
  for mode, started in ((Mode.ONROAD, True), (Mode.OFFROAD, False)):
    reads = []
    owner = NS(snapshot=lambda mode=mode, reads=reads: reads.append(True) or NS(mode=mode))
    values = {
      'Mode': Mode,
      'drive_mode': mode,
      'drive_state': owner,
      'physical_ignition_prev': None,
      'requested_onroad_prev': None,
      'started_ts': 1 if started else None,
      'DT_HW': 0.5,
      'SERVICE_LIST': {'pandaStates': NS(frequency=10)},
      'effective_onroad': effective_onroad,
    }
    for frame in range(1, 101):
      values.update(sm=NS(frame=frame, updated={'pandaStates': True}), pandaStates=[object()], onroad_conditions={'ignition': False, 'not_onroad_cycle': True})
      exec(code, values)
      assert not values['ign_edge']
    assert len(reads) == 20
    # Raw changes between scheduled polls are processed once, including timeout loss and recovery.
    for frame, ignition, updated, expected in (
      (101, True, True, True),
      (102, True, False, False),
      (103, False, False, True),
      (104, False, False, False),
      (106, True, True, True),
    ):
      values.update(
        sm=NS(frame=frame, updated={'pandaStates': updated}), pandaStates=[object()], onroad_conditions={'ignition': ignition, 'not_onroad_cycle': True}
      )
      exec(code, values)
      assert values['physical_edge'] == expected
      assert values['ign_edge'] == expected


def power_branch():
  body = hardware_body()
  index = next(i for i, node in enumerate(body) if isinstance(node, ast.If) and ast.unparse(node.test) == 'should_start')
  return executable(body[index - 1 : index + 1])


def test_physical_shutdown_episode_survives_force_auto_and_clears_only_real_ignition():
  values = {
    'Mode': Mode,
    'off_ts': 100.0,
    'physical_off_ts': None,
    'forced_power_episode': False,
    'started_ts': None,
    'started_seen': False,
    'startup_blocked_ts': None,
    'startup_conditions': {},
    'startup_conditions_prev': {},
    'cloudlog': Mock(),
  }
  code = power_branch()

  def step(now, mode, ignition, started, edge=False):
    values.update(time=NS(monotonic=lambda: now), drive_mode=mode, onroad_conditions={'ignition': ignition}, should_start=started, physical_edge=edge)
    exec(code, values)

  step(110, Mode.ONROAD, False, True)
  assert values['off_ts'] is None and values['physical_off_ts'] == 100 and values['forced_power_episode']
  step(120, Mode.OFFROAD, False, False)
  step(130, Mode.AUTO, False, False)
  assert values['physical_off_ts'] == 100 and values['forced_power_episode']
  step(130, Mode.ONROAD, False, True)  # Established MONOTONIC clock after suspend; no mode reset.
  assert values['physical_off_ts'] == 100
  step(140, Mode.ONROAD, True, True, True)
  assert values['physical_off_ts'] is None and not values['forced_power_episode']
  step(150, Mode.OFFROAD, True, False)
  step(300, Mode.OFFROAD, True, False)
  assert values['physical_off_ts'] is None and not values['forced_power_episode']
  step(301, Mode.OFFROAD, False, False, True)
  assert values['physical_off_ts'] == 301


def test_real_shutdown_cutoff_and_timeout_remain_effective_with_physical_clock():
  monitor = object.__new__(PowerMonitoring)
  monitor._power_policy = lambda now: PowerPolicy()
  monitor.params = NS(get_bool=lambda key: False)
  monitor.car_battery_capacity_uWh = 100000
  monitor.car_voltage_mV = 11000
  with patch('openpilot.system.hardware.power_monitoring.time.monotonic', return_value=1000):
    assert monitor.should_shutdown(False, True, 100, True)
    assert not monitor.should_shutdown(True, True, 100, True)
    assert not monitor.should_shutdown(False, True, None, True)
    monitor.car_voltage_mV = 13000
    assert monitor.should_shutdown(False, True, -200000, True)


def test_default_auto_clock_and_explicit_startup_gates_remain_stock():
  from openpilot.starpilot.drive_state.resolver import should_start

  assert should_start(Mode.AUTO, {'ignition': True, 'device_temp_good': True}, {'terms': True}, already_started=False)
  assert not should_start(Mode.AUTO, {'ignition': False, 'device_temp_good': True}, {'terms': True}, already_started=False)
  assert not should_start(Mode.AUTO, {'ignition': True, 'device_temp_good': False}, {'terms': True}, already_started=True)
  assert not should_start(Mode.AUTO, {'ignition': True, 'device_temp_good': True}, {'terms': False}, already_started=False)
  assert should_start(Mode.AUTO, {'ignition': True, 'device_temp_good': True}, {'terms': False}, already_started=True)
  clock = Mock(return_value=120)
  values = {
    'Mode': Mode,
    'off_ts': 100,
    'physical_off_ts': None,
    'forced_power_episode': False,
    'started_ts': None,
    'started_seen': False,
    'startup_blocked_ts': None,
    'startup_conditions': {},
    'startup_conditions_prev': {},
    'cloudlog': Mock(),
    'time': NS(monotonic=clock),
    'drive_mode': Mode.AUTO,
    'onroad_conditions': {'ignition': False},
    'should_start': False,
    'physical_edge': False,
  }
  exec(power_branch(), values)
  assert values['off_ts'] == 100 and not values['forced_power_episode']
  clock.assert_not_called()


def test_manager_missing_native_key_registry_fails_closed_without_aborting_normal_startup():
  from openpilot.common.params import UnknownKeyName

  tree = ast.parse((ROOT / 'openpilot/system/manager/manager.py').read_text())
  function = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == 'manager_init')
  boundary = next(
    node
    for node in function.body
    if isinstance(node, ast.Try) and any(isinstance(child, ast.Attribute) and child.attr == 'initialize_manager' for child in ast.walk(node))
  )
  owner = NS(initialize_manager=Mock(side_effect=UnknownKeyName('DriveStateRequest')))
  logger = Mock()
  values = {'drive_state': owner, 'cloudlog': logger, 'UnknownKeyName': UnknownKeyName}
  exec(executable([boundary]), values)
  logger.warning.assert_called_once_with('Force drive state is unavailable')


def test_effective_onroad_disables_power_save_before_started_publication_without_changing_auto():
  body = hardware_body()
  power_index = next(i for i, node in enumerate(body) if isinstance(node, ast.Assign) and ast.unparse(node.targets[0]) == 'should_pwrsave')
  started_index = next(i for i, node in enumerate(body) if isinstance(node, ast.Assign) and ast.unparse(node.targets[0]) == 'msg.deviceState.started')
  send_index = next(i for i, node in enumerate(body) if isinstance(node, ast.Expr) and ast.unparse(node.value) == "pm.send('deviceState', msg)")
  assert power_index + 2 < started_index < send_index
  code = executable(body[power_index:power_index + 3] + [body[started_index], body[send_index]])

  def step(ignition, started, brightness, previous, count=1):
    events = []
    msg = NS(deviceState=NS(screenBrightnessPercent=brightness, started=False))
    values = {
      'onroad_conditions': {'ignition': ignition}, 'should_start': started,
      'started_ts': 1 if started else None, 'msg': msg, 'pwrsave': previous, 'count': count,
      'HARDWARE': NS(set_power_save=lambda enabled: events.append(('power_save', enabled))),
      'pm': NS(send=lambda service, message: events.append((service, message.deviceState.started))),
    }
    exec(code, values)
    return values['pwrsave'], events

  # Asleep forced Onroad must enable CPUs before manager sees started=True.
  assert step(False, True, 0, True) == (False, [('power_save', False), ('deviceState', True)])
  # Holding the same state adds no repeated hardware power transition.
  assert step(False, True, 0, False) == (False, [('deviceState', True)])
  assert step(False, False, 0, False) == (True, [('power_save', True), ('deviceState', False)])
  # Physical ignition retains its authority even when forcing the pipeline off.
  assert step(True, False, 0, True) == (False, [('power_save', False), ('deviceState', False)])
  for ignition, started in ((False, False), (True, False), (True, True)):
    for brightness in (0, 0.0009, 0.001, 50):
      expected = not ignition and brightness < 1e-3
      power_save, events = step(ignition, started, brightness, not expected, count=0)
      assert power_save == expected  # Exact ordinary Auto equation, including blocked startup.
      assert events[0] == ('power_save', expected)


def test_forced_onroad_startup_blocked_uses_nominal_hardware_cadence_and_keeps_edges():
  from openpilot.starpilot.drive_state.resolver import effective_onroad, should_start

  body = hardware_body()
  start = next(i for i, node in enumerate(body) if isinstance(node, ast.Assign) and ast.unparse(node.targets[0]) == 'physical_ignition')
  end = next(i for i, node in enumerate(body) if isinstance(node, ast.Assign) and ast.unparse(node.targets[0]) == 'ign_edge')
  code = executable(body[start:end + 1])
  reads = []
  values = {
    'Mode': Mode, 'drive_mode': Mode.ONROAD,
    'drive_state': NS(snapshot=lambda: reads.append(True) or NS(mode=Mode.ONROAD)),
    'physical_ignition_prev': None, 'requested_onroad_prev': None,
    'started_ts': None, 'DT_HW': 0.5,
    'SERVICE_LIST': {'pandaStates': NS(frequency=10)}, 'effective_onroad': effective_onroad,
  }
  full_frames = []
  for frame in range(1, 101):
    conditions = {'ignition': False, 'not_onroad_cycle': True, 'device_temp_good': True}
    values.update(sm=NS(frame=frame, updated={'pandaStates': True}), pandaStates=[object()], onroad_conditions=conditions)
    exec(code, values)
    if frame % 5 == 0 or values['ign_edge']:
      full_frames.append(frame)
    assert not should_start(Mode.ONROAD, conditions, {'terms': False}, already_started=False)
  assert full_frames == list(range(5, 101, 5))
  assert len(reads) == 20
  # Onroad-cycle/thermal eligibility and physical changes still bypass throttle once.
  for frame, ignition, ready, expected in (
    (101, False, False, True), (102, False, False, False),
    (103, False, True, True), (104, False, True, False),
    (106, True, True, True), (107, True, True, False),
    (108, False, True, True), (109, False, True, False),
  ):
    values.update(sm=NS(frame=frame, updated={'pandaStates': True}), pandaStates=[object()],
                  onroad_conditions={'ignition': ignition, 'not_onroad_cycle': ready, 'device_temp_good': True})
    exec(code, values)
    assert values['ign_edge'] == expected
  assert not should_start(Mode.ONROAD, values['onroad_conditions'], {'terms': False}, already_started=False)
  assert should_start(Mode.ONROAD, values['onroad_conditions'], {'terms': True}, already_started=False)
