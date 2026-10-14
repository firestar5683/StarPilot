"""Exercise the actual UI owner with separately delivered hardware/Panda state."""

from unittest.mock import MagicMock
from openpilot.cereal.messaging import SubMaster
from types import SimpleNamespace as NS
from unittest.mock import patch

import pytest

from openpilot.cereal import log
from openpilot.selfdrive.ui.ui_state import UIState, UIStatus
from openpilot.starpilot.ui.runtime_snapshot import current_message


def test_replay_messages_use_clock_sample_after_receipt():
  from openpilot.tools.replay.display_clock import ClockSample
  from openpilot.starpilot.ui.runtime_snapshot import display_message
  from openpilot.starpilot.ui.tests.test_runtime_snapshot import NOW, SubMasterFake

  ui = MagicMock(spec=UIState)
  ui.sm = SubMasterFake()
  ui.replay_sample = ClockSample(NOW, None, NOW, epoch=1, valid=True)
  ui._projection_params_at = time_now = 0
  ui.replay_clock = MagicMock()
  ui.replay_clock.sample.side_effect = lambda: ClockSample(time_now, None, time_now, epoch=1, valid=True)

  def receive(_):
    nonlocal time_now
    time_now = NOW + 100_000
    ui.sm.put('carControl', NS(latActive=True), age_ns=-100_000)

  ui.sm.update = receive
  UIState.update(ui)
  assert ui.replay_sample.now_ns is not None
  assert display_message(ui.sm, 'carControl', ui.replay_sample.now_ns).latActive
  assert ui.sm.replay_sample is ui.replay_sample
  ui._reset_replay_state.assert_not_called()


def owner():
  ui = object.__new__(UIState)
  messages = {'deviceState': NS(started=False, chestnutPresent=False),
              'pandaStates': [NS(pandaType=log.PandaState.PandaType.uno, ignitionLine=False, ignitionCan=False)],
              'selfdriveState': NS(enabled=True)}
  ui.sm = MagicMock(spec=SubMaster)
  ui.sm.__getitem__.side_effect = messages.__getitem__
  ui.sm.frame = 10
  ui.sm.updated = {'pandaStates': True, 'wideRoadCameraState': False, 'selfdriveState': False}
  ui.sm.alive = {'pandaStates': True, 'wideRoadCameraState': False}
  ui.sm.valid = {'wideRoadCameraState': False}
  ui.started = ui.ignition = ui._started_prev = ui._engaged_prev = False
  ui.CP = None
  ui.is_body = ui.chestnut_compiled = ui.usb_connected = False
  ui.status = UIStatus.DISENGAGED
  ui.started_frame = 0
  ui.engaged_edges = []
  ui._engaged_transition_callbacks = [lambda: ui.engaged_edges.append((ui.sm.frame, ui.engaged))]
  ui._on_body_changed_callbacks = []
  transitions = []
  ui._offroad_transition_callbacks = [lambda: transitions.append((ui.sm.frame, ui.started))]
  return ui, messages, transitions


def step(ui, messages, hardware, physical):
  messages['deviceState'].started = hardware
  messages['pandaStates'][0].ignitionLine = physical
  with patch('openpilot.selfdrive.ui.ui_state.gui_app.measure_frame_phase', side_effect=lambda _, fn: fn()):
    ui._update_state()
    ui._update_status()
  ui.sm.frame += 1


@pytest.mark.parametrize('raw', [(True, False, True), (False, False, True), (True, True, True)])
def test_raw_ignition_delivery_does_not_reset_hardware_drive(raw):
  ui, messages, transitions = owner()
  for physical in raw:
    step(ui, messages, True, physical)
    assert ui.started and ui.started_frame == 10
    assert ui.ignition == physical
  assert transitions == [(10, True)]
  assert ui.engaged_edges == [(10, True)]
  step(ui, messages, False, True)
  assert not ui.started and ui.ignition
  assert transitions[-1] == (13, False)
  step(ui, messages, False, False)
  assert len(transitions) == 2
  step(ui, messages, True, True)
  assert ui.started_frame == 15
  assert transitions[-1] == (15, True)
  assert ui.engaged_edges == [(10, True), (13, False), (15, True)]


def test_initial_offroad_publication_and_first_hardware_drive():
  ui, messages, transitions = owner()
  ui.sm.frame = 1
  step(ui, messages, False, False)
  step(ui, messages, False, False)
  assert transitions == [(1, False)]
  step(ui, messages, True, False)
  assert transitions[-1] == (3, True)
  assert ui.started_frame == 3 and not ui.ignition


