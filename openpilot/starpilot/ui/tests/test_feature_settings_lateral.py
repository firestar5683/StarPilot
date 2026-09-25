"""Saved Torque/AOL UI actions against real Params, CarParams and runtime parsers."""

from pathlib import Path
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from opendbc.car import gen_empty_fingerprint
from opendbc.car.car_helpers import interfaces
from opendbc.car.honda.interface import CarInterface
from opendbc.car.honda.values import CAR as HONDA
from opendbc.car.hyundai.interface import CarInterface as HyundaiInterface
from opendbc.car.hyundai.ioniq6_handoff import build_ioniq6_hda2_long_candidate
from opendbc.car.hyundai.values import CAR as HYUNDAI
from openpilot.common.params import Params
from openpilot.starpilot.aol.intent import AolCardIntent, CRUISE_LONG_PRESS, independent_axis_requested, read_settings as read_aol_settings
from openpilot.starpilot.car.hyundai.aol import qualified_ioniq6
from openpilot.starpilot.aol.runtime import decide_axes
from openpilot.selfdrive.car.tests.test_hyundai_aol import candidate as ioniq6_candidate, state as ioniq6_state
from opendbc.car.structs import car
from openpilot.starpilot.lateral.torque_runtime import read_settings as read_torque_settings
from openpilot.starpilot.lateral.torque_settings import DOCUMENT_KEY, parse_document
from openpilot.starpilot.lateral.torque_tuning import TorqueSource, TorqueTuning
from openpilot.starpilot.ui.feature_settings_owner import FeatureSettingsOwner
from openpilot.starpilot.ui.feature_settings_state import FeatureInput, FeatureRow, FeatureSettingsRequest, FeatureSettingsState, row_change
from openpilot.starpilot.ui import feature_settings_compact as compact
from openpilot.starpilot.ui import feature_settings as large
from openpilot.starpilot.ui.presentation import BitmapFonts, Profile


def required_change(row: FeatureRow, direction: int = 1) -> FeatureSettingsRequest:
  request = row_change(row, direction)
  if request is None:
    raise AssertionError(f"Expected an editable row: {row.key}")
  return request


