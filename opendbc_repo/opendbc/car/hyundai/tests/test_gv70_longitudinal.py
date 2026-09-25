"""First-generation GV70 demand/cancel policy through actual CAN callers."""
import unittest

from opendbc.can.packer import CANPacker
from opendbc.can.parser import CANParser
from opendbc.car import Bus, CanData, gen_empty_fingerprint, structs
from opendbc.car.hyundai.gv70_longitudinal import scc_request, suppress_stock_cancel
from opendbc.car.hyundai.hyundaicanfd import CanBus, create_acc_control
from opendbc.car.hyundai.interface import CarInterface
from opendbc.car.hyundai.values import CAR, DBC, HyundaiFlags


def params(car=CAR.GENESIS_GV70_ELECTRIFIED_1ST_GEN, alpha=True, *, lka=True, alt=False):
  fp = gen_empty_fingerprint()
  if lka:
    fp[2][0x50] = 16
  fp[1 if lka else 0][0x1aa if alt else 0x1cf] = 16 if alt else 8
  fw = [structs.CarParams.CarFw(ecu=structs.CarParams.Ecu.adas)] if lka else []
  return CarInterface.get_params(car, fp, fw, alpha, False, False)


def update(ci, packer, tick, brake=False):
  can = CanBus(ci.CP)
  frames = [CanData(*packer.make_can_msg('WHEEL_SPEEDS', can.ECAN,
             dict.fromkeys(('WHL_SpdFLVal', 'WHL_SpdFRVal', 'WHL_SpdRLVal', 'WHL_SpdRRVal'), 36.))),
            CanData(*packer.make_can_msg('ACCELERATOR', can.ECAN, {'GEAR': 4})),
            CanData(*packer.make_can_msg('TCS', can.ECAN, {'DriverBraking': int(brake)})),
            CanData(*packer.make_can_msg('CAM_0x2a4', can.CAM, {})),
            CanData(*packer.make_can_msg('CRUISE_BUTTONS_ALT', can.ECAN, {})),
            CanData(*packer.make_can_msg('SCC_CONTROL', can.CAM if ci.CP.flags & HyundaiFlags.CANFD_CAMERA_SCC else can.ECAN, {}))]
  return ci.update([((tick+1)*10_000_000, frames)])


