"""SLC coast vectors and composition with the actual native MPC."""

import unittest
from unittest.mock import Mock, patch
import shutil
import tempfile

from openpilot.cereal import log
from openpilot.common.params import Params
from openpilot.selfdrive.controls.lib import longitudinal_planner as planner_module
from openpilot.selfdrive.controls.lib.longitudinal_planner import LongitudinalPlanner
from openpilot.starpilot.longitudinal.cruise_ceiling import CruiseCeiling
from openpilot.starpilot.longitudinal.slc_coast import braking_lead_relevant, slc_coast_floor
from openpilot.starpilot.longitudinal.profile_document import default_personality_profiles, profile_document
from openpilot.starpilot.longitudinal.profile_runtime import read_settings, resolve
from openpilot.starpilot.longitudinal.profile_runtime import ProfileSmoother, ProfileTuning
from openpilot.starpilot.longitudinal.tests.test_cruise_ceiling import ACTIVE, V_EGO, messages
from opendbc.car.honda.interface import CarInterface
from opendbc.car.honda.values import CAR


class SlcCoastTests(unittest.TestCase):
  def test_frozen_standard_profile_vectors(self):
    # Frozen StarPilot's standard SLC coast window/excess interpolation.
    for ego, target, expected in ((5.0, 4.8, -0.03), (10.0, 9.7, -0.03),
                                  (10.0, 9.0, -0.2448979591836735),
                                  (20.0, 18.0, -0.2925207756232687), (35.0, 29.5, -1.2)):
      with self.subTest(ego=ego, target=target):
        actual = slc_coast_floor(v_ego=ego, slc_target=target, driver_cruise=40.0,
                                 full_brake_floor=-1.2, relevant_lead=False, stop_context=False)
        self.assertIsNotNone(actual)
        if actual is None:
          self.fail("Expected a qualified coast floor")
        self.assertAlmostEqual(actual, expected)

  def test_frozen_named_braking_profile_vectors(self):
    for style, expected in (('eco', -0.20312213039485763), ('standard', -0.2448979591836735),
                            ('sport', -0.2926222222222221)):
      with self.subTest(style=style):
        actual = slc_coast_floor(v_ego=10.0, slc_target=9.0, driver_cruise=20.0,
                                 full_brake_floor=-1.2, relevant_lead=False, stop_context=False,
                                 braking_style=style)
        self.assertIsNotNone(actual)
        if actual is None:
          self.fail("Expected a qualified coast floor")
        self.assertAlmostEqual(actual, expected)

  def test_unqualified_or_hazard_context_never_shapes(self):
    for ego, target, lead, stop in ((20.0, None, False, False), (20.0, 27.0, False, False),
                                    (4.0, 19.0, False, False), (20.0, 19.0, True, False),
                                    (20.0, 19.0, False, True), (float('nan'), 19.0, False, False)):
      with self.subTest(ego=ego, target=target, lead=lead, stop=stop):
        self.assertIsNone(slc_coast_floor(v_ego=ego, slc_target=target, driver_cruise=27.0,
                                          full_brake_floor=-1.2, relevant_lead=lead, stop_context=stop))
    malformed = Mock(wraps=slc_coast_floor)
    self.assertIsNone(malformed(v_ego=20.0, slc_target=19.0, driver_cruise=27.0,
                                full_brake_floor=-1.2, relevant_lead=False, stop_context=False,
                                braking_style=[]))
    malformed.assert_called_once()

  def test_malformed_lead_is_conservative(self):
    class Lead:
      present = True
      vLead = float('nan')
      aLeadK = 0.0
      dRel = 100.0

    self.assertTrue(braking_lead_relevant(Lead(), 20.0))

  def test_native_planner_only_shapes_qualified_cruise_candidate(self):
    cp = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
    for case in ('qualified', 'absent', 'lead', 'force', 'traffic', 'lateral_only', 'experimental'):
      with self.subTest(case=case):
        shaped = LongitudinalPlanner(cp, init_v=V_EGO)
        with patch.object(planner_module, 'get_cruise_accel', wraps=planner_module.get_cruise_accel) as cruise:
          for _ in range(65):
            sm, _ = messages(lead=case == 'lead', force=case == 'force', e2e=case == 'experimental')
            sm['carControl'].longActive = case != 'lateral_only'
            shaped.update(sm, cruise_ceiling=CruiseCeiling(19.0, ACTIVE) if case != 'absent' else None,
                          traffic_mode=case == 'traffic')
            self.assertEqual(shaped.mpc.solution_status, 0)
          floor = cruise.call_args.args[-1]
        # The shaped path's cruise floor remains a preference: the MPC lead and
        # force-deceleration paths have their own lower acceleration authority.
        if case == 'qualified':
          self.assertGreater(floor, -1.2)
          self.assertGreater(shaped.a_cruise, -1.2)
        elif case == 'lead':
          self.assertIsNone(floor)
          self.assertLess(shaped.output_a_target, shaped.a_cruise)
        elif case == 'force':
          self.assertIsNone(floor)
          self.assertEqual(shaped.last_cruise_ceiling_status, 'force_decel')
        else:
          self.assertIsNone(floor)

  def test_same_slc_ceiling_with_coast_shape_changes_only_cruise_preference(self):
    cp = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
    ordinary = LongitudinalPlanner(cp, init_v=V_EGO)
    shaped = LongitudinalPlanner(cp, init_v=V_EGO)
    ceiling = CruiseCeiling(19.0, ACTIVE)
    for _ in range(65):
      sm, _ = messages()
      sm['carControl'].longActive = True
      with patch.object(planner_module, 'slc_coast_floor', return_value=None):
        ordinary.update(sm, cruise_ceiling=ceiling)
      shaped.update(sm, cruise_ceiling=ceiling)
      self.assertEqual(ordinary.mpc.solution_status, shaped.mpc.solution_status)
    self.assertGreater(shaped.a_cruise, ordinary.a_cruise)
    self.assertAlmostEqual(shaped.mpc.params[0, 4], ordinary.mpc.params[0, 4])
    self.assertEqual(shaped.output_should_stop, ordinary.output_should_stop)

  def test_saved_eco_and_sport_compose_with_real_planner_only_under_slc(self):
    root = tempfile.mkdtemp(prefix='slc-coast-profile-')
    self.addCleanup(shutil.rmtree, root, ignore_errors=True)
    params = Params(root)
    params.put_bool('CustomPersonalities', True, block=True)
    params.put_bool('StandardPersonalityProfile', True, block=True)
    cp = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
    results = {}
    for style in ('eco', 'sport'):
      profiles = default_personality_profiles(False)
      profiles['standard']['braking'] = {'preset': style, 'curve': []}
      params.put('LongitudinalPersonalityProfiles', profile_document(profiles, enabled=True), block=True)
      tuning = resolve(read_settings(params), log.LongitudinalPersonality.standard, V_EGO, cp)
      self.assertEqual(tuning.slc_braking_style, style)
      for accepted in (True, False):
        planner = LongitudinalPlanner(cp, init_v=V_EGO)
        with patch.object(planner_module, 'slc_coast_floor', wraps=planner_module.slc_coast_floor) as coast:
          for _ in range(65):
            sm, _ = messages()
            sm['carControl'].longActive = True
            planner.update(sm, cruise_ceiling=CruiseCeiling(19.0, ACTIVE) if accepted else None,
                           profile_tuning=tuning)
            self.assertEqual(planner.mpc.solution_status, 0)
        self.assertEqual(coast.call_args.kwargs['braking_style'], style)
        results[(style, accepted)] = planner.a_cruise
    self.assertGreater(results['eco', True], results['sport', True])
    self.assertAlmostEqual(results['eco', False], results['sport', False])

    # A disappearing cap or a braking lead immediately revokes the coast
    # preference without clearing the driver's saved named profile.
    planner = LongitudinalPlanner(cp, init_v=V_EGO)
    for lead, cap in ((False, CruiseCeiling(19.0, ACTIVE)), (False, None),
                      (True, CruiseCeiling(19.0, ACTIVE))):
      sm, _ = messages(lead=lead)
      sm['carControl'].longActive = True
      with patch.object(planner_module, 'slc_coast_floor', wraps=planner_module.slc_coast_floor) as coast:
        planner.update(sm, cruise_ceiling=cap, profile_tuning=tuning)
      self.assertEqual(coast.call_args.kwargs['slc_target'], 19.0 if cap is not None else None)
      if lead:
        self.assertTrue(coast.call_args.kwargs['relevant_lead'])
        self.assertLess(planner.output_a_target, planner.a_cruise)

  def test_invalid_style_does_not_survive_profile_validation(self):
    smoother = ProfileSmoother()
    target = ProfileTuning('standard', 1.45, 1.0, 1.0, 1.0, 1.0, 1.0, slc_braking_style='eco')
    self.assertIsNotNone(smoother.sample(target, log.LongitudinalPersonality.standard, 0.05))
    self.assertEqual(smoother.slc_braking_style, 'eco')
    invalid = ProfileTuning('standard', 1.45, 1.0, 1.0, 1.0, 1.0, 1.0, slc_braking_style='unknown')
    smoother.sample(invalid, log.LongitudinalPersonality.standard, 0.05)
    self.assertEqual(smoother.slc_braking_style, 'standard')
    smoother.sample(target, log.LongitudinalPersonality.standard, 0.05)
    self.assertEqual(smoother.slc_braking_style, 'eco')
    smoother.sample(None, log.LongitudinalPersonality.standard, 0.05)
    self.assertEqual(smoother.slc_braking_style, 'standard')
    smoother.sample(target, log.LongitudinalPersonality.standard, 0.05)
    smoother.sample(None, log.LongitudinalPersonality.standard, 0.05, traffic_mode=None)
    self.assertEqual(smoother.slc_braking_style, 'standard')


if __name__ == '__main__':
  unittest.main()
