"""Parked exact-source edits for host-only cruise intervals."""

from dataclasses import replace
from types import SimpleNamespace
import tempfile
import unittest

from openpilot.common.params import Params
from openpilot.starpilot.galaxy.settings import AuthorityContext, SettingsChanged, SettingsGateway
from openpilot.starpilot.longitudinal.cruise_intervals import CruiseIntervals, read_cruise_intervals
from openpilot.starpilot.ui.feature_settings_owner import FeatureSettingsOwner
from openpilot.starpilot.ui.feature_settings_state import FeaturePage, row_change


class Context:
  def __init__(self, cp):
    self.value = AuthorityContext(True, cp, b"cp-source")

  def sample(self):
    return self.value


class CruiseIntervalFeatureTests(unittest.TestCase):
  def setUp(self):
    temp = tempfile.TemporaryDirectory()
    self.addCleanup(temp.cleanup)
    self.params = Params(temp.name)
    self.cp = SimpleNamespace(carFingerprint="HYUNDAI_IONIQ_6", openpilotLongitudinalControl=True,
                              pcmCruise=False, notCar=False, passive=False, dashcamOnly=False)
    self.context = Context(self.cp)
    self.owner = FeatureSettingsOwner(self.params, lambda group: self.context.value.parked and group == "long",
                                      vehicle_fingerprint=lambda: self.context.value.cp.carFingerprint,
                                      vehicle_params=lambda: self.context.value.cp, show_cruise_intervals=True)
    self.gateway = SettingsGateway(self.params, self.context, clock=lambda: 100.0)

  def rows(self):
    state = self.owner.snapshot(FeaturePage.PROFILES, parked=self.context.value.parked, system_long=True,
                                lateral_context=False, metric=False)
    return {row.key: row for row in state.rows if row.key in ("QOLLongitudinal", "CustomCruise", "CustomCruiseLong")}

  @staticmethod
  def change(row, direction=1):
    request = row_change(row, direction)
    assert request is not None
    return replace(request, confirmation=True)

  def test_galaxy_toggle_and_child_readback(self):
    native = FeatureSettingsOwner(self.params, lambda group: self.context.value.parked and group == "long",
                                  vehicle_fingerprint=lambda: self.cp.carFingerprint, vehicle_params=lambda: self.cp)
    native_rows = native.snapshot(FeaturePage.PROFILES, parked=True, system_long=True,
                                  lateral_context=False, metric=False).rows
    self.assertFalse(any(row.key in ("QOLLongitudinal", "CustomCruise", "CustomCruiseLong") for row in native_rows))
    self.params.put("CustomCruise", 5.0, block=True)
    self.params.put("CustomCruiseLong", 1.0, block=True)
    page = self.gateway.page("profiles", "session", b"generation")
    rows = {row["label"]: (index, row) for index, row in enumerate(page["rows"])}
    self.assertEqual(rows["Custom cruise intervals"][1]["value"], "Off")
    self.assertFalse(rows["Short press"][1]["available"])
    self.assertFalse(rows["Hold"][1]["available"])
    intent = self.gateway.preview(page["view"], rows["Custom cruise intervals"][0], 1, "session", b"generation")
    self.assertIn("next drive when StarPilot controls cruise speed", intent["question"])
    self.assertTrue(self.gateway.confirm(intent["intent"], "session", b"generation"))
    self.assertEqual(read_cruise_intervals(self.params, pcm_cruise=False), CruiseIntervals(5, 1))
    with self.assertRaises(SettingsChanged):
      self.gateway.preview(page["view"], rows["Short press"][0], 1, "session", b"generation")
    fresh = self.gateway.page("profiles", "session", b"generation")
    fresh_rows = {row["label"]: (index, row) for index, row in enumerate(fresh["rows"])}
    self.assertTrue(fresh_rows["Short press"][1]["available"])
    self.assertEqual(fresh_rows["Hold"][1]["value"], "1")
    edit = self.gateway.preview(fresh["view"], fresh_rows["Short press"][0], 1, "session", b"generation")
    self.assertTrue(self.gateway.confirm(edit["intent"], "session", b"generation"))
    self.assertEqual(read_cruise_intervals(self.params, pcm_cruise=False), CruiseIntervals(6, 1))

  def test_pcm_and_changed_vehicle_block_both_parent_and_children(self):
    master = self.change(self.rows()["QOLLongitudinal"])
    self.cp.pcmCruise = True
    self.assertFalse(self.owner.apply(master))
    self.assertFalse(any(row.available for row in self.rows().values()))
    self.cp.pcmCruise = False
    self.assertTrue(self.owner.apply(self.change(self.rows()["QOLLongitudinal"])))
    child = self.change(self.rows()["CustomCruise"])
    self.cp.pcmCruise = True
    self.assertFalse(self.owner.apply(child))
    self.assertEqual(read_cruise_intervals(self.params, pcm_cruise=True), CruiseIntervals())

  def test_stale_parent_units_source_and_parked_rejected(self):
    self.assertTrue(self.owner.apply(self.change(self.rows()["QOLLongitudinal"])))
    short = self.change(self.rows()["CustomCruise"])
    self.params.put_bool("IsMetric", True, block=True)
    self.assertFalse(self.owner.apply(short))
    metric = self.rows()["CustomCruise"]
    self.assertEqual(metric.unit, "km/h")
    self.assertTrue(self.owner.apply(self.change(metric)))
    stale = self.change(self.rows()["CustomCruise"])
    self.params.put_bool("QOLLongitudinal", False, block=True)
    self.assertFalse(self.owner.apply(stale))
    master = self.change(self.rows()["QOLLongitudinal"])
    self.context.value = AuthorityContext(False, self.cp, b"cp-source")
    self.assertFalse(self.owner.apply(master))

  def test_numeric_bounds_rejected(self):
    self.assertTrue(self.owner.apply(self.change(self.rows()["QOLLongitudinal"])))
    short = self.change(self.rows()["CustomCruise"])
    self.assertFalse(self.owner.apply(replace(short, value="151")))
    self.assertFalse(self.owner.apply(replace(short, value="nan")))
    self.assertEqual(read_cruise_intervals(self.params, pcm_cruise=False), CruiseIntervals())
