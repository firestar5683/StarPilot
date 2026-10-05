"""Native saved-feature actions use real Params bytes and strict profile helpers."""

from pathlib import Path
from dataclasses import replace
from types import SimpleNamespace
import os
import tempfile
import unittest
from unittest.mock import patch

from openpilot.common.params import Params
from openpilot.starpilot.longitudinal.profile_document import migrate_profile_document
from openpilot.starpilot.ui.feature_settings_owner import FeatureSettingsOwner
from openpilot.starpilot.ui.feature_settings_state import FeatureRow, FeatureSettingsRequest, row_change, row_default
from openpilot.starpilot import saved_document
from openpilot.starpilot.ui import feature_settings_owner


def required_change(row: FeatureRow, direction: int = 1) -> FeatureSettingsRequest:
  request = row_change(row, direction)
  if request is None:
    raise AssertionError(f"Expected an editable row: {row.key}")
  return request


def required_document(raw: object) -> dict:
  document = migrate_profile_document(raw)
  if document is None:
    raise AssertionError("Expected a valid saved profile document")
  return document


class FeatureSettingsOwnerTests(unittest.TestCase):
  def setUp(self):
    self.temp = tempfile.TemporaryDirectory()
    self.addCleanup(self.temp.cleanup)
    self.params = Params(self.temp.name)
    self.allowed = True
    self.groups = []
    self.fingerprint = "TOYOTA COROLLA TSS2"
    self.owner = FeatureSettingsOwner(self.params, self._authority, vehicle_fingerprint=lambda: self.fingerprint)

  def _authority(self, group):
    self.groups.append(group)
    return self.allowed

  def _row(self, page, key):
    state = self.owner.snapshot(page, parked=True, system_long=True, lateral_context=True, metric=False)
    return next(row for row in state.rows if row.key == key)

  def test_camera_interceptor_setup_reports_actual_owner_and_preserves_preferences(self):
    from opendbc.car.gm.tests.test_camera_acc_pedal import params
    from opendbc.car.gm.startup_preferences import prepare_disable_longitudinal
    cp = params()
    self.fingerprint = cp.carFingerprint
    self.owner.vehicle_params = lambda: cp
    self.params.put_bool('GMPedalLongitudinal', False, block=True)
    pedal = self._row('vehicle', 'GMPedalLongitudinal')
    self.assertEqual(pedal.value, 'Automatic')
    self.assertFalse(pedal.available)
    pitch = self._row('vehicle', 'LongPitch')
    self.assertTrue(pitch.available)
    request = replace(required_change(pitch), confirmation=True)
    self.assertTrue(self.owner.apply(request))
    self.assertFalse(self.params.get_bool('LongPitch'))
    prepare_disable_longitudinal(cp, True)
    self.assertEqual(self._row('vehicle', 'GMPedalLongitudinal').value, 'Detected, inactive')
    self.assertFalse(self.owner.apply(request))
    self.assertFalse(self.params.get_bool('GMPedalLongitudinal'))
    self.assertNotIn('LongPitch', [row.key for row in self.owner.snapshot(
      'vehicle', parked=True, system_long=False, lateral_context=True, metric=False).rows])

  def test_malformed_numeric_default_has_no_reset_target(self):
    self.params.put("StandardFollow", 2.8, block=True)
    with patch.object(self.owner, "_default", return_value="not a number"):
      row = self.owner._number_row("StandardFollow", "Follow", True)
    self.assertIsNone(row.default_value)
    self.assertIsNone(row_default(row))

  def test_source_profile_defaults_and_single_numeric_reset(self):
    self.params.put("StandardFollow", 2.8, block=True)
    row = self._row("standard", "StandardFollow")
    self.assertEqual(float(row.default_value), float(self.params.get_default_value("StandardFollow")))
    request = row_default(row)
    assert request is not None
    self.assertTrue(self.owner.apply(request))
    self.assertFalse(self.owner.apply(request))
    preset = self._row("standard/acceleration", "profile:standard:acceleration")
    self.assertEqual(preset.default_value, "Selected Profile")
    self.assertEqual(self._row("profiles", "profile:global_braking").default_value, "Comfort")

  def test_strength_has_actual_runtime_admission_percent_range_and_source_guard(self):
    from openpilot.starpilot.lateral.tests.test_lane_runtime import ioniq_candidate
    _, tagged = ioniq_candidate()
    root = Path(self.params.get_param_path("LaneCentering")).parent
    registered = self.params
    class Files:
      def get_param_path(self, key):
        return str(root / key)
      def get_default_value(self, key):
        return 1.0 if key == "LaneCenteringStrength" else registered.get_default_value(key)
      def put(self, key, value, block=True):
        (root / key).write_bytes(str(value).encode())
    self.owner.params = Files()
    self.owner.vehicle_params = lambda: None
    row = self._row("lane", "LaneCenteringStrength")
    self.assertFalse(row.available)
    self.assertIn("vehicle configuration", row.reason)
    self.owner.vehicle_params = lambda: tagged
    self.fingerprint = tagged.carFingerprint
    row = self._row("lane", "LaneCenteringStrength")
    self.assertEqual((row.value, row.minimum, row.maximum, row.step), ("100.0", 50, 150, 5))
    self.assertTrue(row.available)
    request = FeatureSettingsRequest(row.key, row.source, "150", vehicle_fingerprint=row.vehicle_fingerprint)
    self.assertTrue(self.owner.apply(request))
    self.assertEqual((root / row.key).read_bytes(), b"1.5")
    self.assertFalse(self.owner.apply(request))
    row = self._row("lane", "LaneCenteringStrength")
    for invalid in ("49", "151", "nan"):
      self.assertFalse(self.owner.apply(FeatureSettingsRequest(row.key, row.source, invalid,
                                                             vehicle_fingerprint=row.vehicle_fingerprint)))
    self.owner.vehicle_params = lambda: None
    self.assertFalse(self.owner.apply(FeatureSettingsRequest(row.key, row.source, "100",
                                                           vehicle_fingerprint=row.vehicle_fingerprint)))
    self.assertIsNone(registered.get("LaneCenteringE2EAuthority"))

  def test_turn_assist_defaults_on_independent_of_tune_and_exact_source_guarded(self):
    from openpilot.starpilot.lateral.tests.test_lane_runtime import ioniq_candidate
    from openpilot.starpilot.lateral.controller_selection import DOCUMENT_KEY, ControllerMode, replace_mode
    _, cp = ioniq_candidate()
    self.owner.vehicle_params = lambda: cp
    self.owner.controller.vehicle_params = self.owner.vehicle_params
    self.fingerprint = cp.carFingerprint
    row = self._row("torque", "TurnAssist")
    self.assertEqual(row.value, "On")
    self.assertTrue(row.available)
    self.assertEqual(row.dependencies, ())
    request = required_change(row)
    self.assertTrue(self.owner.apply(request))
    self.assertFalse(self.params.get_bool("TurnAssist"))
    self.assertFalse(self.owner.apply(request))
    import json
    self.params.put(DOCUMENT_KEY, json.loads(replace_mode(None, cp, ControllerMode.STANDARD)), block=True)
    row = self._row("torque", "TurnAssist")
    self.assertTrue(row.available)
    self.assertEqual(row.value, "Off")
    self.assertFalse(self.params.get_bool("TurnAssist"))
    view = self.owner.snapshot("torque", parked=False, system_long=True, lateral_context=True, metric=False)
    self.assertFalse(next(row for row in view.rows if row.key == "TurnAssist").available)
    self.owner.vehicle_params = lambda: None
    view = self.owner.snapshot("torque", parked=True, system_long=True, lateral_context=True, metric=False)
    self.assertFalse(any(row.key == "TurnAssist" for row in view.rows))
    self.assertFalse(self.owner.apply(required_change(row)))
    self.assertFalse(self.params.get_bool("TurnAssist"))

  def test_live_lane_owner_maps_only_explicit_keys(self):
    self.owner.authority = lambda group: group == "lane_live"
    view = self.owner.snapshot("lane", parked=False, system_long=False, lateral_context=False, metric=False)
    row = next(row for row in view.rows if row.key == "LaneCentering")
    self.assertTrue(row.available)
    self.assertTrue(self.owner.apply(required_change(row)))
    self.assertTrue(self.params.get("LaneCentering"))
    view = self.owner.snapshot("lane", parked=False, system_long=False, lateral_context=False, metric=False)
    pause = next(row for row in view.rows if row.key == "LaneCenteringPauseOnSignal")
    self.assertTrue(pause.available)
    self.assertTrue(self.owner.apply(required_change(pause)))
    for key in ("AlwaysOnLateral", "CustomPersonalities", "LongPitch"):
      self.assertFalse(self.owner.apply(FeatureSettingsRequest(key, None, "On", vehicle_fingerprint=self.fingerprint)))

  def test_force_stop_disable_onroad_retains_source_vehicle_and_enable_gates(self):
    self.params.put_bool("ForceStops", True, block=True)
    self.owner.authority = lambda group: group == "preferences"
    view = self.owner.snapshot("profiles", parked=False, system_long=False, lateral_context=True, metric=False)
    row = next(row for row in view.rows if row.key == "ForceStops")
    self.assertTrue(row.available)
    request = required_change(row)
    self.assertEqual(request.value, "Off")
    self.fingerprint = "different vehicle"
    self.assertFalse(self.owner.apply(request))
    self.fingerprint = row.vehicle_fingerprint
    self.assertTrue(self.owner.apply(request))
    self.assertEqual(self.params.get("ForceStops"), False)
    self.assertFalse(self.owner.apply(request))
    enable = FeatureSettingsRequest("ForceStops", b"0", "On", vehicle_fingerprint=self.fingerprint)
    self.assertFalse(self.owner.apply(enable))
    self.assertIsNone(self.params.get("QOLLongitudinal"))

  def test_force_stop_preserves_cruise_master_and_offset_bounds(self):
    self.assertTrue(self._row("profiles", "ForceStops").available)
    self.params.put_bool("QOLLongitudinal", True, block=True)
    force = self._row("profiles", "ForceStops")
    self.assertTrue(force.available)
    self.assertEqual(force.value, "Off")
    self.params.put_bool("ForceStops", True, block=True)
    force = self._row("profiles", "ForceStops")
    self.assertEqual(force.value, "On")
    offset = self._row("profiles", "ForceStopDistanceOffset")
    self.assertTrue(self.owner.apply(FeatureSettingsRequest(offset.key, offset.source, "4",
                                                          vehicle_fingerprint=offset.vehicle_fingerprint)))
    self.assertEqual(self.params.get("ForceStopDistanceOffset"), 4)
    offset = self._row("profiles", "ForceStopDistanceOffset")
    for invalid in ("21", "-21", "0.5"):
      self.assertFalse(self.owner.apply(FeatureSettingsRequest(offset.key, offset.source, invalid,
                                                             vehicle_fingerprint=offset.vehicle_fingerprint)))
    self.assertTrue(self.owner.apply(required_change(force)))
    self.assertFalse(self._row("profiles", "ForceStopDistanceOffset").available)

  def test_corrupt_bytes_remain_visible_and_untouched(self):
    for key, page, raw in (("LaneCenterOffset", "lane", b"nan"),
                           ("SpeedLimitController", "slc", b"maybe"),
                           ("SLCFallback", "slc", b"broken")):
      with self.subTest(key=key):
        path = Path(self.params.get_param_path(key))
        path.write_bytes(raw)
        row = self._row(page, key)
        self.assertFalse(row.available)
        self.assertIsNone(row_change(row))
        self.assertEqual(path.read_bytes(), raw)

  def test_readable_presets_keep_saved_tokens_and_numeric_help(self):
    preset = self._row("aggressive/acceleration", "profile:aggressive:acceleration")
    self.assertEqual(preset.value, "Selected Profile")
    self.assertEqual(preset.choices, ("Selected Profile", "StarPilot Default", "Normal", "Comfort", "Sport", "Sport+"))
    self.assertTrue(self.owner.apply(FeatureSettingsRequest(preset.key, preset.source, "Sport+",
                                                          vehicle_fingerprint=preset.vehicle_fingerprint)))
    document = required_document(Path(self.params.get_param_path("LongitudinalPersonalityProfiles")).read_bytes())
    self.assertEqual(document["profiles"]["aggressive"]["acceleration"]["preset"], "sport_plus")
    self.assertIn("Higher values", self._row("aggressive", "AggressiveJerkAcceleration").reason)
    self.assertFalse(any(row.key == "AggressivePersonalityProfile" for row in self.owner.snapshot(
      "aggressive", parked=True, system_long=True, lateral_context=True, metric=False).rows))
    self.assertIn("Sport+", self._row("aggressive/acceleration", "profile:aggressive:acceleration").value)
    self.assertIsNone(self.params.get("CustomPersonalities"))

  def test_release_rechecks_parked_authority_and_source(self):
    row = self._row("lane", "LaneCentering")
    request = required_change(row)
    self.assertIsNotNone(request)
    self.allowed = False
    self.assertFalse(self.owner.apply(request))
    self.allowed = True
    self.params.put_bool("LaneCentering", True, block=True)
    self.assertFalse(self.owner.apply(request))
    self.assertTrue(self.params.get_bool("LaneCentering"))
    self.assertIn("lane", self.groups)
    fresh = self._row("lane", "LaneCentering")
    self.fingerprint = "OTHER CAR"
    self.assertFalse(self.owner.apply(required_change(fresh)))

  def test_approaching_lead_setting_independent_and_exactly_guarded(self):
    self.fingerprint = None
    Path(self.params.get_param_path("LongitudinalPersonalityProfiles")).write_bytes(b"{invalid")
    Path(self.params.get_param_path("CustomPersonalities")).write_bytes(b"invalid")
    row = self._row("profiles", "LeadApproachBuffer")
    self.assertEqual((row.label, row.value), ("Approaching lead buffer", "Off"))
    self.assertTrue(row.available)
    self.assertIsNone(row.vehicle_fingerprint)
    self.assertIsNone(row.capability)
    request = required_change(row)
    self.allowed = False
    self.assertFalse(self.owner.apply(request))
    self.allowed = True
    self.assertTrue(self.owner.apply(request))
    saved = Path(self.params.get_param_path("LeadApproachBuffer"))
    self.assertEqual(saved.read_bytes(), b"1")
    self.assertFalse(self.owner.apply(request))
    off = required_change(self._row("profiles", "LeadApproachBuffer"))
    saved.write_bytes(b"0")
    self.assertFalse(self.owner.apply(off))
    self.assertEqual(saved.read_bytes(), b"0")
    self.assertTrue(self._row("profiles", "LeadApproachBuffer").available)

  def test_parent_and_units_guards(self):
    child = self._row("slc", "SLCConfirmationLower")
    self.assertFalse(child.available)
    self.assertFalse(self.owner.apply(FeatureSettingsRequest(child.key, child.source, "On", vehicle_fingerprint=child.vehicle_fingerprint)))
    parent = self._row("slc", "SLCConfirmation")
    self.assertTrue(self.owner.apply(required_change(parent)))
    child = self._row("slc", "SLCConfirmationLower")
    self.assertTrue(self.owner.apply(required_change(child)))
    authority = self._row("lane", "LaneCenteringE2EAuthority")
    self.assertEqual(authority.value, "100.0")
    self.assertTrue(self.owner.apply(required_change(authority, -1)))
    self.assertAlmostEqual(self.params.get("LaneCenteringE2EAuthority"), 0.95)
    offset = self._row("slc", "Offset1")
    self.assertFalse(offset.available)
    self.assertFalse(self.owner.apply(FeatureSettingsRequest("Offset1", offset.source, "5", vehicle_fingerprint=offset.vehicle_fingerprint)))
    Path(self.params.get_param_path("IsMetric")).write_bytes(b"bad")
    offset = self._row("slc", "Offset1")
    self.assertIn("invalid saved units", offset.label)
    self.assertEqual(Path(self.params.get_param_path("IsMetric")).read_bytes(), b"bad")

  def test_limit_sign_preference_needs_parked_authority_not_long_control_or_vehicle(self):
    self.fingerprint = None
    self.owner = FeatureSettingsOwner(self.params, lambda group: self.allowed and group == "preferences",
                                      vehicle_fingerprint=lambda: self.fingerprint)
    page = self.owner.snapshot("slc", parked=True, system_long=False, lateral_context=False, metric=False)
    sign = next(row for row in page.rows if row.key == "ShowSpeedLimits")
    self.assertTrue(sign.available)
    self.assertIsNone(sign.vehicle_fingerprint)
    for key in ("SpeedLimitController", "SLCConfirmation", "SLCPriority1", "SLCFallback"):
      self.assertFalse(next(row for row in page.rows if row.key == key).available)
    request = required_change(sign)
    self.allowed = False
    self.assertFalse(self.owner.apply(request))
    self.allowed = True
    self.assertTrue(self.owner.apply(request))
    self.assertTrue(self.params.get_bool("ShowSpeedLimits"))
    self.assertFalse(self.params.get_bool("SpeedLimitController"))
    self.assertFalse(self.owner.apply(request))

  def test_curve_saved_choices_and_invalid_learning(self):
    hub = self.owner.snapshot("hub", parked=True, system_long=True, lateral_context=True, metric=False)
    self.assertIn("curve", [row.page for row in hub.rows])
    master = self._row("curve", "CurveSpeedController")
    self.assertEqual(master.value, "Off")
    self.assertTrue(self.owner.apply(required_change(master)))
    self.assertIn("long", self.groups)
    no_lead = self._row("curve", "CurveSpeedControllerNoLead")
    self.assertTrue(self.owner.apply(required_change(no_lead)))
    self.assertTrue(self.params.get_bool("CurveSpeedControllerNoLead"))
    display = self._row("curve", "ShowCSCStatus")
    self.assertTrue(self.owner.apply(required_change(display)))
    self.assertTrue(self.params.get_bool("ShowCSCStatus"))
    document = Path(self.params.get_param_path("CurveComfortData"))
    document.write_bytes(b"{invalid")
    self.assertFalse(self.owner.apply(required_change(master)))  # Old document evidence cannot authorize another action.
    enabled = self._row("curve", "CurveSpeedController")
    self.assertTrue(enabled.available)
    self.assertTrue(self.owner.apply(required_change(enabled)))  # Off remains available, preserving corrupt bytes.
    self.assertEqual(document.read_bytes(), b"{invalid")
    self.assertFalse(self._row("curve", "CurveSpeedControllerNoLead").available)
    self.assertFalse(self._row("curve", "CurveSpeedController").available)
    self.assertTrue(self._row("curve", "ShowCSCStatus").available)
    Path(self.params.get_param_path("CurveSpeedController")).write_bytes(b"maybe")
    invalid_master = self._row("curve", "CurveSpeedController")
    self.assertFalse(invalid_master.available)
    self.assertEqual(invalid_master.reason, "Invalid saved value")

  def test_curve_requires_fresh_long_authority_and_legacy_source(self):
    legacy = Path(self.params.get_param_path("CurvatureData"))
    legacy.write_bytes(b"{}")
    master = self._row("curve", "CurveSpeedController")
    request = required_change(master)
    legacy.write_bytes(b'{"0.001":{"average":2.0,"count":2}}')
    self.assertFalse(self.owner.apply(request))
    self.allowed = False
    self.assertFalse(self._row("curve", "CurveSpeedController").available)
    self.allowed = True
    fresh = self._row("curve", "CurveSpeedController")
    self.fingerprint = "OTHER CAR"
    self.assertFalse(self.owner.apply(required_change(fresh)))

  def test_curve_learning_automatic_readout_and_confirmed_reset(self):
    legacy = Path(self.params.get_param_path("CurvatureData"))
    legacy_raw = b'{"0.001":{"average":2.4,"count":2}}'
    legacy.write_bytes(legacy_raw)
    state = self.owner.snapshot("curve", parked=True, system_long=True, lateral_context=True, metric=False)
    self.assertFalse(any(row.key == "curve_adopt" for row in state.rows))
    progress = next(row for row in state.rows if row.label == "Learning progress")
    self.assertNotEqual(progress.value, "Unavailable")
    comfort = next(row for row in state.rows if row.label == "Saved cornering comfort")
    self.assertIn("m/s²", comfort.value)
    canonical = Path(self.params.get_param_path("CurveComfortData"))
    self.assertFalse(canonical.exists())
    self.assertEqual(legacy.read_bytes(), legacy_raw)
    reset = self._row("curve", "curve_reset")
    request = FeatureSettingsRequest(reset.key, reset.source, "confirm", confirmation=True,
      vehicle_fingerprint=reset.vehicle_fingerprint, dependencies=reset.dependencies)
    self.assertFalse(self.owner.apply(replace(request, confirmation=False)))
    legacy.write_bytes(b'{"0.001":{"average":2.0,"count":2}}')
    self.assertFalse(self.owner.apply(request))
    reset = self._row("curve", "curve_reset")
    request = FeatureSettingsRequest(reset.key, reset.source, "confirm", confirmation=True,
      vehicle_fingerprint=reset.vehicle_fingerprint, dependencies=reset.dependencies)
    self.assertTrue(self.owner.apply(request))
    self.assertEqual(canonical.read_bytes(), b'{"version":1,"buckets":{}}')
    self.assertEqual(legacy.read_bytes(), b'{"0.001":{"average":2.0,"count":2}}')

  def test_curve_learning_action_rechecks_parked_vehicle(self):
    Path(self.params.get_param_path("CurvatureData")).write_bytes(b'{"0.001":{"average":2.0,"count":2}}')
    adopt = self._row("curve", "curve_reset")
    request = FeatureSettingsRequest(adopt.key, adopt.source, "confirm", confirmation=True,
                                     vehicle_fingerprint=adopt.vehicle_fingerprint, dependencies=adopt.dependencies)
    self.allowed = False
    self.assertFalse(self.owner.apply(request))
    self.allowed = True
    self.fingerprint = "OTHER CAR"
    self.assertFalse(self.owner.apply(request))
    self.assertIsNone(self.params.get("CurveComfortData"))

  def test_profile_document_round_trip_and_explicit_invalid_reset(self):
    self.params.put("LongitudinalPersonalityProfiles", {}, block=True)
    preset = self._row("aggressive/acceleration", "profile:aggressive:acceleration")
    self.assertTrue(self.owner.apply(FeatureSettingsRequest(preset.key, preset.source, "custom", vehicle_fingerprint=preset.vehicle_fingerprint)))
    raw = Path(self.params.get_param_path("LongitudinalPersonalityProfiles")).read_bytes()
    doc = required_document(raw)
    self.assertEqual(doc["profiles"]["aggressive"]["acceleration"]["preset"], "custom")
    point = self._row("aggressive/acceleration", "profile:aggressive:acceleration:0")
    self.assertTrue(self.owner.apply(required_change(point, -1)))
    self.assertNotEqual(Path(self.params.get_param_path("LongitudinalPersonalityProfiles")).read_bytes(), raw)
    path = Path(self.params.get_param_path("LongitudinalPersonalityProfiles"))
    path.write_bytes(b"{invalid")
    self.params.put_bool("CustomPersonalities", True, block=True)
    reset = self._row("profiles", "reset_profiles")
    self.assertFalse(self.owner.apply(FeatureSettingsRequest(reset.key, reset.source, "reset", vehicle_fingerprint=reset.vehicle_fingerprint)))
    self.assertEqual(path.read_bytes(), b"{invalid")
    self.assertTrue(self.owner.apply(FeatureSettingsRequest(reset.key, reset.source, "reset", confirmation=True,
                                                            vehicle_fingerprint=reset.vehicle_fingerprint)))
    restored = required_document(path.read_bytes())
    self.assertIsNotNone(restored)
    self.assertFalse(restored["enabled"])
    self.assertFalse(self.params.get_bool("CustomPersonalities"))

  def test_profile_enable_lost_authority_keeps_boolean_disabled(self):
    self.owner.vehicle_params = lambda: SimpleNamespace(
      carFingerprint=self.fingerprint, openpilotLongitudinalControl=True, pcmCruise=False,
      passive=False, notCar=False, dashcamOnly=False, carVin="VIN1")
    self.params.put("LongitudinalPersonalityProfiles", {}, block=True)
    row = self._row("profiles", "CustomPersonalities")
    request = required_change(row)
    original_replace = os.replace
    replacements = []

    def lose_authority_after_document(source, destination):
      original_replace(source, destination)
      replacements.append(destination)
      self.allowed = False

    with patch.object(saved_document.os, "replace", side_effect=lose_authority_after_document):
      self.assertFalse(self.owner.apply(request))
    self.assertEqual(len(replacements), 1)
    self.assertFalse(self.params.get_bool("CustomPersonalities"))

  def test_staged_profile_edit_rechecks_master_vehicle_and_parked_authority(self):
    original_fsync = os.fsync
    for changed in ("master", "vehicle", "authority"):
      with self.subTest(changed=changed):
        self.allowed = True
        self.fingerprint = "TOYOTA COROLLA TSS2"
        self.params.put_bool("CustomPersonalities", False, block=True)
        request = required_change(self._row("profiles", "profile:global_braking"))
        staged = []
        def invalidate_after_stage(fd, changed=changed, staged=staged):
          original_fsync(fd)
          if not staged:
            staged.append(True)
            if changed == "master":
              self.params.put_bool("CustomPersonalities", True, block=True)
            elif changed == "vehicle":
              self.fingerprint = "OTHER CAR"
            else:
              self.allowed = False
        with patch.object(saved_document.os, "fsync", side_effect=invalidate_after_stage):
          self.assertFalse(self.owner.apply(request))
        self.assertTrue(staged)
        self.assertIsNone(self.params.get("LongitudinalPersonalityProfiles"))

  def test_profile_enable_does_not_adopt_a_competing_document(self):
    self.owner.vehicle_params = lambda: SimpleNamespace(
      carFingerprint=self.fingerprint, openpilotLongitudinalControl=True, pcmCruise=False,
      passive=False, notCar=False, dashcamOnly=False, carVin="VIN1")
    request = required_change(self._row("profiles", "CustomPersonalities"))
    writes = []
    def replace_after_verified_commit(*args, **kwargs):
      result = saved_document.commit_exact(*args, **kwargs)
      self.assertTrue(result.committed and result.verified)
      competing = required_document(self.params.get("LongitudinalPersonalityProfiles"))
      competing["globalBrakingResponse"] = "sport"
      self.params.put("LongitudinalPersonalityProfiles", competing, block=True)
      writes.append(True)
      return result
    with patch.object(feature_settings_owner, "commit_exact", side_effect=replace_after_verified_commit):
      self.assertFalse(self.owner.apply(request))
    self.assertEqual(writes, [True])
    self.assertFalse(self.params.get_bool("CustomPersonalities"))
    self.assertEqual(self.params.get("LongitudinalPersonalityProfiles")["globalBrakingResponse"], "sport")

  def test_profile_enable_rechecks_document_while_staging_switch(self):
    self.owner.vehicle_params = lambda: SimpleNamespace(
      carFingerprint=self.fingerprint, openpilotLongitudinalControl=True, pcmCruise=False,
      passive=False, notCar=False, dashcamOnly=False, carVin="VIN1")
    request = required_change(self._row("profiles", "CustomPersonalities"))
    original_fsync = os.fsync
    calls = []
    def competing_edit(fd):
      original_fsync(fd)
      calls.append(fd)
      if len(calls) == 3:
        document = self.params.get("LongitudinalPersonalityProfiles")
        document["globalBrakingResponse"] = "sport"
        self.params.put("LongitudinalPersonalityProfiles", document, block=True)
    with patch.object(saved_document.os, "fsync", side_effect=competing_edit):
      self.assertFalse(self.owner.apply(request))
    self.assertEqual(len(calls), 3)
    self.assertFalse(self.params.get_bool("CustomPersonalities"))
    self.assertEqual(self.params.get("LongitudinalPersonalityProfiles")["globalBrakingResponse"], "sport")

  def test_global_braking_saved_choice_is_parked_source_bound_and_preserved_by_profile_edit(self):
    row = self._row("profiles", "profile:global_braking")
    self.assertEqual((row.value, row.choices), ("Comfort", ("StarPilot Default", "Normal", "Comfort", "Sport")))
    self.assertFalse(self.params.get_bool("CustomPersonalities"))
    change = required_change(row)
    assert change is not None
    self.allowed = False
    self.assertFalse(self.owner.apply(change))
    self.allowed = True
    self.assertTrue(self.owner.apply(change))
    saved = required_document(self.params.get("LongitudinalPersonalityProfiles"))
    self.assertEqual(saved["selectedDecelerationProfile"], "sport")
    self.assertFalse(saved["enabled"])
    self.assertFalse(self.owner.apply(change))
    category = self._row("standard/braking", "profile:standard:braking")
    self.assertTrue(self.owner.apply(required_change(category)))
    self.assertEqual(required_document(self.params.get("LongitudinalPersonalityProfiles"))["selectedDecelerationProfile"], "sport")
    unparked = self.owner.snapshot("profiles", parked=False, system_long=True, lateral_context=True, metric=False)
    self.assertFalse(next(row for row in unparked.rows if row.key == "profile:global_braking").available)


if __name__ == "__main__":
  unittest.main()
