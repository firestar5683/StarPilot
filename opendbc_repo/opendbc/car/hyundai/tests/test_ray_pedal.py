import unittest

from opendbc.can import CANPacker, CANParser
from opendbc.can.dbc import DBC as CANDBC, SignalType
from opendbc.car import Bus, gen_empty_fingerprint, structs
from opendbc.car.hyundai.carcontroller import CarController
from opendbc.car.hyundai.carstate import CarState
from opendbc.car.hyundai.interface import CarInterface
from opendbc.car.hyundai.ray_pedal import create_ray_pedal_command, ray_pedal_gas, ray_pedal_enabled
from opendbc.car.hyundai.values import CAR, DBC, HyundaiSafetyFlags


def ray_fingerprint(sensor=6, lfa=8):
  fp = gen_empty_fingerprint()
  fp[0].update({0x201: sensor, 0x391: 8})
  fp[2][0x485] = lfa
  return fp


def ray_controller():
  cp = CarInterface.get_params(CAR.KIA_RAY_EV, ray_fingerprint(), [], False, False, False)
  controller = CarController(DBC[cp.carFingerprint], cp)
  state = CarState(cp)
  state.out = structs.CarState()
  state.out.vEgo = state.out.vEgoRaw = 12
  state.out.gearShifter = structs.CarState.GearShifter.drive
  state.ray_pedal_valid = True
  state.ray_pedal_state = 0
  parser = CANParser(DBC[cp.carFingerprint][Bus.pt], [('LKAS11', 0), ('CLU11', 0)], 0)
  state.lkas11, state.clu11 = parser.vl['LKAS11'], parser.vl['CLU11']
  command = structs.CarControl()
  command.enabled = command.latActive = command.longActive = True
  command.hudControl.setSpeed = 20
  command.actuators.accel = 1.5
  return cp, controller, command, state


