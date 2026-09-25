"""Actual committed-stop detector and production planner stop-hold caller."""
from types import SimpleNamespace
import os
import unittest
from unittest.mock import patch

from opendbc.car.car_helpers import interfaces
from opendbc.car.hyundai.values import CAR

from openpilot.cereal import messaging
from openpilot.cereal.services import SERVICE_LIST
from openpilot.selfdrive.controls import plannerd
from openpilot.starpilot.conditional_mode.planner_host import ConditionalPlannerHost
from openpilot.starpilot.conditional_mode.tests import test_stop_commit_transport as transport
from openpilot.starpilot.conditional_mode.tests.test_projection import MONO, serialized_scene


class TestStopHoldClock(unittest.TestCase):
  def setUp(self):
    self.source = transport.TestStopCommitTransport(methodName='runTest')
    self.source.setUp()
    self.addCleanup(self.source.doCleanups)
    self.source.prime()
    for _ in range(24):
      self.source.sample(standstill=True, ego_speed=0., horizon=.15, model_should_stop=True)
    assert self.source.host.projector.stop_detector.standstill_committed
    self.host = ConditionalPlannerHost(self.source.params)
    self.addCleanup(self.host.close)
    self.host.mode = self.source.host
    self.now = MONO + self.source.tick * 50_000_000
    self.host.settings.refresh(self.now, force=True)
    self.cp = interfaces[CAR.HYUNDAI_IONIQ_6].get_non_essential_params(CAR.HYUNDAI_IONIQ_6)
    self.cp.openpilotLongitudinalControl = True  # Existing handoff fixture stock-long configuration.
    self.enterContext(patch.dict(os.environ, {'SIMULATION': '0'}))
    payloads = serialized_scene(stamp=self.now - 2_000_000, standstill=True,
                                speed=0., horizon=.15, lead_present=False)
    self.sm = messaging.SubMaster(list(plannerd.NATIVE_PLAN_INPUTS))
    for tick in range(-110, 1):
      stamp = self.now - 2_000_000 + tick * 10_000_000
      events = []
      for service in plannerd.NATIVE_PLAN_INPUTS:
        period = round(100 / SERVICE_LIST[service].frequency)
        if tick % period:
          continue
        event = messaging.new_message(service, valid=True, logMonoTime=stamp)
        if service in payloads:
          setattr(event, service, payloads[service])
        events.append(event.as_reader())
      self.sm.update_msgs(stamp / 1e9, events)
    self.assertFalse(self.sm.simulation)
    self.assertTrue(self.sm.all_checks(list(plannerd.NATIVE_PLAN_INPUTS)))
    self.planner = SimpleNamespace(output_should_stop=False, output_a_target=.2)

  def call(self, offset=0, skew=0):
    return plannerd.apply_conditional_stop_hold(self.host, self.planner, self.sm, self.cp, self.now,
      self.source.drive, now_boot_ns=self.now + offset, sample_skew_ns=skew)

  def change(self, service, field, value):
    event = messaging.new_message(service, valid=True, logMonoTime=self.now - 2_000_000)
    setattr(event, service, self.sm[service])
    setattr(getattr(event, service), field, value)
    self.sm.data[service] = getattr(messaging.log_from_bytes(event.to_bytes()), service)

  def test_true_zero_and_positive_offset_apply(self):
    for offset in (0, 500):
      with self.subTest(offset=offset):
        self.assertTrue(self.call(offset, 2000))
        self.assertTrue(self.planner.output_should_stop)
        self.assertEqual(self.planner.output_a_target, 0.)

  def test_exact_negative_half_skew_applies(self):
    self.assertTrue(self.call(-1000, 2000))
    self.assertTrue(self.planner.output_should_stop)
    self.assertEqual(self.planner.output_a_target, 0.)
    self.assertTrue(self.host.mode.projector.stop_detector.standstill_committed)

  def test_just_outside_half_skew_rejects(self):
    self.assertFalse(self.call(-1001, 2000))
    self.assertFalse(self.planner.output_should_stop)
    self.assertEqual(self.planner.output_a_target, .2)
    self.assertTrue(self.host.mode.projector.stop_detector.standstill_committed)

  def test_malformed_or_overbudget_skew_rejects(self):
    for skew in (-1, 1_000_001, True, 1., None):
      with self.subTest(skew=skew):
        self.assertFalse(self.call(0, skew))
        self.assertFalse(self.planner.output_should_stop)

  def test_expired_model_eof_rejects(self):
    self.change('modelV2', 'timestampEof', self.now - 150_000_001)
    self.assertFalse(self.call())
    self.assertFalse(self.planner.output_should_stop)
    self.assertTrue(self.host.mode.projector.stop_detector.standstill_committed)

  def test_user_brake_retains_existing_reset_and_rejects(self):
    self.change('carState', 'brakePressed', True)
    self.assertFalse(self.call(-500, 2000))
    self.assertFalse(self.planner.output_should_stop)
    self.assertFalse(self.host.mode.projector.stop_detector.standstill_committed)

  def test_nonstandstill_detector_cannot_apply_hold(self):
    self.source.host.projector.stop_detector.reset()
    self.source.prime()
    self.assertTrue(self.source.host.projector.stop_detector.committed)
    self.assertFalse(self.source.host.projector.stop_detector.standstill_committed)
    self.assertFalse(self.call(-500, 2000))
    self.assertFalse(self.planner.output_should_stop)

  def test_native_source_failure_rejects(self):
    self.sm.valid['modelV2'] = False
    self.assertFalse(self.call(-500, 2000))
    self.assertFalse(self.planner.output_should_stop)
