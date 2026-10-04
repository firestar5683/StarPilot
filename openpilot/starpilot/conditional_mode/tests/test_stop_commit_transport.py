from dataclasses import replace
import json
import tempfile
import unittest

from openpilot.cereal import messaging
from openpilot.selfdrive.controls.plannerd import traffic_observation
from openpilot.common.params import Params
from openpilot.starpilot.conditional_mode.consumer import ModeConsumer
from openpilot.starpilot.conditional_mode.host import ConditionalModeHost
from openpilot.starpilot.conditional_mode.policy import ManualIntent, ModeChoice
from openpilot.starpilot.conditional_mode.preferences import SavedPreferences, encode_preferences, manual_for_drive
from openpilot.starpilot.conditional_mode.projection import ConditionalOwnerContext, ObservedBool
from openpilot.starpilot.conditional_mode.runtime_settings import ConditionalSettingsOwner, DOCUMENT_KEY
from openpilot.starpilot.conditional_mode.status import StatusPublisher, settings_fingerprint
from openpilot.starpilot.conditional_mode.tests.test_projection import BOOT, CP, MONO, FakeSubMaster, serialized_scene


class TestStopCommitTransport(unittest.TestCase):
  def setUp(self):
    directory = self.enterContext(tempfile.TemporaryDirectory())
    self.params = Params(directory)
    self.save(ModeChoice.CEM)
    self.owner = ConditionalSettingsOwner(self.params)
    self.host = ConditionalModeHost()
    self.publisher = StatusPublisher()
    self.consumer = ModeConsumer()
    self.drive = MONO - 1_000_000_000
    self.tick = 0

  def save(self, choice):
    self.params.put(DOCUMENT_KEY, json.loads(encode_preferences(SavedPreferences(mode=choice))), block=True)

  def sample(self, *, invalid=False, lead=False, horizon=20., manual=ManualIntent.NONE, alive=True, gas=False,
             unavailable=None, traffic_verdict=None, traffic_owner_present=None, cp=CP):
    now = MONO + self.tick * 50_000_000
    self.tick += 1
    payloads = serialized_scene(stamp=BOOT+now-MONO-2_000_000, horizon=horizon, speed=4.27,
                                lead_present=lead, lead_distance=50., lead_speed=4.27, gas_pressed=gas)
    event = messaging.new_message('modelV2', valid=True)
    event.modelV2 = payloads['modelV2']
    event.modelV2.orientationRate.z = [0.] * 33
    if invalid:
      values = list(event.modelV2.position.x)
      values[-2] = values[-1] + .015308380126953125
      event.modelV2.position.x = values
      event.modelV2.velocity.x = [4.27] * 32 + [-.0027507354971021414]
    payloads['modelV2'] = messaging.log_from_bytes(event.to_bytes()).modelV2
    controls = messaging.new_message('controlsState', valid=True)
    controls.controlsState = payloads['controlsState']
    controls.controlsState.curvature = 0.
    payloads['controlsState'] = messaging.log_from_bytes(controls.to_bytes()).controlsState
    sm = FakeSubMaster(payloads, now-2_000_000)
    sm.alive['modelV2'] = alive
    if unavailable is not None:
      sm.alive[unavailable] = False
    context = ConditionalOwnerContext(**{field: ObservedBool(False, now-2_000_000) for field in
      ('traffic_mode', 'stop_sign_confirmed', 'forcing_stop', 'dashboard_stop_sign', 'slc_experimental',
       'previous_experimental', 'red_light', 'plan_forcing_stop', 'plan_should_stop')},
      pedal_override=ObservedBool(gas, now-2_000_000), plan_allow_throttle=ObservedBool(True, now-2_000_000))
    if traffic_owner_present is not None:
      context = replace(context, traffic_mode=traffic_observation(traffic_verdict,
                        model_ns=now-2_000_000, owner_present=traffic_owner_present))
    proposal = self.host.sample(sm, cp, now_mono_ns=now, now_boot_ns=BOOT+now-MONO,
      sample_skew_ns=1000, drive_id=self.drive, settings_owner=self.owner,
      manual=manual_for_drive(manual, self.drive, self.drive+1), owner_context=context,
      selected_t_follow_s=.5, selected_t_follow_observed_mono_ns=now-2_000_000)
    event = self.publisher.attach(None, proposal, self.owner.current, now_ns=now, drive_id=self.drive,
                                  model_ns=now-2_000_000, car_state_ns=now-2_000_000)
    state = messaging.log_from_bytes(event.to_bytes()).slcState
    result = self.consumer.sample(state, now_ns=now, now_boot_ns=BOOT+now-MONO, sample_skew_ns=1000,
      message_ns=now, receipt_ns=now, drive_id=self.drive, model_ns=now-2_000_000,
      car_state_ns=now-2_000_000, authority=alive, stock_experimental=False,
      choice=proposal.choice, settings_fingerprint=settings_fingerprint(self.owner.current))
    return proposal, result

  def prime(self):
    for _ in range(40):
      proposal, result = self.sample()
    self.assertTrue(self.host.projector.stop_detector.committed)
    self.assertTrue(result.accepted and result.experimental)

  def test_fresh_invalid_geometry_and_unknown_lead_tracking_preserve_actual_transport(self):
    self.prime()
    for _ in range(30):
      proposal, result = self.sample(invalid=True, lead=True, horizon=6.683574199676514)
      self.assertTrue(proposal.projected.scene.committed_stop)
      self.assertTrue(result.accepted and result.experimental)

  def test_mode_change_manual_chill_stock_then_valid_clear(self):
    self.prime()
    for choice in (ModeChoice.CCM, ModeChoice.STOCK):
      self.save(choice)
      for _ in range(25):
        proposal, result = self.sample(manual=ManualIntent.FORCE_CHILL)
        self.assertTrue(result.accepted and result.experimental)
      self.assertEqual(proposal.choice, choice)
    for _ in range(30):
      proposal, result = self.sample(horizon=192.)
    self.assertFalse(result.experimental)
    self.assertFalse(self.host.projector.stop_detector.committed)

  def test_cold_stock_and_lost_authority_or_driver_override_cannot_hold_commit(self):
    self.save(ModeChoice.STOCK)
    for _ in range(30):
      _, result = self.sample()
      self.assertFalse(result.experimental)
    self.assertFalse(self.host.projector.stop_detector.committed)
    self.save(ModeChoice.CEM)
    self.prime()
    _, result = self.sample(alive=False)
    self.assertFalse(result.experimental)
    self.assertFalse(self.host.projector.stop_detector.committed)
    self.prime()
    _, result = self.sample(gas=True)
    self.assertFalse(self.host.projector.stop_detector.committed)

  def test_dead_control_or_selfdrive_authority_cannot_revive_previous_commit(self):
    for service in ('carControl', 'selfdriveState'):
      self.prime()
      _, result = self.sample(unavailable=service)
      self.assertFalse(result.experimental)
      self.assertFalse(self.host.projector.stop_detector.committed)
      _, result = self.sample(invalid=True)
      self.assertFalse(result.experimental)
      self.assertFalse(self.host.projector.stop_detector.committed)

  def test_current_traffic_owner_decision_survives_raw_packet_silence(self):
    from openpilot.starpilot.conditional_mode.tests.test_traffic import TrafficOwnerTests, DRIVE
    physical = TrafficOwnerTests('test_unassigned_preserves_ordinary_profile_without_media')
    physical.setUp()
    self.addCleanup(physical.doCleanups)
    physical.params, physical.settings = self.params, self.owner
    physical.params.put('ModeButtonControl', 6, block=True)
    self.drive = DRIVE
    for _ in range(40):
      now = MONO + self.tick * 50_000_000
      verdict = physical.sample(now)
      self.assertFalse(verdict.requested)
      proposal, result = self.sample(traffic_verdict=verdict, traffic_owner_present=True)
    self.assertTrue(self.host.projector.stop_detector.committed)
    self.assertTrue(result.accepted and result.experimental)
    now = MONO + self.tick * 50_000_000
    on = physical.sample(now, physical.event(1, now, toggle=True))
    self.assertTrue(on.effective)
    for _ in range(30):
      now = MONO + self.tick * 50_000_000
      held = physical.sample(now)
      self.assertEqual(held.source_mono_ns, on.source_mono_ns)
      proposal, result = self.sample(traffic_verdict=held, traffic_owner_present=True)
      self.assertTrue(self.host.projector.stop_detector.committed)
      self.assertTrue(result.accepted and result.experimental)
    self.assertEqual(held.source_boot_ns, 0)
    _, result = self.sample(traffic_verdict=held, traffic_owner_present=True, unavailable='carControl')
    self.assertFalse(result.experimental)
    self.assertFalse(self.host.projector.stop_detector.committed)

  def test_optional_absent_traffic_owner_does_not_prevent_cold_cem_stop(self):
    for _ in range(40):
      _, result = self.sample(traffic_owner_present=False)
    self.assertTrue(self.host.projector.stop_detector.committed)
    self.assertTrue(result.accepted and result.experimental)
    self.sample(traffic_owner_present=False, alive=False)
    self.assertFalse(self.host.projector.stop_detector.committed)

  def test_unsupported_optional_traffic_owner_does_not_block_actual_other_factory_cem(self):
    from opendbc.car.honda.interface import CarInterface
    from opendbc.car.honda.values import CAR
    from openpilot.starpilot.conditional_mode.tests.test_traffic import TrafficOwnerTests, DRIVE
    physical = TrafficOwnerTests('test_unassigned_preserves_ordinary_profile_without_media')
    physical.setUp()
    self.addCleanup(physical.doCleanups)
    cp = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
    self.assertTrue(cp.openpilotLongitudinalControl)
    physical.cp = cp
    self.drive = DRIVE
    for _ in range(40):
      now = MONO + self.tick * 50_000_000
      verdict = physical.sample(now)
      self.assertEqual(verdict.reason, 'unsupported_car')
      _, result = self.sample(traffic_verdict=verdict, traffic_owner_present=True, cp=cp)
    self.assertTrue(self.host.projector.stop_detector.committed)
    self.assertTrue(result.accepted and result.experimental)
    self.sample(traffic_verdict=verdict, traffic_owner_present=True, cp=cp, unavailable='carControl')
    self.assertFalse(self.host.projector.stop_detector.committed)
