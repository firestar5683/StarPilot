"""Exact camera ACC interceptor factory and joined ownership checks."""
import unittest
import os
from unittest.mock import patch

import numpy as np

from opendbc.can import CANPacker
from opendbc.car import Bus, gen_empty_fingerprint, structs
from opendbc.car.gm import gmcan
from opendbc.car.gm.interface import CarInterface
from opendbc.car.gm.values import CAR, DBC
from opendbc.safety.tests.libsafety import libsafety_py

CAMERA_IDS = (CAR.CHEVROLET_SILVERADO, CAR.CHEVROLET_EQUINOX, CAR.CHEVROLET_TRAILBLAZER,
              CAR.CHEVROLET_TRAX, CAR.GMC_YUKON, CAR.CHEVROLET_SUBURBAN_CAMERA)


def fingerprint(*, camera=True, be=True, pedal=True, gear=True):
  fp = gen_empty_fingerprint()
  fp[0].update({0x184: 8, 0x34A: 5, 0x348: 5, 0x1E1: 7, 0x1C4: 8, 0xC9: 8})
  fp[0][0xBE if be else 0xF1] = 6
  if pedal:
    fp[0][0x201] = 6
  if gear:
    fp[0][0x1F5] = 8
  if camera:
    fp[2].update({0x320: 6, 0x180: 4, 0x370: 6})
  return fp


def params(candidate=CAR.CHEVROLET_SILVERADO, *, camera=True, be=True, pedal=True, gear=True,
           release=False, alpha=False):
  return CarInterface.get_params(candidate, fingerprint(camera=camera, be=be, pedal=pedal, gear=gear), [], alpha, release, False)


def controls_command(controls, state, now, *, enabled, should_stop=False):
  from openpilot.cereal import messaging
  messages = []

  def message(service, size=None):
    event = messaging.new_message(service, size, valid=True, logMonoTime=now)
    messages.append(event)
    return getattr(event, service)
  message('carState').from_dict(state.to_dict())
  host = message('selfdriveState')
  host.enabled, host.active = enabled, False
  host.state = 'enabled' if enabled else 'disabled'
  parameters = message('vehicleParameters')
  parameters.stiffnessFactor, parameters.steerRatio = 1., controls.CP.steerRatio
  plan = message('longitudinalPlan')
  plan.aTarget, plan.shouldStop = .5, should_stop
  message('modelV2')
  message('lateralDelay').lateralDelay = .1
  message('carOutput')
  events = message('onroadEvents', int(state.gasPressed))
  if state.gasPressed:
    events[0].name = 'gasPressedOverride'
    events[0].overrideLongitudinal = True
  controls.sm.update_msgs(now / 1e9, [event.as_reader() for event in messages])
  command, lateral_log = controls.state_control()
  controls.publish(command, lateral_log)
  return command


