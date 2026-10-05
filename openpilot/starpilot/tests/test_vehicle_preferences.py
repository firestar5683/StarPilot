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

  def test_gm_stop_preferences_require_strict_saved_opt_in(self):
    from openpilot.common.params import ParamKeyType
    for key, name in (("VoltSNG", "volt_sng"), ("GMAutoHold", "gm_auto_hold")):
      self.raw("SafeMode", None)
      self.assertEqual(self.params.get_type(key), ParamKeyType.BOOL)
      self.assertIs(self.params.get_default_value(key), False)
      for raw in (None, b"0", b"", b"true", b"1\n", b"1" * 20, b"1"):
        self.raw(key, raw)
        self.assertEqual(getattr(VehicleStartupPreferences.read(self.params, enabled=True), name), raw == b"1")
      self.assertFalse(getattr(VehicleStartupPreferences.read(self.params, enabled=False), name))
      self.raw("SafeMode", b"1")
      self.assertFalse(getattr(VehicleStartupPreferences.read(self.params, enabled=True), name))
    self.assertTrue(VehicleStartupPreferences(True, True).turn_assist)

  def test_gm_hold_runtime_withdraws_for_disabled_or_malformed_preferences(self):
    from opendbc.car.gm.tests.test_bolt_volt_configurations import ordinary_params
    from opendbc.car.gm.values import CAR as GM_CAR
    from openpilot.starpilot.car.gm.auto_hold import AutoHoldPreference
    cp = ordinary_params(GM_CAR.CHEVROLET_VOLT, radar=True)
    VehicleStartupPreferences(gm_auto_hold=True).prepare(cp)
    now = 1_000_000_000
    for key in ("GMAutoHold", "OpenpilotEnabledToggle", "SafeMode", "DisableOpenpilotLongitudinal"):
      for raw in (b"0", b"1", b"", b"true", None):
        for clean_key, value in (("GMAutoHold", b"1"), ("OpenpilotEnabledToggle", b"1"),
                                 ("SafeMode", b"0"), ("DisableOpenpilotLongitudinal", b"0")):
          self.raw(clean_key, value)
        owner = AutoHoldPreference(cp, self.params)
        self.assertTrue(owner.update(now))
        self.raw(key, raw)
        now += 250_000_000
        expected = raw == b"1" if key in ("GMAutoHold", "OpenpilotEnabledToggle") else raw in (None, b"0")
        self.assertEqual(owner.update(now), expected, (key, raw))
        self.assertFalse(owner.update(now - 1))
        cp.passive = True
        self.assertFalse(owner.update(now))
        cp.passive = False
    preferences = VehicleStartupPreferences(gm_auto_hold=True, disable_bolt_long=True)
    preferences.prepare(cp)
    preferences.finalize(cp)
    self.assertFalse(cp.openpilotLongitudinalControl)
    self.assertEqual(cp.safetyConfigs[0].safetyParam, 0x4004)

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

  def start(self, candidate, *, enabled=True, requested=True, change_saved=False, key="ToyotaAutoHold", observed=None, capture=None):
    self.raw(key, b"1" if requested else b"0")
    self.params.put_bool("OpenpilotEnabledToggle", enabled, block=True)
    snapshots = []

    def fingerprint(*args, **kwargs):
      return candidate, observed if observed is not None else gen_empty_fingerprint(), "0" * 17, [], structs.CarParams.FingerprintSource.can, True

    def create(*args, **kwargs):
      ci = car_helpers.get_car(*args, **kwargs)
      snapshots.append(capture(ci) if capture is not None else (bool(ci.CP.flags & ToyotaFlags.AUTO_BRAKE_HOLD), int(ci.CP.alternativeExperience)))
      if change_saved:
        self.raw(key, b"0")
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

  def test_gm_hold_card_publishes_admitted_configuration_and_honors_live_opt_out(self):
    from opendbc.car.gm.values import CAR as GM_CAR, is_volt_auto_hold
    for accelerator in (False, True):
      observed = gen_empty_fingerprint()
      observed[1][0x460] = 8
      if accelerator:
        observed[0][0xBE] = 6
      base = 0x4004 if accelerator else 0xC004
      for enabled, requested, change_saved in ((True, True, False), (True, True, True), (True, False, False), (False, True, False)):
        with self.subTest(accelerator=accelerator, enabled=enabled, requested=requested, change_saved=change_saved):
          host, constructed, published = self.start(GM_CAR.CHEVROLET_VOLT, key="GMAutoHold", observed=observed,
            capture=lambda ci: int(ci.CS.CP.safetyConfigs[0].safetyParam), enabled=enabled,
            requested=requested, change_saved=change_saved)
          admitted = enabled and requested
          self.assertEqual(constructed, [base | (0x80 if admitted else 0)])
          self.assertEqual(is_volt_auto_hold(published), admitted)
          if enabled:
            self.assertEqual(published.safetyConfigs[0].safetyParam, constructed[0])
            self.assertEqual(host.CI.CC.gm_auto_hold, requested)
            if requested:
              self.assertEqual(host.CI.CC.gm_auto_hold_input.update(1_000_000_000), not change_saved)
            else:
              self.assertIsNone(host.CI.CC.gm_auto_hold_input)
          else:
            self.assertEqual(published.safetyConfigs[0].safetyModel, structs.CarParams.SafetyModel.noOutput)

  def test_camera_volt_hold_startup_retains_release_and_disable_longitudinal_owners(self):
    from opendbc.car.gm.values import CAR as GM_CAR, is_volt_auto_hold
    for candidate in (GM_CAR.CHEVROLET_VOLT_ASCM, GM_CAR.CHEVROLET_VOLT_CAMERA, GM_CAR.CHEVROLET_VOLT_2019):
      for radar in (False, True):
        for brake_c9 in ((True,) if candidate == GM_CAR.CHEVROLET_VOLT_CAMERA else (False, True)):
          observed = gen_empty_fingerprint()
          if candidate == GM_CAR.CHEVROLET_VOLT_ASCM:
            observed[0][0x2FF] = 8
            stock_word = 0x205 | (0x400 if brake_c9 else 0) | (0x800 if radar else 0)
          elif candidate == GM_CAR.CHEVROLET_VOLT_2019:
            observed[0][0x2FF] = 8
            stock_word = 0x1005 | (0x400 if brake_c9 else 0)
          else:
            observed[2][0x320] = 6
            stock_word = 5
          if not brake_c9:
            observed[0][0xBE] = 6
          if radar:
            observed[1][0x460] = 8
          startup_choices = [(False, False, True), (True, False, True), (False, True, True)]
          if candidate == GM_CAR.CHEVROLET_VOLT_2019:
            startup_choices.append((False, False, False))
          for release, disable, sascm in startup_choices:
            if not sascm:
              observed[0].pop(0x2FF)
            with self.subTest(candidate=candidate, radar=radar, brake_c9=brake_c9, release=release, disable=disable, sascm=sascm):
              self.params.put_bool("IsReleaseBranch", release, block=True)
              self.params.put_bool("AlphaLongitudinalEnabled", True, block=True)
              self.params.put_bool("DisableOpenpilotLongitudinal", disable, block=True)
              host, constructed, published = self.start(candidate, key="GMAutoHold", observed=observed,
                capture=lambda ci: int(ci.CS.CP.safetyConfigs[0].safetyParam))
              admitted = not release and not disable and sascm
              self.assertEqual(constructed, [stock_word | (0x4082 if admitted else 0)])
              self.assertEqual(published.safetyConfigs[0].safetyParam, constructed[0])
              self.assertEqual(is_volt_auto_hold(published), admitted)
              self.assertEqual(published.openpilotLongitudinalControl, admitted)
              self.assertEqual(published.pcmCruise, not admitted)
              self.assertEqual(host.CI.CC.gm_auto_hold, admitted)
              self.assertEqual(host.CI.CC.gm_auto_hold_input is not None, admitted)
              self.assertTrue(self.params.get_bool("GMAutoHold"))
              self.assertTrue(self.params.get_bool("AlphaLongitudinalEnabled"))

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