class LateralFeatureSettingsTests(unittest.TestCase):
  def setUp(self):
    self.temp = tempfile.TemporaryDirectory()
    self.addCleanup(self.temp.cleanup)
    self.params = Params(self.temp.name)
    self.parked = True
    self.cp = interfaces["TOYOTA_COROLLA_TSS2"].get_non_essential_params("TOYOTA_COROLLA_TSS2")
    self.owner = FeatureSettingsOwner(self.params, lambda group: self.parked,
                                      vehicle_fingerprint=lambda: str(self.cp.carFingerprint), vehicle_params=lambda: self.cp)

  def row(self, page, key):
    state = self.owner.snapshot(page, parked=True, system_long=True, lateral_context=True, metric=False)
    return next(item for item in state.rows if item.key == key)

  def test_torque_master_and_force_off_match_runtime_parser(self):
    self.assertTrue(self.owner.apply(required_change(self.row("torque", "LateralControllerSelection"))))
    master = self.row("torque", "AdvancedLateralTune")
    self.assertTrue(master.available)
    self.assertTrue(self.owner.apply(required_change(master)))
    force = self.row("torque", "ForceAutoTuneOff")
    self.assertEqual(force.value, "Off")
    self.assertTrue(self.owner.apply(required_change(force)))
    self.assertTrue(self.owner.apply(required_change(self.row("torque", "ForceAutoTuneOff"))))
    tune = self.cp.lateralTuning.torque
    vehicle = TorqueTuning(TorqueSource.VEHICLE, str(self.cp.carFingerprint), tune.latAccelFactor,
                           tune.latAccelOffset, tune.friction)
    saved = read_torque_settings(self.params, vehicle)
    self.assertTrue(saved.valid and saved.advanced and saved.force_auto_off)
    self.assertIsNone(saved.user_factor)
    self.assertFalse(self.row("torque", "SteerLatAccel").available)

  def test_onroad_saved_torque_edit_keeps_vehicle_binding_and_parked_repair(self):
    owner = FeatureSettingsOwner(self.params, lambda group: group != "parked_preferences",
                                 vehicle_fingerprint=lambda: str(self.cp.carFingerprint), vehicle_params=lambda: self.cp)
    page = owner.snapshot("torque", parked=False, system_long=False, lateral_context=True, metric=False,
                          configure_while_driving=True)
    master = next(row for row in page.rows if row.key == "AdvancedLateralTune")
    adopt = next(row for row in page.rows if row.key == "torque_adopt")
    self.assertTrue(master.available)
    self.assertFalse(adopt.available)
    self.assertTrue(owner.apply(required_change(master)))
    self.assertFalse(owner.apply(FeatureSettingsRequest("torque_adopt", adopt.source, "confirm", confirmation=True,
                                                        vehicle_fingerprint=adopt.vehicle_fingerprint,
                                                        capability=adopt.capability, dependencies=adopt.dependencies)))
    self.cp.carFingerprint = "TOYOTA_CAMRY"
    self.assertFalse(owner.apply(required_change(master)))

  def test_torque_corrupt_dependent_blocks_enable_but_allows_off(self):
    Path(self.params.get_param_path("SteerLatAccel")).write_bytes(b"nan")
    row = self.row("torque", "AdvancedLateralTune")
    self.assertFalse(row.available)
    self.params.put_bool("AdvancedLateralTune", True, block=True)
    row = self.row("torque", "AdvancedLateralTune")
    self.assertTrue(self.owner.apply(required_change(row)))
    self.assertFalse(self.params.get_bool("AdvancedLateralTune"))
    self.assertEqual(Path(self.params.get_param_path("SteerLatAccel")).read_bytes(), b"nan")

  def test_torque_corrupt_force_off_and_unsupported_cp_bytes(self):
    Path(self.params.get_param_path("ForceAutoTuneOff")).write_bytes(b"maybe")
    self.assertFalse(self.row("torque", "AdvancedLateralTune").available)
    self.params.put_bool("AdvancedLateralTune", True, block=True)
    self.assertTrue(self.owner.apply(required_change(self.row("torque", "AdvancedLateralTune"))))
    self.honda()
    Path(self.params.get_param_path("SteerLatAccel")).write_bytes(b"\xff")
    row = self.row("torque", "SteerLatAccel")
    self.assertEqual(row.value, "Invalid saved value")
    self.assertFalse(row.available)

  def test_unreadable_saved_source_is_visible_and_not_writable(self):
    self.honda()
    path = Path(self.params.get_param_path("AolBrakePauseSpeedMps"))
    path.write_bytes(b"4")
    from openpilot.starpilot.ui import feature_settings_owner
    original = feature_settings_owner.read_saved

    def unreadable(params, key, limit):
      return (b"", False) if key == "AolBrakePauseSpeedMps" else original(params, key, limit)

    with patch.object(feature_settings_owner, "read_saved", side_effect=unreadable):
      threshold = self.row("aol", "AolBrakePauseSpeedMps")
      self.assertFalse(threshold.available)
      self.assertFalse(self.row("aol", "AlwaysOnLateral").available)
    self.assertEqual(path.read_bytes(), b"4")

  def test_torque_capability_tuple_and_parked_evidence_rechecked(self):
    master = self.row("torque", "AdvancedLateralTune")
    self.cp.lateralTuning.torque.latAccelFactor *= 1.1
    self.assertFalse(self.owner.apply(required_change(master)))
    master = self.row("torque", "AdvancedLateralTune")
    self.parked = False
    self.assertFalse(self.owner.apply(required_change(master)))

  @staticmethod
  def confirm(row):
    return FeatureSettingsRequest(row.key, row.source, "confirm", confirmation=True,
                                  vehicle_fingerprint=row.vehicle_fingerprint,
                                  capability=row.capability, dependencies=row.dependencies)

  def test_torque_adoption_custom_partial_and_source_preserve_legacy(self):
    self.assertFalse(self.cp.carVin and self.cp.carVin != "0" * 17)  # no VIN availability requirement
    self.params.put("SteerLatAccel", self.cp.lateralTuning.torque.latAccelFactor * 1.1, block=True)
    old = Path(self.params.get_param_path("SteerLatAccel")).read_bytes()
    adopt = self.row("torque", "torque_adopt")
    self.assertFalse(self.owner.apply(FeatureSettingsRequest(adopt.key, adopt.source, "confirm",
                                                              vehicle_fingerprint=adopt.vehicle_fingerprint,
                                                              capability=adopt.capability, dependencies=adopt.dependencies)))
    self.assertTrue(self.owner.apply(self.confirm(adopt)))
    self.assertEqual(Path(self.params.get_param_path("SteerLatAccel")).read_bytes(), old)
    mode = self.row("torque", "torque:factor:mode")
    self.assertEqual(mode.value, "Vehicle/learned")
    self.assertTrue(self.owner.apply(required_change(mode)))
    value = self.row("torque", "torque:factor:value")
    self.assertTrue(self.owner.apply(required_change(value)))
    parsed = parse_document(Path(self.params.get_param_path(DOCUMENT_KEY)).read_bytes())
    self.assertEqual(parsed[str(self.cp.carFingerprint)].factor.mode, "custom")
    self.assertEqual(parsed[str(self.cp.carFingerprint)].friction.mode, "source")
    self.assertTrue(self.owner.apply(required_change(self.row("torque", "torque:factor:mode"))))
    parsed = parse_document(Path(self.params.get_param_path(DOCUMENT_KEY)).read_bytes())
    self.assertEqual(parsed[str(self.cp.carFingerprint)].factor.mode, "source")
    self.assertIsNotNone(parsed[str(self.cp.carFingerprint)].factor.custom_value)
    self.assertEqual(Path(self.params.get_param_path("SteerLatAccel")).read_bytes(), old)

  def test_torque_stale_source_capability_and_invalid_reset(self):
    adopt = self.row("torque", "torque_adopt")
    self.cp.carVin = "1HGCM82633A004352"
    self.assertFalse(self.owner.apply(self.confirm(adopt)))
    adopt = self.row("torque", "torque_adopt")
    self.parked = False
    self.assertFalse(self.owner.apply(self.confirm(adopt)))
    self.parked = True
    self.assertTrue(self.owner.apply(self.confirm(self.row("torque", "torque_adopt"))))
    old_mode = self.row("torque", "torque:factor:mode")
    Path(self.params.get_param_path(DOCUMENT_KEY)).write_bytes(b"bad")
    self.assertFalse(self.owner.apply(required_change(old_mode)))
    reset = self.row("torque", "torque_reset")
    self.assertTrue(reset.available)
    self.assertTrue(self.owner.apply(self.confirm(reset)))
    self.assertEqual(parse_document(Path(self.params.get_param_path(DOCUMENT_KEY)).read_bytes()), {})

  def test_torque_final_confirmation_rechecks_readability_and_fingerprint(self):
    document_path = Path(self.params.get_param_path(DOCUMENT_KEY))
    for raw, action in ((None, "torque_adopt"), (b"", "torque_reset")):
      if raw is None:
        document_path.unlink(missing_ok=True)
      else:
        document_path.write_bytes(raw)
      request = self.confirm(self.row("torque", action))
      original = self.owner.torque._readable
      reads = 0

      def loses_readability(key, original=original):
        nonlocal reads
        if key == DOCUMENT_KEY:
          reads += 1
          return reads == 1
        return original(key)

      with patch.object(self.owner.torque, "_readable", side_effect=loses_readability), \
           patch.object(self.params, "put", wraps=self.params.put) as put:
        self.assertFalse(self.owner.apply(request))
        put.assert_not_called()
      fingerprint = str(self.cp.carFingerprint)
      with patch.object(self.owner.torque, "vehicle_fingerprint", side_effect=(fingerprint, "TOYOTA_CAMRY")), \
           patch.object(self.params, "put", wraps=self.params.put) as put:
        self.assertFalse(self.owner.apply(request))
        put.assert_not_called()

  def test_torque_basis_change_pauses_custom_until_confirmed_review(self):
    self.assertTrue(self.owner.apply(self.confirm(self.row("torque", "torque_adopt"))))
    self.assertTrue(self.owner.apply(required_change(self.row("torque", "torque:factor:mode"))))
    self.cp.lateralTuning.torque.latAccelFactor *= 1.05
    state = self.owner.snapshot("torque", parked=True, system_long=True, lateral_context=True, metric=False)
    self.assertTrue(any(row.key == "torque_rebase" for row in state.rows))
    review = self.row("torque", "torque_rebase")
    self.assertIn("Lateral acceleration", review.value)
    detail = next(row for row in state.rows if row.label == "Lateral acceleration" and not row.key)
    self.assertIn("Saved", detail.value)
    self.assertIn("vehicle", detail.value)
    self.assertIn("range", detail.value)
    self.assertFalse(self.owner.apply(FeatureSettingsRequest(review.key, review.source, "confirm",
                                                              vehicle_fingerprint=review.vehicle_fingerprint,
                                                              capability=review.capability, dependencies=review.dependencies)))
    self.assertTrue(self.owner.apply(self.confirm(review)))
    self.assertEqual(self.row("torque", "torque:factor:mode").value, "Custom")
    self.cp.lateralTuning.torque.latAccelFactor *= 3
    self.assertFalse(self.owner.apply(self.confirm(self.row("torque", "torque_rebase"))))
    self.assertTrue(self.owner.apply(self.confirm(self.row("torque", "torque_reset_profile"))))
    self.assertEqual(self.row("torque", "torque:factor:mode").value, "Vehicle/learned")

  def honda(self):
    self.cp = CarInterface.get_params(HONDA.HONDA_CIVIC_BOSCH, gen_empty_fingerprint(), [], True, False, False)
    self.cp.safetyConfigs[-1].safetyParam |= 0x20

  def test_aol_explicit_metric_to_si_write_preserves_legacy(self):
    self.honda()
    self.params.put_bool("IsMetric", True, block=True)
    self.params.put("PauseAOLOnBrake", 10.0, block=True)
    legacy = Path(self.params.get_param_path("PauseAOLOnBrake")).read_bytes()
    threshold = self.row("aol", "AolBrakePauseSpeedMps")
    self.assertEqual((threshold.value, threshold.unit), ("36.0", "km/h"))
    self.assertTrue(self.owner.apply(required_change(threshold)))
    self.assertEqual(Path(self.params.get_param_path("PauseAOLOnBrake")).read_bytes(), legacy)
    self.assertAlmostEqual(read_aol_settings(self.params).pause_brake_mps, 37 / 3.6)

  def test_aol_threshold_source_and_units_stale_release(self):
    self.honda()
    self.params.put("PauseAOLOnBrake", 10.0, block=True)
    request = required_change(self.row("aol", "AolBrakePauseSpeedMps"))
    self.params.put_bool("IsMetric", True, block=True)
    self.assertFalse(self.owner.apply(request))
    self.params.remove("IsMetric")
    self.params.put("PauseAOLOnBrake", 11.0, block=True)
    self.assertFalse(self.owner.apply(request))
    self.params.put("PauseAOLOnBrake", 10.0, block=True)
    self.params.put("AolBrakePauseSpeedMps", 1.0, block=True)
    self.assertFalse(self.owner.apply(request))

  def test_fresh_honda_without_native_bit_can_save_request_preference(self):
    self.cp = CarInterface.get_params(HONDA.HONDA_CIVIC_BOSCH, gen_empty_fingerprint(), [], True, False, False)
    self.assertEqual(self.cp.safetyConfigs[-1].safetyParam & 0x20, 0)
    master = self.row("aol", "AlwaysOnLateral")
    self.assertTrue(master.available)
    self.assertTrue(self.owner.apply(required_change(master)))
    saved = read_aol_settings(self.params)
    self.assertTrue(saved.enabled)
    self.assertTrue(independent_axis_requested(saved))
    self.cp.safetyConfigs[-1].safetyParam |= 0x20
    self.assertTrue(self.row("aol", "AlwaysOnLateral").available)

  def test_ioniq6_stock_cp_exposes_saved_requests_without_claiming_live_long(self):
    fp = gen_empty_fingerprint()
    fp[2].update({0x50: 16, 0x2A4: 24})
    fp[1].update({0x1CF: 8, 0x1AA: 16, 0x35: 32, 0x175: 24, 0xA0: 24, 0xEA: 24,
                  0x1BA: 24, 0x1E5: 16, 0x36A: 16})
    fp[0][0x3A5] = 24
    self.cp = HyundaiInterface.get_params(HYUNDAI.HYUNDAI_IONIQ_6, fp, [], False, False, False)
    self.assertEqual(self.cp.safetyConfigs[0].safetyParam, 0x11)
    master = self.row("aol", "AlwaysOnLateral")
    self.assertTrue(master.available)
    self.assertEqual("Applies after the next startup", master.reason)
    self.assertFalse(self.row("wheel", "LKASButtonControl").available)
    nostalgia = self.row("wheel", "NostalgiaMode")
    self.assertTrue(nostalgia.available)
    self.assertTrue(self.owner.apply(required_change(nostalgia)))
    self.assertTrue(self.params.get_bool("NostalgiaMode"))
    self.assertTrue(self.owner.apply(required_change(master)))
    self.assertTrue(read_aol_settings(self.params).enabled)
    self.assertFalse(self.cp.openpilotLongitudinalControl)
    tagged = build_ioniq6_hda2_long_candidate(self.cp, fp)
    self.assertIsNotNone(tagged)
    self.cp = tagged
    self.assertTrue(self.row("wheel", "NostalgiaMode").available)
    tagged.safetyConfigs[0].safetyParam |= 0x800
    self.cp = tagged
    self.assertTrue(self.row("aol", "AlwaysOnLateral").available)
    self.assertFalse(self.row("wheel", "LKASButtonControl").available)

  def test_ioniq6_nostalgia_is_independent_of_aol_master_and_exact_source(self):
    fp = gen_empty_fingerprint()
    fp[2].update({0x50: 16, 0x2A4: 24})
    fp[1].update({0x1CF: 8, 0x1AA: 16, 0x35: 32, 0x175: 24, 0xA0: 24, 0xEA: 24,
                  0x1BA: 24, 0x1E5: 16, 0x36A: 16})
    fp[0][0x3A5] = 24
    stock = HyundaiInterface.get_params(HYUNDAI.HYUNDAI_IONIQ_6, fp, [], False, False, False)
    self.cp = stock
    self.assertTrue(self.row("wheel", "NostalgiaMode").available)
    tagged = build_ioniq6_hda2_long_candidate(stock, fp)
    self.assertIsNotNone(tagged)
    self.cp = tagged
    self.assertTrue(self.row("wheel", "NostalgiaMode").available)
    tagged.safetyConfigs[0].safetyParam |= 0x800
    self.cp = tagged
    row = self.row("wheel", "NostalgiaMode")
    self.assertEqual(row.value, "Off")
    self.assertTrue(row.available)
    self.assertFalse(self.params.get_bool("AlwaysOnLateral"))
    self.assertTrue(self.owner.apply(required_change(row)))
    self.assertTrue(self.params.get_bool("NostalgiaMode"))
    self.assertFalse(self.params.get_bool("AlwaysOnLateral"))
    old = self.row("wheel", "NostalgiaMode")
    self.params.put_bool("NostalgiaMode", False, block=True)
    self.assertFalse(self.owner.apply(required_change(old)))
    path = Path(self.params.get_param_path("NostalgiaMode"))
    path.write_bytes(b"01")
    repair = self.row("wheel", "NostalgiaMode")
    self.assertEqual(repair.repair_value, "Off")
    self.assertTrue(self.owner.apply(required_change(repair)))
    self.assertEqual(path.read_bytes(), b"0")
    on = required_change(self.row("wheel", "NostalgiaMode"))
    self.parked = False
    self.assertFalse(self.owner.apply(on))

  def test_aol_invalid_source_explicit_repair_and_master_guard(self):
    self.honda()
    path = Path(self.params.get_param_path("AolBrakePauseSpeedMps"))
    path.write_bytes(b"bad")
    master = self.row("aol", "AlwaysOnLateral")
    self.assertFalse(master.available)
    self.params.put_bool("AlwaysOnLateral", True, block=True)
    self.assertTrue(self.owner.apply(required_change(self.row("aol", "AlwaysOnLateral"))))
    self.assertFalse(self.params.get_bool("AlwaysOnLateral"))
    repair = self.row("aol", "AolBrakePauseSpeedMps")
    self.assertEqual(repair.repair_value, "0")
    self.assertTrue(self.owner.apply(required_change(repair)))
    self.assertEqual(self.params.get("AolBrakePauseSpeedMps"), 0.0)
    master = self.row("aol", "AlwaysOnLateral")
    self.assertTrue(self.owner.apply(required_change(master)))
    self.assertTrue(read_aol_settings(self.params).enabled)

  def test_wheel_page_moves_assignments_without_moving_feature_settings(self):
    self.honda()
    def snapshot(page):
      return self.owner.snapshot(page, parked=True, system_long=True, lateral_context=True, metric=False)
    self.assertIn("wheel", [row.page for row in snapshot("hub").rows])
    self.assertEqual({row.key for row in snapshot("aol").rows}, {"AlwaysOnLateral", "AolBrakePauseSpeedMps"})
    self.assertIn("LKASButtonControl", {row.key for row in snapshot("wheel").rows})
    self.cp = interfaces["TOYOTA_COROLLA_TSS2"].get_non_essential_params("TOYOTA_COROLLA_TSS2")
    self.assertEqual(snapshot("wheel").rows, ())

  def test_aol_button_intent_and_safety_tuple(self):
    self.honda()
    row = self.row("wheel", "LKASButtonControl")
    self.assertTrue(self.owner.apply(required_change(row)))
    self.assertEqual(read_aol_settings(self.params).lkas_action, 3)
    self.assertFalse(any(item.key == "CancelButtonControl" for item in
                         self.owner.snapshot("aol", parked=True, system_long=True, lateral_context=True, metric=False).rows))
    main = self.row("wheel", "MainCruiseButtonControl")
    self.cp.safetyConfigs[-1].safetyParam &= ~0x20
    self.assertFalse(self.owner.apply(required_change(main)))

  def test_wheel_assignment_can_be_saved_in_drive_without_enabling_aol_master(self):
    self.honda()
    self.parked = False
    self.owner = FeatureSettingsOwner(self.params, lambda group: group == "aol_wheel",
                                      vehicle_fingerprint=lambda: str(self.cp.carFingerprint), vehicle_params=lambda: self.cp)
    state = self.owner.snapshot("wheel", parked=False, system_long=False, lateral_context=False, metric=False)
    row = next(row for row in state.rows if row.key == "LKASButtonControl")
    self.assertTrue(row.available)
    request = required_change(row)
    self.assertTrue(self.owner.apply(request))
    self.assertEqual(read_aol_settings(self.params).lkas_action, 3)
    self.assertFalse(self.owner.snapshot("aol", parked=False, system_long=False,
                                         lateral_context=False, metric=False).rows[0].available)
    main = next(row for row in self.owner.snapshot("wheel", parked=False, system_long=False,
                                                  lateral_context=False, metric=False).rows if row.key == "MainCruiseButtonControl")
    self.cp.safetyConfigs[-1].safetyParam &= ~0x20
    self.assertFalse(self.owner.apply(required_change(main)))

  def test_ioniq_distance_saved_pause_reaches_only_native_acknowledged_axes(self):
    stock, long_cp = ioniq6_candidate(False)
    self.cp = stock
    self.params.put_bool("AlwaysOnLateral", True, block=True)
    self.assertFalse(self.row("wheel", "LKASButtonControl").available)
    self.assertFalse(self.row("wheel", "MainCruiseButtonControl").available)
    cases = (("DistanceButtonControl", "Pause steering", 1, (False, True), True),
             ("LongDistanceButtonControl", "Pause longitudinal", CRUISE_LONG_PRESS, (True, False), True),
             ("VeryLongDistanceButtonControl", "Pause steering", CRUISE_LONG_PRESS * 5, (False, True), True),
             ("DistanceButtonControl", "Pause steering", 1, (False, True), False))
    for key, choice, ticks, expected, aol_on in cases:
      with self.subTest(key=key, aol_on=aol_on):
        self.params.put_bool("AlwaysOnLateral", aol_on, block=True)
        row = self.row("wheel", key)
        self.assertTrue(row.available)
        self.assertEqual(row.choices, ("Off", "Pause steering", "Pause longitudinal"))
        request = FeatureSettingsRequest(key, row.source, choice, vehicle_fingerprint=row.vehicle_fingerprint,
                                         capability=row.capability, dependencies=row.dependencies)
        self.assertTrue(self.owner.apply(request))
        slot = ("DistanceButtonControl", "LongDistanceButtonControl", "VeryLongDistanceButtonControl").index(key)
        self.assertEqual(read_aol_settings(self.params).distance_actions[slot], 3 if choice == "Pause steering" else 4)
        self.cp = long_cp.as_reader().as_builder()
        self.cp.safetyConfigs[0].safetyParam |= 0x800
        self.assertTrue(qualified_ioniq6(self.cp))
        intent = AolCardIntent(read_aol_settings(self.params), explicit_latch=True)
        cs = ioniq6_state()
        intent.update(cs)
        if aol_on:
          cs.buttonEvents = [car.CarState.ButtonEvent(type=car.CarState.ButtonEvent.Type.lkas, pressed=True)]
          intent.update(cs)
          cs.buttonEvents = [car.CarState.ButtonEvent(type=car.CarState.ButtonEvent.Type.lkas, pressed=False)]
          intent.update(cs)
        cs.buttonEvents = [car.CarState.ButtonEvent(type=car.CarState.ButtonEvent.Type.gapAdjustCruise, pressed=True)]
        intent.update(cs)
        cs.buttonEvents = []
        for _ in range(ticks - 1):
          intent.update(cs)
        cs.buttonEvents = [car.CarState.ButtonEvent(type=car.CarState.ButtonEvent.Type.gapAdjustCruise, pressed=False)]
        intent.update(cs)
        latch, pause_lat, pause_long = intent.output(cs)
        self.assertEqual(latch, aol_on)
        self.assertEqual((not pause_lat, not pause_long), expected)
        wire = SimpleNamespace(allowedLatch=latch, pauseLateral=pause_lat, pauseLongitudinal=pause_long)
        def axes(native, aol_on=aol_on, wire=wire, cs=cs):
          return decide_axes(standard_lateral=not aol_on, standard_longitudinal=True, intent=wire,
                             native=native, car_state=cs, initialized=True, model_ready=True,
                             no_entry=False, immediate_disable=False, dm_lockout=False, pause_brake_mps=0.0)

        missing = axes(None)
        self.assertEqual((missing.desired_lateral, missing.desired_longitudinal), expected)
        self.assertEqual(missing.mode, "off")
        native = SimpleNamespace(requestedLateral=expected[0], requestedLongitudinal=expected[1],
                                 lateralAllowed=True, longitudinalAllowed=True)
        active = axes(native)
        self.assertEqual((active.lateral_active, active.longitudinal_active), expected)
        self.cp = stock
        reset = self.row("wheel", key)
        self.assertTrue(self.owner.apply(FeatureSettingsRequest(key, reset.source, "Off",
                                                               vehicle_fingerprint=reset.vehicle_fingerprint,
                                                               capability=reset.capability, dependencies=reset.dependencies)))

  def test_ioniq_distance_canonical_repair_and_fixed_gestures(self):
    self.cp, _ = ioniq6_candidate(False)
    key = "DistanceButtonControl"
    row = self.row("wheel", key)
    for fixed in ("LKASButtonControl", "MainCruiseButtonControl"):
      blocked = self.row("wheel", fixed)
      self.assertEqual(blocked.value, "Toggle Always On Lateral")
      self.assertEqual(blocked.choices, ())
      self.assertFalse(blocked.available)
      request = FeatureSettingsRequest(fixed, blocked.source, "Pause steering",
                                       vehicle_fingerprint=blocked.vehicle_fingerprint,
                                       capability=blocked.capability, dependencies=blocked.dependencies)
      self.assertFalse(self.owner.apply(request))
    self.assertFalse(self.owner.apply(FeatureSettingsRequest(key, row.source, "Toggle AOL",
                                                             vehicle_fingerprint=row.vehicle_fingerprint,
                                                             capability=row.capability, dependencies=row.dependencies)))
    for raw, label in ((b"5", "Conditional mode assignment"), (b"03", "Unsupported saved action")):
      Path(self.params.get_param_path(key)).write_bytes(raw)
      row = self.row("wheel", key)
      self.assertEqual(row.value, label)
      self.assertEqual(row.repair_value, "Off")
      request = FeatureSettingsRequest(key, row.source, "Pause steering",
                                       vehicle_fingerprint=row.vehicle_fingerprint,
                                       capability=row.capability, dependencies=row.dependencies)
      self.assertFalse(self.owner.apply(request))
      self.assertEqual(Path(self.params.get_param_path(key)).read_bytes(), raw)
      self.assertTrue(self.owner.apply(required_change(row)))
      self.assertEqual(Path(self.params.get_param_path(key)).read_bytes(), b"0")

  def test_honda_distance_toggle_remains_editable_and_ioniq_stage_revokes(self):
    self.honda()
    key = "DistanceButtonControl"
    self.params.put(key, 9, block=True)
    row = self.row("wheel", key)
    self.assertEqual(row.value, "Toggle AOL")
    self.assertTrue(self.owner.apply(FeatureSettingsRequest(key, row.source, "Pause steering",
                                                            vehicle_fingerprint=row.vehicle_fingerprint,
                                                            capability=row.capability, dependencies=row.dependencies)))
    self.assertEqual(Path(self.params.get_param_path(key)).read_bytes(), b"3")
    stock, long_cp = ioniq6_candidate(False)
    from openpilot.starpilot import saved_document
    actual_fsync = saved_document.os.fsync
    source = Path(self.params.get_param_path(key))
    master = Path(self.params.get_param_path("AlwaysOnLateral"))
    for change, expected in (("parked", b"0"), ("dependency", b"0"),
                             ("source", b"4"), ("capability", b"0")):
      with self.subTest(change=change):
        self.cp = stock
        self.parked = True
        master.unlink(missing_ok=True)
        source.write_bytes(b"0")
        row = self.row("wheel", key)
        request = required_change(row)
        called = False

        def revoke_after_stage(fd, change=change):
          nonlocal called
          result = actual_fsync(fd)
          if not called:
            called = True
            if change == "parked":
              self.parked = False
            elif change == "dependency":
              master.write_bytes(b"1")
            elif change == "source":
              source.write_bytes(b"4")
            else:
              self.cp = long_cp
          return result

        with patch.object(saved_document.os, "fsync", side_effect=revoke_after_stage):
          self.assertFalse(self.owner.apply(request))
        self.assertTrue(called)
        self.assertEqual(source.read_bytes(), expected)

  def test_native_large_and_compact_child_actions(self):
    hub = self.owner.snapshot("hub", parked=True, system_long=True, lateral_context=True, metric=False)
    actions = []
    control = FeatureInput(actions.append)
    torque_index = next(i for i, row in enumerate(hub.rows) if row.page == "torque")
    control.press(650, 135 + torque_index * 104, hub)
    control.release(650, 135 + torque_index * 104, hub)
    self.assertEqual(actions[0].row.page, "torque")
    torque_page = self.owner.snapshot("torque", parked=True, system_long=True, lateral_context=True, metric=False)
    adopt_index = next(i for i, row in enumerate(torque_page.rows) if row.key == "torque_adopt")
    control.press(1900, 135 + adopt_index * 104, torque_page)
    control.release(1900, 135 + adopt_index * 104, torque_page)
    self.assertEqual((actions[-1].kind, actions[-1].row.key), ("reset", "torque_adopt"))

    class Button:
      def __init__(self, text, value):
        self.text, self.value, self.click = text, value, None

      def set_click_callback(self, callback):
        self.click = callback

      def set_enabled(self, enabled):
        self.enabled = enabled

    class ReadButton(Button):
      pass

    class Dialog:
      def __init__(self, text, texture, confirmed, red=False):
        self.text, self.confirmed = text, confirmed

    class Scroller:
      def __init__(self):
        self.items = []
        self._scroller = self

      def add_widgets(self, items):
        self.items.extend(items)

    class Session:
      def __init__(self, owner):
        self.owner = owner

      def feature_snapshot(self, page):
        return self.owner.snapshot(page, parked=True, system_long=True, lateral_context=True, metric=False)

      def feature_request(self, request):
        return self.owner.apply(request)

    pushed = []
    adapter = compact.FeatureSettingsCompact(Session(self.owner))
    with patch.object(compact, "BigButton", Button), patch.object(compact, "GreyBigButton", ReadButton), \
         patch.object(compact, "NavScroller", Scroller), patch.object(compact, "BigConfirmationDialog", Dialog), \
         patch.object(compact.gui_app, "texture", lambda *_args: None), \
         patch.object(compact.gui_app, "push_widget", pushed.append):
      adapter.open("torque")
      page = pushed[-1]
      self.assertIsInstance(next(item for item in page.items if item.text == "automatic torque learning"), ReadButton)
      next(item for item in page.items if item.text == "manual torque adjustments").click()
      self.assertIsInstance(next(item for item in page.items if item.text == "automatic torque learning"), ReadButton)
      next(item for item in page.items if item.text == "torque controller").click()
      self.assertNotIsInstance(next(item for item in page.items if item.text == "automatic torque learning"), ReadButton)
      page = pushed[-1]
      next(item for item in page.items if item.text == "use new torque editor").click()
      self.assertIsInstance(pushed[-1], Dialog)
      pushed[-1].confirmed()
      self.assertTrue(any(item.text == "lateral acceleration source" for item in page.items))
      next(item for item in page.items if item.text == "lateral acceleration source").click()
      self.assertTrue(any(item.text == "lateral acceleration custom +" for item in page.items))
      next(item for item in page.items if item.text == "lateral acceleration custom +").click()
      self.assertEqual(parse_document(Path(self.params.get_param_path(DOCUMENT_KEY)).read_bytes())
                       [str(self.cp.carFingerprint)].factor.mode, "custom")
      self.honda()
      adapter.open("aol")
      page = pushed[-1]
      next(item for item in page.items if item.text == "brake pause below +").click()
      self.assertAlmostEqual(read_aol_settings(self.params).pause_brake_mps, 0.44704)
      adapter.open("wheel")
      page = pushed[-1]
      next(item for item in page.items if item.text == "lkas press").click()
      self.assertEqual(read_aol_settings(self.params).lkas_action, 3)
      Path(self.params.get_param_path("AolBrakePauseSpeedMps")).write_bytes(b"bad")
      Path(self.params.get_param_path("LKASButtonControl")).write_bytes(b"\xff")
      adapter.open("aol")
      self.assertTrue(any(item.text == "brake pause below set 0" for item in pushed[-1].items))
      adapter.open("wheel")
      self.assertTrue(any(item.text == "lkas press set off" for item in pushed[-1].items))

  def test_large_repair_labels_match_requested_values(self):
    class Fonts(BitmapFonts):
      profile = Profile.LARGE

      def __init__(self):
        self.text = []

      def draw(self, value, *args, **kwargs):
        self.text.append(value)

    fonts = Fonts()
    state = FeatureSettingsState(rows=(
      FeatureRow("AolBrakePauseSpeedMps", "Brake pause below", "Invalid", available=True, repair_value="0"),
      FeatureRow("LKASButtonControl", "LKAS press", "Unsupported", available=True, repair_value="Off"),
    ))
    with patch.object(large.rl, "draw_rectangle_rounded"), patch.object(large.clip, "begin_scissor_mode"), \
         patch.object(large.clip, "end_scissor_mode"):
      large.FeatureSettingsView(fonts).render(state)
    self.assertIn("Set 0", fonts.text)
    self.assertIn("Set Off", fonts.text)

  def test_starpilot_tuning_help_is_visible_in_large_native_settings(self):
    class Fonts:
      profile = Profile.LARGE

      def __init__(self):
        self.text = []

      def draw(self, value, *args, **kwargs):
        self.text.append(value)

    fonts = Fonts()
    state = self.owner.snapshot("torque", parked=True, system_long=True, lateral_context=True, metric=False)
    with patch.object(large.rl, "draw_rectangle_rounded"), patch.object(large.clip, "begin_scissor_mode"), \
         patch.object(large.clip, "end_scissor_mode"):
      large.FeatureSettingsView(fonts).render(state)
    self.assertIn("Need Help With Steering?", fonts.text)
    self.assertTrue(any("Discord: https://firestar.link/discord" in text for text in fonts.text))
    self.assertTrue(self.owner.apply(required_change(self.row("torque", "LateralControllerSelection"))))
    standard = self.owner.snapshot("torque", parked=True, system_long=True, lateral_context=True, metric=False)
    self.assertFalse(any(row.label == "Need Help With Steering?" for row in standard.rows))


if __name__ == "__main__":
  unittest.main()
