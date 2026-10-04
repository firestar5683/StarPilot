from types import SimpleNamespace
import unittest
from unittest.mock import patch

from opendbc.can import CANPacker, CANParser
from opendbc.car import Bus, structs
from opendbc.car.hyundai.tests.test_ioniq6_longitudinal import controller_fixture
from opendbc.car.hyundai.values import DBC
from opendbc.car.hyundai.hyundaicanfd import hkg_can_fd_checksum


class TestIoniq6EngagementMessages(unittest.TestCase):
  def test_engagement_and_axis_pause_keep_dom_scc_state_without_demand(self):
    for alternate in (False, True):
      cp, cs, controller = controller_fixture(alternate)
      parser = CANParser(DBC[cp.carFingerprint][Bus.pt], [('SCC_CONTROL', 0)], 1)
      control = structs.CarControl()
      control.latActive = True
      control.actuators.accel = 1.0
      for frame, (enabled, longitudinal, override, visible) in enumerate((
        (False, False, False, False), (True, False, False, False),
        (True, True, False, False), (True, False, True, False),
        (True, False, False, True), (False, False, False, False),
      )):
        control.enabled = enabled
        control.longActive = longitudinal
        control.cruiseControl.override = override
        control.hudControl.leadVisible = visible
        controller.frame = frame * 2
        _, messages = controller.update(control.as_reader(), cs, 1_000_000_000 + frame * 20_000_000)
        scc = [message for message in messages if message[0] == 0x1A0]
        self.assertEqual(len(scc), 1)
        parser.update((1_000_000_000 + frame * 20_000_000, scc))
        values = parser.vl['SCC_CONTROL']
        self.assertEqual(values['ACCMode'], 0 if not enabled else 2 if override else 1)
        self.assertEqual(values['ACC_ObjDist'], 20.0 if visible else 0.0)
        self.assertAlmostEqual(values['ACC_ObjRelSpd'], 0.0, places=12)
        self.assertEqual(values['ObjValid'], int(not visible))
        self.assertEqual(values['OBJ_STATUS'], 0 if not enabled or not visible else 1 if override else 2)
        if not longitudinal or override:
          self.assertEqual((values['aReqRaw'], values['aReqValue'], values['StopReq']), (0.0, 0.0, 0))

  def test_actual_optional_camera_and_radar_provider_reach_controller_payload(self):
    from openpilot.starpilot.longitudinal.canfd_lead import CANFDLeadInputs
    from openpilot.starpilot.longitudinal.radar_lead_context import LeadContext, PrimaryLead
    cp, cs, controller = controller_fixture()
    now = 2_000_000_000
    context = LeadContext(1, now, now, 0, 0, PrimaryLead(now, now, True, 37.5, -1.3))
    with patch('openpilot.starpilot.longitudinal.canfd_lead.RadarLeadContext',
               return_value=SimpleNamespace(update=lambda: context)):
      controller.ioniq6_lead_inputs = CANFDLeadInputs()
    packer = CANPacker(DBC[cp.carFingerprint][Bus.pt])
    camera = packer.make_can_msg('FR_CMR_03_50ms', controller.CAN.ECAN,
                                {'Longitudinal_Distance': 23.0, 'Relative_Velocity': -0.7})
    address, data, bus = camera
    checksum = hkg_can_fd_checksum(address, None, bytearray(data))
    camera = (address, checksum.to_bytes(2, 'little') + data[2:], bus)
    with patch('opendbc.car.hyundai.canfd_camera_lead.time.CLOCK_BOOTTIME', 7, create=True), \
         patch('opendbc.car.hyundai.canfd_camera_lead.time.clock_gettime_ns', return_value=now):
      cs.ioniq6_camera_lead.update([(now, [camera])])
    self.assertIsNotNone(cs.ioniq6_camera_lead.current(now))
    control = structs.CarControl()
    control.enabled = True
    control.longActive = True
    parser = CANParser(DBC[cp.carFingerprint][Bus.pt], [('SCC_CONTROL', 0)], 1)
    for frame, radar, expected in ((0, context.radar, (37.5, -1.3)), (2, None, (23.0, -0.7))):
      controller.ioniq6_lead_inputs.context.update = lambda radar=radar: LeadContext(1, now, now, 0, 0, radar)
      controller.frame = frame
      _, messages = controller.update(control.as_reader(), cs, now)
      scc = next(message for message in messages if message[0] == 0x1A0)
      parser.update((now + frame, [scc]))
      values = parser.vl['SCC_CONTROL']
      self.assertAlmostEqual(values['ACC_ObjDist'], expected[0])
      self.assertAlmostEqual(values['ACC_ObjRelSpd'], expected[1])

  def test_stock_profile_does_not_create_longitudinal_lead_owner(self):
    from opendbc.car import gen_empty_fingerprint
    from opendbc.car.hyundai.interface import CarInterface
    from opendbc.car.hyundai.values import CAR
    fingerprint = gen_empty_fingerprint()
    fingerprint[2].update({0x50: 16, 0x2A4: 24})
    fingerprint[1].update({0x1CF: 8, 0x35: 32})
    cp = CarInterface.get_params(CAR.HYUNDAI_IONIQ_6, fingerprint, [], False, False, False)
    interface = CarInterface(cp)
    self.assertFalse(cp.openpilotLongitudinalControl)
    self.assertIsNone(interface.CS.ioniq6_camera_lead)
    self.assertIsNone(interface.CC.ioniq6_longitudinal)
