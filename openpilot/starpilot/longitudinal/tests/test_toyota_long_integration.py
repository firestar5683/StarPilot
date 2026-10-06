"""Real Toyota CP and LongControl composition, with optional radar transport."""

from openpilot.starpilot.longitudinal.extension import LongitudinalContext
from openpilot.starpilot.longitudinal.tests.extension_helpers import extension_state
from openpilot.starpilot.longitudinal.tests.extension_helpers import attach_inputs
import os
from types import SimpleNamespace as NS
from unittest import TestCase
from unittest.mock import patch

from opendbc.car.toyota.interface import CarInterface
from opendbc.car.toyota.values import CAR
from openpilot.cereal import messaging
from openpilot.selfdrive.controls.controlsd import Controls
from openpilot.selfdrive.controls.lib.longcontrol import LongControl
from openpilot.starpilot.longitudinal.toyota_output_policy import Lead


class ToyotaLongIntegrationTests(TestCase):
  @staticmethod
  def car_state(speed=1.0):
    event = messaging.new_message('carState')
    event.carState.vEgo = speed
    event.carState.aEgo = 0.0
    event.carState.brakePressed = False
    event.carState.cruiseState.standstill = False
    return messaging.log_from_bytes(event.to_bytes()).carState

  @staticmethod
  def controller(car, enabled=True):
    cp = CarInterface.get_non_essential_params(car)
    with patch.dict(os.environ, {'TOYOTA_LONG_OUTPUT_REPLAY_RUNTIME': '1' if enabled else '0'}):
      return LongControl(cp)

  def test_tss2_stopping_ramp_uses_admitted_vehicle_rate(self):
    from opendbc.car import structs
    from opendbc.car.toyota.values import ToyotaFlags

    for car in CAR:
      if not car.config.flags & ToyotaFlags.TSS2:
        continue
      cp = CarInterface.get_params(car, {0: {}, 1: {}, 2: {}}, [], True, False, False)
      if not cp.openpilotLongitudinalControl or cp.dashcamOnly:
        continue
      variants = [(cp, 0.3)]
      for mutation in ('no_output', 'multiple', 'stock', 'passive'):
        denied = cp.as_reader().as_builder()
        if mutation == 'no_output':
          denied.safetyConfigs[0].safetyModel = structs.CarParams.SafetyModel.noOutput
        elif mutation == 'multiple':
          denied.safetyConfigs = list(denied.safetyConfigs) + [structs.CarParams.SafetyConfig()]
        elif mutation == 'stock':
          denied.openpilotLongitudinalControl = False
        else:
          denied.passive = True
        variants.append((denied, 1.0))
      for candidate, rate in variants:
        for target in (-0.8, 0.8):
          with self.subTest(car=car, rate=rate, target=target, model=candidate.safetyConfigs[0].safetyModel):
            with patch.dict(os.environ, {'TOYOTA_LONG_OUTPUT_REPLAY_RUNTIME': '0'}):
              owner = LongControl(candidate)
            state = self.car_state(0.0)
            for tick in range(1, 6):
              result = owner.update(True, state, target, True, (-3.5, 2.0))
              self.assertEqual(owner.long_control_state, structs.CarControl.Actuators.LongControlState.stopping)
              self.assertAlmostEqual(result, -rate * 0.01 * tick)
            self.assertEqual(owner.update(False, state, target, True, (-3.5, 2.0)), 0.0)

  def test_real_controller_gate_and_native_missing_lead_fallback(self):
    sienna = self.controller(CAR.TOYOTA_SIENNA_4TH_GEN)
    native = self.controller(CAR.TOYOTA_SIENNA_4TH_GEN, enabled=False)
    self.assertIsNotNone(extension_state(sienna, 'toyota_output'))
    self.assertIsNone(extension_state(native, 'toyota_output'))
    for target, speed, stopping, active in ((1.0, 1.0, False, True), (1.5, 0.2, False, True),
                                             (-0.8, 0.2, True, True), (0.5, 0.0, False, False),
                                             (1.0, 1.0, False, True)):
      cs = self.car_state(speed)
      actual = sienna.update(active, cs, target, stopping, (-3.5, 2.0), context=LongitudinalContext(leads=None))
      expected = native.update(active, cs, target, stopping, (-3.5, 2.0))
      self.assertEqual(actual, expected)
      self.assertFalse(extension_state(sienna, 'toyota_output').initialized)

  def test_real_controller_output_changes_only_when_qualified(self):
    cs = self.car_state(0.0)
    for car, leads in ((CAR.TOYOTA_COROLLA_TSS2, None), (CAR.TOYOTA_SIENNA_4TH_GEN, ())):
      tuned = self.controller(car)
      native = self.controller(car, enabled=False)
      tuned_output = tuned.update(True, cs, 1.5, False, (-3.5, 2.0), context=LongitudinalContext(leads=leads))
      native_output = native.update(True, cs, 1.5, False, (-3.5, 2.0))
      self.assertLess(tuned_output, native_output)
      self.assertTrue(-3.5 <= tuned_output <= 2.0)
    sienna = self.controller(CAR.TOYOTA_SIENNA_4TH_GEN)
    lead = (Lead(True, 15.0, 0.0, 10.0, 0.0),)
    self.assertTrue(-3.5 <= sienna.update(True, cs, 2.0, False, (-3.5, 2.0), context=LongitudinalContext(leads=lead)) <= 2.0)

  def test_optional_radar_transport_does_not_change_stock_health(self):
    now = 1_050_000_000
    radar_event = messaging.new_message('radarState', valid=True)
    radar_event.radarState.leadOne.present = True
    radar_event.radarState.leadOne.dRel = 15.0
    radar = messaging.log_from_bytes(radar_event.to_bytes()).radarState
    device_event = messaging.new_message('deviceState', valid=True)
    device_event.deviceState.started = True
    device_event.deviceState.startedMonoTime = 900_000_000
    device = messaging.log_from_bytes(device_event.to_bytes()).deviceState
    class FakeSubMaster(NS):
      def __getitem__(self, name):
        return {'radarState': radar, 'deviceState': device}[name]

    sm = FakeSubMaster(seen={'radarState': True, 'deviceState': True},
            alive={'radarState': True, 'deviceState': True},
            valid={'radarState': True, 'deviceState': True},
            logMonoTime={'radarState': now - 30_000_000, 'deviceState': now - 50_000_000,
                         'carState': now - 20_000_000},
            recv_time={'radarState': (now - 10_000_000) / 1e9,
                       'deviceState': (now - 10_000_000) / 1e9},
            all_checks=lambda names: names == ['carState'])
    controls = Controls.__new__(Controls)
    attach_inputs(controls)
    controls.longitudinal_inputs.toyota_sienna_replay = True
    controls.longitudinal_inputs.toyota_boot_offset_ns = 500_000_000
    controls.longitudinal_inputs.toyota_source_floor_ns = 900_000_000
    self.enterContext(patch.object(controls, 'sm', sm, create=True))
    with patch('openpilot.starpilot.longitudinal.inputs.clock_pair_ns', return_value=(now, now + 500_000_000)):
      self.assertIsNotNone(controls.longitudinal_inputs._toyota_leads())
      sm.valid['radarState'] = False
      self.assertIsNone(controls.longitudinal_inputs._toyota_leads())
      sm.valid['radarState'] = True
      sm.logMonoTime['radarState'] = now - 101_000_000
      self.assertIsNone(controls.longitudinal_inputs._toyota_leads())
      sm.logMonoTime['radarState'] = now - 30_000_000
      device = NS(started=True, startedMonoTime=now - 5_000_000)
      self.assertIsNone(controls.longitudinal_inputs._toyota_leads())

  def test_optional_leads_require_new_producer_frames_after_suspend(self):
    now = 1_050_000_000
    offset = 500_000_000
    radar_event = messaging.new_message('radarState', valid=True)
    radar_event.radarState.leadOne.present = True
    radar_event.radarState.leadOne.dRel = 15.0
    radar = messaging.log_from_bytes(radar_event.to_bytes()).radarState
    device_event = messaging.new_message('deviceState', valid=True)
    device_event.deviceState.started = True
    device_event.deviceState.startedMonoTime = 900_000_000
    device = messaging.log_from_bytes(device_event.to_bytes()).deviceState

    class FakeSubMaster(NS):
      def __getitem__(self, name):
        return {'radarState': radar, 'deviceState': device}[name]

    sm = FakeSubMaster(seen={'radarState': True, 'deviceState': True},
                       alive={'radarState': True, 'deviceState': True},
                       valid={'radarState': True, 'deviceState': True},
                       logMonoTime={'radarState': now - 20_000_000, 'deviceState': now - 20_000_000,
                                    'carState': now - 20_000_000},
                       recv_time={'radarState': (now - 10_000_000) / 1e9,
                                  'deviceState': (now - 10_000_000) / 1e9},
                       all_checks=lambda names: names == ['carState'])
    controls = Controls.__new__(Controls)
    attach_inputs(controls)
    controls.longitudinal_inputs.toyota_sienna_replay = True
    controls.longitudinal_inputs.toyota_boot_offset_ns = None
    controls.longitudinal_inputs.toyota_source_floor_ns = 0
    self.enterContext(patch.object(controls, 'sm', sm, create=True))

    clock = [now, offset]
    with patch('openpilot.starpilot.longitudinal.inputs.clock_pair_ns', side_effect=lambda: (clock[0], clock[0] + clock[1])):
      self.assertIsNone(controls.longitudinal_inputs._toyota_leads())  # initial epoch establishes a source floor
      self.assertIsNone(controls.longitudinal_inputs._toyota_leads())  # cached pre-floor messages cannot renew it
      clock[0] += 20_000_000
      for name in ('radarState', 'deviceState', 'carState'):
        sm.logMonoTime[name] = clock[0] - 5_000_000
      for name in ('radarState', 'deviceState'):
        sm.recv_time[name] = (clock[0] - 2_000_000) / 1e9
      self.assertIsNotNone(controls.longitudinal_inputs._toyota_leads())

      # MONOTONIC advances only 10 ms while BOOTTIME advances nine seconds.
      # The cached messages still look young to ordinary MONOTONIC freshness.
      clock[0] += 10_000_000
      clock[1] += 9_000_000_000
      self.assertIsNone(controls.longitudinal_inputs._toyota_leads())
      clock[0] += 10_000_000
      self.assertIsNone(controls.longitudinal_inputs._toyota_leads())
      sm.logMonoTime['radarState'] = clock[0] - 2_000_000
      sm.logMonoTime['deviceState'] = clock[0] - 2_000_000
      sm.recv_time['radarState'] = (clock[0] - 1_000_000) / 1e9
      sm.recv_time['deviceState'] = (clock[0] - 1_000_000) / 1e9
      self.assertIsNone(controls.longitudinal_inputs._toyota_leads())  # carState has not advanced yet
      sm.logMonoTime['carState'] = clock[0] - 1_000_000
      self.assertIsNotNone(controls.longitudinal_inputs._toyota_leads())


if __name__ == '__main__':
  import unittest
  unittest.main()