def test_started_presentation_does_not_replace_existing_message_freshness():
  ui, messages, _ = owner()
  step(ui, messages, True, False)
  assert ui.started and not ui.ignition
  ui.sm.seen = {'selfdriveState': True}
  ui.sm.alive = {'selfdriveState': True}
  ui.sm.valid = {'selfdriveState': True}
  ui.sm.recv_frame = {'selfdriveState': 9}
  ui.sm.logMonoTime = {'selfdriveState': 10_000_000_000}
  ui.sm.recv_time = {'selfdriveState': 10.0}
  assert current_message(ui.sm, 'selfdriveState', 10_000_000_000, after_frame=ui.started_frame) is None
  ui.sm.recv_frame['selfdriveState'] = 11
  assert current_message(ui.sm, 'selfdriveState', 10_000_000_000, after_frame=ui.started_frame) is messages['selfdriveState']
  assert current_message(ui.sm, 'selfdriveState', 20_000_000_000, after_frame=ui.started_frame) is None


def replay_owner(sample):
  from openpilot.starpilot.ui.tests.test_runtime_snapshot import SubMasterFake
  ui = object.__new__(UIState)
  ui.sm = SubMasterFake()
  ui.sm.sock = {name: object() for name in ('carControl', 'carState', 'selfdriveState')}
  ui.sm.static_freq_services = set(ui.sm.sock)
  ui.sm.data = ui.sm.messages
  for name in ui.sm.sock:
    ui.sm.put(name, NS(latActive=True, enabled=True), age_ns=0)
  ui._replay_state_epoch = 1
  ui.replay_sample = sample
  ui.replay_clock = MagicMock()
  ui._projection_params_at = 0
  for name in ('_update_state', '_update_status', 'update_params', '_update_chestnut_state'):
    setattr(ui, name, MagicMock())
  return ui


def test_epoch_reset_precedes_paused_primer_and_never_drains_socket():
  from openpilot.tools.replay.display_clock import ClockSample
  from openpilot.starpilot.ui.tests.test_runtime_snapshot import NOW
  from openpilot.starpilot.ui.runtime_snapshot import display_message
  sample = ClockSample(NOW, None, NOW, epoch=2, paused=True, valid=True)
  ui = replay_owner(ClockSample(NOW, None, NOW, epoch=1, valid=True))
  ui.replay_clock.sample.return_value = sample
  def receive(_):
    assert not ui.sm.seen['carControl']
    assert not ui.sm['carControl'].latActive
    ui.sm.frame += 1
    ui.sm.put('carControl', NS(latActive=True), frame=ui.sm.frame)
  ui.sm.update = receive
  with patch('openpilot.selfdrive.ui.ui_state.messaging.drain_sock_raw') as drain:
    ui.update()
  drain.assert_not_called()
  assert display_message(ui.sm, 'carControl', NOW, after_frame=ui.started_frame).latActive
  assert ui.sm.alive['carControl']


def test_straddled_epoch_withholds_frame_but_retains_new_paused_primer():
  from openpilot.tools.replay.display_clock import ClockSample
  from openpilot.starpilot.ui.tests.test_runtime_snapshot import NOW
  from openpilot.starpilot.ui.runtime_snapshot import display_message
  old = ClockSample(NOW + 1_000_000, None, NOW, epoch=1, valid=True)
  new = ClockSample(NOW, None, NOW + 1_000_000, epoch=2, paused=True, valid=True)
  ui = replay_owner(old)
  ui.replay_clock.sample.side_effect = [old, new, new, new]
  def receive(_):
    ui.sm.frame += 1
    ui.sm.updated = dict.fromkeys(ui.sm.sock, False)
    if ui.sm.frame == 4:
      ui.sm.put('carControl', NS(latActive=True), frame=ui.sm.frame)
      ui.sm.put('carState', NS(vEgo=30), age_ns=-1, frame=ui.sm.frame)
  ui.sm.update = receive
  ui.update()
  assert not ui.replay_sample.valid
  assert display_message(ui.sm, 'carControl', NOW) is None
  assert ui.sm.seen['carControl']
  assert not ui.sm.seen['selfdriveState']  # old/unupdated cached service
  assert not ui.sm.seen['carState']  # future stamp from the old timeline
  ui.update()
  assert ui.replay_sample.valid
  assert display_message(ui.sm, 'carControl', NOW).latActive
  assert ui.sm.alive['carControl']  # the paused primer remains logically current


