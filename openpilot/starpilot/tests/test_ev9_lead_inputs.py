"""EV9 current-drive lead selection through the real controller and CAN packer."""
import time
import unittest
from unittest.mock import patch

from opendbc.can import CANPacker, CANParser
from opendbc.car import Bus, structs
from opendbc.car.hyundai.canfd_lead import ABSENT
from opendbc.car.hyundai.ev9_camera_lead import EV9CameraLead
from opendbc.car.hyundai.ev9_longitudinal import candidate
from opendbc.car.hyundai.hyundaicanfd import CanBus
from opendbc.car.hyundai.interface import CarInterface
from opendbc.car.hyundai.tests.test_gv70_camera_lead import packet as camera_packet
from opendbc.car.hyundai.tests.test_ioniq5pe_stock import params
from opendbc.car.hyundai.values import CAR, DBC
from openpilot.starpilot.controller_extensions import configure_controller
from openpilot.starpilot.longitudinal.canfd_lead import CANFDLeadInputs
from openpilot.starpilot.longitudinal import radar_lead_context
from openpilot.starpilot.tests.test_g90_lead_inputs import RadarMessages

OFFSET = 20_000_000_000


def long_params():
  return candidate(params(candidate=CAR.KIA_EV9), enabled=True, is_release=False)


class TestEV9LeadInputs(unittest.TestCase):
  def setUp(self):
    self.boot = patch.object(time, 'CLOCK_BOOTTIME', getattr(time, 'CLOCK_BOOTTIME', time.CLOCK_MONOTONIC), create=True)
    self.boot.start()
    self.addCleanup(self.boot.stop)

  def test_exact_owner_and_optional_transport_failure(self):
    cp = long_params()
    camera = EV9CameraLead(cp)
    self.assertEqual(camera.bus, 1)
    ci = CarInterface(cp)
    self.assertIsInstance(ci.CS.ev9_camera_lead, EV9CameraLead)
    self.assertNotIn(camera.parser, ci.can_parsers.values())
    self.assertTrue(all(0x1b5 not in parser.addresses for parser in ci.can_parsers.values()))
    with patch.object(radar_lead_context.messaging, 'SubMaster', side_effect=OSError('unavailable')), \
         patch('openpilot.starpilot.controller_extensions.cloudlog.exception') as diagnostic:
      configure_controller(ci, None)
    self.assertIsNone(ci.CC.ev9_lead_inputs)
    diagnostic.assert_called_once()
    for stock in (params(candidate=CAR.KIA_EV9), params()):
      with self.assertRaises(ValueError):
        EV9CameraLead(stock)
      stock_ci = CarInterface(stock)
      with patch.object(radar_lead_context.messaging, 'SubMaster', side_effect=AssertionError('stock must not subscribe')):
        configure_controller(stock_ci, None)
      self.assertIsNone(stock_ci.CS.ev9_camera_lead)
      self.assertIsNone(stock_ci.CC.ev9_lead_inputs)

  def test_shared_provider_selects_radar_camera_hud_and_rejects_old_drive(self):
    messages = RadarMessages(auto=True)
    with patch.object(radar_lead_context.messaging, 'SubMaster', return_value=messages):
      provider = CANFDLeadInputs()
    camera = EV9CameraLead(long_params())
    packer = CANPacker(DBC[CAR.KIA_EV9][Bus.pt])
    def sample(hud=False):
      with patch.object(radar_lead_context, 'clock_pair_ns', side_effect=lambda: (messages.now, messages.now+OFFSET)):
        return provider.update(camera, hud, messages.now)
    self.assertEqual(sample(), ABSENT)
    self.assertEqual(sample().distance, 26.)
    stamp = messages.now+OFFSET-1000
    with patch.object(time, 'clock_gettime_ns', return_value=messages.now+OFFSET):
      camera.update([(stamp, [camera_packet(packer, 1, 1, 12., -2.)])])
    messages.valid['radarState'] = False
    selected = sample()
    self.assertEqual((selected.visible, selected.distance, selected.relative_speed), (True, 12., -2.))
    messages.now += 300_000_001
    self.assertEqual(sample(), ABSENT)
    self.assertEqual(sample(True).distance, 20.)
    messages['deviceState'].startedMonoTime = messages.now-1
    self.assertEqual(sample(), ABSENT)
    self.assertEqual(sample(), ABSENT)  # Camera data from the old drive cannot reappear.

  def test_real_50hz_scc_receives_optional_lead_without_changing_required_health(self):
    ci = CarInterface(long_params())
    messages = RadarMessages()
    messages.valid['radarState'] = False
    with patch.object(radar_lead_context.messaging, 'SubMaster', return_value=messages):
      configure_controller(ci, None)
    packer = CANPacker(DBC[CAR.KIA_EV9][Bus.pt])
    decoder = CANParser(DBC[CAR.KIA_EV9][Bus.pt], [('SCC_CONTROL', 50)], CanBus(ci.CP).ECAN)
    control = structs.CarControl(enabled=True, latActive=True, longActive=True)
    control.actuators.longControlState = structs.CarControl.Actuators.LongControlState.pid
    control.actuators.accel = 1.
    control.hudControl.setSpeed = 20.
    values = {}
    for tick in range(14):
      messages.now += 10_000_000
      messages.refresh('deviceState', 'carState')
      frames = []
      for parser in ci.can_parsers.values():
        for address in parser.addresses:
          name = parser.dbc.addr_to_msg[address].name
          fields = {'GEAR': 5} if name == 'ACCELERATOR' else {}
          frames.append(packer.make_can_msg(name, parser.bus, fields))
      frames.append(camera_packet(packer, 1, tick+1, 30., -1.))
      stamp = messages.now+OFFSET-1000
      with patch.object(time, 'clock_gettime_ns', return_value=messages.now+OFFSET):
        state = ci.update([(stamp, frames)])
      with patch.object(radar_lead_context, 'clock_pair_ns', side_effect=lambda: (messages.now, messages.now+OFFSET)):
        _, packets = ci.apply(control.as_reader(), messages.now)
      scc = [packet for packet in packets if packet[0] == 0x1a0]
      self.assertEqual(len(scc), int(tick % 2 == 0))
      if scc:
        decoder.update([(stamp, scc)])
        values[tick] = dict(decoder.vl['SCC_CONTROL'])
    self.assertTrue(state.canValid)
    self.assertFalse(state.canTimeout)
    self.assertEqual(state.gearShifter, structs.CarState.GearShifter.drive)
    # Original CCNC LONG encodes absent lead as204.6m, unlike generic SCC's zero.
    self.assertAlmostEqual(values[0]['ACC_ObjDist'], 204.6)
    self.assertEqual(values[0]['ObjValid'], 1)
    self.assertAlmostEqual(values[0]['ACC_ObjRelSpd'], 34.6)
    self.assertEqual(values[2]['ACC_ObjDist'], 30.)
    self.assertEqual(values[12]['ACC_ObjDist'], 30.)
    self.assertAlmostEqual(values[12]['ACC_ObjRelSpd'], -1.)
    self.assertEqual(values[12]['ObjValid'], 0)
    self.assertEqual(values[12]['OBJ_STATUS'], 2)
    self.assertEqual(values[12]['SCC_ObjSta'], 2)  # Original109|2 field, bit110 remainszero.
    self.assertEqual(values[12]['DISTANCE_SETTING'], 7)
