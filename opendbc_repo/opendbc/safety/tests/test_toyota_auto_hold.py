import unittest

from opendbc.can import CANPacker
from opendbc.car import structs
from opendbc.car.toyota import toyotacan
from opendbc.car.toyota.values import CAR, ToyotaSafetyFlags
from opendbc.car.toyota.tests.test_auto_hold import decode, setup_cruise_hold, setup_hold, step_hold
from opendbc.safety import ALTERNATIVE_EXPERIENCE as AE
from opendbc.safety.tests.libsafety import libsafety_py


class TestToyotaAutoHoldSafety(unittest.TestCase):
  def setUp(self):
    self.safety = libsafety_py.libsafety
    self.packer = CANPacker('toyota_nodsu_pt_generated')

  @staticmethod
  def packet(frame):
    return libsafety_py.make_CANPacket(frame[0], frame[2], frame[1])

  def send_rx(self, name, values, bus=0):
    frame = self.packer.make_can_msg(name, bus, values)
    self.assertTrue(self.safety.safety_rx_hook(self.packet(frame)))
    return frame

  def arm(self, permission=AE.TOYOTA_AUTO_HOLD, param=73, speed=0, gas=False, main=True):
    self.safety.set_safety_hooks(structs.CarParams.SafetyModel.toyota, param)
    self.safety.init_tests()
    self.safety.set_alternative_experience(permission)
    self.safety.set_timer(1_000_000)
    self.send_rx('WHEEL_SPEEDS', {f'WHEEL_SPEED_{n}': speed * 3.6 for n in ('FL', 'FR', 'RL', 'RR')})
    self.send_rx('PCM_CRUISE', {'GAS_RELEASED': not gas, 'CRUISE_ACTIVE': False})
    self.send_rx('PCM_CRUISE_2', {'MAIN_ON': main})
    self.send_rx('PRE_COLLISION_2', {}, 2)
    self.send_rx('STEER_TORQUE_SENSOR', {})
    self.send_rx('BRAKE_MODULE', {'BRAKE_PRESSED': True})
    self.safety.safety_tick()
    self.assertFalse(self.safety.get_controls_allowed())

  def acc(self, accel=-1, permit=True, standstill=True, cancel=False, bus=0):
    frame = toyotacan.create_accel_command(self.packer, accel, cancel, permit, standstill, True, 1, False, 0)
    return self.packet((frame[0], frame[1], bus))

  def aeb(self, active=True, bus=0, values=None):
    frame = (toyotacan.create_brake_hold_command(self.packer, 100, {}, active) if values is None else
             self.packer.make_can_msg('PRE_COLLISION_2', bus, values))
    return self.packet((frame[0], frame[1], bus))

  def test_acc_exact_stopped_permission_rejects_other_inactive_actuation(self):
    self.arm()
    self.assertTrue(self.safety.safety_tx_hook(self.acc()))
    for packet in (self.acc(-0.9), self.acc(-1.1), self.acc(1), self.acc(permit=False),
                   self.acc(standstill=False), self.acc(cancel=True), self.acc(bus=1), self.acc(bus=2)):
      self.assertFalse(self.safety.safety_tx_hook(packet))
    for permission in (0, AE.ALLOW_AEB, AE.TOYOTA_AEB_HOLD, AE.TOYOTA_AUTO_HOLD | AE.TOYOTA_AEB_HOLD):
      self.arm(permission)
      self.assertFalse(self.safety.safety_tx_hook(self.acc()))

  def test_hold_sensor_revocations_restart_and_stale(self):
    for permission in (AE.TOYOTA_AUTO_HOLD, AE.TOYOTA_AEB_HOLD):
      for changes in ({'speed': .01}, {'gas': True}, {'main': False}):
        with self.subTest(permission=permission, changes=changes):
          self.arm(permission, **changes)
          packet = self.acc() if permission == AE.TOYOTA_AUTO_HOLD else self.aeb()
          self.assertFalse(self.safety.safety_tx_hook(packet))
          self.assertEqual(self.safety.safety_fwd_hook(2, 0x344), 0)
      self.arm(permission)
      packet = self.acc() if permission == AE.TOYOTA_AUTO_HOLD else self.aeb()
      self.assertTrue(self.safety.safety_tx_hook(packet))
      self.safety.set_timer(2_000_001)
      self.assertFalse(self.safety.safety_tx_hook(packet))
      self.assertEqual(self.safety.safety_fwd_hook(2, 0x344), 0)
      self.arm(permission)
      self.safety.set_safety_hooks(structs.CarParams.SafetyModel.toyota, 73)
      self.safety.init_tests()
      self.safety.set_alternative_experience(permission)
      self.assertFalse(self.safety.safety_tx_hook(packet))
      self.assertEqual(self.safety.safety_fwd_hook(2, 0x344), 0)

  def test_invalid_configuration_rejected_in_release_and_debug(self):
    for permission in (AE.TOYOTA_AUTO_HOLD, AE.TOYOTA_AEB_HOLD):
      for param in (0, 73 | ToyotaSafetyFlags.STOCK_LONGITUDINAL, 73 | ToyotaSafetyFlags.SECOC,
                    73 | 0x1000, 73 | 0x2000, 73 | 0x8000):
        self.arm(permission, param=int(param))
        self.assertFalse(self.safety.safety_tx_hook(self.acc() if permission == AE.TOYOTA_AUTO_HOLD else self.aeb()))
        self.assertEqual(self.safety.safety_fwd_hook(2, 0x344), 0)

  def test_bad_main_checksum_cannot_prime_hold(self):
    self.safety.set_safety_hooks(structs.CarParams.SafetyModel.toyota, 73)
    self.safety.init_tests()
    self.safety.set_alternative_experience(AE.TOYOTA_AUTO_HOLD)
    self.safety.set_timer(1_000_000)
    self.send_rx('WHEEL_SPEEDS', {f'WHEEL_SPEED_{n}': 0 for n in ('FL', 'FR', 'RL', 'RR')})
    self.send_rx('PCM_CRUISE', {'GAS_RELEASED': True})
    frame = self.packer.make_can_msg('PCM_CRUISE_2', 0, {'MAIN_ON': True})
    data = bytearray(frame[1])
    data[-1] ^= 1
    self.safety.safety_rx_hook(self.packet((frame[0], bytes(data), 0)))
    self.assertFalse(self.safety.get_acc_main_on())
    self.assertFalse(self.safety.safety_tx_hook(self.acc()))

  def test_required_health_bad_main_and_relay_revoke_hold(self):
    for permission in (AE.TOYOTA_AUTO_HOLD, AE.TOYOTA_AEB_HOLD):
      self.arm(permission)
      packet = self.acc() if permission == AE.TOYOTA_AUTO_HOLD else self.aeb()
      self.assertTrue(self.safety.safety_tx_hook(packet))
      wheel = self.packer.make_can_msg('WHEEL_SPEEDS', 0, {'WHEEL_SPEED_FR_FAULT': 1})
      self.assertFalse(self.safety.safety_rx_hook(self.packet(wheel)))
      self.assertFalse(self.safety.safety_tx_hook(packet))
      self.assertEqual(self.safety.safety_fwd_hook(2, 0x344), 0)
      self.arm(permission)
      main = self.packer.make_can_msg('PCM_CRUISE_2', 0, {'MAIN_ON': True})
      data = bytearray(main[1])
      data[-1] ^= 1
      self.safety.safety_rx_hook(self.packet((main[0], bytes(data), 0)))
      self.assertFalse(self.safety.safety_tx_hook(packet))
      self.arm(permission)
      self.safety.safety_rx_hook(self.acc(0))
      self.assertTrue(self.safety.get_relay_malfunction())
      self.assertFalse(self.safety.safety_tx_hook(packet))
      self.assertEqual(self.safety.safety_fwd_hook(2, 0x344), -1)

  def test_camry_exact_hold_camera_copy_and_forwarding(self):
    self.arm(AE.TOYOTA_AEB_HOLD)
    self.assertTrue(self.safety.safety_tx_hook(self.aeb()))
    self.assertEqual(self.safety.safety_fwd_hook(2, 0x344), -1)
    self.assertEqual(self.safety.safety_fwd_hook(0, 0x344), 2)
    self.assertEqual(self.safety.safety_fwd_hook(1, 0x344), -1)
    for packet in (self.aeb(bus=1), self.aeb(bus=2), self.aeb(values={'DSS1GDRV': -2}),
                   self.aeb(values={'DSS1GDRV': -1, 'PCSABK': 1})):
      self.assertFalse(self.safety.safety_tx_hook(packet))
    frame = self.send_rx('PRE_COLLISION_2', {'DSS1GDRV': -0.5, 'PBRTRGR': 1, 'PCSABK': 1}, 2)
    self.assertTrue(self.safety.safety_tx_hook(self.packet((frame[0], frame[1], 0))))
    data = bytearray(frame[1])
    data[-1] ^= 1
    self.assertFalse(self.safety.safety_tx_hook(self.packet((frame[0], bytes(data), 0))))
    self.arm(AE.TOYOTA_AUTO_HOLD | AE.ALLOW_AEB)
    self.assertEqual(self.safety.safety_fwd_hook(2, 0x344), 0)
    self.assertTrue(self.safety.safety_tx_hook(self.acc()))
    self.arm(AE.TOYOTA_AUTO_HOLD | AE.TOYOTA_AEB_HOLD)
    self.assertFalse(self.safety.safety_tx_hook(self.aeb()))
    self.assertEqual(self.safety.safety_fwd_hook(2, 0x344), 0)

  def test_camry_forwarding_requires_fresh_accepted_host_ownership(self):
    self.arm(AE.TOYOTA_AEB_HOLD)
    self.assertEqual(self.safety.safety_fwd_hook(2, 0x344), 0)
    self.assertFalse(self.safety.safety_tx_hook(self.aeb(values={'DSS1GDRV': -2})))
    self.assertEqual(self.safety.safety_fwd_hook(2, 0x344), 0)
    self.assertTrue(self.safety.safety_tx_hook(self.aeb()))
    self.assertEqual(self.safety.safety_fwd_hook(2, 0x344), -1)
    self.safety.set_timer(1_100_001)
    self.assertEqual(self.safety.safety_fwd_hook(2, 0x344), 0)
    self.assertTrue(self.safety.safety_tx_hook(self.aeb()))
    self.assertEqual(self.safety.safety_fwd_hook(2, 0x344), -1)
    self.send_rx('PCM_CRUISE_2', {'MAIN_ON': False})
    self.assertEqual(self.safety.safety_fwd_hook(2, 0x344), 0)

  def test_actual_controller_hold_and_moving_camera_ownership(self):
    for car in (CAR.TOYOTA_COROLLA_TSS2, CAR.TOYOTA_CAMRY_TSS2):
      cp, controller, command, state = setup_hold(car)
      self.arm(cp.alternativeExperience, cp.safetyConfigs[0].safetyParam)
      for _ in range(105):
        for frame in step_hold(controller, command, state):
          if frame[0] in (0x343, 0x344):
            self.assertTrue(self.safety.safety_tx_hook(self.packet(frame)), (car, frame))
      state.out.brakePressed = False
      for _ in range(6):
        for frame in step_hold(controller, command, state):
          if frame[0] in (0x343, 0x344):
            self.assertTrue(self.safety.safety_tx_hook(self.packet(frame)))
      state.out.standstill = False
      self.send_rx('WHEEL_SPEEDS', {f'WHEEL_SPEED_{n}': 10 for n in ('FL', 'FR', 'RL', 'RR')})
      for _ in range(4):
        sends = step_hold(controller, command, state)
        self.assertFalse(any(frame[0] == 0x344 for frame in sends))
      self.assertEqual(self.safety.safety_fwd_hook(2, 0x344), 0)
      self.assertFalse(self.safety.safety_tx_hook(self.acc()))

  def test_actual_cruise_hold_resume_gas_tap_and_rearm(self):
    cp, controller, command, state = setup_cruise_hold()
    self.arm(cp.alternativeExperience, cp.safetyConfigs[0].safetyParam)
    self.send_rx('BRAKE_MODULE', {'BRAKE_PRESSED': False})

    def tick():
      frames = [frame for _ in range(3) for frame in step_hold(controller, command, state) if frame[0] == 0x343]
      self.assertEqual(len(frames), 1)
      self.assertTrue(self.safety.safety_tx_hook(self.packet(frames[0])))
      return decode(cp, frames[0], 'ACC_CONTROL')

    # The stopped permission admits the actual controller's exact hold even
    # before controls_allowed is raised by cruise engagement.
    self.assertFalse(self.safety.get_controls_allowed())
    self.assertEqual(tick()['ACCEL_CMD'], -1)
    command.actuators.accel = 1.5
    command.actuators.longControlState = structs.CarControl.Actuators.LongControlState.starting
    command.cruiseControl.resume = True
    for _ in range(10):
      values = tick()
      self.assertEqual(values['ACCEL_CMD'], -1)
      self.assertEqual(values['RELEASE_STANDSTILL'], 0)

    state.out.gasPressed = True
    command.longActive = False
    command.actuators.accel = 0
    self.send_rx('PCM_CRUISE', {'GAS_RELEASED': False, 'CRUISE_ACTIVE': False})
    values = tick()
    self.assertEqual(values['ACCEL_CMD'], 0)
    self.assertEqual(values['RELEASE_STANDSTILL'], 1)
    self.assertFalse(self.safety.safety_tx_hook(self.acc()))

    state.out.gasPressed = False
    command.longActive = True
    command.actuators.accel = -0.7
    command.actuators.longControlState = structs.CarControl.Actuators.LongControlState.stopping
    self.send_rx('PCM_CRUISE', {'GAS_RELEASED': True, 'CRUISE_ACTIVE': True})
    for _ in range(10):
      self.assertEqual(tick()['RELEASE_STANDSTILL'], 1)
      self.assertFalse(controller.brake_hold_active)

    state.out.standstill = state.out.cruiseState.standstill = False
    state.out.vEgo = state.out.vEgoRaw = 1
    self.send_rx('WHEEL_SPEEDS', {f'WHEEL_SPEED_{n}': 3.6 for n in ('FL', 'FR', 'RL', 'RR')})
    tick()
    state.out.standstill = state.out.cruiseState.standstill = True
    state.out.vEgo = state.out.vEgoRaw = 0
    self.send_rx('WHEEL_SPEEDS', {f'WHEEL_SPEED_{n}': 0 for n in ('FL', 'FR', 'RL', 'RR')})
    values = tick()
    self.assertEqual(values['ACCEL_CMD'], -1)
    self.assertEqual(values['RELEASE_STANDSTILL'], 0)
    self.assertTrue(controller.brake_hold_active)
    self.send_rx('PCM_CRUISE', {'GAS_RELEASED': True, 'CRUISE_ACTIVE': False})
    self.safety.set_timer(2_000_001)
    self.safety.safety_tick()
    sends = [frame for _ in range(3) for frame in step_hold(controller, command, state) if frame[0] == 0x343]
    self.assertFalse(self.safety.safety_tx_hook(self.packet(sends[0])))
