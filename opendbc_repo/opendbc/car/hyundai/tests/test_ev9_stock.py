"""Exact EV9 stock-SCC metadata, decoder and ordinary request boundary."""
import math
import unittest

from opendbc.can import CANPacker
from opendbc.car import Bus, structs
from opendbc.car.hyundai.ccnc_ev_stock import qualified, replacement_requested
from opendbc.car.hyundai.fingerprints import FW_VERSIONS
from opendbc.car.hyundai.interface import CarInterface
from opendbc.car.hyundai.tests.test_ioniq5pe_stock import params, update
from opendbc.car.hyundai.values import CAR, DBC, HyundaiFlags
from opendbc.car.interfaces import get_torque_params


class TestEV9Stock(unittest.TestCase):
  def test_original_metadata_and_constructor(self):
    cfg = CAR.KIA_EV9.config
    self.assertEqual((cfg.specs.mass, cfg.specs.wheelbase, cfg.specs.steerRatio), (2664, 3.1, 16))
    self.assertEqual(cfg.flags, HyundaiFlags.CANFD | HyundaiFlags.EV | HyundaiFlags.CANFD_ANGLE_STEERING | HyundaiFlags.CCNC)
    self.assertEqual(cfg.dbc_dict[Bus.radar], "hyundai_mrr35_radar_generated")
    tune = get_torque_params()[CAR.KIA_EV9]
    self.assertEqual(tune["MAX_LAT_ACCEL_MEASURED"], 2.5)
    self.assertTrue(math.isnan(tune["LAT_ACCEL_FACTOR"]))
    self.assertEqual(CarInterface.get_std_params(CAR.KIA_EV9).maxLateralAccel, 2.5)
    self.assertEqual(set(FW_VERSIONS[CAR.KIA_EV9]), {(structs.CarParams.Ecu.fwdCamera, 0x7c4, None),
                                                 (structs.CarParams.Ecu.fwdRadar, 0x7d0, None)})

  def test_exact_stock_topology_and_no_automatic_long(self):
    for alpha in (False, True):
      for release in (False, True):
        with self.subTest(alpha=alpha, release=release):
          cp = params(candidate=CAR.KIA_EV9, alpha=alpha, release=release)
          self.assertTrue(qualified(cp))
          self.assertEqual(cp.safetyConfigs[0].safetyParam, 0x5c91)
          self.assertFalse(cp.openpilotLongitudinalControl)
          self.assertTrue(cp.pcmCruise)
          self.assertEqual(cp.alphaLongitudinalAvailable, not release)
          self.assertFalse(cp.steerAtStandstill)
          self.assertEqual(cp.longitudinalActuatorDelay, 0.5)
    for alpha in (False, True):
      for missing in (0x35, 0x110, 0x362, 0x1cf, 0x1a0):
        cp = params(candidate=CAR.KIA_EV9, missing=missing, alpha=alpha)
        self.assertFalse(qualified(cp))
        self.assertFalse(cp.alphaLongitudinalAvailable)
        self.assertFalse(cp.openpilotLongitudinalControl)
      for topology in ("lka", "lfa"):
        cp = params(candidate=CAR.KIA_EV9, topology=topology, alpha=alpha)
        self.assertFalse(qualified(cp))
        self.assertFalse(cp.alphaLongitudinalAvailable)
        self.assertFalse(cp.openpilotLongitudinalControl)
      for release in (False, True):
        pe = params(alpha=alpha, release=release)
        self.assertFalse(pe.alphaLongitudinalAvailable)
        self.assertFalse(pe.openpilotLongitudinalControl)
        self.assertEqual(pe.safetyConfigs[0].safetyParam, 0x5491)

  def test_actual_ev_decoder_and_all_lv2_faults(self):
    cp = params(candidate=CAR.KIA_EV9)
    ci = CarInterface(cp)
    self.assertEqual(ci.CS.gear_msg_canfd, "ACCELERATOR")
    packer = CANPacker(DBC[cp.carFingerprint][Bus.pt])
    ci.update([])
    for tick in range(1, 13):
      state = update(ci, packer, tick)
    self.assertTrue(state.canValid)
    self.assertEqual(state.gearShifter, structs.CarState.GearShifter.drive)
    for fault in range(1, 8):
      state = update(ci, packer, 12 + fault, fault=fault)
      self.assertTrue(state.steerFaultTemporary)

  def test_normal_lateral_request_releases_at_standstill_and_fault(self):
    cp = params(candidate=CAR.KIA_EV9)
    state = structs.CarState(canValid=True, gearShifter=structs.CarState.GearShifter.drive)
    state.cruiseState.enabled = True
    control = structs.CarControl(enabled=True, latActive=True)
    self.assertTrue(replacement_requested(cp, control, state))
    for field in ("standstill", "brakePressed", "gasPressed", "steerFaultTemporary", "canTimeout"):
      setattr(state, field, True)
      self.assertFalse(replacement_requested(cp, control, state))
      setattr(state, field, False)
    control.latActive = False
    self.assertFalse(replacement_requested(cp, control, state))

  def test_actual_state_fault_and_ordered_replacement_recipe(self):
    cp = params(candidate=CAR.KIA_EV9)
    ci = CarInterface(cp)
    packer = CANPacker(DBC[cp.carFingerprint][Bus.pt])
    ci.update([])
    command = structs.CarControl()
    command.enabled = command.latActive = True
    command.actuators.steeringAngleDeg = 5.0
    for warmup in range(1, 13):
      state = update(ci, packer, warmup)
    self.assertTrue(state.canValid)
    self.assertFalse(state.canTimeout)
    tick = 0
    for fault, moving, gear, cruise, active in [(0, True, 5, True, True),
                                               *[(value, True, 5, True, True) for value in range(1, 8)],
                                               (0, False, 5, True, True), (0, True, 7, True, True),
                                               (0, True, 5, False, True), (0, True, 5, True, False),
                                               (0, True, 5, True, True)]:
      with self.subTest(fault=fault, moving=moving, gear=gear, cruise=cruise, active=active):
        command.latActive = active
        state = update(ci, packer, tick + 13, fault=fault, moving=moving, gear=gear, cruise=cruise)
        self.assertEqual(state.steerFaultTemporary, fault != 0)
        self.assertEqual(state.standstill, not moving)
        expected = fault == 0 and moving and gear == 5 and cruise and active
        self.assertEqual(bool(replacement_requested(cp, command, state)), expected)
        _, frames = ci.apply(command.as_reader(), (tick + 13) * 10_000_000)
        addresses = [frame[0] for frame in frames]
        self.assertEqual(0x110 in addresses, expected)
        self.assertEqual(0x362 in addresses, expected and tick % 5 == 0)
        if 0x362 in addresses:
          self.assertLess(addresses.index(0x110), addresses.index(0x362))
        tick += 1

  def test_original_ev9_optional_corner_and_rear_blindspots(self):
    cp = params(candidate=CAR.KIA_EV9)
    self.assertTrue(cp.deprecated.enableBsm)
    ci = CarInterface(cp)
    packer = CANPacker(DBC[cp.carFingerprint][Bus.pt])
    ci.update([])
    for tick in range(1, 13):
      state = update(ci, packer, tick)
    self.assertTrue(state.canValid)  # No optional corner sources in startup.
    for tick, (rear_left, rear_right, corner, expected) in enumerate(
        ((0, 0, 0x10, (True, False)), (0, 0, 0x08, (False, True)),
         (1, 0, 0x08, (True, True)), (0, 1, 0, (False, True)), (0, 0, 0, (False, False))), 14):
      update(ci, packer, tick)
      messages = [packer.make_can_msg("ADAS_CMD_50_50ms", 1, {"BCW_LtIndSta": rear_left, "BCW_RtIndSta": rear_right}),
                  packer.make_can_msg("BLINDSPOTS_FRONT_CORNER_2", 1, {"SIDE_DETECT_STATE": corner})]
      state = ci.update([(tick * 10_000_000 + 1, messages)])
      self.assertTrue(state.canValid)
      self.assertEqual((state.leftBlindspot, state.rightBlindspot), expected)
