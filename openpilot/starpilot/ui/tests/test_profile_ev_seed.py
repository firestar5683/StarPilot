from pathlib import Path
from types import SimpleNamespace
import os
import tempfile
import unittest
from unittest.mock import patch

from opendbc.car.structs import car
from openpilot.common.params import Params
from openpilot.starpilot import saved_document
from openpilot.starpilot.longitudinal.profile_document import migrate_profile_document
from openpilot.starpilot.ui.feature_settings_owner import FeatureSettingsOwner
from openpilot.starpilot.ui.feature_settings_state import FeatureSettingsRequest


class NamedAccelerationSeedTests(unittest.TestCase):
  def setUp(self):
    temporary = tempfile.TemporaryDirectory()
    self.addCleanup(temporary.cleanup)
    self.params = Params(temporary.name)
    self.cp = SimpleNamespace(carFingerprint="HYUNDAI IONIQ 6", openpilotLongitudinalControl=True, pcmCruise=False,
                              passive=False, notCar=False, dashcamOnly=False, carVin="VIN1",
                              transmissionType=car.CarParams.TransmissionType.automatic)
    self.owner = FeatureSettingsOwner(self.params, lambda group: group == "long",
                                      vehicle_fingerprint=lambda: "HYUNDAI IONIQ 6",
                                      vehicle_params=lambda: self.cp)

  def select(self, value):
    row = self.owner.snapshot("standard/acceleration", parked=True, system_long=True,
                              lateral_context=False, metric=False).rows[0]
    request = FeatureSettingsRequest(row.key, row.source, value, vehicle_fingerprint=row.vehicle_fingerprint,
                                     capability=row.capability)
    return row, request

  def curve(self):
    raw = Path(self.params.get_param_path("LongitudinalPersonalityProfiles")).read_bytes()
    document = migrate_profile_document(raw)
    self.assertIsNotNone(document)
    if document is None:
      self.fail("the saved profile document did not decode")
    return document["profiles"]["standard"]["acceleration"]["curve"]

  def test_named_to_custom_uses_actual_ev_or_non_ev_curve(self):
    for transmission, last in ((car.CarParams.TransmissionType.automatic, 0.35),
                               (car.CarParams.TransmissionType.direct, 0.58)):
      with self.subTest(transmission=transmission):
        self.cp.transmissionType = transmission
        self.assertTrue(self.owner.apply(self.select("eco")[1]))
        row, request = self.select("Custom")
        self.assertIsNotNone(row.capability)
        self.assertTrue(self.owner.apply(request))
        self.assertEqual(self.curve()[-1], last)
        Path(self.params.get_param_path("LongitudinalPersonalityProfiles")).unlink()

  def test_named_seed_rejects_missing_or_changed_cp_before_and_after_staging(self):
    self.assertTrue(self.owner.apply(self.select("eco")[1]))
    row, request = self.select("Custom")
    path = Path(self.params.get_param_path("LongitudinalPersonalityProfiles"))
    original = path.read_bytes()
    self.cp.transmissionType = car.CarParams.TransmissionType.direct
    self.assertFalse(self.owner.apply(request))
    self.cp.transmissionType = car.CarParams.TransmissionType.automatic
    with patch.object(self, "cp", None):
      self.assertNotIn("Custom", self.select("Custom")[0].choices)
      self.assertFalse(self.owner.apply(request))
    self.assertEqual(path.read_bytes(), original)
    row, request = self.select("custom")
    real_fsync = os.fsync
    def change(fd):
      real_fsync(fd)
      self.cp.transmissionType = car.CarParams.TransmissionType.direct
    with patch.object(saved_document.os, "fsync", side_effect=change):
      self.assertFalse(self.owner.apply(request))
    self.assertEqual(path.read_bytes(), original)

  def test_selected_profile_to_custom_requires_current_vehicle_seed(self):
    with patch.object(self, "cp", None):
      row, request = self.select("Custom")
      self.assertIsNone(row.capability)
      self.assertNotIn("Custom", row.choices)
      self.assertFalse(self.owner.apply(request))
    self.assertFalse(Path(self.params.get_param_path("LongitudinalPersonalityProfiles")).exists())

  def test_named_preset_restores_dormant_custom_without_new_vehicle_seed(self):
    self.assertTrue(self.owner.apply(self.select("custom")[1]))
    original_curve = self.curve()
    self.assertTrue(self.owner.apply(self.select("eco")[1]))
    with patch.object(self, "cp", None):
      row, request = self.select("custom")
      self.assertIn("Custom", row.choices)
      self.assertTrue(self.owner.apply(request))
    self.assertEqual(self.curve(), original_curve)


if __name__ == "__main__":
  unittest.main()
