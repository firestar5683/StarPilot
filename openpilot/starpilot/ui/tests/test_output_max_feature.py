"""Shared numeric owner and Galaxy onroad exact-source acceleration edits."""

from dataclasses import replace
from pathlib import Path
import tempfile
import unittest

from opendbc.car.honda.interface import CarInterface
from opendbc.car.honda.values import CAR
from openpilot.common.params import Params
from openpilot.starpilot.galaxy.settings import AuthorityContext, SettingsChanged, SettingsGateway
from openpilot.starpilot.longitudinal.output_max import KEY
from openpilot.starpilot.ui.feature_settings_owner import FeatureSettingsOwner
from openpilot.starpilot.ui.feature_settings_state import FeatureRow, FeatureSettingsRequest, row_change



def required_change(row: FeatureRow, direction: int = 1) -> FeatureSettingsRequest:
  request = row_change(row, direction)
  assert request is not None
  return request


class Context:
  def __init__(self, cp):
    self.value = AuthorityContext(False, cp, b"current-cp")

  def sample(self):
    return self.value


class OutputMaximumFeatureTests(unittest.TestCase):
  def setUp(self):
    temporary = tempfile.TemporaryDirectory()
    self.addCleanup(temporary.cleanup)
    self.params = Params(temporary.name)
    self.cp = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
    self.context = Context(self.cp)
    self.gateway = SettingsGateway(self.params, self.context, clock=lambda: 10.)
    self.owner = FeatureSettingsOwner(self.params, lambda group: group == "long_output",
                                      vehicle_fingerprint=lambda: self.cp.carFingerprint, vehicle_params=lambda: self.cp)

  def page(self):
    page = self.gateway.page("profiles", "session", b"generation")
    index = next(index for index, row in enumerate(page['rows']) if row['label'] == "Maximum acceleration")
    return page, index

  def test_onroad_galaxy_and_native_share_scalar_independent_of_personalities(self):
    self.params.put_bool("CustomPersonalities", False, block=True)
    Path(self.params.get_param_path("LongitudinalPersonalityProfiles")).write_bytes(b"{invalid")
    self.assertTrue(self.cp.openpilotLongitudinalControl and self.cp.pcmCruise)
    page, index = self.page()
    self.assertTrue(page['rows'][index]['available'])
    intent = self.gateway.preview(page['view'], index, 0, "session", b"generation", value=.6)
    self.assertTrue(self.gateway.confirm(intent['intent'], "session", b"generation"))
    row = next(row for row in self.owner.snapshot("profiles", parked=False, system_long=False,
                                                lateral_context=False, metric=False).rows if row.key == KEY)
    self.assertEqual(float(row.value), .6)
    request = required_change(row, -1)
    self.assertTrue(self.owner.apply(request))
    self.assertEqual(float(Path(self.params.get_param_path(KEY)).read_bytes()), .5)
    self.assertFalse(self.params.get_bool("CustomPersonalities"))
    self.assertEqual(Path(self.params.get_param_path("LongitudinalPersonalityProfiles")).read_bytes(), b"{invalid")

  def test_source_cp_session_revocation_and_invalid_value_repair(self):
    path = Path(self.params.get_param_path(KEY))
    row = self.owner.output_maximum.row()
    request = required_change(row, -1)
    for field, value in (("passive", True), ("dashcamOnly", True), ("notCar", True), ("openpilotLongitudinalControl", False)):
      previous = getattr(self.cp, field)
      setattr(self.cp, field, value)
      self.assertFalse(self.owner.apply(request))
      setattr(self.cp, field, previous)
    path.write_bytes(b"1.0")
    self.assertFalse(self.owner.apply(request))
    for value in ("nan", "inf", "0.01", "4.1"):
      request = required_change(self.owner.output_maximum.row())
      assert request is not None
      self.assertFalse(self.owner.apply(replace(request, value=value)))
    page, index = self.page()
    intent = self.gateway.preview(page['view'], index, 0, "session", b"generation", value=.7)
    with self.assertRaises(SettingsChanged):
      self.gateway.confirm(intent['intent'], "session", b"generation", session_valid=lambda: False)
    page, index = self.page()
    intent = self.gateway.preview(page['view'], index, 0, "session", b"generation", value=.7)
    self.context.value = replace(self.context.value, cp_raw=b"changed-cp")
    with self.assertRaises(SettingsChanged):
      self.gateway.confirm(intent['intent'], "session", b"generation")
    path.write_bytes(b"broken")
    repair = required_change(self.owner.output_maximum.row())
    self.assertEqual(repair.value, "4.0")
    self.assertTrue(self.owner.apply(repair))
    self.assertEqual(float(path.read_bytes()), 4.0)

  def test_parked_desk_and_invalid_cp_configure_global_but_intent_cannot_cross_onroad(self):
    desk = FeatureSettingsOwner(self.params,
                                lambda group: self.context.value.parked if group == "parked_preferences" else group == "long_output",
                                vehicle_fingerprint=lambda: getattr(self.context.value.cp, "carFingerprint", None),
                                vehicle_params=lambda: self.context.value.cp)
    path = Path(self.params.get_param_path(KEY))
    self.cp.passive = True
    for cp in (None, self.cp):
      self.context.value = AuthorityContext(True, cp, b"desk-cp")
      row = next(row for row in desk.snapshot("profiles", parked=True, system_long=False,
                                              lateral_context=False, metric=False).rows if row.key == KEY)
      self.assertTrue(row.available)
      self.assertIsNone(row.capability)
      self.assertIsNone(row.vehicle_fingerprint)
      self.assertTrue(desk.apply(required_change(row, -1)))
      page, index = self.page()
      self.assertTrue(page['rows'][index]['available'])
      intent = self.gateway.preview(page['view'], index, 0, "session", b"generation", value=.8)
      self.assertTrue(self.gateway.confirm(intent['intent'], "session", b"generation"))
    parked_request = required_change(desk.output_maximum.row(), 1)
    page, index = self.page()
    pending = self.gateway.preview(page['view'], index, 0, "session", b"generation", value=.9)
    self.cp.passive = False
    self.context.value = AuthorityContext(False, self.cp, b"desk-cp")
    before = path.read_bytes()
    self.assertFalse(desk.apply(parked_request))
    self.assertFalse(self.gateway.confirm(pending['intent'], "session", b"generation"))
    self.assertEqual(path.read_bytes(), before)
    onroad = desk.output_maximum.row()
    self.assertIsNotNone(onroad.capability)
    self.assertTrue(desk.apply(required_change(onroad, 1)))
