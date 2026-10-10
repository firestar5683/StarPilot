"""Regression checks for qualified values, saved geometry and request feedback."""
from dataclasses import replace
from types import SimpleNamespace as N
from unittest.mock import Mock

from openpilot.starpilot.ui.onroad_state import ObservationKind, OnroadInput, OnroadState, SlcActionKind, SlcUiRequest, SpeedLimitObservation
from openpilot.starpilot.ui.onroad_customization import default_document, validate_document, rgba
from openpilot.starpilot.ui.large_speed_geometry import source_toggle_bounds, source_panel_bounds
from openpilot.starpilot.ui.slc_action_dispatch import SlcActionDispatcher
from openpilot.starpilot.ui.tests.test_slc_ui_actions import native_state, NOW
from openpilot.starpilot.speed_limits.speed_domain import adjusted_limit, OffsetBand, OffsetSchedule
from openpilot.starpilot.speed_limits.runtime import Runtime
from openpilot.starpilot.speed_limits.runtime_settings import parse
from openpilot.starpilot.ui.tests.test_slc_ui_runtime import START, replay_inputs, publish_request


def road(document=None):
  obs = SpeedLimitObservation(ObservationKind.VALID, 'dashboard', 20, accepted_speed_limit_mps=20,
                             accepted_adjusted_limit_mps=22, session_id='drive-session', presentation_id=9,
                             decision_id=7, action_enabled=True)
  return OnroadState(True, False, 20, 100, obs, longitudinal_active=True, slc_system_long_available=True,
                     customization=document or default_document())


def test_offset_proposals_use_their_own_band_and_reject_invalid_values():
  schedule = OffsetSchedule((OffsetBand(0, 20, 1), OffsetBand(20, None, 3)))
  assert adjusted_limit(19, schedule) == 20
  assert adjusted_limit(20, schedule) == 23
  assert adjusted_limit(float('nan'), schedule) is None
  assert adjusted_limit(10, OffsetSchedule((OffsetBand(0, None, -20),))) is None


def test_numeric_card_is_not_an_accept_target_but_sources_work_while_pending():
  state = road()
  state = replace(state, speed_limit=replace(state.speed_limit, pending_speed_limit_mps=25))
  emitted = []
  touch = OnroadInput(emitted.append)
  touch.press(120, 320, state)
  touch.release(120, 320, state)
  assert not emitted
  x, y, _, _ = source_toggle_bounds(state)
  touch.press(x + 12, y + 12, state)
  touch.release(x + 12, y + 12, state)
  assert emitted[0].kind == 'set_speed_sources'


def test_saved_edge_geometry_keeps_toggle_and_panel_accessible():
  viewport = N(x=30, y=30, width=1800, height=1020)
  for card_x, card_y in ((88, 75), (1350, 528), (88, 528)):
    for action_y in (567, 750, 942):
      doc = default_document()
      doc['layouts']['large']['cruise_limits'].update(x=card_x, y=card_y)
      doc['layouts']['large']['speed_limit_actions'].update(x=card_x, y=action_y)
      state = road(validate_document(doc))
      left, top, right, bottom = source_toggle_bounds(state)
      assert 30 <= left < right <= 1830
      assert 30 <= top < bottom <= 1050
      bounds = source_panel_bounds(state, 200, viewport)
      assert bounds is not None
      x, y, width, height = bounds
      assert 30 <= x and x + width <= 1830
      assert 30 <= y and y + height <= 1050


def test_v4_migration_preserves_settings_and_clamps_only_enlarged_widgets():
  doc = default_document()
  doc['version'] = 4
  doc['palette']['cardFill'] = '#12345678'
  doc['speedSources'] = True
  doc['layouts']['large']['cruise_limits'].update(x=1654, y=75)
  doc['layouts']['large']['speed_limit_actions'].update(x=1654, y=500)
  old_speed = dict(doc['layouts']['large']['current_speed'])
  migrated = validate_document(doc)
  assert migrated['version'] == 6
  assert migrated['layouts']['large']['cruise_limits']['x'] == 1486
  assert migrated['layouts']['large']['speed_limit_actions'] == {'x': 1486, 'y': 567, 'enabled': True}
  assert migrated['layouts']['large']['current_speed'] == old_speed
  assert migrated['speedSources'] is True
  assert rgba(migrated, 'cardFill', 'large', 'cruise_limits') == (18, 52, 86, 120)
  assert validate_document(migrated) == migrated


def test_feedback_requires_matching_receipts_and_command_application():
  now = [NOW]
  dispatcher = SlcActionDispatcher(Mock(), lambda _: native_state(), lambda: now[0])
  assert dispatcher.dispatch(SlcUiRequest(SlcActionKind.ACCEPT, 'drive-session', 7, 9, 22))
  obs = road().speed_limit
  assert dispatcher.feedback(obs) == 'Waiting…'
  obs = replace(obs, action_sequence_id=NOW, action_status='accept')
  assert dispatcher.feedback(obs) == 'Limit accepted'
  obs = replace(obs, command_action_sequence_id=NOW, command_status='issued')
  assert dispatcher.feedback(obs) == 'Applying…'
  assert dispatcher.feedback(replace(obs, command_status='applied')) == 'Applied'
  assert dispatcher.feedback(replace(obs, command_status='expired')) == 'Setpoint not applied'
  assert dispatcher.feedback(replace(obs, session_id='next-drive')) == ''


def test_publisher_receipt_survives_next_cycle_and_resets_with_session():
  sm, cp = replay_inputs()
  runtime = Runtime(parse({'SpeedLimitController': True, 'SLCConfirmation': True, 'SLCConfirmationHigher': True}), session_id='drive')
  pending = runtime.step(sm, cp, now_ns=START).message.slcState
  request = SlcUiRequest(SlcActionKind.ACCEPT, 'drive', pending.decisionId, pending.presentationId, pending.pendingSpeedLimit)
  action = publish_request(pending, request, START)
  sm.advance(START + 50_000_000)
  accepted = runtime.step(sm, cp, now_ns=START + 50_000_000, request=action).message.slcState
  sm.advance(START + 100_000_000)
  next_frame = runtime.step(sm, cp, now_ns=START + 100_000_000).message.slcState
  assert accepted.actionSequenceId == next_frame.actionSequenceId == action.sequence_id
  assert accepted.actionStatus == next_frame.actionStatus == 'accept'
  assert accepted.commandActionSequenceId == next_frame.commandActionSequenceId == action.sequence_id
  runtime.reset()
  assert runtime._ui_receipt is None
  assert runtime._command_ui_sequence == 0


def test_disengaging_during_receipt_keeps_sources_separate_from_feedback():
  state = road()
  state = replace(state, longitudinal_active=False, speed_limit=replace(state.speed_limit, action_feedback='Applied'))
  _, top, _, _ = source_toggle_bounds(state)
  assert top >= 447 + 36 + 8
  assert source_panel_bounds(state, 200, N(x=30, y=30, width=1800, height=1020)) is not None
