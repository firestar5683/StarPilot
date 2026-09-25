"""The saved global braking response changes only the qualified cruise candidate."""

import unittest
from unittest.mock import patch

from openpilot.selfdrive.controls.lib import longitudinal_planner as planner_module
from openpilot.selfdrive.controls.lib.longitudinal_planner import LongitudinalPlanner
from openpilot.selfdrive.controls.plannerd import update_curve_frame
from openpilot.starpilot.longitudinal.cruise_ceiling import CruiseCeiling
from openpilot.starpilot.longitudinal.profile_runtime import ProfileTuning
from openpilot.starpilot.longitudinal.tests.test_cruise_ceiling import ACTIVE, V_EGO, messages, snapshot
from opendbc.car.honda.interface import CarInterface
from opendbc.car.honda.values import CAR


class GlobalBrakingTests(unittest.TestCase):
  def setUp(self):
    self.cp = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)

  def run_planner(self, response=None, *, ceiling=None, lead=False, stop=False, force=False,
                  profile=None, traffic=False):
    planner = LongitudinalPlanner(self.cp, init_v=V_EGO)
    with patch.object(planner_module, 'slc_coast_floor', wraps=planner_module.slc_coast_floor) as coast:
      for _ in range(65):
        sm, _ = messages(lead=lead, force=force)
        sm['carState'].vCruise = 100.0 if ceiling is not None else 50.0
        sm['carControl'].longActive = True
        sm['modelV2'].action.shouldStop = stop
        update_curve_frame(planner, sm, self.cp, 1_000_000_000,
                           cruise_ceiling=ceiling, profile_tuning=profile, traffic_mode=traffic,
                           global_braking_response=response)
        self.assertEqual(planner.mpc.solution_status, 0)
    return planner, coast.call_args.kwargs

  def test_real_cruise_candidate_uses_global_floor_without_changing_native_mpc(self):
    ordinary, _ = self.run_planner()
    standard, _ = self.run_planner('standard')
    eco, _ = self.run_planner('eco')
    sport, _ = self.run_planner('sport')
    self.assertEqual(snapshot(ordinary), snapshot(standard))
    self.assertGreater(eco.a_cruise, ordinary.a_cruise)
    self.assertLess(sport.a_cruise, ordinary.a_cruise)
    self.assertAlmostEqual(eco.mpc.params[0, 4], ordinary.mpc.params[0, 4])
    self.assertAlmostEqual(sport.mpc.params[0, 4], ordinary.mpc.params[0, 4])

  def test_slc_style_hazards_and_category_override(self):
    ceiling = CruiseCeiling(19.0, ACTIVE)
    eco, coast = self.run_planner('eco', ceiling=ceiling)
    self.assertEqual(coast['braking_style'], 'eco')
    self.assertEqual(coast['full_brake_floor'], -1.2)
    self.assertIsNotNone(coast['slc_target'])
    lead, coast = self.run_planner('eco', ceiling=ceiling, lead=True)
    self.assertTrue(coast['relevant_lead'])
    self.assertLess(lead.output_a_target, lead.a_cruise)
    native_lead, _ = self.run_planner(ceiling=ceiling, lead=True)
    sport_lead, _ = self.run_planner('sport', ceiling=ceiling, lead=True)
    self.assertEqual(snapshot(lead), snapshot(native_lead))
    self.assertEqual(snapshot(sport_lead), snapshot(native_lead))
    for kwargs in ({'stop': True}, {'force': True}):
      with self.subTest(kwargs=kwargs):
        protected, coast = self.run_planner('eco', ceiling=ceiling, **kwargs)
        native, _ = self.run_planner(ceiling=ceiling, **kwargs)
        self.assertEqual(coast['braking_style'], 'standard')
        self.assertIsNone(planner_module.slc_coast_floor(**coast))
        self.assertEqual(snapshot(protected), snapshot(native))
    selected = ProfileTuning('standard', 1.45, 1.0, 1.0, 1.0, 1.0, 1.0,
                             cruise_brake_magnitude=1.0, slc_braking_style='standard')
    baseline, coast = self.run_planner(profile=selected, ceiling=ceiling)
    with_global, with_coast = self.run_planner('sport', profile=selected, ceiling=ceiling)
    self.assertEqual(snapshot(baseline), snapshot(with_global))
    self.assertEqual((coast['braking_style'], with_coast['braking_style']), ('standard', 'standard'))

  def test_inactive_and_traffic_never_consume_global_choice(self):
    ordinary, _ = self.run_planner()
    traffic, coast = self.run_planner('sport', traffic=True)
    ordinary_traffic, _ = self.run_planner(traffic=True)
    self.assertEqual(snapshot(traffic), snapshot(ordinary_traffic))
    self.assertEqual(coast['braking_style'], 'standard')
    self.assertEqual(snapshot(ordinary), snapshot(self.run_planner('unknown')[0]))
    self.assertEqual(snapshot(ordinary), snapshot(self.run_planner([])[0]))


if __name__ == '__main__':
  unittest.main()
