from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from opendbc.car import car_helpers, gen_empty_fingerprint, structs
from opendbc.car.toyota.values import CAR, ToyotaFlags
from opendbc.safety import ALTERNATIVE_EXPERIENCE
from openpilot.common.params import Params
from openpilot.selfdrive.car import card
from openpilot.starpilot.vehicle_preferences import VehicleStartupPreferences


class TestVehicleStartupPreferences(unittest.TestCase):
  def setUp(self):
    temporary = tempfile.TemporaryDirectory()
    self.addCleanup(temporary.cleanup)
    self.params = Params(temporary.name)

  def raw(self, key, value):
    path = Path(self.params.get_param_path(key))
    if value is None:
      path.unlink(missing_ok=True)
    else:
      path.write_bytes(value)

  def test_suburban_saved_long_pitch_configures_exact_controller(self):
    from opendbc.car.gm.carcontroller import CarController
    from opendbc.car.gm.interface import CarInterface
    from opendbc.car.gm.values import CAR as GM_CAR, DBC
    fingerprint = gen_empty_fingerprint()
    fingerprint[1][0x460] = 8
    cp = CarInterface.get_params(GM_CAR.CHEVROLET_SUBURBAN, fingerprint, [], False, False, False)
    for requested in (False, True):
      self.raw("LongPitch", b"1" if requested else b"0")
      preferences = VehicleStartupPreferences.read(self.params, enabled=True)
      controller = CarController(DBC[cp.carFingerprint], cp)
      preferences.configure_controller(SimpleNamespace(CP=cp, CC=controller))
      self.assertEqual(controller.long_pitch, requested)

  def test_only_exact_saved_opt_in_is_loaded(self):
    for raw in (None, b"0", b"", b"true", b"1\n", b"1" * 20, b"1"):
      with self.subTest(raw=raw):
        self.raw("ToyotaAutoHold", raw)
        preferences = VehicleStartupPreferences.read(self.params, enabled=True)
        self.assertEqual(preferences.toyota_auto_hold, raw == b"1")
    self.assertFalse(VehicleStartupPreferences.read(self.params, enabled=False).toyota_auto_hold)
    for safe in (b"1", b"invalid", b"", b"0", None):
      with self.subTest(safe=safe):
        self.raw("SafeMode", safe)
        self.assertEqual(VehicleStartupPreferences.read(self.params, enabled=True).toyota_auto_hold, safe in (None, b"0"))
    self.raw("SafeMode", None)
    path = Path(self.params.get_param_path("ToyotaAutoHold"))
    path.unlink()
    path.symlink_to("SafeMode")
    self.assertFalse(VehicleStartupPreferences.read(self.params, enabled=True).toyota_auto_hold)

  def start(self, candidate, *, enabled=True, requested=True, change_saved=False):
    self.raw("ToyotaAutoHold", b"1" if requested else b"0")
    self.params.put_bool("OpenpilotEnabledToggle", enabled, block=True)
    snapshots = []

    def fingerprint(*args, **kwargs):
      return candidate, gen_empty_fingerprint(), "0" * 17, [], structs.CarParams.FingerprintSource.can, True

    def create(*args, **kwargs):
      ci = car_helpers.get_car(*args, **kwargs)
      snapshots.append((bool(ci.CP.flags & ToyotaFlags.AUTO_BRAKE_HOLD), int(ci.CP.alternativeExperience)))
      if change_saved:
        self.raw("ToyotaAutoHold", b"0")
      return ci

    with patch.object(card, "Params", return_value=self.params), \
         patch.object(card, "feature_requested", return_value=False), \
         patch.object(card.messaging, "sub_sock", return_value=Mock()), \
         patch.object(card.messaging, "SubMaster", return_value=Mock()), \
         patch.object(card.messaging, "PubMaster", return_value=SimpleNamespace(sock={"sendcan": Mock()})), \
         patch.object(card.messaging, "recv_one_retry", return_value=SimpleNamespace(can=[object()])), \
         patch.object(card, "Ratekeeper", return_value=Mock()), \
         patch.object(card, "get_cache", return_value=None), \
         patch.object(card, "put_cache"), \
         patch.object(card, "get_car", side_effect=create), \
         patch.object(car_helpers, "fingerprint", side_effect=fingerprint):
      host = card.Car()
    with structs.CarParams.from_bytes(self.params.get("CarParams")) as cp:
      published = cp.as_builder()
    return host, snapshots, published

  def test_real_card_admits_before_construction_and_publishes_final_permission(self):
    for candidate, permission in ((CAR.TOYOTA_COROLLA_TSS2, ALTERNATIVE_EXPERIENCE.TOYOTA_AUTO_HOLD),
                                  (CAR.TOYOTA_CAMRY_TSS2, ALTERNATIVE_EXPERIENCE.TOYOTA_AEB_HOLD)):
      with self.subTest(candidate=candidate):
        host, constructed, published = self.start(candidate, change_saved=True)
        self.assertEqual(constructed, [(True, permission)])
        self.assertTrue(host.CI.CS.CP.flags & ToyotaFlags.AUTO_BRAKE_HOLD)
        self.assertEqual(published.alternativeExperience, permission)
        self.assertTrue(published.flags & ToyotaFlags.AUTO_BRAKE_HOLD)
        self.assertEqual(self.params.get("ToyotaAutoHold"), False)

  def test_default_disabled_and_master_off_never_admit_hold(self):
    for enabled, requested in ((True, False), (False, True)):
      with self.subTest(enabled=enabled, requested=requested):
        _, constructed, published = self.start(CAR.TOYOTA_CAMRY_TSS2, enabled=enabled, requested=requested)
        self.assertEqual(constructed, [(False, 0)])
        self.assertEqual(published.alternativeExperience, 0)
        self.assertFalse(published.flags & ToyotaFlags.AUTO_BRAKE_HOLD)
        if not enabled:
          self.assertTrue(published.passive)
          self.assertEqual(published.safetyConfigs[0].safetyModel, structs.CarParams.SafetyModel.noOutput)

  def test_finalize_cannot_late_enable_unprepared_parser(self):
    cp = car_helpers.interfaces[CAR.TOYOTA_CAMRY_TSS2].get_non_essential_params(CAR.TOYOTA_CAMRY_TSS2)
    preferences = VehicleStartupPreferences(True)
    preferences.finalize(cp)
    self.assertFalse(cp.flags & ToyotaFlags.AUTO_BRAKE_HOLD)
    self.assertEqual(cp.alternativeExperience, 0)

  def test_unrelated_vehicle_flags_are_untouched(self):
    cp = SimpleNamespace(brand="other", flags=4096, alternativeExperience=256)
    preferences = VehicleStartupPreferences(True)
    self.assertIs(preferences.prepare(cp), cp)
    preferences.finalize(cp)
    self.assertEqual((cp.flags, cp.alternativeExperience), (4096, 256))
