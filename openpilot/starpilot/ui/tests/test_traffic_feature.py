"""Saved Traffic controls use real Params and current Long Planner authority."""

from pathlib import Path
from types import SimpleNamespace
import os
import tempfile
import unittest
from unittest.mock import patch

from openpilot.common.params import Params
from opendbc.car.structs import car
from openpilot.starpilot import saved_document
from openpilot.starpilot.longitudinal.profile_document import default_personality_profiles, migrate_profile_document, serialize_personality_profiles
from openpilot.starpilot.longitudinal.profile_runtime import read_traffic_settings
from openpilot.starpilot.ui.feature_settings_owner import FeatureSettingsOwner
from openpilot.starpilot.ui.feature_settings_state import FeatureRow, FeatureSettingsRequest, row_change
from openpilot.starpilot.ui.traffic_feature import FOLLOW, REPAIR_FOLLOW, SWITCH


def required_change(row: FeatureRow, direction: int = 1) -> FeatureSettingsRequest:
  request = row_change(row, direction)
  assert request is not None
  return request


class TrafficFeatureTests(unittest.TestCase):
  def setUp(self):
    temporary = tempfile.TemporaryDirectory()
    self.addCleanup(temporary.cleanup)
    self.params = Params(temporary.name)
    self.parked = True
    self.cp = SimpleNamespace(carFingerprint="TOYOTA COROLLA TSS2", openpilotLongitudinalControl=True, pcmCruise=False,
                              passive=False, notCar=False, dashcamOnly=False, carVin="VIN1",
                              transmissionType=car.CarParams.TransmissionType.automatic)
    self.owner = FeatureSettingsOwner(self.params, lambda group: self.parked and group in ("long", "parked_preferences"),
                                      vehicle_fingerprint=lambda: self.cp.carFingerprint, vehicle_params=lambda: self.cp)

  def row(self, key):
    state = self.owner.snapshot("traffic", parked=self.parked, system_long=True, lateral_context=False, metric=False)
    return next(row for row in state.rows if row.key == key)

  def test_saved_scalar_rows_and_category_editor_are_real_while_master_off(self):
    traffic = self.owner.snapshot("traffic", parked=True, system_long=True, lateral_context=False, metric=False)
    self.assertEqual(traffic.title, "Traffic Profile")
    self.assertEqual((self.row(SWITCH).value, self.row(FOLLOW).value), ("On", "0.75"))
    self.assertTrue(self.row(FOLLOW).available)
    self.assertIn("inactive while Custom Driving Profiles is Off", self.row(FOLLOW).reason)
    self.assertEqual([row.page for row in traffic.rows if row.page],
                     ["traffic/acceleration", "traffic/braking", "traffic/following"])
    self.assertTrue(self.owner.apply(required_change(self.row(SWITCH), -1)))
    self.assertEqual(self.params.get_bool(SWITCH), False)
    self.assertTrue(self.owner.apply(required_change(self.row(FOLLOW))))
    self.assertEqual(self.params.get(FOLLOW), 0.8)
    jerk = self.row("TrafficJerkAcceleration")
    self.assertEqual((jerk.value, jerk.minimum, jerk.maximum, jerk.step, jerk.unit), ("100.0", 25.0, 200.0, 5.0, "%"))
    self.assertTrue(self.owner.apply(required_change(jerk)))
    self.assertEqual(self.params.get("TrafficJerkAcceleration"), 105.0)
    self.assertEqual(read_traffic_settings(self.params).follow[0], 0.75)
    category = self.owner.snapshot("traffic/braking", parked=True, system_long=True, lateral_context=False, metric=False)
    preset = category.rows[0]
    self.assertEqual(preset.key, "profile:traffic:braking")
    self.assertTrue(self.owner.apply(required_change(preset)))
    document = migrate_profile_document(Path(self.params.get_param_path("LongitudinalPersonalityProfiles")).read_bytes())
    assert document is not None
    self.assertEqual(document["profiles"]["traffic"]["braking"]["preset"], "standard")
    self.assertFalse(document["enabled"])
    self.params.put_bool("CustomPersonalities", True, block=True)
    self.assertIn("apply when Traffic mode is selected", self.row(FOLLOW).reason)
    self.params.put_bool(SWITCH, True, block=True)
    self.assertIn("apply when Traffic mode is selected", self.row(FOLLOW).reason)

  def test_below_floor_saved_follow_requires_explicit_confirmed_repair(self):
    path = Path(self.params.get_param_path(FOLLOW))
    path.write_bytes(b"0.5")
    self.assertEqual(self.row(FOLLOW).value, "0.5")
    self.assertFalse(self.row(FOLLOW).available)
    self.assertEqual(path.read_bytes(), b"0.5")
    repair = self.row(REPAIR_FOLLOW)
    self.assertTrue(repair.available)
    request = FeatureSettingsRequest(repair.key, repair.source, "confirm", confirmation=True,
                                     vehicle_fingerprint=repair.vehicle_fingerprint,
                                     capability=repair.capability, dependencies=repair.dependencies)
    self.assertFalse(self.owner.apply(FeatureSettingsRequest(repair.key, repair.source, "confirm",
                                                              vehicle_fingerprint=repair.vehicle_fingerprint,
                                                              capability=repair.capability, dependencies=repair.dependencies)))
    self.assertEqual(path.read_bytes(), b"0.5")
    self.assertTrue(self.owner.apply(request))
    self.assertEqual(path.read_bytes(), b"0.75")
    self.assertFalse(self.owner.apply(request))

  def test_invalid_saved_switch_is_not_displayed_as_off(self):
    Path(self.params.get_param_path(SWITCH)).write_bytes(b"invalid")
    row = self.row(SWITCH)
    self.assertEqual(row.value, "Invalid saved value")
    self.assertFalse(row.available)

  def test_repair_row_and_commit_require_parked_repair_authority(self):
    path = Path(self.params.get_param_path(FOLLOW))
    path.write_bytes(b"0.5")
    self.owner.authority = lambda group: group == "long"
    row = self.row(REPAIR_FOLLOW)
    self.assertFalse(row.available)
    request = FeatureSettingsRequest(row.key, row.source, "confirm", confirmation=True,
                                     vehicle_fingerprint=row.vehicle_fingerprint,
                                     capability=row.capability, dependencies=row.dependencies)
    self.assertFalse(self.owner.apply(request))
    self.assertEqual(path.read_bytes(), b"0.5")

  def test_below_floor_traffic_curve_must_select_supported_preset(self):
    profiles = default_personality_profiles(False)
    profiles["traffic"]["following"] = {"preset": "custom", "curve": [0.5] * 10}
    raw = serialize_personality_profiles(profiles, False, False, enabled=False)
    path = Path(self.params.get_param_path("LongitudinalPersonalityProfiles"))
    path.write_bytes(raw.encode())
    page = self.owner.snapshot("traffic/following", parked=True, system_long=True, lateral_context=False, metric=False)
    self.assertEqual(page.rows[0].value, "Custom")
    self.assertFalse(page.rows[1].available)
    self.assertIn("supported following preset", page.rows[1].reason)
    preset = page.rows[0]
    invalid = FeatureSettingsRequest(preset.key, preset.source, "custom", vehicle_fingerprint=preset.vehicle_fingerprint,
                                     capability=preset.capability, dependencies=preset.dependencies)
    self.assertFalse(self.owner.apply(invalid))
    self.assertEqual(path.read_bytes(), raw.encode())
    supported = FeatureSettingsRequest(preset.key, preset.source, "dom_default", vehicle_fingerprint=preset.vehicle_fingerprint,
                                       capability=preset.capability, dependencies=preset.dependencies)
    self.assertTrue(self.owner.apply(supported))
    document = migrate_profile_document(path.read_bytes())
    assert document is not None
    self.assertEqual(document["profiles"]["traffic"]["following"]["preset"], "dom_default")

  def test_category_edit_rechecks_system_long_capability_under_lock(self):
    row = self.owner.snapshot("traffic/braking", parked=True, system_long=True, lateral_context=False, metric=False).rows[0]
    request = required_change(row)
    self.assertIsNotNone(request)
    self.cp.openpilotLongitudinalControl = False
    self.assertFalse(self.owner.apply(request))
    self.cp.openpilotLongitudinalControl = True
    path = Path(self.params.get_param_path("LongitudinalPersonalityProfiles"))
    real_fsync = os.fsync
    def revoke(fd):
      real_fsync(fd)
      self.cp.openpilotLongitudinalControl = False
    with patch.object(saved_document.os, "fsync", side_effect=revoke):
      self.assertFalse(self.owner.apply(request))
    self.assertFalse(path.exists())

  def test_custom_starts_from_actual_traffic_defaults_and_ev_named_curve(self):
    def select(category, preset):
      row = self.owner.snapshot(f"traffic/{category}", parked=True, system_long=True,
                                lateral_context=False, metric=False).rows[0]
      request = FeatureSettingsRequest(row.key, row.source, preset, vehicle_fingerprint=row.vehicle_fingerprint,
                                       capability=row.capability, dependencies=row.dependencies)
      self.assertTrue(self.owner.apply(request))
      raw = Path(self.params.get_param_path("LongitudinalPersonalityProfiles")).read_bytes()
      document = migrate_profile_document(raw)
      assert document is not None
      return document["profiles"]["traffic"][category]

    acceleration = select("acceleration", "custom")
    self.assertEqual((acceleration["curve"][0], acceleration["curve"][-1]), (1.1, 0.23))
    braking = select("braking", "custom")
    self.assertEqual(braking["curve"], [0.42] * 10)
    self.assertEqual(self.owner.snapshot("traffic/braking", parked=True, system_long=True,
                                        lateral_context=False, metric=False).rows[1].minimum, 0.35)

    self.params.put("TrafficFollow", 0.8, block=True)
    self.params.put("RelaxedFollow", 1.8, block=True)
    following = select("following", "custom")
    self.assertEqual((following["curve"][0], following["curve"][-1]), (0.8, 1.8))

    self.cp.transmissionType = car.CarParams.TransmissionType.direct
    Path(self.params.get_param_path("LongitudinalPersonalityProfiles")).write_bytes(
      serialize_personality_profiles(default_personality_profiles(False), False, False, enabled=False).encode())
    select("acceleration", "eco")
    acceleration = select("acceleration", "custom")
    self.assertEqual(acceleration["curve"][-1], 0.58)

  def test_locked_save_rejects_staged_source_authority_and_unverified_readback(self):
    request = required_change(self.row(FOLLOW))
    self.assertIsNotNone(request)
    path = Path(self.params.get_param_path(FOLLOW))
    real_fsync = os.fsync
    calls = 0

    def concurrent(fd):
      nonlocal calls
      real_fsync(fd)
      calls += 1
      if calls == 1:
        path.write_bytes(b"1.2")

    with patch.object(saved_document.os, "fsync", side_effect=concurrent):
      self.assertFalse(self.owner.apply(request))
    self.assertEqual(path.read_bytes(), b"1.2")

    request = required_change(self.row(FOLLOW))
    calls = 0

    def revoke(fd):
      nonlocal calls
      real_fsync(fd)
      calls += 1
      if calls == 1:
        self.parked = False

    with patch.object(saved_document.os, "fsync", side_effect=revoke):
      self.assertFalse(self.owner.apply(request))
    self.assertEqual(path.read_bytes(), b"1.2")
    self.parked = True

    request = required_change(self.row(FOLLOW))
    real_read = saved_document.read_saved
    calls = 0

    def unverified(*args):
      nonlocal calls
      calls += 1
      return (b"unverified", True) if calls == 3 else real_read(*args)

    with patch.object(saved_document, "read_saved", side_effect=unverified):
      self.assertFalse(self.owner.apply(request))
    self.assertEqual(calls, 3)
    self.assertEqual(path.read_bytes(), b"1.25")


if __name__ == "__main__":
  unittest.main()
