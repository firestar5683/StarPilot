"""Optional StarPilot observations cannot invalidate the native longitudinal plan."""

import unittest
from unittest.mock import patch

from opendbc.car.honda.interface import CarInterface
from opendbc.car.honda.values import CAR
from openpilot.cereal import messaging
from openpilot.selfdrive.controls.lib.longitudinal_planner import LongitudinalPlanner, NATIVE_PLAN_INPUTS


OPTIONAL_INPUTS = ('deviceState', 'starpilotRadarState', 'slcDashboardObservation', 'slcVisionObservation')


class Sources(messaging.SubMaster):
  def __init__(self):
    self.services = list(NATIVE_PLAN_INPUTS + OPTIONAL_INPUTS)
    self.alive = dict.fromkeys(self.services, True)
    self.freq_ok = dict.fromkeys(self.services, True)
    self.valid = dict.fromkeys(self.services, True)
    self.ignore_alive = ['starpilotRadarState']
    self.ignore_valid = ['starpilotRadarState']
    self.ignore_average_freq = ['starpilotRadarState']
    self.logMonoTime = {'modelV2': 1_000_000_000}
    radar = messaging.new_message('radarState', valid=True)
    self.data = {'radarState': messaging.log_from_bytes(radar.to_bytes()).radarState}


class Capture:
  def __init__(self):
    self.message = None

  def send(self, service, message):
    assert service == 'longitudinalPlan'
    self.message = messaging.log_from_bytes(message.to_bytes())


class LongitudinalPlanValidityTest(unittest.TestCase):
  def test_processing_delay_uses_seconds_from_the_two_nanosecond_timestamps(self):
    cp = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
    planner = LongitudinalPlanner(cp)
    sources, published = Sources(), Capture()
    sources.logMonoTime['modelV2'] = 9_000_000_000_000_000
    for delay_ns in (0, 16_365_123, 250_000_000):
      with self.subTest(delay_ns=delay_ns):
        plan = messaging.new_message('longitudinalPlan')
        plan.logMonoTime = sources.logMonoTime['modelV2'] + delay_ns
        with patch('openpilot.selfdrive.controls.lib.longitudinal_planner.messaging.new_message', return_value=plan):
          planner.publish(sources, published)
        self.assertEqual(published.message.longitudinalPlan.modelMonoTime, sources.logMonoTime['modelV2'])
        self.assertAlmostEqual(published.message.longitudinalPlan.processingDelay, delay_ns / 1e9, places=8)

  def test_optional_vision_frequency_and_dashboard_absence_do_not_invalidate_native_plan(self):
    cp = CarInterface.get_non_essential_params(CAR.HONDA_CIVIC)
    planner = LongitudinalPlanner(cp)
    sources = Sources()
    sources.freq_ok['slcVisionObservation'] = False
    sources.alive['slcDashboardObservation'] = False
    sources.valid['deviceState'] = False
    self.assertFalse(sources.all_checks())
    self.assertTrue(sources.all_checks(list(NATIVE_PLAN_INPUTS)))

    published = Capture()
    planner.publish(sources, published)
    self.assertTrue(published.message.valid)
    self.assertEqual(published.message.which(), 'longitudinalPlan')

    for required in NATIVE_PLAN_INPUTS:
      with self.subTest(required=required):
        sources.valid[required] = False
        planner.publish(sources, published)
        self.assertFalse(published.message.valid)
        sources.valid[required] = True


if __name__ == '__main__':
  unittest.main()
