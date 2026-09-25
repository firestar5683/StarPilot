from dataclasses import replace
from types import SimpleNamespace

import pytest

from openpilot.cereal import log, messaging

from openpilot.starpilot.conditional_mode.host import HostProposal
from openpilot.starpilot.conditional_mode.policy import Authority, Decision, ModeChoice, Reason
from openpilot.starpilot.conditional_mode.status import StatusPublisher
from openpilot.starpilot.conditional_mode.runtime_settings import SettingsSnapshot, DocumentState, SafeModeState
from openpilot.starpilot.ui.conditional_status import ConditionalPerceptionProjector
from openpilot.starpilot.ui.onroad_conditional import reason, stop_active
from openpilot.starpilot.ui.onroad_state import AlertSize


def test_aol_perception_is_not_longitudinal_authority():
  now = 100_000_000_000
  authority = Authority(True, True, False, False, False, True)
  decision = Decision(True, False, True, True, Reason.CEM_STOP, 8)
  settings = SettingsSnapshot("test", 1, now, now, DocumentState.ABSENT, SafeModeState.ABSENT_FALSE, None, None, None)
  proposal = HostProposal(ModeChoice.CEM, SimpleNamespace(authority=authority), decision, None,
                          'inactive_axis', settings.revision)
  publisher = StatusPublisher()
  event = publisher.attach(None, proposal, settings, now_ns=now, drive_id=now - 1_000_000_000,
                           model_ns=now, car_state_ns=now)
  assert not event.slcState.conditionalMode.hasOverride
  projector = ConditionalPerceptionProjector()
  args = {'now_ns': now + 20_000_000, 'event_ns': now, 'drive_id': now - 1_000_000_000, 'choice': ModeChoice.CEM,
          'lateral_active': True, 'selfdrive_enabled': False, 'car_valid': True, 'system_long': True}
  value = projector.project(event.slcState, **args)
  assert value is not None and value.reason == 'cem_stop' and not value.effective_experimental
  state = SimpleNamespace(visual_preview=None, conditional_effective=None, conditional_perception=value,
                          longitudinal_active=False, longitudinal_overridden=False,
                          alert=SimpleNamespace(size=AlertSize.NONE))
  assert reason(state) == 'cem_stop'
  assert not stop_active(state)
  for changed in ({'now_ns': now + 200_000_001}, {'drive_id': now + 1}, {'car_valid': False},
                  {'lateral_active': False}, {'choice': ModeChoice.STOCK}):
    assert projector.project(event.slcState, **(args | changed)) is None
  state.conditional_effective = replace(value, effective_experimental=True)
  assert not stop_active(state)
  state.longitudinal_active = True
  assert stop_active(state)


@pytest.mark.parametrize('sample_delay_ns', [1_315_523, 10_509_607])
def test_independently_stamped_scene_survives_transport_without_control_authority(sample_delay_ns):
  envelope_ns = 100_000_000_000
  scene_ns = envelope_ns + sample_delay_ns
  drive_id = envelope_ns - 1_000_000_000
  settings = SettingsSnapshot("test", 1, scene_ns, scene_ns, DocumentState.ABSENT, SafeModeState.ABSENT_FALSE, None, None, None)
  decision = Decision(True, False, True, True, Reason.CEM_STOP, 8)
  authority = Authority(True, True, False, False, False, True)
  proposal = HostProposal(ModeChoice.CEM, SimpleNamespace(authority=authority), decision, None,
                          'inactive_axis', settings.revision)
  event = messaging.new_message('slcState')
  event.valid = True
  event.logMonoTime = envelope_ns
  publisher = StatusPublisher()
  publisher.attach(event, proposal, settings, now_ns=scene_ns, drive_id=drive_id,
                   model_ns=envelope_ns, car_state_ns=envelope_ns)
  with log.Event.from_bytes(event.to_bytes()) as received:
    assert received.logMonoTime == envelope_ns
    assert received.slcState.conditionalMode.observedMonoTime == scene_ns
    projector = ConditionalPerceptionProjector()
    args = {'now_ns': scene_ns + 20_000_000, 'event_ns': int(received.logMonoTime), 'drive_id': drive_id,
            'choice': ModeChoice.CEM, 'lateral_active': True, 'selfdrive_enabled': False, 'car_valid': True, 'system_long': True}
    value = projector.project(received.slcState, **args)
    assert value is not None and value.reason == 'cem_stop'
    assert not value.effective_experimental
    assert not received.slcState.conditionalMode.hasOverride
    ui = SimpleNamespace(visual_preview=None, conditional_effective=None, conditional_perception=value,
                         longitudinal_active=False, longitudinal_overridden=False, alert=SimpleNamespace(size=AlertSize.NONE))
    assert reason(ui) == 'cem_stop' and not stop_active(ui)
    # The display may outlast the control proposal, but neither timestamp is unbounded.
    assert projector.project(received.slcState, **(args | {'now_ns': envelope_ns + 200_000_000})) is not None
    assert projector.project(received.slcState, **(args | {'now_ns': scene_ns - 1})) is None
    assert projector.project(received.slcState, **(args | {'now_ns': envelope_ns + 200_000_001})) is None
    assert projector.project(received.slcState, **(args | {'event_ns': scene_ns + 20_000_001})) is None
    assert projector.project(received.slcState, **(args | {'drive_id': drive_id + 1})) is None

  # A fresh envelope must not revive a stale or malformed nested scene.
  for altered in ({'observedMonoTime': envelope_ns - 200_000_001},
                  {'modelMonoTime': scene_ns + 1}, {'carStateMonoTime': drive_id - 1},
                  {'validUntilMonoTime': scene_ns + 100_000_001}):
    changed = event.as_reader().as_builder()
    for key, value in altered.items():
      setattr(changed.slcState.conditionalMode, key, value)
    assert ConditionalPerceptionProjector().project(changed.slcState, **args) is None

  first = event.as_reader().as_builder()
  publisher.attach(event, proposal, settings, now_ns=scene_ns + 10_000_000, drive_id=drive_id,
                   model_ns=scene_ns, car_state_ns=scene_ns)
  projector = ConditionalPerceptionProjector()
  assert projector.project(event.slcState, **args) is not None
  assert projector.project(first.slcState, **args) is None
