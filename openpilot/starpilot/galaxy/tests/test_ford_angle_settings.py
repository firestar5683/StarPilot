"""One typed Ford choice through the real Galaxy shared settings owner."""
from pathlib import Path
import tempfile
import unittest

from openpilot.common.params import Params
from openpilot.starpilot.galaxy.settings import AuthorityContext, SettingsChanged, SettingsGateway
from openpilot.starpilot.ui.feature_settings_owner import FeatureSettingsOwner
from opendbc.car.ford.tests.test_three_ports import params as ford_params
from opendbc.car.ford.values import CAR
from opendbc.bluepilot_lateral.hosts.starpilot import CLASSIC, CANFD, select


class FordContext:
  def __init__(self, owner):
    self.owner = owner

  def sample(self) -> AuthorityContext:
    return AuthorityContext(self.owner.parked, self.owner.cp, self.owner.cp.as_reader().as_builder().to_bytes())


class TestFordAngleSettings(unittest.TestCase):
  def setUp(self):
    temporary = tempfile.TemporaryDirectory()
    self.addCleanup(temporary.cleanup)
    self.params = Params(temporary.name)
    self.params.put_bool("SafeMode", False, block=True)
    self.params.put_bool("AlwaysOnLateral", False, block=True)
    self.cp = ford_params(CAR.FORD_BRONCO_SPORT_MK1)
    self.parked = True
    self.context = FordContext(self)
    self.gateway = SettingsGateway(self.params, self.context)
    self.addCleanup(self.gateway.close)

  def page(self):
    return self.gateway.page("torque", "ford-session", b"ford-generation")

  def row(self, page):
    rows = [(i, r) for i, r in enumerate(page["rows"]) if r["label"] == "Ford steering controller"]
    self.assertEqual(len(rows), 1)
    return rows[0]

  def choose(self, label):
    page = self.page()
    index, row = self.row(page)
    self.assertTrue(row["available"])
    intent = self.gateway.preview(page["view"], index, 0, "ford-session", b"ford-generation", value=label)
    return self.gateway.confirm(intent["intent"], "ford-session", b"ford-generation")

  def test_actual_final_profiles_one_dropdown_and_typed_explicit_persistence(self):
    for identity in sorted(CLASSIC | CANFD):
      for already_selected in (False, True):
        self.cp = ford_params(identity)
        if already_selected:
          self.assertTrue(select(self.cp, 1))
        page = self.page()
        _, row = self.row(page)
        self.assertEqual(row["choices"], ["Current curvature", "BluePilot angle"])
        self.choose("BluePilot angle")
        self.assertEqual(self.params.get("FordLateralMode"), 1)
        self.assertEqual(Path(self.params.get_param_path("FordLateralMode")).read_bytes(), b"1")
        self.choose("Current curvature")
        self.assertEqual(self.params.get("FordLateralMode"), 0)
    owner = FeatureSettingsOwner(self.params, lambda _: True, vehicle_fingerprint=lambda: self.cp.carFingerprint,
                                 vehicle_params=lambda: self.cp)
    rows = owner.snapshot("torque", parked=True, system_long=False, lateral_context=True, metric=False).rows
    self.assertEqual(sum(r.key == "FordLateralMode" for r in rows), 1)

  def test_excluded_or_modified_final_capability_has_no_angle_row(self):
    for identity in (CAR.FORD_EDGE_MK2, CAR.FORD_MONDEO_MK5, CAR.FORD_TRANSIT_MK5):
      self.cp = ford_params(identity)
      self.assertFalse(any(r["label"] == "Ford steering controller" for r in self.page()["rows"]))
    for field, value in (("alternativeExperience", 32), ("passive", True), ("dashcamOnly", True), ("notCar", True)):
      self.cp = ford_params(CAR.FORD_BRONCO_SPORT_MK1)
      setattr(self.cp, field, value)
      self.assertFalse(any(r["label"] == "Ford steering controller" for r in self.page()["rows"]))
    self.cp = ford_params(CAR.FORD_BRONCO_SPORT_MK1)
    self.cp.safetyConfigs[-1].safetyParam = 0
    self.assertFalse(any(r["label"] == "Ford steering controller" for r in self.page()["rows"]))

  def test_stale_expected_dependency_vehicle_and_parked_changes_deny_commit(self):
    for change in ("saved", "safe", "aol", "vehicle", "parked"):
      self.cp = ford_params(CAR.FORD_BRONCO_SPORT_MK1)
      self.parked = True
      self.params.put("FordLateralMode", 0, block=True)
      self.params.put_bool("SafeMode", False, block=True)
      self.params.put_bool("AlwaysOnLateral", False, block=True)
      page = self.page()
      index, _ = self.row(page)
      intent = self.gateway.preview(page["view"], index, 0, "ford-session", b"ford-generation", value="BluePilot angle")
      if change == "saved":
        Path(self.params.get_param_path("FordLateralMode")).write_bytes(b"invalid")
      elif change in ("safe", "aol"):
        self.params.put_bool("SafeMode" if change == "safe" else "AlwaysOnLateral", True, block=True)
      elif change == "vehicle":
        self.cp.safetyConfigs[-1].safetyParam = 128
      else:
        self.parked = False
      if change == "vehicle":
        with self.assertRaises(SettingsChanged):
          self.gateway.confirm(intent["intent"], "ford-session", b"ford-generation")
      else:
        self.assertFalse(self.gateway.confirm(intent["intent"], "ford-session", b"ford-generation"))
      self.assertEqual(Path(self.params.get_param_path("FordLateralMode")).read_bytes(), b"invalid" if change == "saved" else b"0")
      with self.assertRaises(SettingsChanged):
        self.gateway.confirm(intent["intent"], "ford-session", b"ford-generation")

  def test_invalid_saved_choice_can_only_repair_to_current_curvature(self):
    path = Path(self.params.get_param_path("FordLateralMode"))
    path.write_bytes(b"2")
    page = self.page()
    index, row = self.row(page)
    self.assertEqual(row["value"], "Invalid saved choice")
    with self.assertRaises(SettingsChanged):
      self.gateway.preview(page["view"], index, 0, "ford-session", b"ford-generation", value="BluePilot angle")
    intent = self.gateway.preview(page["view"], index, 0, "ford-session", b"ford-generation", reset_default=True)
    self.gateway.confirm(intent["intent"], "ford-session", b"ford-generation")
    self.assertEqual(path.read_bytes(), b"0")