class TestCameraAccPedal(unittest.TestCase):
  def test_actual_parser_launch_handoff(self):
    from opendbc.car.gm.tests.test_cc_gateway_stock import pt_frames
    from openpilot.common.params import Params
    from openpilot.common.prefix import OpenpilotPrefix
    from openpilot.selfdrive.controls.controlsd import Controls
    safety = libsafety_py.libsafety
    release = safety.set_safety_hooks(structs.CarParams.SafetyModel.allOutput, 0) != 0
    with OpenpilotPrefix(), patch.dict(os.environ, {'SIMULATION': '1', 'REPLAY': '1'}):
      settings = Params()
      settings.put_bool('OpenpilotEnabledToggle', True, block=True)
      for identity in CAMERA_IDS:
        for camera in (False, True):
          for be in (False, True):
            with self.subTest(identity=identity, camera=camera, be=be):
              from openpilot.starpilot.tests.test_vehicle_preferences import TestVehicleStartupPreferences
              startup = TestVehicleStartupPreferences()
              startup.params = settings
              settings.put_bool('IsReleaseBranch', release, block=True)
              host, _, cp = startup.start(identity, observed=fingerprint(camera=camera, be=be),
                                          key='LongPitch', requested=False)
              ci = host.CI
              controls = Controls()
              self.assertEqual(controls.CP.to_dict(), cp.to_dict())
              packer = CANPacker(DBC[identity][Bus.pt])
              self.assertEqual(safety.set_safety_hooks(structs.CarParams.SafetyModel.gm, cp.safetyConfigs[0].safetyParam), 0)
              safety.init_tests()
              positive = ordinary = False
              loopback = []
              boundary = identity == CAMERA_IDS[0] and camera and be and not release
              withdrawn = False
              for tick in range(250 if boundary else 100):
                now = 1_000_000_000 + tick * 10_000_000
                launch = 50 <= tick < 75 or boundary and tick >= 100
                driver_gas = boundary and 108 <= tick < 116
                driver_brake = boundary and 120 <= tick < 128
                reverse = boundary and 132 <= tick < 140
                fault = boundary and 144 <= tick < 152
                bad_crc = boundary and 156 <= tick < 164
                should_stop = boundary and 100 <= tick < 104
                if boundary and tick == 190:
                  settings.put_bool('SafeMode', True, block=True)
                frames = pt_frames(packer, counter=tick % 4, acc_cruise=4 if launch else 2)
                frames = [f for f in frames if f[0] not in (0xF1, 0xBE, 0x34A, 0x348, 0x1E1, 0x1F5, 0x232)]
                frames += [packer.make_can_msg('EBCMWheelSpdRear', 0, {'RLWheelSpd': 0 if launch else 5, 'RRWheelSpd': 0 if launch else 5}),
                           packer.make_can_msg('EBCMWheelSpdFront', 0, {'FLWheelSpd': 0 if launch else 5, 'FRWheelSpd': 0 if launch else 5}),
                           packer.make_can_msg('ASCMSteeringButton', 0, {'ACCButtons': 3 if tick in (40, 117, 141, 165) else 1,
                                                                      'RollingCounter': tick % 4}),
                           packer.make_can_msg('ECMPRDNL2', 0, {'PRNDL2': 2 if reverse else 4}),
                           packer.make_can_msg('EBCMFrictionBrakeStatus', 0, {'FrictionBrakeUnavailable': int(fault)})]
                frames.append(packer.make_can_msg('ECMAcceleratorPos' if be else 'EBCMBrakePedalPosition', 0,
                                                 {'BrakePedalPos': 10} if be and driver_brake else {}))
                sensor = bytearray.fromhex('053502ba0000' if driver_gas else '0279012a0000')
                sensor[4] = tick % 16
                sensor[5] = gmcan.pedal_crc(sensor)
                if bad_crc:
                  sensor[5] ^= 1
                frames.append((0x201, bytes(sensor), 0))
                if camera:
                  frames += [packer.make_can_msg('ASCMLKASteeringCmd', 2, {'RollingCounter': tick % 4}),
                             packer.make_can_msg('AEBCmd', 2, {}),
                             packer.make_can_msg('ASCMActiveCruiseControlStatus', 2, {'ACCCruiseState': 4 if launch else 2})]
                safety.set_timer(now // 1000)
                for addr, data, bus in frames:
                  self.assertTrue(safety.safety_rx_hook(libsafety_py.make_CANPacket(addr, bus, data)))
                safety.safety_tick()
                state = ci.update([(now, frames + loopback)])
                if tick >= 40:
                  self.assertTrue(state.canValid)
                enabled = tick >= 42 and not (driver_brake or reverse or fault or bad_crc)
                control = controls_command(controls, state, now, enabled=enabled, should_stop=should_stop)
                self.assertEqual(control.longActive, cp.openpilotLongitudinalControl and enabled and not state.gasPressed)
                self.assertEqual(control.cruiseControl.resume, enabled and state.cruiseState.standstill and not should_stop)
                _, tx = ci.apply(control.as_reader(), now)
                if driver_gas or driver_brake or reverse or fault or bad_crc or should_stop:
                  self.assertFalse(ci.CC.camera_pedal_launch)
                if fault:
                  self.assertTrue(state.accFaulted)
                if bad_crc:
                  self.assertFalse(ci.CS.pedal_sensor_healthy)
                if tick >= 220:
                  self.assertFalse(ci.CC.camera_pedal_input.update(now))
                  self.assertFalse(ci.CC.camera_pedal_launch)
                  withdrawn = True
                loopback = [(addr, data, 128) for addr, data, _ in tx if addr == 0x180]
                longitudinal = [frame for frame in tx if frame[0] in (0x200, 0x2CB, 0x315)]
                if longitudinal:
                  if 44 <= tick < 100 and not launch and cp.openpilotLongitudinalControl:
                    radius = .075 * cp.wheelbase + .1453
                    frontal = 1.05 * cp.wheelbase + .0679
                    torque = radius * (cp.mass * control.actuators.accel + .5 * .30 * frontal * 1.225 * state.vEgo ** 2)
                    expected_brake = round(float(np.interp(min(torque / (radius * cp.mass), 0), [-4., 0.], [400, 0])))
                    expected_gas = -500 if expected_brake else round(min(max(torque + 6150, 5610), 8848)) - 6150
                    self.assertEqual(ci.CC.apply_gas, expected_gas,
                                     (tick, control.actuators.accel, state.canValid, ci.CS.camera_pedal_sources,
                                      ci.CS.pedal_sensor_healthy, ci.CC.camera_pedal_input.update(now)))
                    self.assertEqual(ci.CC.apply_brake, expected_brake)
                  self.assertEqual([addr for addr, _, _ in longitudinal],
                                   [0x2CB, 0x315, 0x200] if ci.CC.camera_pedal_launch else [0x200, 0x2CB, 0x315])
                  idx = ((tick // 4) % 4)
                  self.assertEqual(longitudinal[-1 if ci.CC.camera_pedal_launch else 0],
                                   gmcan.create_pedal_command(packer, 18 / 255 if ci.CC.camera_pedal_launch else 0, idx))
                  if ci.CC.camera_pedal_launch:
                    self.assertEqual((ci.CC.apply_gas, ci.CC.apply_brake), (-500, 0))
                for addr, data, bus in tx:
                  if addr == 0x370:
                    self.assertEqual(data[0] & 1, int(identity in (CAR.GMC_YUKON, CAR.CHEVROLET_SUBURBAN_CAMERA)))
                  self.assertTrue(safety.safety_tx_hook(libsafety_py.make_CANPacket(addr, bus, data)), (tick, hex(addr), data.hex()))
                if any(addr == 0x200 for addr, _, _ in tx):
                  positive |= ci.CC.camera_pedal_launch
                  ordinary |= not ci.CC.camera_pedal_launch
              self.assertEqual(positive, not release)
              self.assertEqual(ordinary, not release)
              if boundary:
                self.assertTrue(withdrawn)
                settings.put_bool('SafeMode', False, block=True)
              del controls

  def test_actual_factory_reached_acceleration_limits(self):
    for identity in CAMERA_IDS:
      cp = params(identity)
      for speed in (0, 1.5, 4, 8, 15, 30, 40):
        expected = (float(np.interp(speed, [0, 1.5, 4, 8, 15, 30], [-.95, -1.3, -1.85, -2.3, -2.6, -2.8])),
                    float(np.interp(speed, [0, 1.5, 4, 8, 15], [.60, .85, 1.15, 1.60, 2])))
        self.assertEqual(CarInterface.get_pid_accel_limits(cp, speed, 0), expected)
