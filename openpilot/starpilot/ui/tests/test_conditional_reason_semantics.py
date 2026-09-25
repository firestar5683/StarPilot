"""Wire receipt regression: scene readiness must not become generic unavailability."""
from types import SimpleNamespace

import unittest

from openpilot.cereal import log, messaging
from openpilot.starpilot.conditional_mode.host import HostProposal
from openpilot.starpilot.conditional_mode.policy import Authority, Decision, ModeChoice, Reason
from openpilot.starpilot.conditional_mode.runtime_settings import SettingsSnapshot, DocumentState, SafeModeState
from openpilot.starpilot.conditional_mode.status import StatusPublisher
from openpilot.starpilot.ui.conditional_status import ConditionalPerceptionProjector
from openpilot.starpilot.ui.onroad_conditional import status, stop_active
from openpilot.starpilot.ui.onroad_state import AlertSize


def check_fresh_validated_receipt_preserves_unavailable_reason(choice, policy_reason, detail):
  now = 100_000_000_000
  drive_id = now - 1_000_000_000
  authority = Authority(True, True, False, False, False, True)
  decision = Decision(True, False, True, True, policy_reason, 0)
  settings = SettingsSnapshot('test', 1, now, now, DocumentState.ABSENT, SafeModeState.ABSENT_FALSE, None, None, None)
  # Controlled wire reasons isolate presentation; this is not policy/control admission.
  proposal = HostProposal(choice, SimpleNamespace(authority=authority), decision, None, 'inactive_axis', settings.revision)
  event = messaging.new_message('slcState')
  event.valid = True
  event.logMonoTime = now
  StatusPublisher().attach(event, proposal, settings, now_ns=now, drive_id=drive_id,
                           model_ns=now, car_state_ns=now)
  args = dict(now_ns=now + 20_000_000, event_ns=now, drive_id=drive_id, choice=choice,
              lateral_active=True, selfdrive_enabled=False, car_valid=True, system_long=True)
  with log.Event.from_bytes(event.to_bytes()) as received:
    projector = ConditionalPerceptionProjector()
    value = projector.project(received.slcState, **args)
    assert value is not None and value.reason == policy_reason.value
    assert not value.effective_experimental
    assert not received.slcState.conditionalMode.hasOverride
    ui = SimpleNamespace(visual_preview=None, conditional_effective=None, conditional_perception=value,
                         longitudinal_active=False, longitudinal_overridden=False, alert=SimpleNamespace(size=AlertSize.NONE))
    assert status(ui)[:2] == (choice.name, detail)
    assert not stop_active(ui)
    for changed in ({'now_ns': now + 200_000_001}, {'drive_id': drive_id + 1}, {'car_valid': False},
                    {'system_long': False}, {'lateral_active': False}, {'choice': ModeChoice.STOCK}):
      rejected = ConditionalPerceptionProjector().project(received.slcState, **(args | changed))
      assert rejected is None
      ui.conditional_perception = rejected
      assert status(ui) is None and not stop_active(ui)


class TestConditionalReasonSemantics(unittest.TestCase):
  def test_cem_scene_waits_for_road_data(self):
    check_fresh_validated_receipt_preserves_unavailable_reason(ModeChoice.CEM, Reason.SCENE_UNAVAILABLE, 'WAITING FOR ROAD DATA')

  def test_cem_unavailable_remains_visible(self):
    check_fresh_validated_receipt_preserves_unavailable_reason(ModeChoice.CEM, Reason.UNAVAILABLE, 'UNAVAILABLE')

  def test_ccm_scene_waits_for_road_data(self):
    check_fresh_validated_receipt_preserves_unavailable_reason(ModeChoice.CCM, Reason.SCENE_UNAVAILABLE, 'WAITING FOR ROAD DATA')

  def test_ccm_unavailable_remains_visible(self):
    check_fresh_validated_receipt_preserves_unavailable_reason(ModeChoice.CCM, Reason.UNAVAILABLE, 'UNAVAILABLE')


if __name__ == '__main__':
  unittest.main()
