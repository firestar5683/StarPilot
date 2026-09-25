"""Joined optional lead callers with explicit synthetic CAN and transport clocks."""
import time
import unittest
from unittest.mock import patch

from opendbc.can.packer import CANPacker
from opendbc.can.parser import CANParser
from opendbc.car import Bus, CanData, structs
from opendbc.car.hyundai.canfd_lead import ABSENT
from opendbc.car.hyundai.gv70_camera_lead import GV70CameraLead
from opendbc.car.hyundai.hyundaicanfd import CanBus, create_acc_control
from opendbc.car.hyundai.interface import CarInterface
from opendbc.car.hyundai.tests.test_gv70_camera_lead import packet as camera_packet, params
from opendbc.car.hyundai.values import CAR, DBC
from openpilot.starpilot.controller_extensions import configure_controller
from openpilot.starpilot.longitudinal import radar_lead_context
from openpilot.starpilot.longitudinal.gv70_lead import GV70LeadInputs
from openpilot.starpilot.tests.test_g90_lead_inputs import RadarMessages

OFFSET = 20_000_000_000


class TestGV70LeadInputs(unittest.TestCase):
  def setUp(self):
    # Mac has no BOOTTIME constant. Both synthetic CAN and paired-clock values
    # explicitly use the same chosen BOOTTIME domain in these host fixtures.
    self.boot = patch.object(time, 'CLOCK_BOOTTIME', getattr(time, 'CLOCK_BOOTTIME', time.CLOCK_MONOTONIC), create=True)
    self.boot.start()
    self.addCleanup(self.boot.stop)

  def provider(self, messages):
    with patch.object(radar_lead_context.messaging, 'SubMaster', return_value=messages):
      return GV70LeadInputs()

  def sample(self, provider, messages, camera=None, hud=False, control=None, offset=OFFSET):
    with patch.object(radar_lead_context, 'clock_pair_ns', side_effect=lambda: (messages.now, messages.now+offset)):
      return provider.update(camera, hud, messages.now if control is None else control)

  def camera(self, messages, *, offset=OFFSET, distance=12., relative=-2.):
    cp = params()
    owner = GV70CameraLead(cp)
    packer = CANPacker(DBC[cp.carFingerprint][Bus.pt])
    with patch.object(time, 'clock_gettime_ns', return_value=messages.now+offset):
      owner.update([(messages.now+offset-1000, [camera_packet(packer, owner.bus, 1, distance, relative)])])
    return owner

  def test_camera_recovery_staggered_context_is_independent_of_missing_radar(self):
    messages = RadarMessages()
    messages.seen['radarState'] = False
    provider = self.provider(messages)
    self.assertEqual(self.sample(provider, messages), ABSENT)
    floor = provider.context.floor_ns
    for name in ('deviceState', 'carState'):
      messages.now += 10_000_000
      messages.refresh(name)
      camera = self.camera(messages)
      result = self.sample(provider, messages, camera)
      self.assertEqual(provider.context.floor_ns, floor)
    self.assertTrue(result.visible)
    self.assertEqual(result.distance, 12.)
    messages.now += 10_000_000
    self.assertTrue(self.sample(provider, messages, camera).visible)
    messages.seen['radarState'] = True
    messages['radarState'].radarErrors.radarFault = True
    self.assertEqual(self.sample(provider, messages, camera).distance, 12.)
    self.assertEqual(provider.context.floor_ns, floor)

  def test_radar_precedence_controls_and_clock_drive_epochs_reject_old_sources(self):
    messages = RadarMessages(auto=True)
    provider = self.provider(messages)
    self.sample(provider, messages)
    self.assertEqual(self.sample(provider, messages).distance, 26.)
    camera = self.camera(messages)
    messages.valid['radarState'] = False
    self.assertEqual(self.sample(provider, messages, camera).distance, 12.)
    self.assertEqual(self.sample(provider, messages, None, True).distance, 20.)
    self.assertEqual(self.sample(provider, messages, camera, control=messages.now+1_000_000_000), ABSENT)
    self.assertEqual(self.sample(provider, messages, camera, control=messages.now-150_000_001), ABSENT)
    messages.auto = False
    messages.now += 10_000_000
    messages.refresh('deviceState', 'carState')
    self.assertEqual(self.sample(provider, messages, camera, offset=OFFSET+20_000_000_000), ABSENT)
    floor = provider.context.floor_ns
    for name in ('deviceState', 'carState'):
      messages.now += 10_000_000
      messages.refresh(name)
      self.assertEqual(self.sample(provider, messages, camera, offset=OFFSET+20_000_000_000), ABSENT)
      self.assertEqual(provider.context.floor_ns, floor)
    fresh_camera = self.camera(messages, offset=OFFSET+20_000_000_000)
    self.assertTrue(self.sample(provider, messages, fresh_camera, offset=OFFSET+20_000_000_000).visible)
    messages['deviceState'].startedMonoTime = messages.now-1
    messages.now += 10_000_000
    messages.refresh('deviceState', 'carState')
    self.assertEqual(self.sample(provider, messages, fresh_camera, offset=OFFSET+20_000_000_000), ABSENT)
    for name in ('carState', 'deviceState'):
      messages.now += 10_000_000
      messages.refresh(name)
      self.assertEqual(self.sample(provider, messages, fresh_camera, offset=OFFSET+20_000_000_000), ABSENT)
    new_camera = self.camera(messages, offset=OFFSET+20_000_000_000)
    self.assertTrue(self.sample(provider, messages, new_camera, offset=OFFSET+20_000_000_000).visible)

  def test_actual_interface_isolated_camera_bad_counter_keeps_required_health(self):
    for lka in (True, False):
      cp = params(lka)
      ci, baseline = CarInterface(cp), CarInterface(params(lka))
      ci.update([])
      baseline.update([])
      packer = CANPacker(DBC[cp.carFingerprint][Bus.pt])
      camera = ci.CS.gv70_camera_lead
      good = camera_packet(packer, camera.bus, 1)
      for tick in range(60):
        stamp = 1_000_000_000+tick*10_000_000
        frames = []
        for parser in ci.can_parsers.values():
          self.assertNotIn(0x1b5, parser.addresses)
          for address in parser.addresses:
            name = parser.dbc.addr_to_msg[address].name
            frames.append(CanData(*packer.make_can_msg(name, parser.bus, {})))
        with patch.object(time, 'clock_gettime_ns', return_value=stamp):
          actual = ci.update([(stamp, frames+[good])])
          expected = baseline.update([(stamp, frames)])
        self.assertEqual(actual.canValid, expected.canValid)
        self.assertEqual(actual.canTimeout, expected.canTimeout)
      self.assertTrue(actual.canValid)
      self.assertEqual(camera.observation.producer_boot_ns, 1_000_000_000)
      self.assertIsNone(camera.current(stamp))
      self.assertNotIn(camera.parser, ci.can_parsers.values())

  def test_actual_configure_camera_context_and_50hz_packed_lead_have_no_hysteresis(self):
    for lka in (True, False):
      cp = params(lka)
      ci = CarInterface(cp)
      messages = RadarMessages()
      messages.seen['radarState'] = False
      with patch.object(radar_lead_context.messaging, 'SubMaster', return_value=messages):
        configure_controller(ci, None)
      self.assertIsInstance(ci.CC.gv70_lead_inputs, GV70LeadInputs)
      packer = CANPacker(DBC[cp.carFingerprint][Bus.pt])
      decoder = CANParser(DBC[cp.carFingerprint][Bus.pt], [('SCC_CONTROL', 50)], CanBus(cp).ECAN)
      command = structs.CarControl()
      command.enabled = True
      command.actuators.accel = 1.
      ci.update([])
      values_by_tick = {}
      for tick in range(8):
        messages.now += 10_000_000
        messages.refresh('deviceState', 'carState')
        boot_stamp = messages.now+OFFSET-1000
        frames = []
        for parser in ci.can_parsers.values():
          for address in parser.addresses:
            name = parser.dbc.addr_to_msg[address].name
            frames.append(CanData(*packer.make_can_msg(name, parser.bus, {})))
        frames.append(camera_packet(packer, ci.CS.gv70_camera_lead.bus, tick+1, 30., -1.))
        with patch.object(time, 'clock_gettime_ns', return_value=messages.now+OFFSET):
          state = ci.update([(boot_stamp, frames)])
        control_now = messages.now
        with patch.object(radar_lead_context, 'clock_pair_ns', side_effect=lambda messages=messages: (messages.now, messages.now+OFFSET)):
          _, outputs = ci.apply(command.as_reader(), control_now)
        packets = [CanData(*frame) for frame in outputs if frame[0] == 0x1a0]
        self.assertEqual(len(packets), int(tick % 2 == 0))
        if packets:
          decoder.update([(boot_stamp, packets)])
          values_by_tick[tick] = dict(decoder.vl['SCC_CONTROL'])
      self.assertTrue(state.canValid)
      self.assertFalse(state.canTimeout)
      self.assertEqual(values_by_tick[0]['ACC_ObjDist'], 0.)
      self.assertEqual(values_by_tick[0]['ObjValid'], 1)
      self.assertEqual(values_by_tick[2]['ACC_ObjDist'], 30.)
      self.assertAlmostEqual(values_by_tick[2]['ACC_ObjRelSpd'], -1., places=12)
      self.assertEqual(values_by_tick[2]['ObjValid'], 0)
      self.assertEqual(values_by_tick[2]['OBJ_STATUS'], 2)
      self.assertEqual(values_by_tick[2]['JerkUpperLimit'], 1.5)
      self.assertAlmostEqual(values_by_tick[2]['aReqValue'], .06)

  def test_optional_constructor_failure_and_unchanged_generic_helper_bytes(self):
    ci = CarInterface(params())
    with patch.object(radar_lead_context.messaging, 'SubMaster', side_effect=OSError('explicit constructor failure')), \
         patch('openpilot.starpilot.controller_extensions.cloudlog.exception') as diagnostic:
      configure_controller(ci, None)
    self.assertIsNone(ci.CC.gv70_lead_inputs)
    diagnostic.assert_called_once()
    for car in (CAR.KIA_EV6, CAR.HYUNDAI_IONIQ_6):
      cp = params()
      cp.carFingerprint = car
      old, new = CANPacker(DBC[car][Bus.pt]), CANPacker(DBC[car][Bus.pt])
      arguments = (CanBus(cp), True, 0., .5, False, False, 80., structs.CarControl.HUDControl())
      expected_values = {'ACCMode': 1, 'MainMode_ACC': 1, 'StopReq': 0, 'aReqValue': .1, 'aReqRaw': .5,
                         'VSetDis': 80., 'JerkLowerLimit': 5., 'JerkUpperLimit': 3., 'ACC_ObjDist': 1,
                         'ObjValid': 0, 'OBJ_STATUS': 2, 'SET_ME_2': 4, 'SET_ME_3': 3, 'SET_ME_TMP_64': 100,
                         'DISTANCE_SETTING': 0}
      self.assertEqual(old.make_can_msg('SCC_CONTROL', CanBus(cp).ECAN, expected_values), create_acc_control(new, *arguments))