class TestRayPedal(unittest.TestCase):
  def test_actual_cp_signature_is_unique_and_requires_exact_sensor_layout(self):
    signature = int(HyundaiSafetyFlags.EV_GAS | HyundaiSafetyFlags.LONG | HyundaiSafetyFlags.NON_SCC |
                    HyundaiSafetyFlags.HAS_LDA_BUTTON | HyundaiSafetyFlags.CAN_REFRESH_MSGS)
    self.assertEqual(signature, 0x9805)
    for car in CAR:
      for alpha in (False, True):
        cp = CarInterface.get_params(car, ray_fingerprint(), [], alpha, False, False)
        self.assertEqual(ray_pedal_enabled(cp), car == CAR.KIA_RAY_EV)
        self.assertEqual(cp.safetyConfigs[-1].safetyParam == signature, car == CAR.KIA_RAY_EV)
    for fp in (ray_fingerprint(sensor=8), ray_fingerprint(lfa=4)):
      cp = CarInterface.get_params(CAR.KIA_RAY_EV, fp, [], False, False, False)
      self.assertFalse(ray_pedal_enabled(cp))
      self.assertFalse(cp.openpilotLongitudinalControl)
      self.assertTrue(cp.pcmCruise)
    cp, _, _, _ = ray_controller()
    self.assertTrue(cp.openpilotLongitudinalControl)
    self.assertFalse(cp.pcmCruise)
    self.assertFalse(cp.autoResumeSng)
    self.assertEqual(cp.minEnableSpeed, -1)

  def test_sensor_real_route_crc_fault_and_physical_override(self):
    cp, _, _, state = ray_controller()
    parsers = state.get_can_parsers(cp)
    state.update(parsers)
    samples = ['01f403d55de8', '01f603d55ef1', '01f403d55f51', '01f603d3503f', '01f903d551ab', '01f903d552a4', '01f703d55370']
    for index, sample in enumerate(samples):
      frame = (0x201, bytes.fromhex(sample), 0)
      parsers[Bus.party].update([(1_000_000_000 + index * 20_000_000, [frame])])
      result = state.update(parsers)
      self.assertTrue(state.ray_pedal_valid)
      self.assertEqual(state.ray_pedal_state, 5)
      self.assertTrue(result.accFaulted)
    prior = dict(parsers[Bus.party].vl['GAS_SENSOR'])
    bad = bytearray(bytes.fromhex(samples[-1]))
    bad[-1] ^= 1
    parsers[Bus.party].update([(1_160_000_000, [(0x201, bytes(bad), 0)])])
    self.assertEqual(dict(parsers[Bus.party].vl['GAS_SENSOR']), prior)
    packer = CANPacker('hyundai_kia_ray_pedal')
    for counter, tracks, pressed in ((4, (0, 0), False), (5, ((310-264)*.672, (593-497)*.332), True)):
      sensor = packer.make_can_msg('GAS_SENSOR', 0, {'INTERCEPTOR_GAS': tracks[0], 'INTERCEPTOR_GAS2': tracks[1],
                                                   'STATE': 0, 'COUNTER_PEDAL': counter})
      parsers[Bus.party].update([(1_200_000_000 + counter * 20_000_000, [sensor])])
      result = state.update(parsers)
      self.assertFalse(result.accFaulted)
      self.assertEqual(result.gasPressed, pressed)
    camera = CANPacker(DBC[cp.carFingerprint][Bus.pt]).make_can_msg('LABEL11', 0, {'CC_React': 1, 'CC_Engaged': 1})
    parsers[Bus.pt].update([(1_500_000_000, [camera])])
    result = state.update(parsers)
    self.assertTrue(result.cruiseState.enabled)
    self.assertTrue(result.cruiseState.available)

  def test_checksum_extension_is_scoped_to_ray_dbc(self):
    for name in ('honda_accord_2017_can_ext_generated', 'toyota_nodsu_pt_generated'):
      db = CANDBC(name)
      for msg in db.name_to_msg.values():
        for sig in msg.sigs.values():
          if sig.name in ('CHECKSUM_PEDAL', 'COUNTER_PEDAL'):
            self.assertEqual(sig.type, SignalType.DEFAULT)
            self.assertIsNone(sig.calc_checksum)
    db = CANDBC('hyundai_kia_ray_pedal')
    self.assertEqual(db.name_to_msg['GAS_SENSOR'].sigs['CHECKSUM_PEDAL'].type, SignalType.RAY_PEDAL_CHECKSUM)
    packet = create_ray_pedal_command(CANPacker('hyundai_kia_ray_pedal'), 0, 15)
    self.assertEqual(packet[1][:4], bytes(4))
    self.assertEqual(packet[1][4] & 15, 15)

  def test_controller_cadence_override_cancellation_and_no_scc_commands(self):
    cp, controller, command, state = ray_controller()

    def messages(frame):
      controller.frame = frame
      return controller.update(command.as_reader(), state, frame * 10_000_000)[1]
    first = messages(0)
    self.assertFalse(any(frame[0] == 0x340 for frame in first))
    self.assertTrue(any(frame[0] == 0x485 and len(frame[1]) == 8 for frame in first))
    self.assertFalse(any(frame[0] in (0x420, 0x421, 0x50A, 0x389, 0x7D0) for frame in first))
    self.assertTrue(any(frame[0] == 0x340 for frame in messages(1)))
    self.assertFalse(any(frame[0] == 0x200 for frame in messages(2)))
    for frame in range(4, 160, 4):
      pedal = next(m for m in messages(frame) if m[0] == 0x200)
      self.assertEqual(pedal[1][4] & 15, frame // 4 & 15)
    self.assertAlmostEqual(controller._ray_pedal_gas_last, .55)
    for cause in ('brake', 'gas', 'override', 'inactive', 'invalid', 'fault'):
      with self.subTest(cause=cause):
        cp, controller, command, state = ray_controller()
        if cause == 'brake':
          state.out.brakePressed = True
        elif cause == 'gas':
          state.out.gasPressed = True
        elif cause == 'override':
          command.cruiseControl.override = True
        elif cause == 'inactive':
          command.longActive = False
        elif cause == 'invalid':
          state.ray_pedal_valid = False
        else:
          state.ray_pedal_state = 5
        pedal = next(m for m in messages(20) if m[0] == 0x200)
        self.assertEqual(pedal[1][:4], bytes(4))
        self.assertFalse(pedal[1][4] & 0x80)
    state.out.cruiseState.enabled = True
    state.out.gasPressed = True
    msgs = messages(24)
    self.assertTrue(any(m[0] == 0x4F1 and m[1][0] & 7 == 4 for m in msgs))
    self.assertFalse(any(m[0] == 0x4F1 for m in messages(25)))

  def test_source_ray_dashboard_icons_active_and_disengaging(self):
    cp, controller, command, state = ray_controller()
    parser = CANParser('hyundai_kia_ray_lfa', [('LFAHDA_MFC', 0)], 0)
    lkas = CANParser(DBC[cp.carFingerprint][Bus.pt], [('LKAS11', 0)], 0)
    for frame in range(106):
      if frame == 5:
        command.enabled = command.latActive = command.longActive = False
      sends = controller.update(command.as_reader(), state, frame*10_000_000)[1]
      parser.update([(frame+1, sends)])
      lkas.update([(frame+1, sends)])
      if frame in (0, 5, 100, 105):
        expected = 2 if frame == 0 else 3 if frame < 104 else 0
        self.assertEqual(parser.vl['LFAHDA_MFC']['LFA_Icon_State'], expected)
        if frame:
          self.assertEqual(lkas.vl['LKAS11']['CF_Lkas_FcwOpt_USM'], expected or 1)

  def test_exact_latest_taper_rate_and_regen_behavior(self):
    gas = 0
    for _ in range(40):
      gas = ray_pedal_gas(gas, 12, 1.5, 20)
    self.assertEqual(gas, .55)
    gas = ray_pedal_gas(gas, 12, 1.5, 12)
    self.assertAlmostEqual(gas, .55 * .65)
    gas = ray_pedal_gas(gas, 12, 1.5, 11.8)
    self.assertAlmostEqual(gas, .55 * .65 * .6)
    for speed in (11.4, float('nan'), .9, 40.1):
      self.assertEqual(ray_pedal_gas(gas, 12, 1.5, speed), 0)
    self.assertEqual(ray_pedal_gas(.55, 12, -1.5, 20), 0)
