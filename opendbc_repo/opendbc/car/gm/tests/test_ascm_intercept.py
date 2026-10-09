import unittest

from opendbc.can import CANPacker
from opendbc.car import Bus, structs
from opendbc.car import gen_empty_fingerprint
from opendbc.car.gm.carstate import CarState
from opendbc.car.gm import gmcan
from opendbc.car.gm.values import CruiseButtons
from opendbc.car.gm.interface import CarInterface
from opendbc.car.gm.fingerprints import FINGERPRINTS, FW_VERSIONS
from opendbc.car.gm.values import ASCM_INTERCEPT_CAR, CAR, DBC, GMSafetyFlags, CarControllerParams
from opendbc.car.structs import CarParams


def params(car, *, sascm=False, accelerator=True, radar=False, alpha=False, release=False):
  fp = gen_empty_fingerprint()
  if sascm:
    fp[0][0x2ff] = 8
  if accelerator:
    fp[0][0xbe] = 6
  if radar:
    fp[1][0x460] = 8
  return CarInterface.get_params(car, fp, [], alpha, release, False)


class TestAscmIntercept(unittest.TestCase):
  def authority_frame(self, ci, packer, tick, *, status=1, active=True, main=True,
                      regen=False, brake=False, button=CruiseButtons.UNPRESS, driver=0., speed=8., torque=0.02,
                      malformed=False, physical_delay_ns=0, eps_missing=False):
    now = 1_000_000_000 + tick * 10_000_000
    values = {
      'ECMCruiseControl': {'CruiseActive': 0},
      'ECMEngineStatus': {'CruiseMainOn': int(main), 'BrakePressed': int(brake)},
      'AcceleratorPedal2': {'CruiseState': 0},
      'ECMPRDNL2': {'PRNDL2': 4},
      'EBCMWheelSpdRear': {'RLWheelSpd': speed * 3.6, 'RRWheelSpd': speed * 3.6, 'RLWheelDir': 1, 'RRWheelDir': 1},
      'EBCMWheelSpdFront': {'FLWheelSpd': speed * 3.6, 'FRWheelSpd': speed * 3.6},
      'ESPStatus': {'TractionControlOn': 1},
      'BCMDoorBeltStatus': {'LeftSeatBelt': 1},
      'BCMGeneralPlatformStatus': {}, 'BCMTurnSignals': {}, 'PSCMSteeringAngle': {},
      'ECMAcceleratorPos': {'BrakePedalPos': 30 if brake else 0},
      'EBCMFrictionBrakeStatus': {}, 'EBCMRegenPaddle': {'RegenPaddle': int(regen)},
    }
    packets = [packer.make_can_msg(name, 0, signals) for name, signals in values.items()]
    packets += [gmcan.create_buttons(packer, 0, tick % 4, button),
                packer.make_can_msg('ASCMLKASteeringCmd', 2, {}),
                packer.make_can_msg('ASCMActiveCruiseControlStatus', 2, {}),
                packer.make_can_msg('AEBCmd', 2, {})]
    if tick % 10 == 0 and not eps_missing:
      pscm = packer.make_can_msg('PSCMStatus', 0, {'LKATorqueDeliveredStatus': status,
                                                'LKADriverAppldTrq': driver, 'LKATorqueDelivered': 0})
      if malformed:
        packets.append((0x184, b'\x00', 0))
      packets.append(pscm)
    physical = [packet for packet in packets if packet[0] in (0xC9, 0xBE, 0xBD, 0x1E1)]
    other = [packet for packet in packets if packet[0] not in (0xC9, 0xBE, 0xBD, 0x1E1)]
    cs = ci.update([(now - physical_delay_ns, physical), (now, other)])
    if tick >= 10 and not eps_missing:
      self.assertTrue(cs.canValid, (tick, status))
      self.assertFalse(cs.canTimeout, tick)
    cc = structs.CarControl()
    cc.enabled = active
    cc.latActive = active
    cc.actuators.torque = torque
    cc.hudControl.setSpeed = 30
    _, sends = ci.apply(cc.as_reader(), now)
    steering = [data for address, data, bus in sends if address == 0x180 and bus == 0]
    if steering:
      self.assertEqual(bool((steering[-1][0] >> 3) & 1), active and not ci.CS.steering_authority.latched, tick)
    return cs

  def test_volt_steering_loss_requires_driver_rearm(self):
    for reset in ('regen', 'brake', 'cancel', 'set', 'main'):
      with self.subTest(reset=reset):
        cp = params(CAR.CHEVROLET_VOLT_ASCM, sascm=True, alpha=True, radar=True)
        ci, packer = CarInterface(cp), CANPacker(DBC[cp.carFingerprint][Bus.pt])
        for tick in range(30):
          self.authority_frame(ci, packer, tick)
        self.assertTrue(ci.CS.steering_authority.seen_active)
        # One emitted neutral frame must not erase the confirmed EPS episode.
        for tick in range(30, 34):
          self.authority_frame(ci, packer, tick, active=False)
        for tick in range(34, 41):
          cs = self.authority_frame(ci, packer, tick, status=0)
        self.assertTrue(cs.steerFaultTemporary)
        self.assertTrue(ci.CS.steering_authority.latched)
        for tick in range(41, 60):
          cs = self.authority_frame(ci, packer, tick, active=False)
        self.assertTrue(cs.steerFaultTemporary)  # EPS recovery/automatic CC off cannot rearm.
        for tick in range(60, 70):
          self.authority_frame(ci, packer, tick, active=False, main=reset != 'main',
                               regen=reset == 'regen', brake=reset == 'brake',
                               button=CruiseButtons.CANCEL if reset == 'cancel' else CruiseButtons.UNPRESS)
        cs = self.authority_frame(ci, packer, 70, active=False, physical_delay_ns=200_000_000 if reset == 'main' else 1_000_000,
                                  button=CruiseButtons.DECEL_SET if reset == 'set' else
                                  CruiseButtons.RES_ACCEL if reset != 'main' else CruiseButtons.UNPRESS)
        if reset in ('set', 'main'):
          self.assertTrue(cs.steerFaultTemporary, reset)
          cs = self.authority_frame(ci, packer, 71, active=False)
        resume_tick = 72
        if reset == 'set':
          # SET alone is not the physical disable required to reset a loss latch.
          self.assertTrue(cs.steerFaultTemporary, reset)
          self.assertTrue(ci.CS.steering_authority.latched, reset)
          self.assertEqual(ci.CS.steering_authority.disable_ns, 0, reset)
          for tick in range(72, 82):
            self.authority_frame(ci, packer, tick, active=False, regen=True)
          self.assertGreater(ci.CS.steering_authority.neutral_ns, ci.CS.steering_authority.disable_ns, reset)
          cs = self.authority_frame(ci, packer, 82, active=False, button=CruiseButtons.DECEL_SET)
          self.assertTrue(cs.steerFaultTemporary, reset)
          cs = self.authority_frame(ci, packer, 83, active=False)
          resume_tick = 84
        context = (reset, cs.buttonEnable, cs.brakePressed, cs.regenBraking,
                   ci.CS.steering_authority.disable_ns, ci.CS.steering_authority.neutral_ns)
        self.assertFalse(cs.steerFaultTemporary, context)
        self.assertFalse(ci.CS.steering_authority.latched, context)
        for tick in range(resume_tick, resume_tick + 20):
          self.authority_frame(ci, packer, tick)
        self.assertTrue(ci.CS.steering_authority.seen_active, context)

  def test_volt_steering_acquisition_and_invalid_status(self):
    for status, malformed in ((0, False), (4, False), (1, True)):
      with self.subTest(status=status, malformed=malformed):
        cp = params(CAR.CHEVROLET_VOLT_ASCM, sascm=True, alpha=True, radar=True)
        ci, packer = CarInterface(cp), CANPacker(DBC[cp.carFingerprint][Bus.pt])
        for tick in range(30):
          cs = self.authority_frame(ci, packer, tick, status=status, malformed=malformed)
          self.assertFalse(cs.steerFaultTemporary, tick)
        for tick in range(30, 41):
          cs = self.authority_frame(ci, packer, tick, status=status, malformed=malformed)
        self.assertTrue(cs.steerFaultTemporary)
        self.assertTrue(ci.CS.steering_authority.latched)

    cp = params(CAR.CHEVROLET_VOLT_ASCM, sascm=True, alpha=True, radar=True)
    ci, packer = CarInterface(cp), CANPacker(DBC[cp.carFingerprint][Bus.pt])
    for tick in range(30):
      self.authority_frame(ci, packer, tick)
    for tick in range(30, 70):
      cs = self.authority_frame(ci, packer, tick, active=tick < 40, eps_missing=True)
    self.assertTrue(cs.steerFaultTemporary)
    for tick in range(70, 90):
      cs = self.authority_frame(ci, packer, tick, active=False)
    self.assertTrue(cs.steerFaultTemporary)  # Fresh EPS does not erase a missing-feed latch.

    # A total receive gap cannot conceal a stale EPS episode on the first fresh return.
    cp = params(CAR.CHEVROLET_VOLT_ASCM, sascm=True, alpha=True, radar=True)
    ci, packer = CarInterface(cp), CANPacker(DBC[cp.carFingerprint][Bus.pt])
    for tick in range(30):
      self.authority_frame(ci, packer, tick)
    cs = self.authority_frame(ci, packer, 70)
    self.assertTrue(cs.steerFaultTemporary)
    self.assertTrue(ci.CS.steering_authority.latched)

  def test_volt_steering_healthy_zero_and_existing_faults(self):
    for status, active, speed, driver in ((1, True, 8., 0.), (0, False, 8., 0.),
                                         (0, True, 0., 0.), (0, True, 8., 3.),
                                         (2, True, 8., 0.), (3, True, 8., 0.)):
      with self.subTest(status=status, active=active, speed=speed, driver=driver):
        cp = params(CAR.CHEVROLET_VOLT_ASCM, sascm=True, alpha=True, radar=True)
        ci, packer = CarInterface(cp), CANPacker(DBC[cp.carFingerprint][Bus.pt])
        for tick in range(60):
          cs = self.authority_frame(ci, packer, tick, status=status, active=active, speed=speed, driver=driver,
                                    torque=0. if status == 1 else 0.02)
        self.assertFalse(ci.CS.steering_authority.latched)
        self.assertEqual(cs.steerFaultTemporary, status == 2)
        self.assertEqual(cs.steerFaultPermanent, status == 3)
    # A genuine driver pause starts a new acquisition window, unlike an unexplained brief CC drop.
    for pause in ('regen', 'brake', 'cancel', 'main', 'override', 'standstill'):
      with self.subTest(pause=pause):
        cp = params(CAR.CHEVROLET_VOLT_ASCM, sascm=True, alpha=True, radar=True)
        ci, packer = CarInterface(cp), CANPacker(DBC[cp.carFingerprint][Bus.pt])
        for tick in range(30):
          self.authority_frame(ci, packer, tick)
        for tick in range(30, 50):
          cs = self.authority_frame(ci, packer, tick, status=0, active=False,
                                    regen=pause == 'regen', brake=pause == 'brake', main=pause != 'main',
                                    button=CruiseButtons.CANCEL if pause == 'cancel' else CruiseButtons.UNPRESS,
                                    driver=3. if pause == 'override' else 0., speed=0. if pause == 'standstill' else 8.)
          self.assertFalse(cs.steerFaultTemporary)
        for tick in range(50, 70):
          cs = self.authority_frame(ci, packer, tick, status=0 if tick < 65 else 1)
          self.assertFalse(cs.steerFaultTemporary, tick)
        for tick in range(70, 80):
          cs = self.authority_frame(ci, packer, tick)
          self.assertFalse(cs.steerFaultTemporary, tick)
        self.assertTrue(ci.CS.steering_authority.seen_active)
    # Ordinary temporary EPS faults retain their normal recovery/acquisition behavior.
    cp = params(CAR.CHEVROLET_VOLT_ASCM, sascm=True, alpha=True, radar=True)
    ci, packer = CarInterface(cp), CANPacker(DBC[cp.carFingerprint][Bus.pt])
    for tick in range(30):
      self.authority_frame(ci, packer, tick)
    for tick in range(30, 50):
      cs = self.authority_frame(ci, packer, tick, status=2, active=False)
      self.assertTrue(cs.steerFaultTemporary)
      self.assertFalse(ci.CS.steering_authority.latched)
    for tick in range(50, 80):
      cs = self.authority_frame(ci, packer, tick, status=0 if tick < 65 else 1)
      self.assertFalse(cs.steerFaultTemporary, tick)
    self.assertTrue(ci.CS.steering_authority.seen_active)
    for cp in (params(CAR.CHEVROLET_VOLT_ASCM), params(CAR.CHEVROLET_VOLT),
               params(CAR.CHEVROLET_BOLT_EUV)):
      self.assertFalse(CarState(cp).steering_authority.enabled)

  def test_eight_manual_ids_have_stock_acc_default(self):
    self.assertEqual(len(ASCM_INTERCEPT_CAR), 8)
    for car in ASCM_INTERCEPT_CAR:
      with self.subTest(car=car):
        cp = params(car)
        self.assertEqual(cp.networkLocation, CarParams.NetworkLocation.fwdCamera)
        self.assertTrue(cp.pcmCruise)
        self.assertFalse(cp.openpilotLongitudinalControl)
        self.assertFalse(cp.alphaLongitudinalAvailable)
        self.assertAlmostEqual(cp.minEnableSpeed, -1. if car == CAR.CADILLAC_ESCALADE_ESV_2019_ASCM else 5 / 3.6, places=6)
        self.assertTrue(cp.safetyConfigs[0].safetyParam & GMSafetyFlags.ASCM_INTERCEPT)
        self.assertFalse(cp.safetyConfigs[0].safetyParam & GMSafetyFlags.HW_CAM_LONG)
        self.assertEqual(car.config.car_docs, [])
        self.assertNotIn(car, FINGERPRINTS)
        self.assertNotIn(car, FW_VERSIONS)

  def test_sascm_alpha_requires_source_opt_in_and_debug(self):
    for car in ASCM_INTERCEPT_CAR:
      for sascm, alpha, release in ((False, True, False), (True, False, False),
                                    (True, True, True), (True, True, False)):
        with self.subTest(car=car, sascm=sascm, alpha=alpha, release=release):
          cp = params(car, sascm=sascm, alpha=alpha, release=release)
          enabled = sascm and alpha and not release
          self.assertEqual(cp.openpilotLongitudinalControl, enabled)
          self.assertEqual(cp.pcmCruise, not enabled)
          self.assertEqual(bool(cp.safetyConfigs[0].safetyParam & GMSafetyFlags.HW_CAM_LONG), enabled)

  def test_brake_source_and_radar_follow_observed_frames(self):
    for car in ASCM_INTERCEPT_CAR:
      for accelerator, radar in ((True, True), (False, False)):
        cp = params(car, accelerator=accelerator, radar=radar)
        self.assertEqual(bool(cp.safetyConfigs[0].safetyParam & GMSafetyFlags.ASCM_BRAKE_C9), not accelerator)
        self.assertEqual(bool(cp.safetyConfigs[0].safetyParam & GMSafetyFlags.ASCM_RADAR), radar)
        self.assertEqual(cp.radarUnavailable, not radar)

  def test_existing_gateway_and_bolt_configuration_unchanged(self):
    gateway = params(CAR.GMC_ACADIA)
    self.assertEqual(gateway.networkLocation, CarParams.NetworkLocation.gateway)
    self.assertTrue(gateway.openpilotLongitudinalControl)
    self.assertFalse(gateway.safetyConfigs[0].safetyParam & GMSafetyFlags.ASCM_INTERCEPT)
    bolt = params(CAR.CHEVROLET_BOLT_EUV)
    self.assertFalse(bolt.safetyConfigs[0].safetyParam & GMSafetyFlags.ASCM_INTERCEPT)

  def test_intercept_alpha_limits_match_ordinary_ascm_long(self):
    cp = params(CAR.CADILLAC_ESCALADE_ASCM, sascm=True, alpha=True)
    limits = CarControllerParams(cp)
    self.assertEqual((limits.MAX_GAS, limits.MAX_ACC_REGEN, limits.INACTIVE_REGEN), (2041., -650., -650.))

  def test_camera_parser_requires_status_but_aeb_is_optional(self):
    for car in ASCM_INTERCEPT_CAR:
      with self.subTest(car=car):
        cp = params(car)
        state = CarState(cp)
        parsers = state.get_can_parsers(cp)
        camera = parsers[Bus.cam]
        packer = CANPacker(DBC[car][Bus.pt])
        steer = packer.make_can_msg("ASCMLKASteeringCmd", 2, {})
        status = packer.make_can_msg("ASCMActiveCruiseControlStatus", 2, {"ACCCruiseState": 0})
        camera.update([(1_000_000_000, [steer, status])])
        self.assertTrue(camera.can_valid)
        out = state.update(parsers)
        self.assertFalse(out.stockAeb)
        self.assertFalse(out.cruiseState.nonAdaptive)
        aeb = packer.make_can_msg("AEBCmd", 2, {"AEBCmdActive": 1})
        camera.update([(1_100_000_000, [steer, status, aeb])])
        self.assertTrue(state.update(parsers).stockAeb)
        camera.update([(12_000_000_000, [steer, status])])
        self.assertTrue(camera.can_valid)
        for index in range(5):
          camera.update([(12_600_000_000 + index * 40_000_000, [steer])])
          _ = camera.can_valid
        self.assertFalse(camera.can_valid)

  def test_intercept_stock_status_never_infers_nonadaptive(self):
    cp = params(CAR.GMC_ACADIA_ASCM)
    state = CarState(cp)
    parsers = state.get_can_parsers(cp)
    camera = parsers[Bus.cam]
    packer = CANPacker(DBC[cp.carFingerprint][Bus.pt])
    for index, cruise_state in enumerate((0, 1, 2, 3)):
      status = packer.make_can_msg("ASCMActiveCruiseControlStatus", 2, {"ACCCruiseState": cruise_state})
      camera.update([(1_000_000_000 + index * 40_000_000, [status])])
      self.assertFalse(state.update(parsers).cruiseState.nonAdaptive)
