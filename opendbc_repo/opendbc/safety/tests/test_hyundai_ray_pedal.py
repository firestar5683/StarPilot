import unittest

from opendbc.can import CANPacker
from opendbc.car import structs
from opendbc.car.hyundai.ray_pedal import create_ray_pedal_command, pedal_checksum
from opendbc.car.hyundai.tests.test_ray_pedal import ray_controller
from opendbc.car.hyundai.values import RAY_PEDAL_SAFETY_PARAM
from opendbc.safety.tests.libsafety import libsafety_py
from opendbc.safety.tests.test_hyundai import checksum


class TestHyundaiRayPedal(unittest.TestCase):
  def setUp(self):
    self.safety = libsafety_py.libsafety
    self.packer = CANPacker('hyundai_can_generated')
    self.pedal = CANPacker('hyundai_kia_ray_pedal')
    self.counter = 0

  @staticmethod
  def packet(frame):
    return libsafety_py.make_CANPacket(frame[0], frame[2], frame[1])

  def rx(self, name, values, bus=0):
    frame = self.packer.make_can_msg(name, bus, values)
    if frame[0] in (0x260, 0x386, 0x394):
      frame = checksum(frame)
    self.assertTrue(self.safety.safety_rx_hook(self.packet(frame)))
    return frame

  def sensor(self, state=0, pressed=False):
    self.counter = (self.counter + 1) & 15
    frame = self.pedal.make_can_msg('GAS_SENSOR', 0, {'STATE': state, 'COUNTER_PEDAL': self.counter,
      'INTERCEPTOR_GAS': (310-264)*.672 if pressed else 0, 'INTERCEPTOR_GAS2': (593-497)*.332 if pressed else 0})
    self.assertTrue(self.safety.safety_rx_hook(self.packet(frame)))
    return frame

  def arm(self, param=RAY_PEDAL_SAFETY_PARAM):
    self.safety.set_safety_hooks(structs.CarParams.SafetyModel.hyundai, param)
    self.safety.init_tests()
    self.safety.set_timer(1_000_000)
    self.counter = 0
    self.rx('E_EMS11', {})
    self.rx('WHL_SPD11', {'WHL_SPD_FL': 0, 'WHL_SPD_RR': 0})
    self.rx('TCS13', {'DriverOverride': 0})
    self.rx('MDPS12', {})
    self.rx('CLU11', {'CF_Clu_AliveCnt1': 1})
    self.rx('LABEL11', {'CC_React': 1})
    self.rx('BCM_PO_11', {})
    self.sensor()
    self.safety.safety_tick()
    self.rx('CLU11', {'CF_Clu_CruiseSwState': 2, 'CF_Clu_AliveCnt1': 2})
    self.rx('CLU11', {'CF_Clu_CruiseSwState': 0, 'CF_Clu_AliveCnt1': 3})
    self.assertTrue(self.safety.get_controls_allowed())

  def command(self, gas, bus=0):
    frame = create_ray_pedal_command(self.pedal, gas, 3)
    return self.packet((frame[0], frame[1], bus))

  def test_exact_actual_cp_and_near_neighbor_native_admission(self):
    cp, _, _, _ = ray_controller()
    self.assertEqual(cp.safetyConfigs[0].safetyParam, RAY_PEDAL_SAFETY_PARAM)
    self.arm(cp.safetyConfigs[0].safetyParam)
    self.assertTrue(self.safety.safety_tx_hook(self.command(.55)))
    self.assertTrue(self.safety.safety_tx_hook(self.command(0)))
    for param in (0x9405, 0x9801, 0x1805, 0x9804, 0x9807, 0x9885, 0x9825, 0xB805, 0):
      self.safety.set_safety_hooks(structs.CarParams.SafetyModel.hyundai, param)
      self.safety.init_tests()
      self.safety.set_controls_allowed(True)
      self.assertFalse(self.safety.safety_tx_hook(self.command(0)), hex(param))
      self.assertFalse(self.safety.safety_tx_hook(self.command(.1)), hex(param))

  def test_command_limits_channels_checksum_and_buses(self):
    self.arm()
    for gas in (.56, .7, 1):
      self.assertFalse(self.safety.safety_tx_hook(self.command(gas)))
    for bus in (1, 2):
      self.assertFalse(self.safety.safety_tx_hook(self.command(.1, bus)))
    frame = create_ray_pedal_command(self.pedal, .1, 3)
    for kind in ('checksum', 'track', 'reserved', 'disabled'):
      data = bytearray(frame[1])
      if kind == 'checksum':
        data[-1] ^= 1
      elif kind == 'track':
        data[3] += 5
        data[-1] = pedal_checksum(0, None, data)
      elif kind == 'reserved':
        data[4] |= 0x10
        data[-1] = pedal_checksum(0, None, data)
      else:
        data[4] &= ~0x80
        data[-1] = pedal_checksum(0, None, data)
      self.assertFalse(self.safety.safety_tx_hook(self.packet((frame[0], bytes(data), 0))), kind)
    for addr in (0x420, 0x421, 0x50A, 0x389, 0x7D0):
      self.assertFalse(self.safety.safety_tx_hook(libsafety_py.make_CANPacket(addr, 0, bytes(8))))

  def test_generated_channel_rounding_bound_exhaustive(self):
    self.arm()
    maximum = 0
    for step in range(101, 55001):
      frame = create_ray_pedal_command(self.pedal, step / 100000, step & 15)
      track1 = int.from_bytes(frame[1][:2], 'big')
      track2 = int.from_bytes(frame[1][2:4], 'big')
      error = abs(83*(track2-497)-168*(track1-264))
      maximum = max(maximum, error)
      self.assertLessEqual(error, 125)
      self.assertTrue(self.safety.safety_tx_hook(self.packet(frame)))
    self.assertEqual(maximum, 125)

  def test_fault_driver_brake_stale_restart_and_cancel_gates(self):
    self.arm()
    self.assertTrue(self.safety.safety_tx_hook(self.command(.1)))
    for fault in range(1, 6):
      self.sensor(state=fault)
      self.assertFalse(self.safety.safety_tx_hook(self.command(.1)))
      self.assertTrue(self.safety.safety_tx_hook(self.command(0)))
    self.sensor()
    self.assertTrue(self.safety.safety_tx_hook(self.command(.1)))
    self.sensor(pressed=True)
    self.assertFalse(self.safety.safety_tx_hook(self.command(.1)))
    cancel = self.packer.make_can_msg('CLU11', 0, {'CF_Clu_CruiseSwState': 4})
    self.assertTrue(self.safety.safety_tx_hook(self.packet(cancel)))
    self.sensor()
    self.rx('TCS13', {'DriverOverride': 2, 'AliveCounterTCS': 1})
    self.assertFalse(self.safety.safety_tx_hook(self.command(.1)))
    self.assertTrue(self.safety.safety_tx_hook(self.command(0)))
    self.arm()
    self.safety.set_timer(2_000_001)
    self.assertFalse(self.safety.safety_tx_hook(self.command(.1)))
    self.assertTrue(self.safety.safety_tx_hook(self.command(0)))
    self.arm()
    self.safety.set_controls_allowed(False)
    self.assertFalse(self.safety.safety_tx_hook(self.command(.1)))
    self.safety.set_safety_hooks(structs.CarParams.SafetyModel.hyundai, RAY_PEDAL_SAFETY_PARAM)
    self.safety.init_tests()
    self.safety.set_controls_allowed(True)
    self.assertFalse(self.safety.safety_tx_hook(self.command(.1)))

  def test_actual_buttons_main_off_cancel_and_no_spurious_reenable(self):
    self.arm()
    self.assertTrue(self.safety.safety_tx_hook(self.command(.1)))
    self.rx('CLU11', {'CF_Clu_CruiseSwState': 4, 'CF_Clu_AliveCnt1': 4})
    self.assertFalse(self.safety.get_controls_allowed())
    self.assertFalse(self.safety.safety_tx_hook(self.command(.1)))
    self.assertTrue(self.safety.safety_tx_hook(self.command(0)))
    self.rx('CLU11', {'CF_Clu_CruiseSwState': 1, 'CF_Clu_AliveCnt1': 5})
    self.assertFalse(self.safety.get_controls_allowed())
    self.rx('CLU11', {'CF_Clu_CruiseSwState': 0, 'CF_Clu_AliveCnt1': 6})
    self.assertTrue(self.safety.get_controls_allowed())
    self.rx('LABEL11', {'CC_React': 0, 'CC_Engaged': 0})
    self.assertFalse(self.safety.get_controls_allowed())
    self.assertFalse(self.safety.safety_tx_hook(self.command(.1)))
    self.rx('LABEL11', {'CC_React': 1})
    self.assertFalse(self.safety.get_controls_allowed())
    self.assertFalse(self.safety.safety_tx_hook(self.command(.1)))
    self.rx('CLU11', {'CF_Clu_CruiseSwState': 2, 'CF_Clu_AliveCnt1': 7})
    self.rx('CLU11', {'CF_Clu_CruiseSwState': 0, 'CF_Clu_AliveCnt1': 8})
    self.assertTrue(self.safety.safety_tx_hook(self.command(.1)))

  def test_host_to_native_and_required_health_loss(self):
    cp, controller, command, state = ray_controller()
    self.arm(cp.safetyConfigs[0].safetyParam)
    for frame in range(40):
      for message in controller.update(command.as_reader(), state, frame*10_000_000)[1]:
        self.assertTrue(self.safety.safety_tx_hook(self.packet(message)), message)
    sensor = self.sensor()
    bad = bytearray(sensor[1])
    bad[-1] ^= 1
    self.assertFalse(self.safety.safety_rx_hook(self.packet((sensor[0], bytes(bad), 0))))
    self.assertFalse(self.safety.safety_tx_hook(self.command(.1)))
    self.assertTrue(self.safety.safety_tx_hook(self.command(0)))
