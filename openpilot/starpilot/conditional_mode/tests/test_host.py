"""Inactive host proposals against serialized current owner messages."""

from types import SimpleNamespace
import json
import tempfile
import unittest

from openpilot.cereal import messaging
from openpilot.common.params import Params
from openpilot.starpilot.conditional_mode.host import ConditionalModeHost
from openpilot.starpilot.conditional_mode.policy import Authority, ManualIntent, ModeChoice, ModeSettings, Reason, SceneEvidence
from openpilot.starpilot.conditional_mode.preferences import CEMOptions, SavedPreferences, encode_preferences, manual_for_drive, selection_for_drive
from openpilot.starpilot.conditional_mode.projection import ObservedBool
from openpilot.starpilot.conditional_mode.runtime_settings import ConditionalSettingsOwner, DOCUMENT_KEY, SAFE_MODE_KEY
from openpilot.starpilot.conditional_mode.tests.test_projection import BOOT, MONO, FakeSubMaster, serialized_scene


CP = SimpleNamespace(openpilotLongitudinalControl=True, pcmCruise=False, carFingerprint='HYUNDAI_IONIQ_6')
STOCK_ACC = SimpleNamespace(openpilotLongitudinalControl=False, pcmCruise=True, carFingerprint='OTHER')


def set_axes(sm: FakeSubMaster, *, long_active: bool, lat_active: bool, enabled: bool) -> None:
  control = messaging.new_message('carControl', valid=True)
  control.carControl.longActive = long_active
  control.carControl.latActive = lat_active
  sm.payloads['carControl'] = messaging.log_from_bytes(control.to_bytes()).carControl
  state = messaging.new_message('selfdriveState', valid=True)
  state.selfdriveState.enabled = enabled
  sm.payloads['selfdriveState'] = messaging.log_from_bytes(state.to_bytes()).selfdriveState


