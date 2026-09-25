"""Exercise the actual UI owner with separately delivered hardware/Panda state."""

from types import SimpleNamespace as NS
from unittest.mock import patch

import pytest

from openpilot.cereal import log
from openpilot.selfdrive.ui.ui_state import UIState, UIStatus
from openpilot.starpilot.ui.runtime_snapshot import current_message


def owner():
  ui = object.__new__(UIState)
  messages = {'deviceState': NS(started=False, chestnutPresent=False),
              'pandaStates': [NS(pandaType=log.PandaState.PandaType.uno, ignitionLine=False, ignitionCan=False)],
              'selfdriveState': NS(enabled=True)}
  ui.sm = type('SubMaster', (), {'__getitem__': lambda self, key: messages[key]})()
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