def test_straddle_during_seeking_requests_one_renderer_reprime():
  from openpilot.tools.replay.display_clock import ClockSample
  from openpilot.starpilot.ui.tests.test_runtime_snapshot import NOW
  old = ClockSample(NOW, None, NOW, epoch=1, valid=True)
  seeking = ClockSample(None, None, NOW, epoch=2, paused=True, valid=False)
  ui = replay_owner(old)
  ui.replay_clock.sample.side_effect = [old, seeking]
  ui.sm.update = lambda _: None
  ui.update()
  assert ui.replay_needs_reprime
  assert not any(ui.sm.seen.values())
  assert not ui.replay_sample.valid


def test_missing_clock_heartbeat_does_not_discard_same_epoch_paused_data():
  from openpilot.tools.replay.display_clock import ClockSample
  from openpilot.starpilot.ui.tests.test_runtime_snapshot import NOW
  paused = ClockSample(NOW, None, NOW, epoch=1, paused=True, valid=True)
  missing = ClockSample(None, None, NOW + 1_000_000_000)
  ui = replay_owner(paused)
  ui.replay_clock.sample.side_effect = [missing, missing, paused, paused]
  ui.sm.update = lambda _: None
  ui.update()
  assert not ui.sm.alive['carControl']
  assert ui.sm.seen['carControl']
  ui.update()
  assert ui.sm.alive['carControl']
  assert ui.sm['carControl'].latActive


def test_paused_primer_is_eligible_in_same_started_receive():
  from openpilot.tools.replay.display_clock import ClockSample
  from openpilot.starpilot.ui.tests.test_runtime_snapshot import NOW
  ui, messages, _ = owner()
  ui.replay_clock = MagicMock()
  ui.replay_sample = ClockSample(NOW, None, NOW, epoch=1, paused=True, valid=True)
  messages['deviceState'].started = True
  messages['selfdriveState'].state = log.SelfdriveState.OpenpilotState.enabled
  messages['selfdriveState'].personality = 'standard'
  ui.sm.updated['selfdriveState'] = True
  ui.sm.valid['selfdriveState'] = ui.sm.alive['selfdriveState'] = True
  ui.sm.recv_frame = {'selfdriveState': 10}
  ui.sm.logMonoTime = {'selfdriveState': NOW}
  ui.sm.recv_time = {'selfdriveState': NOW / 1e9}
  ui.sm.replay_sample = ui.replay_sample
  with patch('openpilot.selfdrive.ui.ui_state.gui_app.measure_frame_phase', side_effect=lambda _, fn: fn()):
    ui._update_state()
    ui._update_status()
  assert ui.started_frame == 9
  assert ui.status == UIStatus.ENGAGED
  assert current_message(ui.sm, 'selfdriveState', NOW, after_frame=ui.started_frame).enabled


def test_replay_boot_time_camera_primer_retention_and_freshness():
  from openpilot.tools.replay.display_clock import ClockSample
  from openpilot.starpilot.ui.tests.test_runtime_snapshot import NOW
  from openpilot.starpilot.ui.runtime_snapshot import display_message
  sample = ClockSample(NOW, NOW + 2_000_000_000, NOW, epoch=2, paused=True, valid=True)
  ui = replay_owner(sample)
  ui.sm.sock['cabinCameraState'] = object()
  ui.sm.static_freq_services.add('cabinCameraState')
  ui.sm.put('cabinCameraState', NS(frameId=42))
  ui.sm.logMonoTime['cabinCameraState'] = sample.boot_ns - 1_000_000
  ui.sm.replay_sample = sample
  ui._update_replay_alive(sample)
  assert ui.sm.alive['cabinCameraState']
  ui._reset_replay_state(retain_sample=sample)
  assert ui.sm.seen['cabinCameraState']
  assert display_message(ui.sm, 'cabinCameraState', NOW).frameId == 42
  ui.sm.replay_sample = ClockSample(NOW, None, NOW, epoch=2, paused=True, valid=True)
  assert display_message(ui.sm, 'cabinCameraState', NOW) is None


def test_replay_python_gps_timestamp_uses_mono_domain():
  from openpilot.tools.replay.display_clock import ClockSample
  from openpilot.starpilot.ui.tests.test_runtime_snapshot import NOW
  sample = ClockSample(NOW, NOW + 100_000_000_000, NOW, epoch=1, valid=True)
  ui = replay_owner(sample)
  ui.sm.sock['gpsLocationExternal'] = object()
  ui.sm.static_freq_services.add('gpsLocationExternal')
  ui.sm.put('gpsLocationExternal', NS(latitude=1))
  ui._update_replay_alive(sample)
  assert ui.sm.alive['gpsLocationExternal']
  ui.sm.logMonoTime['gpsLocationExternal'] = NOW + 1_000_000
  ui._update_replay_alive(sample)
  assert not ui.sm.alive['gpsLocationExternal']