class TestConditionalHost(unittest.TestCase):
  def setUp(self):
    self.sm = FakeSubMaster(serialized_scene(), MONO - 5_000_000)
    self.host = ConditionalModeHost()

  def sample(self, *, event=MONO + 10_000_000, cp=CP, selection=None, manual=None, safe=None, drive_id=MONO, settings_owner=None, scene=None):
    self.sm.stamp(event)
    if scene is None:
      self.sm.payloads['modelV2'] = serialized_scene(stamp=BOOT + event - MONO)['modelV2']
    else:
      self.sm.payloads.update(scene)
    return self.host.sample(
      self.sm,
      cp,
      now_mono_ns=event + 2_000_000,
      now_boot_ns=BOOT + event - MONO + 2_000_000,
      sample_skew_ns=1000,
      drive_id=drive_id,
      selection=selection,
      manual=manual,
      safe_mode=(safe if safe is not None else ObservedBool(False, event)) if settings_owner is None else None,
      settings_owner=settings_owner,
      selected_t_follow_s=1.45,
      selected_t_follow_observed_mono_ns=event,
    )

  def rearm(self, selection, manual):
    self.sample(event=MONO - 5_000_000, selection=selection, manual=manual)

  def test_default_stock_and_invalid_typed_selection_never_override(self):
    self.assertIsNone(self.sample(selection=None).override_experimental)
    self.assertEqual(self.sample(selection=object()).status, 'invalid_selection')
    self.assertIsNone(selection_for_drive('conditional_experimental', ModeSettings(), MONO))
    self.assertIsNone(selection_for_drive(ModeChoice.CEM, None, MONO))
    self.assertIsNone(manual_for_drive('force_chill', MONO, MONO + 1))
    malformed = selection_for_drive(ModeChoice.CEM, ModeSettings(cem_speed_mps=float('nan')), MONO)
    manual = manual_for_drive(ManualIntent.NONE, MONO, MONO + 1_000_000)
    self.rearm(malformed, manual)
    invalid = self.sample(selection=malformed, manual=manual)
    self.assertIsNone(invalid.override_experimental)
    self.assertEqual(invalid.status, 'invalid_preferences')

  def test_saved_owner_revision_and_serialized_lane_updates_join(self):
    with tempfile.TemporaryDirectory() as directory:
      params = Params(directory)
      saved = SavedPreferences(mode=ModeChoice.CEM,
                               cem=CEMOptions(speed_mps=20.0, signal_speed_mps=20.0, signal_lane_width_m=3.0))
      params.put(DOCUMENT_KEY, json.loads(encode_preferences(saved)), block=True)
      owner = ConditionalSettingsOwner(params)
      manual = manual_for_drive(ManualIntent.NONE, MONO, MONO + 1_000_000)
      self.sample(event=MONO - 5_000_000, settings_owner=owner, manual=manual)
      for index in range(1, 5):
        event = MONO + index * 50_000_000
        scene = serialized_scene(stamp=BOOT + event - MONO, left_blinker=True, left_edge=-2.0)
        result = self.sample(event=event, settings_owner=owner, manual=manual, scene=scene)
        self.assertEqual(result.settings_revision, 1)
        self.assertEqual(result.projected.scene.lane_available, False if index == 4 else None)
      params.put_bool(SAFE_MODE_KEY, True, block=True)
      pending = self.sample(event=MONO + 250_000_000, settings_owner=owner, manual=manual)
      self.assertEqual(pending.settings_revision, 1)
      denied = self.sample(event=MONO + 1_100_000_000, settings_owner=owner, manual=manual)
      self.assertEqual(denied.status, 'safe_mode')
      self.assertEqual(denied.settings_revision, 2)
      self.assertIsNone(denied.override_experimental)

  def test_long_only_can_propose_but_lateral_only_and_stock_acc_cannot(self):
    selection = selection_for_drive(ModeChoice.CEM, ModeSettings(cem_speed_mps=20.0), MONO)
    manual = manual_for_drive(ManualIntent.NONE, MONO, MONO + 1_000_000)
    self.rearm(selection, manual)
    long_only = self.sample(selection=selection, manual=manual)
    self.assertTrue(long_only.override_experimental)
    self.assertEqual(long_only.decision.reason, Reason.CEM_SPEED)
    self.assertFalse(long_only.projected.authority.lat_active)

    set_axes(self.sm, long_active=False, lat_active=True, enabled=False)
    aol = self.sample(event=MONO + 60_000_000, selection=selection, manual=manual)
    self.assertIsNone(aol.override_experimental)
    self.assertEqual(aol.status, 'inactive_axis')
    self.assertTrue(aol.projected.authority.lat_active)

    self.host.reset()
    self.rearm(selection, manual)
    set_axes(self.sm, long_active=True, lat_active=False, enabled=True)
    stock_acc = self.sample(cp=STOCK_ACC, selection=selection, manual=manual)
    self.assertIsNone(stock_acc.override_experimental)
    self.assertEqual(stock_acc.status, 'authority_unavailable')

  def test_manual_latch_survives_scene_loss_but_not_authority_loss(self):
    selection = selection_for_drive(ModeChoice.CEM, ModeSettings(), MONO)
    manual = manual_for_drive(ManualIntent.FORCE_CHILL, MONO, MONO + 1_000_000)
    self.rearm(selection, manual)
    self.sm.seen['modelV2'] = False
    forced = self.sample(selection=selection, manual=manual)
    self.assertFalse(forced.override_experimental)
    self.assertEqual(forced.decision.reason, Reason.MANUAL_CHILL)
    self.assertIsNone(forced.projected.model_horizon_m)
    later = self.sample(event=MONO + 410_000_000, selection=selection, manual=manual)
    self.assertFalse(later.override_experimental)  # Session manual event is a latch, not a 250-ms sensor sample.
    manual_exp = manual_for_drive(ManualIntent.FORCE_EXPERIMENTAL, MONO, MONO + 1_000_000)
    forced_exp = self.sample(event=MONO + 430_000_000, selection=selection, manual=manual_exp)
    self.assertTrue(forced_exp.override_experimental)
    self.assertEqual(forced_exp.decision.reason, Reason.MANUAL_EXPERIMENTAL)
    denied = self.sample(event=MONO + 460_000_000, selection=selection, manual=manual, safe=ObservedBool(False, MONO))
    self.assertIsNone(denied.override_experimental)
    self.assertEqual(denied.status, 'authority_unavailable')

  def test_ccm_unknown_veto_stays_experimental_and_drive_change_rearms(self):
    selection = selection_for_drive(ModeChoice.CCM, ModeSettings(), MONO)
    manual = manual_for_drive(ManualIntent.NONE, MONO, MONO + 1_000_000)
    self.rearm(selection, manual)
    unknown = self.sample(selection=selection, manual=manual)
    self.assertTrue(unknown.override_experimental)
    self.assertEqual(unknown.decision.reason, Reason.SCENE_UNAVAILABLE)
    next_drive = MONO + 1_000_000_000
    changed = self.sample(event=next_drive + 10_000_000, selection=selection, manual=manual, drive_id=next_drive)
    self.assertIsNone(changed.override_experimental)
    self.assertEqual(changed.status, 'invalid_selection')


