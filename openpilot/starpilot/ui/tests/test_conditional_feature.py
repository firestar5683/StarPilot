"""Disposable Params and real shared-owner conditional editor requests."""

from pathlib import Path
from dataclasses import replace
from types import SimpleNamespace
import subprocess
import sys
import os
import tempfile
import unittest
from unittest.mock import Mock, patch

from openpilot.common.params import Params
from opendbc.car.car_helpers import interfaces
from opendbc.car.hyundai.values import CAR, HyundaiFlags
from openpilot.starpilot.conditional_mode.button_actions import BUTTON_PREFIX, MEDIA_KEYS
from openpilot.starpilot.conditional_mode.preferences import MPH_TO_MPS, SavedPreferences, decode_preferences, encode_preferences
from openpilot.starpilot.conditional_mode.actions import commit, commit_manual, stock_document
from openpilot.starpilot.conditional_mode.policy import ModeChoice
from openpilot.starpilot.conditional_mode.manual_saved import SavedCodes, decode as decode_manual, encode as encode_manual
from openpilot.starpilot.ui.feature_settings_owner import FeatureSettingsOwner
from openpilot.starpilot.ui.feature_settings_state import FeatureInput, FeaturePage, FeatureRow, FeatureSettingsRequest, row_change
from openpilot.starpilot.ui import feature_settings_compact as compact
from openpilot.starpilot.ui import feature_settings as large
from openpilot.starpilot.ui.presentation import BitmapFonts, Profile


def required_change(row: FeatureRow, direction: int = 1) -> FeatureSettingsRequest:
  request = row_change(row, direction)
  assert request is not None
  return request