class TestGV70Longitudinal(unittest.TestCase):
  def test_demand_thresholds_disable_override_and_shaped_history(self):
    for raw, stop, lower in ((-.999, False, 2.), (-1., False, 5.), (.7, True, 5.)):
      result = scc_request(True, False, stop, raw, 0.)
      self.assertEqual(result.raw_accel, raw)
      self.assertEqual(result.jerk_lower, lower)
      self.assertEqual(result.jerk_upper, 1.5)
      self.assertAlmostEqual(result.accel, min(max(raw, -lower/50.), .03))
    for enabled, override in ((False, False), (True, True)):
      self.assertEqual(scc_request(enabled, override, False, 1., .5).accel, 0.)
    self.assertAlmostEqual(scc_request(True, False, False, 1., .03).accel, .06)

  def test_actual_50hz_sender_raw_shaped_jerk_and_disabled_modes(self):
    for lka, alt in ((True, False), (False, False), (False, True)):
      with self.subTest(lka=lka, alt=alt):
        cp = params(lka=lka, alt=alt)
        self.assertTrue(cp.openpilotLongitudinalControl)
        self.assertEqual(bool(cp.flags & HyundaiFlags.CANFD_LKA_STEER_MSG), lka)
        self.assertEqual(bool(cp.flags & HyundaiFlags.CANFD_ALT_BUTTONS), alt)
        ci = CarInterface(cp)
        packer = CANPacker(DBC[cp.carFingerprint][Bus.pt])
        decoder = CANParser(DBC[cp.carFingerprint][Bus.pt], [('SCC_CONTROL', 50)], CanBus(cp).ECAN)
        command = structs.CarControl()
        history = 0.
        for tick in range(14):
          raw, stop, enabled, override = [(1., False, True, False), (-.5, False, True, False),
                                         (-1., False, True, False), (.8, True, True, False),
                                         (.4, False, True, True), (.8, False, False, False),
                                         (1., False, True, False)][tick//2]
          command.enabled = enabled
          command.cruiseControl.override = override
          command.actuators.accel = raw
          command.actuators.longControlState = structs.CarControl.Actuators.LongControlState.stopping if stop else \
                                               structs.CarControl.Actuators.LongControlState.pid
          update(ci, packer, tick)
          _, outputs = ci.apply(command.as_reader(), (tick+1)*10_000_000)
          packets = [CanData(*frame) for frame in outputs if frame[0] == 0x1a0]
          self.assertEqual(len(packets), int(tick % 2 == 0))
          if not packets:
            self.assertEqual(ci.CC.accel_last, history)
            continue
          lower = 5. if stop or raw <= -1. else 2.
          history = min(max(raw, history-lower/50.), history+.03) if enabled and not override else 0.
          decoder.update([((tick+1)*10_000_000, packets)])
          values = decoder.vl['SCC_CONTROL']
          self.assertAlmostEqual(values['aReqRaw'], raw if enabled and not override else 0., places=2)
          self.assertAlmostEqual(values['aReqValue'], history, places=2)
          self.assertEqual(values['JerkUpperLimit'], 1.5)
          self.assertEqual(values['JerkLowerLimit'], lower)
          self.assertEqual(values['ACCMode'], 0 if not enabled else 2 if override else 1)
          self.assertEqual(values['StopReq'], int(stop))
          self.assertEqual(values['MainMode_ACC'], 1)
          self.assertAlmostEqual(ci.CC.accel_last, history)

  def test_stock_brake_cancel_scope_through_actual_controller(self):
    for car, brake, lateral, suppress, lka, alt in (
        (CAR.GENESIS_GV70_ELECTRIFIED_1ST_GEN, True, True, True, True, False),
        (CAR.GENESIS_GV70_ELECTRIFIED_1ST_GEN, False, True, False, True, False),
        (CAR.GENESIS_GV70_ELECTRIFIED_1ST_GEN, True, False, False, True, False),
        (CAR.KIA_EV6, True, True, False, True, False),
        (CAR.GENESIS_GV70_ELECTRIFIED_1ST_GEN, True, True, True, False, False),
        (CAR.GENESIS_GV70_ELECTRIFIED_1ST_GEN, False, True, False, False, False),
        (CAR.GENESIS_GV70_ELECTRIFIED_1ST_GEN, True, True, True, False, True),
        (CAR.GENESIS_GV70_ELECTRIFIED_1ST_GEN, False, True, False, False, True)):
      cp = params(car, False, lka=lka, alt=alt)
      self.assertEqual(bool(cp.flags & HyundaiFlags.CANFD_LKA_STEER_MSG), lka)
      self.assertEqual(bool(cp.flags & HyundaiFlags.CANFD_ALT_BUTTONS), alt)
      self.assertEqual(suppress_stock_cancel(cp, brake, lateral), suppress)
      ci = CarInterface(cp)
      # Non-LKA parsers lazily subscribe TCS on the first actual state update.
      # Prime registration before the first observed brake frame.
      ci.update([])
      packer = CANPacker(DBC[car][Bus.pt])
      command = structs.CarControl()
      command.cruiseControl.cancel = True
      command.latActive = lateral
      buttons = []
      for tick in range(60):
        state = update(ci, packer, tick, brake)
        self.assertEqual(state.brakePressed, brake, (car, lka, alt, tick))
        _, outputs = ci.apply(command.as_reader(), (tick+1)*10_000_000)
        buttons.extend(frame for frame in outputs if frame[0] == (0x1a0 if alt else 0x1cf))
      self.assertEqual(bool(buttons), not suppress)

  def test_raw_optional_keyword_preserves_generic_and_ioniq_defaults(self):
    for car in (CAR.KIA_EV6, CAR.HYUNDAI_IONIQ_6):
      cp = params(car)
      first, second = CANPacker(DBC[car][Bus.pt]), CANPacker(DBC[car][Bus.pt])
      args = (CanBus(cp), True, 0., .5, False, False, 80., structs.CarControl.HUDControl())
      self.assertEqual(create_acc_control(first, *args), create_acc_control(second, *args, raw_accel=None))