class TestCEMTransportContinuity(unittest.TestCase):
  def setUp(self):
    self.sm = FakeSubMaster(serialized_scene(lead_present=False), MONO - 5_000_000)
    self.host = ConditionalModeHost()
    self.selection = selection_for_drive(ModeChoice.CEM, ModeSettings(), MONO)
    self.manual = manual_for_drive(ManualIntent.NONE, MONO, MONO + 1_000_000)
    self.sample(MONO - 5_000_000)  # Establish the clock pair and drive barrier.
    self.sample(MONO + 10_000_000)
    # The next frames lack a stop trigger, so only the qualified policy hold
    # can carry the prior detector-confirmed CEM_STOP decision through a gap.
    seed_ns = MONO + 12_000_000
    authority = Authority(True, True, False, True, True, False)
    scene = SceneEvidence(observed_mono_s=seed_ns / 1e9, speed_mps=15.0,
                          standstill=False, stop_light_detected=True)
    decision = self.host.policy.step(seed_ns / 1e9, ModeChoice.CEM, ManualIntent.NONE, authority, scene, ModeSettings())
    self.assertEqual(decision.reason, Reason.CEM_STOP)

  def sample(self, event: int, *, safe=False, boot_shift=0):
    self.sm.stamp(event)
    self.sm.payloads['modelV2'] = serialized_scene(stamp=BOOT + event - MONO, horizon=192.0, lead_present=False)['modelV2']
    return self.host.sample(
      self.sm, CP, now_mono_ns=event + 2_000_000,
      now_boot_ns=BOOT + event - MONO + 2_000_000 + boot_shift, sample_skew_ns=1000,
      drive_id=MONO, selection=self.selection, manual=self.manual,
      safe_mode=ObservedBool(safe, event), selected_t_follow_s=1.45,
      selected_t_follow_observed_mono_ns=event,
    )

  def test_one_missing_control_frame_withholds_override_then_uses_original_hold(self):
    self.sm.seen['carControl'] = False
    unavailable = self.sample(MONO + 60_000_000)
    self.assertEqual(unavailable.status, 'authority_unavailable')
    self.assertIsNone(unavailable.override_experimental)
    self.sm.seen['carControl'] = True
    recovered = self.sample(MONO + 110_000_000)
    self.assertEqual(recovered.status, 'proposed')
    self.assertTrue(recovered.override_experimental)
    self.assertEqual(recovered.decision.reason, Reason.CEM_HOLD)
    self.assertEqual(recovered.decision.status_code, 8)

  def test_long_gap_expires_hold(self):
    self.sm.seen['carControl'] = False
    self.assertIsNone(self.sample(MONO + 60_000_000).override_experimental)
    self.sm.seen['carControl'] = True
    recovered = self.sample(MONO + 320_000_000)
    self.assertEqual(recovered.decision.reason, Reason.NO_TRIGGER)
    self.assertFalse(recovered.override_experimental)

  def test_safe_mode_resets_hold(self):
    denied = self.sample(MONO + 60_000_000, safe=True)
    self.assertEqual(denied.status, 'authority_unavailable')
    recovered = self.sample(MONO + 110_000_000)
    self.assertEqual(recovered.decision.reason, Reason.NO_TRIGGER)

  def test_safe_mode_resets_even_with_missing_required_frame(self):
    self.sm.seen['carControl'] = False
    denied = self.sample(MONO + 60_000_000, safe=True)
    self.assertEqual(denied.status, 'authority_unavailable')
    self.sm.seen['carControl'] = True
    recovered = self.sample(MONO + 110_000_000)
    self.assertEqual(recovered.decision.reason, Reason.NO_TRIGGER)

  def test_malformed_fresh_control_resets_during_other_service_gap(self):
    self.sm.seen['selfdriveState'] = False
    self.sm.payloads['carControl'] = SimpleNamespace(longActive='true', latActive=False)
    denied = self.sample(MONO + 60_000_000)
    self.assertEqual(denied.status, 'authority_unavailable')
    self.sm.seen['selfdriveState'] = True
    self.sm.payloads['carControl'] = serialized_scene(lead_present=False)['carControl']
    recovered = self.sample(MONO + 110_000_000)
    self.assertEqual(recovered.decision.reason, Reason.NO_TRIGGER)

  def test_clock_rearm_resets_hold(self):
    unavailable = self.sample(MONO + 60_000_000, boot_shift=1_000_000_000)
    self.assertEqual(unavailable.status, 'authority_unavailable')
    recovered = self.sample(MONO + 110_000_000, boot_shift=1_000_000_000)
    self.assertEqual(recovered.decision.reason, Reason.NO_TRIGGER)

  def test_fresh_invalid_car_resets_hold(self):
    car = messaging.new_message('carState', valid=True)
    car.carState.canValid = False
    self.sm.payloads['carState'] = messaging.log_from_bytes(car.to_bytes()).carState
    invalid = self.sample(MONO + 60_000_000)
    self.assertEqual(invalid.status, 'authority_unavailable')
    self.sm.payloads['carState'] = serialized_scene(lead_present=False)['carState']
    recovered = self.sample(MONO + 110_000_000)
    self.assertEqual(recovered.decision.reason, Reason.NO_TRIGGER)