class ConditionalFeatureTests(unittest.TestCase):
  def setUp(self):
    temporary = tempfile.TemporaryDirectory()
    self.addCleanup(temporary.cleanup)
    self.params = Params(temporary.name)
    self.parked = True
    self.cp = SimpleNamespace(carFingerprint="HONDA TEST", carVin="VIN1", openpilotLongitudinalControl=True,
                              pcmCruise=True, notCar=False, dashcamOnly=False, passive=False)
    self.owner = FeatureSettingsOwner(self.params, lambda group: self.parked and group in
                                      ("conditional", "conditional_wheel", "preferences", "parked_preferences"),
                                      vehicle_fingerprint=lambda: getattr(self.cp, "carFingerprint", None),
                                      vehicle_params=lambda: self.cp)

  def test_saved_mode_and_conditions_can_change_during_drive_with_exact_source(self):
    self.parked = False
    self.owner.authority = lambda group: group == "preferences"
    mode = self.row("conditional:mode")
    self.assertTrue(mode.available)
    self.assertTrue(self.owner.apply(required_change(mode)))
    threshold = self.row("conditional:cem:speed_mps", FeaturePage.CONDITIONAL_CEM)
    self.assertTrue(threshold.available)
    request = required_change(threshold)
    self.params.put_bool("IsMetric", True, block=True)
    self.assertFalse(self.owner.apply(request))

  def test_repair_and_manual_choice_reset_stay_parked(self):
    self.parked = False
    self.owner.authority = lambda group: group == "preferences"
    persist = self.row("conditional:cem:persist_manual", FeaturePage.CONDITIONAL_CEM)
    self.assertFalse(persist.available)
    self.assertFalse(self.owner.apply(FeatureSettingsRequest(persist.key, persist.source, "On",
                                                             dependencies=persist.dependencies)))
    invalid = b'{"version":2}'
    Path(self.params.get_param_path("ConditionalModeConfig")).write_bytes(invalid)
    reset = self.row("conditional:reset")
    self.assertFalse(reset.available)
    self.assertFalse(self.owner.apply(FeatureSettingsRequest(reset.key, reset.source, "confirm", confirmation=True,
                                                             dependencies=reset.dependencies)))
    self.assertEqual(Path(self.params.get_param_path("ConditionalModeConfig")).read_bytes(), invalid)

  def test_supported_wheel_assignment_can_change_during_drive_but_rechecks_sources(self):
    cp = interfaces[CAR.HYUNDAI_IONIQ_6].get_non_essential_params(CAR.HYUNDAI_IONIQ_6)
    cp.flags = int(cp.flags | HyundaiFlags.CANFD_LKA_STEER_MSG)
    cp.openpilotLongitudinalControl = True
    self.cp = cp
    self.parked = False
    self.owner.authority = lambda group: group == "conditional_wheel"
    row = self.row(BUTTON_PREFIX + MEDIA_KEYS[0])
    self.assertTrue(row.available)
    request = required_change(row)
    self.assertTrue(self.owner.apply(request))
    self.assertFalse(self.owner.apply(request))
    other = required_change(self.row(BUTTON_PREFIX + MEDIA_KEYS[1]))
    cp.flags = int(cp.flags & ~HyundaiFlags.CANFD_LKA_STEER_MSG)
    self.assertFalse(self.owner.apply(other))

  def rows(self, page=FeaturePage.CONDITIONAL):
    return self.owner.snapshot(page, parked=self.parked, system_long=False,
                               lateral_context=False, metric=False).rows

  def row(self, key, page=FeaturePage.CONDITIONAL):
    return next(row for row in self.rows(FeaturePage.WHEEL if key.startswith(BUTTON_PREFIX) else page) if row.key == key)

  def test_factory_cem_and_honda_pcm_cruise_does_not_veto(self):
    self.assertIsNone(self.params.get("ConditionalModeConfig"))
    self.assertIn(FeaturePage.CONDITIONAL, [row.page for row in self.rows(FeaturePage.HUB)])
    mode = self.row("conditional:mode")
    self.assertEqual(mode.value, "Conditional Experimental")
    self.assertTrue(mode.available)
    self.assertTrue(self.owner.apply(required_change(mode)))
    saved = decode_preferences(Path(self.params.get_param_path("ConditionalModeConfig")).read_bytes())
    self.assertEqual(saved.mode.value, "conditional_chill")
    self.assertFalse(saved.cem.persist_manual)

  def test_chill_label_and_signal_rows_preserve_existing_consumers(self):
    path = Path(self.params.get_param_path("ConditionalModeConfig"))
    path.write_bytes(stock_document())
    original = path.read_bytes()
    mode = self.row("conditional:mode")
    self.assertEqual(mode.value, "Chill")
    self.assertNotIn("Stock", mode.choices)
    self.assertEqual(path.read_bytes(), original)
    self.assertFalse(any(row.key.endswith((":signal_lane_detection", ":signal_lane_width_m"))
                         for row in self.rows(FeaturePage.CONDITIONAL_CEM)))
    row = self.row("conditional:cem:signal_lane_detection", FeaturePage.LANE_CHANGE)
    self.assertIn("Conditional Experimental", row.reason)
    self.assertTrue(self.owner.apply(required_change(row)))
    saved = decode_preferences(path.read_bytes())
    self.assertEqual(saved.mode, ModeChoice.STOCK)
    self.assertNotEqual(saved.cem.signal_lane_detection, decode_preferences(original).cem.signal_lane_detection)
    mode = self.row("conditional:mode")
    self.assertTrue(self.owner.apply(FeatureSettingsRequest(mode.key, mode.source, "Chill", dependencies=mode.dependencies)))
    self.assertEqual(decode_preferences(path.read_bytes()).mode, ModeChoice.STOCK)

  def test_core_configuration_without_car_params_keeps_media_vehicle_bound(self):
    self.cp = None
    mode = self.row("conditional:mode")
    self.assertTrue(mode.available)
    self.assertIsNone(mode.vehicle_fingerprint)
    self.assertTrue(self.owner.apply(required_change(mode)))
    self.assertFalse(any(row.key.startswith(BUTTON_PREFIX) for row in self.rows(FeaturePage.WHEEL)))
    self.cp = SimpleNamespace(carFingerprint="UNSUPPORTED", openpilotLongitudinalControl=False,
                              pcmCruise=True, notCar=False, dashcamOnly=False, passive=False)
    threshold = self.row("conditional:cem:speed_mps", FeaturePage.CONDITIONAL_CEM)
    self.assertTrue(threshold.available)
    self.assertTrue(self.owner.apply(required_change(threshold)))
    pending = required_change(self.row("conditional:ccm:launch_assist", FeaturePage.CONDITIONAL_CCM))
    self.parked = False
    self.assertFalse(self.owner.apply(pending))

  def test_six_ioniq_media_rows_and_exact_source_guards(self):
    cp = interfaces[CAR.HYUNDAI_IONIQ_6].get_non_essential_params(CAR.HYUNDAI_IONIQ_6)
    cp.flags = int(cp.flags | HyundaiFlags.CANFD_LKA_STEER_MSG)
    cp.openpilotLongitudinalControl = True
    self.cp = cp
    rows = [row for row in self.rows(FeaturePage.WHEEL) if row.key.startswith(BUTTON_PREFIX)]
    self.assertEqual([row.key for row in rows], [BUTTON_PREFIX + key for key in MEDIA_KEYS])
    self.assertTrue(all(row.available and row.value == "Off" for row in rows))
    self.assertFalse(any(row.key.startswith(BUTTON_PREFIX) for row in self.rows()))
    self.assertFalse(any(row.label == "Button assignments" for row in self.rows(FeaturePage.WHEEL)))
    self.assertFalse(any(row.label == "Remembered manual choices" for row in self.rows()))
    first = rows[0]
    request = required_change(first)
    self.assertIsNotNone(request)
    self.parked = False
    self.assertFalse(self.owner.apply(request))
    self.parked = True
    Path(self.params.get_param_path("LongStarButtonControl")).write_bytes(b"5")
    self.assertFalse(self.owner.apply(request))
    self.assertFalse(Path(self.params.get_param_path(MEDIA_KEYS[0])).exists())
    self.assertTrue(self.owner.apply(required_change(self.row(first.key))))
    self.assertEqual(Path(self.params.get_param_path(MEDIA_KEYS[0])).read_bytes(), b"5")
    Path(self.params.get_param_path("CancelButtonControl")).write_bytes(b"5")
    self.assertEqual(next(row for row in self.rows(FeaturePage.WHEEL) if row.label == "Button assignments").value,
                     "Review saved actions")
    cp.flags = int(cp.flags & ~HyundaiFlags.CANFD_LKA_STEER_MSG)
    self.assertFalse(any(row.key.startswith(BUTTON_PREFIX) for row in self.rows(FeaturePage.WHEEL)))

  def test_captured_wheel_request_stays_vehicle_bound_with_generic_preferences(self):
    cp = interfaces[CAR.HYUNDAI_IONIQ_6].get_non_essential_params(CAR.HYUNDAI_IONIQ_6)
    cp.flags = int(cp.flags | HyundaiFlags.CANFD_LKA_STEER_MSG)
    cp.openpilotLongitudinalControl = True
    self.cp = cp
    request = required_change(self.row(BUTTON_PREFIX + MEDIA_KEYS[0]))
    destination = Path(self.params.get_param_path(MEDIA_KEYS[0]))
    for replacement in (None, SimpleNamespace(carFingerprint="UNSUPPORTED", openpilotLongitudinalControl=False,
                                              notCar=False, passive=False, dashcamOnly=False)):
      self.cp = replacement
      self.assertTrue(self.parked)
      self.assertFalse(self.owner.apply(request))
      self.assertFalse(destination.exists())

  def test_native_authority_uses_system_long_without_pcm_cruise_veto(self):
    from openpilot.starpilot.ui import runtime_app
    shell = runtime_app.StarShellSession.__new__(runtime_app.StarShellSession)
    shell._mode = runtime_app.ShellMode.SETTINGS
    with patch.object(shell, "confirmed_offroad", return_value=True), \
         patch.object(runtime_app.ui_state, "CP", self.cp):
      self.assertTrue(shell._feature_authority("conditional"))
      self.assertFalse(shell._feature_authority("long"))
      self.cp.openpilotLongitudinalControl = False
      self.assertFalse(shell._feature_authority("conditional"))
      self.assertTrue(shell._feature_authority("preferences"))

  def test_native_saved_actions_use_settings_mode_and_supported_current_car(self):
    from openpilot.starpilot.ui import runtime_app
    shell = runtime_app.StarShellSession.__new__(runtime_app.StarShellSession)
    shell._mode = runtime_app.ShellMode.SETTINGS
    with patch.object(shell, "confirmed_offroad", return_value=False), \
         patch.object(runtime_app.ui_state, "CP", self.cp):
      self.assertTrue(shell._feature_authority("lane_change"))
      self.assertTrue(shell._feature_authority("conditional_wheel"))
      self.assertFalse(shell._feature_authority("conditional"))
      self.assertTrue(shell._feature_authority("aol"))
      shell._mode = runtime_app.ShellMode.ONROAD
      self.assertFalse(shell._feature_authority("lane_change"))
      self.assertFalse(shell._feature_authority("conditional_wheel"))

  def test_threshold_units_and_exact_source_guard(self):
    speed = self.row("conditional:cem:speed_mps", FeaturePage.CONDITIONAL_CEM)
    self.assertEqual(speed.unit, "mph")
    request = required_change(speed)
    self.params.put_bool("IsMetric", True, block=True)
    self.assertFalse(self.owner.apply(request))
    self.assertIsNone(self.params.get("ConditionalModeConfig"))
    speed = self.row("conditional:cem:speed_mps", FeaturePage.CONDITIONAL_CEM)
    self.assertEqual(speed.unit, "km/h")
    self.assertTrue(self.owner.apply(required_change(speed)))
    saved = decode_preferences(Path(self.params.get_param_path("ConditionalModeConfig")).read_bytes())
    self.assertAlmostEqual(saved.cem.speed_mps, 1 / 3.6)
    stale = required_change(self.row("conditional:ccm:launch_assist", FeaturePage.CONDITIONAL_CCM))
    Path(self.params.get_param_path("ConditionalModeConfig")).write_bytes(b'{"bad":true}')
    self.assertFalse(self.owner.apply(stale))

  def test_bounds_and_manual_persistence_clears_only_selected_code(self):
    row = self.row("conditional:ccm:set_speed_margin_mps", FeaturePage.CONDITIONAL_CCM)
    forged = FeatureSettingsRequest(row.key, row.source, "100", vehicle_fingerprint=row.vehicle_fingerprint,
                                    capability=row.capability, dependencies=row.dependencies, display_unit=row.display_unit)
    self.assertFalse(self.owner.apply(forged))
    self.assertIsNone(self.params.get("ConditionalModeConfig"))
    manual_path = Path(self.params.get_param_path("ConditionalManualState"))
    manual_path.write_bytes(encode_manual(SavedCodes(cem=2, ccm=1)))
    persist = self.row("conditional:cem:persist_manual", FeaturePage.CONDITIONAL_CEM)
    self.assertEqual(persist.value, "Off")
    self.assertTrue(self.owner.apply(required_change(persist)))
    self.assertTrue(decode_preferences(Path(self.params.get_param_path("ConditionalModeConfig")).read_bytes()).cem.persist_manual)
    self.assertEqual(decode_manual(manual_path.read_bytes()), SavedCodes(cem=0, ccm=1))
    manual_path.write_bytes(encode_manual(SavedCodes(cem=2, ccm=1)))
    self.assertTrue(self.owner.apply(required_change(self.row("conditional:cem:persist_manual", FeaturePage.CONDITIONAL_CEM))))
    self.assertFalse(decode_preferences(Path(self.params.get_param_path("ConditionalModeConfig")).read_bytes()).cem.persist_manual)
    self.assertEqual(decode_manual(manual_path.read_bytes()), SavedCodes(cem=0, ccm=1))

  def test_manual_source_stale_and_partial_clear_cannot_resurrect_override(self):
    from openpilot.starpilot.conditional_mode import actions
    manual_path = Path(self.params.get_param_path("ConditionalManualState"))
    config_path = Path(self.params.get_param_path("ConditionalModeConfig"))
    manual_path.write_bytes(encode_manual(SavedCodes(cem=2, ccm=1)))
    request = required_change(self.row("conditional:cem:persist_manual", FeaturePage.CONDITIONAL_CEM))
    manual_path.write_bytes(encode_manual(SavedCodes(cem=1, ccm=1)))
    self.assertFalse(self.owner.apply(request))
    self.assertFalse(config_path.exists())
    request = required_change(self.row("conditional:cem:persist_manual", FeaturePage.CONDITIONAL_CEM))
    original = actions.os.replace
    def fail_config(source, destination):
      if Path(destination) == config_path:
        raise OSError("simulated config rename failure")
      return original(source, destination)
    with patch.object(actions.os, "replace", side_effect=fail_config):
      self.assertFalse(self.owner.apply(request))
    self.assertEqual(decode_manual(manual_path.read_bytes()), SavedCodes(cem=0, ccm=1))
    self.assertFalse(config_path.exists())

  def test_failed_manual_clear_never_changes_config(self):
    from openpilot.starpilot.conditional_mode import actions
    manual_path = Path(self.params.get_param_path("ConditionalManualState"))
    config_path = Path(self.params.get_param_path("ConditionalModeConfig"))
    manual_path.write_bytes(encode_manual(SavedCodes(cem=2, ccm=1)))
    request = required_change(self.row("conditional:cem:persist_manual", FeaturePage.CONDITIONAL_CEM))
    original = actions.os.replace
    def fail_manual(source, destination):
      if Path(destination) == manual_path:
        raise OSError("simulated manual rename failure")
      return original(source, destination)
    with patch.object(actions.os, "replace", side_effect=fail_manual):
      self.assertFalse(self.owner.apply(request))
    self.assertEqual(decode_manual(manual_path.read_bytes()), SavedCodes(cem=2, ccm=1))
    self.assertFalse(config_path.exists())

  def test_parked_authority_loss_after_clear_leaves_config_off(self):
    from openpilot.starpilot.conditional_mode.preferences import encode_preferences
    manual_path = Path(self.params.get_param_path("ConditionalManualState"))
    config_path = Path(self.params.get_param_path("ConditionalModeConfig"))
    original = encode_manual(SavedCodes(cem=2, ccm=1))
    manual_path.write_bytes(original)
    desired = SavedPreferences()
    desired = replace(desired, cem=replace(desired.cem, persist_manual=True))
    calls = 0
    def authority():
      nonlocal calls
      calls += 1
      return calls < 3
    result = commit_manual(self.params, expected_config=None, expected_units=None, expected_safe=None,
                           expected_manual=original, authorized=authority, choice=ModeChoice.CEM,
                           config_raw=encode_preferences(desired))
    self.assertTrue(result.manual_cleared)
    self.assertFalse(result.committed)
    self.assertEqual(decode_manual(manual_path.read_bytes()), SavedCodes(cem=0, ccm=1))
    self.assertFalse(config_path.exists())

  def test_stock_is_not_a_manual_saved_family(self):
    path = Path(self.params.get_param_path("ConditionalManualState"))
    raw = encode_manual(SavedCodes(cem=2, ccm=1))
    path.write_bytes(raw)
    result = commit_manual(self.params, expected_config=None, expected_units=None, expected_safe=None,
                           expected_manual=raw, authorized=lambda: True, choice=ModeChoice.STOCK,
                           config_raw=stock_document())
    self.assertFalse(result.committed)
    self.assertEqual(path.read_bytes(), raw)
    malformed_commit = Mock(wraps=commit_manual)
    result = malformed_commit(self.params, expected_config=None, expected_units=None, expected_safe=None,
                              expected_manual=raw, authorized=lambda: True, choice="conditional_experimental",
                              config_raw=stock_document())
    malformed_commit.assert_called_once()
    self.assertFalse(result.committed)
    self.assertEqual(path.read_bytes(), raw)

  def test_invalid_manual_bytes_need_explicit_confirmed_reset(self):
    manual_path = Path(self.params.get_param_path("ConditionalManualState"))
    manual_path.write_bytes(b'{"version":9}')
    persist = self.row("conditional:ccm:persist_manual", FeaturePage.CONDITIONAL_CCM)
    self.assertFalse(persist.available)
    reset = self.row("conditional:manual_reset")
    request = FeatureSettingsRequest(reset.key, reset.source, "confirm", vehicle_fingerprint=reset.vehicle_fingerprint,
                                     capability=reset.capability, dependencies=reset.dependencies)
    self.assertFalse(self.owner.apply(request))
    self.assertEqual(manual_path.read_bytes(), b'{"version":9}')
    request = replace(request, confirmation=True)
    self.parked = False
    self.assertFalse(self.owner.apply(request))
    self.parked = True
    self.assertTrue(self.owner.apply(request))
    self.assertEqual(decode_manual(manual_path.read_bytes()), SavedCodes())

  def test_active_manual_writer_lease_defers_persist_toggle(self):
    from openpilot.starpilot.conditional_mode.manual_saved import manual_lock_path
    path = Path(self.params.get_param_path("ConditionalManualState"))
    path.write_bytes(encode_manual(SavedCodes(cem=2, ccm=1)))
    request = required_change(self.row("conditional:cem:persist_manual", FeaturePage.CONDITIONAL_CEM))
    script = "import fcntl,sys; f=open(sys.argv[1],'a'); fcntl.flock(f,fcntl.LOCK_EX); print('ready',flush=True); sys.stdin.read(1)"
    child = subprocess.Popen([sys.executable, "-c", script, str(manual_lock_path(self.params))],
                             stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
    try:
      self.assertEqual(child.stdout.readline().strip(), "ready")
      self.assertFalse(self.owner.apply(request))
      self.assertEqual(decode_manual(path.read_bytes()), SavedCodes(cem=2, ccm=1))
      self.assertIsNone(self.params.get("ConditionalModeConfig"))
    finally:
      child.communicate(input="x", timeout=5)
    self.assertTrue(self.owner.apply(request))

  def test_safe_mode_source_change_invalidates_pending_toggle(self):
    manual_path = Path(self.params.get_param_path("ConditionalManualState"))
    manual_path.write_bytes(encode_manual(SavedCodes(cem=2, ccm=1)))
    request = required_change(self.row("conditional:cem:persist_manual", FeaturePage.CONDITIONAL_CEM))
    self.params.put_bool("SafeMode", True, block=True)
    self.assertFalse(self.owner.apply(request))
    self.assertEqual(decode_manual(manual_path.read_bytes()), SavedCodes(cem=2, ccm=1))
    self.assertIsNone(self.params.get("ConditionalModeConfig"))

  def test_valid_other_unit_value_can_step_down_without_clamping_on_render(self):
    preferences = SavedPreferences()
    preferences = replace(preferences, cem=replace(preferences.cem, speed_mps=99 * MPH_TO_MPS))
    path = Path(self.params.get_param_path("ConditionalModeConfig"))
    path.write_bytes(encode_preferences(preferences))
    self.params.put_bool("IsMetric", True, block=True)
    row = self.row("conditional:cem:speed_mps", FeaturePage.CONDITIONAL_CEM)
    self.assertGreater(float(row.value), 150.0)
    self.assertEqual(row.maximum, float(row.value))
    self.assertIsNone(row_change(row, 1))
    self.assertTrue(self.owner.apply(required_change(row, -1)))
    self.assertLess(decode_preferences(path.read_bytes()).cem.speed_mps, 99 * MPH_TO_MPS)
    preferences = SavedPreferences()
    preferences = replace(preferences, cem=replace(preferences.cem, signal_lane_width_m=15.0),
                          ccm=replace(preferences.ccm, set_speed_margin_mps=30 / 3.6))
    path.write_bytes(encode_preferences(preferences))
    self.params.put_bool("IsMetric", False, block=True)
    for key, page, old in (("conditional:cem:signal_lane_width_m", FeaturePage.LANE_CHANGE, 15.0),
                           ("conditional:ccm:set_speed_margin_mps", FeaturePage.CONDITIONAL_CCM, 30 / 3.6)):
      row = self.row(key, page)
      self.assertGreater(float(row.value), 15.0)
      self.assertTrue(self.owner.apply(required_change(row, -1)))
      current = decode_preferences(path.read_bytes())
      section, field = key.split(":")[1:]
      self.assertLess(getattr(getattr(current, section), field), old)

  def test_corrupt_bytes_preserved_until_confirmed_reset(self):
    path = Path(self.params.get_param_path("ConditionalModeConfig"))
    path.write_bytes(b'{"version":2}')
    self.assertFalse(any(row.key == "conditional:mode" for row in self.rows(FeaturePage.WHEEL)))
    reset = self.row("conditional:reset")
    self.assertFalse(self.owner.apply(FeatureSettingsRequest(reset.key, reset.source, "confirm",
                                                            vehicle_fingerprint=reset.vehicle_fingerprint,
                                                            capability=reset.capability, dependencies=reset.dependencies)))
    self.assertEqual(path.read_bytes(), b'{"version":2}')
    request = FeatureSettingsRequest(reset.key, reset.source, "confirm", confirmation=True,
                                     vehicle_fingerprint=reset.vehicle_fingerprint, capability=reset.capability,
                                     dependencies=reset.dependencies)
    self.parked = False
    self.assertFalse(self.owner.apply(request))
    self.parked = True
    self.assertTrue(self.owner.apply(request))
    self.assertEqual(decode_preferences(path.read_bytes()).mode.value, "stock")

  def test_core_configuration_survives_car_change_and_params_lock_contention(self):
    request = required_change(self.row("conditional:mode"))
    self.cp.carVin = "VIN2"
    self.assertTrue(self.owner.apply(request))
    self.cp.carVin = "VIN1"
    Path(self.params.get_param_path("ConditionalModeConfig")).unlink()
    request = required_change(self.row("conditional:mode"))
    root = Path(self.params.get_param_path("ConditionalModeConfig")).parent.parent
    script = "import fcntl,sys; f=open(sys.argv[1],'a'); fcntl.flock(f,fcntl.LOCK_EX); print('ready',flush=True); sys.stdin.read(1)"
    child = subprocess.Popen([sys.executable, "-c", script, str(root / ".lock")],
                             stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
    try:
      self.assertEqual(child.stdout.readline().strip(), "ready")
      self.assertFalse(self.owner.apply(request))
      self.assertIsNone(self.params.get("ConditionalModeConfig"))
    finally:
      child.communicate(input="x", timeout=5)
    self.assertTrue(self.owner.apply(request))

  def test_oversized_document_never_repaired_by_render(self):
    path = Path(self.params.get_param_path("ConditionalModeConfig"))
    path.write_bytes(b'x' * 4097)
    self.assertFalse(any(row.key == "conditional:reset" for row in self.rows(FeaturePage.WHEEL)))
    self.assertEqual(path.read_bytes(), b'x' * 4097)

  def test_nonregular_document_does_not_block_or_offer_repair(self):
    path = Path(self.params.get_param_path("ConditionalModeConfig"))
    os.mkfifo(path)
    self.assertFalse(any(row.key == "conditional:reset" for row in self.rows(FeaturePage.WHEEL)))
    path.unlink()
    outside = path.parent.parent / "outside-conditional"
    outside.write_bytes(b'{"version":2}')
    path.symlink_to(outside)
    self.assertFalse(any(row.key == "conditional:reset" for row in self.rows(FeaturePage.WHEEL)))
    self.assertEqual(outside.read_bytes(), b'{"version":2}')

  def test_final_locked_guard_rejects_new_editor_bytes_and_revoked_authority(self):
    path = Path(self.params.get_param_path("ConditionalModeConfig"))
    calls = 0
    def changed_source():
      nonlocal calls
      calls += 1
      if calls == 2:
        path.write_bytes(b'other editor')
      return True
    result = commit(self.params, stock_document(), None, None, changed_source)
    self.assertFalse(result.committed)
    self.assertEqual(path.read_bytes(), b'other editor')
    path.unlink()
    calls = 0
    def revoked():
      nonlocal calls
      calls += 1
      return calls == 1
    self.assertFalse(commit(self.params, stock_document(), None, None, revoked).committed)
    self.assertFalse(path.exists())

  def test_large_hit_target_and_compact_parent_child_reset(self):
    from openpilot.system.ui.widgets import DialogResult
    state = self.owner.snapshot(FeaturePage.CONDITIONAL, parked=True, system_long=False,
                                lateral_context=False, metric=False)
    hit = FeatureInput.target(2000, 150, state)
    assert hit is not None and hit.row is not None
    self.assertEqual(hit.row.key, "conditional:mode")
    class Button:
      def __init__(self, text, value):
        self.text, self.value, self.click = text, value, None
      def set_click_callback(self, callback):
        self.click = callback
      def set_enabled(self, enabled):
        self.enabled = enabled
    class Scroller:
      def __init__(self):
        self.items = []
        self._scroller = self
      def add_widgets(self, widgets):
        self.items.extend(widgets)
    class Session:
      def __init__(self, owner):
        self.owner = owner
      def feature_snapshot(self, page):
        return self.owner.snapshot(page, parked=True, system_long=False, lateral_context=False, metric=False)
      def feature_request(self, request):
        return self.owner.apply(request)
    stack = []
    with patch.object(compact, "BigButton", Button), patch.object(compact, "GreyBigButton", Button), \
         patch.object(compact, "NavScroller", Scroller), \
         patch.object(compact, "ConfirmDialog", side_effect=lambda *args, **kwargs: SimpleNamespace(callback=kwargs["callback"])), \
         patch.object(compact.gui_app, "push_widget", stack.append), \
         patch.object(compact.gui_app, "get_active_widget", side_effect=lambda: stack[-1]):
      adapter = compact.FeatureSettingsCompact(Session(self.owner))
      adapter.open(FeaturePage.HUB)
      next(card for card in stack[-1].items if card.text == "conditional driving modes").click()
      child = stack[-1]
      next(card for card in child.items if card.text == "saved driving mode").click()
      self.assertEqual(decode_preferences(Path(self.params.get_param_path("ConditionalModeConfig")).read_bytes()).mode.value,
                       "conditional_chill")
      next(card for card in child.items if card.text == "experimental conditions").click()
      self.assertTrue(any(card.text.startswith("speed threshold") for card in stack[-1].items))
      stack.pop()
      Path(self.params.get_param_path("ConditionalModeConfig")).write_bytes(b'{"version":2}')
      adapter.open(FeaturePage.CONDITIONAL)
      next(card for card in stack[-1].items if card.text == "restore chill defaults").click()
      dialog = stack.pop()
      dialog.callback(DialogResult.CONFIRM)
      self.assertEqual(decode_preferences(Path(self.params.get_param_path("ConditionalModeConfig")).read_bytes()).mode.value,
                       "stock")
      manual_path = Path(self.params.get_param_path("ConditionalManualState"))
      manual_path.write_bytes(b'{"version":9}')
      adapter.open(FeaturePage.CONDITIONAL)
      next(card for card in stack[-1].items if card.text == "reset remembered manual choices").click()
      dialog = stack.pop()
      dialog.callback(DialogResult.CONFIRM)
      self.assertEqual(decode_manual(manual_path.read_bytes()), SavedCodes())

  def test_large_pane_renders_mode_and_child_labels_in_existing_geometry(self):
    labels = []
    fonts = BitmapFonts.__new__(BitmapFonts)
    fonts.profile = Profile.LARGE
    state = self.owner.snapshot(FeaturePage.CONDITIONAL, parked=True, system_long=False,
                                lateral_context=False, metric=False)
    with patch.object(fonts, "draw", side_effect=lambda value, *_args, **_kwargs: labels.append(value)), \
         patch.object(large.rl, "draw_rectangle_rounded"), patch.object(large.clip, "begin_scissor_mode"), \
         patch.object(large.clip, "end_scissor_mode"):
      large.FeatureSettingsView(fonts).render(state)
    self.assertIn("Conditional Driving Modes", labels)
    self.assertIn("Saved driving mode", labels)
    self.assertIn("Experimental conditions", labels)
    self.assertIn("Chill conditions", labels)

  def test_large_manual_reset_confirmation_revoked_on_navigation(self):
    from openpilot.starpilot.ui.runtime_app import StarShellSession
    from openpilot.starpilot.ui.settings_state import Destination
    from openpilot.starpilot.ui.shell import ShellMode
    from openpilot.system.ui.widgets import DialogResult
    manual_path = Path(self.params.get_param_path("ConditionalManualState"))
    manual_path.write_bytes(b'{"version":9}')
    row = self.row("conditional:manual_reset")
    request = FeatureSettingsRequest(row.key, row.source, "confirm", confirmation=True,
                                     vehicle_fingerprint=row.vehicle_fingerprint, capability=row.capability,
                                     dependencies=row.dependencies)
    session = StarShellSession.__new__(StarShellSession)
    session._mode = ShellMode.SETTINGS
    session.selected = Destination.DRIVING_CONTROLS
    session.feature_page = FeaturePage.CONDITIONAL
    session._lane_change_request_epoch = 0
    dialogs = []
    with patch.object(StarShellSession, "feature_request", side_effect=self.owner.apply), \
         patch("openpilot.system.ui.widgets.confirm_dialog.ConfirmDialog",
               side_effect=lambda *args, **kwargs: SimpleNamespace(callback=kwargs["callback"])), \
         patch("openpilot.starpilot.ui.runtime_app.gui_app.push_widget", dialogs.append):
      session._confirm_conditional(request)
      session._lane_change_request_epoch += 1
      dialogs[-1].callback(DialogResult.CONFIRM)
      self.assertEqual(manual_path.read_bytes(), b'{"version":9}')
      session._confirm_conditional(request)
      dialogs[-1].callback(DialogResult.CONFIRM)
      self.assertEqual(decode_manual(manual_path.read_bytes()), SavedCodes())


if __name__ == "__main__":
  unittest.main()
