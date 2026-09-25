"""Ordinary Suburban control selection and transition boundaries."""
import json
import struct
from types import SimpleNamespace as NS
import unittest
from unittest.mock import patch

from opendbc.car import DT_CTRL, gen_empty_fingerprint, structs
from opendbc.car.gm.interface import CarInterface
from opendbc.car.gm.suburban import policy_for, supported_cp, SuburbanStopEvidence
from opendbc.car.gm.values import CAR, GMFlags
from opendbc.car.vehicle_model import VehicleModel
from openpilot.selfdrive.controls.lib.latcontrol_torque import LatControlTorque
from openpilot.selfdrive.controls.lib.longcontrol import LongControl
from openpilot.starpilot.lateral.controller_selection import ControllerMode, policy_for as lateral_policy, selection_from_bytes
from openpilot.starpilot.lateral.torque_extension import selected_policy
from openpilot.starpilot.longitudinal.extension import LongitudinalContext
from openpilot.starpilot.longitudinal.inputs import LongitudinalInputs
from openpilot.starpilot.longitudinal.tests.test_gm_volt_long_policy import state, SubMasterFixture


def params():
  fp = gen_empty_fingerprint()
  fp[1][0x460] = 8
  return CarInterface.get_params(CAR.CHEVROLET_SUBURBAN, fp, [], False, False, False).as_reader()


def context(tick, lead=False):
  return LongitudinalContext(vehicle_stop_evidence=SuburbanStopEvidence(1, 1_000_000_000 + tick * 10_000_000, lead))


class TestSuburbanOuter(unittest.TestCase):
  def test_exact_profile_and_saved_standard_choice(self):
    cp = params()
    self.assertTrue(supported_cp(cp))
    self.assertEqual(lateral_policy(cp), 'suburban')
    for field, value in (('carFingerprint', CAR.CHEVROLET_SUBURBAN_ASCM), ('brand', 'toyota'),
                         ('networkLocation', structs.CarParams.NetworkLocation.fwdCamera),
                         ('pcmCruise', True), ('openpilotLongitudinalControl', False),
                         ('passive', True), ('notCar', True), ('dashcamOnly', True), ('flags', int(GMFlags.PEDAL_LONG))):
      altered = cp.as_builder()
      setattr(altered, field, value)
      self.assertFalse(supported_cp(altered), field)
      self.assertIsNone(policy_for(altered), field)
    interceptor = cp.as_builder()
    interceptor.deprecated.enableGasInterceptor = True
    self.assertFalse(supported_cp(interceptor))
    for word in (1, 0xC170, 0xC186):
      altered = cp.as_builder()
      altered.safetyConfigs[0].safetyParam = word
      self.assertFalse(supported_cp(altered))
    raw = json.dumps({'version': 1, 'vehicles': {str(CAR.CHEVROLET_SUBURBAN): {'brand': 'gm', 'mode': 'standard'}}}).encode()
    selected = selection_from_bytes(cp, raw)
    self.assertEqual(selected.mode, ControllerMode.STANDARD)
    standard = LatControlTorque(cp, CarInterface(cp), DT_CTRL, controller_mode=selected.mode)
    default = LatControlTorque(cp, CarInterface(cp), DT_CTRL)
    self.assertIsNone(selected_policy(standard))
    self.assertIsNotNone(selected_policy(default))
    for speed in (5., 8., 15., 30.):
      default.pid.speed = speed
      self.assertEqual(default.pid.k_p, .6)
    self.assertEqual(default.torque_params.to_dict(), standard.torque_params.to_dict())

  def test_actual_lateral_withdrawal_resets_integrator(self):
    cp = params()
    lateral = LatControlTorque(cp, CarInterface(cp), DT_CTRL)
    cs = structs.CarState(vEgo=12., steeringAngleDeg=1.)
    lateral.pid.i = .3
    output = lateral.update(False, cs, VehicleModel(cp), NS(angleOffsetDeg=0., roll=0.), False, .001, False, .1)
    self.assertEqual(output[:2], (0., 0.))
    self.assertEqual(lateral.pid.i, 0.)
    self.assertFalse(output[2].active)

  def test_actual_stop_rate_and_ordinary_pid_limits(self):
    cp = params()
    stored_rate = struct.unpack('f', struct.pack('f', .8))[0]
    owner = LongControl(cp)
    self.assertEqual(owner.stopping_decel_rate, stored_rate)
    for tick in range(1, 41):
      output = owner.update(True, state(0.), -2., True, (-4., 2.), context=context(tick))
      self.assertAlmostEqual(output, -tick * stored_rate * DT_CTRL, places=12)
    moving = LongControl(cp)
    self.assertAlmostEqual(moving.update(True, state(6.), -2., True, (-4., 2.), context=context(1)),
                           -stored_rate * DT_CTRL - .05, places=12)
    for integral, target, measured, expected in ((1., -.2, .3, .04), (-1., 0., 0., -1.)):
      loop = LongControl(cp)
      loop.pid.i = integral
      self.assertAlmostEqual(loop.update(True, state(12., measured), target, False, (-4., 2.), context=context(1)), expected)
      self.assertEqual(loop.update(False, state(), target, False, (-4., 2.), context=context(2)), 0.)
      self.assertEqual(loop.pid.i, 0.)

  def test_half_metre_stop_release_and_invalid_evidence(self):
    for speed, expected in ((.5, 2), (.500001, 1)):
      loop = LongControl(params())
      cs = state(speed)
      cs.cruiseState.standstill = True
      loop.update(True, cs, 0., True, (-4., 2.), context=context(0))
      loop.update(True, cs, .1, False, (-4., 2.), context=context(1))
      self.assertEqual(int(loop.long_control_state), expected)
    loop = LongControl(params())
    cs = state(0.)
    cs.cruiseState.standstill = True
    loop.update(True, cs, 0., True, (-4., 2.), context=context(0))
    for tick in range(1, 35):
      loop.update(True, cs, .2, False, (-4., 2.), context=context(tick))
      self.assertEqual(int(loop.long_control_state), 2)
    loop.update(True, cs, .2, False, (-4., 2.), context=LongitudinalContext())
    self.assertEqual(int(loop.long_control_state), 2)
    for tick in range(36, 71):
      loop.update(True, cs, .2, False, (-4., 2.), context=context(tick))
    self.assertEqual(int(loop.long_control_state), 1)

  def test_actual_transport_owner_and_stale_source_withdrawal(self):
    now, offset = 5_000_000_000, 500_000_000
    sm = SubMasterFixture(now)
    owner = LongitudinalInputs(params(), NS(), lambda: sm)
    self.assertTrue(owner.gm_suburban_enabled)
    self.assertFalse(owner.gm_ascm_enabled)
    self.assertEqual(owner.optional_services, ['radarState', 'deviceState'])
    owner.gm_suburban_boot_offset_ns = offset
    owner.gm_suburban_source_floor_ns = now - 500_000_000
    with patch('openpilot.starpilot.longitudinal.inputs.clock_pair_ns', return_value=(now, now + offset)):
      self.assertIsInstance(owner.context(True).vehicle_stop_evidence, SuburbanStopEvidence)
      for source in ('carState', 'longitudinalPlan', 'radarState', 'deviceState'):
        sm.valid[source] = False
        self.assertIsNone(owner.context(True).vehicle_stop_evidence, source)
        sm.valid[source] = True
      sm.recv_time['carState'] = (now - 150_000_001) / 1e9
      self.assertIsNone(owner.context(True).vehicle_stop_evidence)
      self.assertIsNone(owner.context(False).vehicle_stop_evidence)
