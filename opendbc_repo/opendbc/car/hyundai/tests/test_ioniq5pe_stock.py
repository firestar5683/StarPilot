import unittest

from opendbc.can import CANPacker
from opendbc.car import Bus, gen_empty_fingerprint, structs
from opendbc.car.hyundai.interface import CarInterface
from opendbc.car.hyundai.ioniq5pe import qualified, replacement_requested
from opendbc.car.hyundai.values import CAR, DBC


def params(*, candidate=CAR.HYUNDAI_IONIQ_5_PE, alpha=False, release=False, topology="lka_alt", missing=None, gear_metadata=0x130):
  fingerprint = gen_empty_fingerprint()
  fingerprint[1].update({0x35: 32, 0x175: 24, 0xA0: 24, 0xEA: 24, 0x1CF: 8, 0x1A0: 32})
  if gear_metadata is not None:
    fingerprint[1][gear_metadata] = 16 if gear_metadata == 0x130 else 32
  if topology == "lka_alt":
    fingerprint[2].update({0x110: 32, 0x362: 32})
  elif topology == "lka":
    fingerprint[2][0x50] = 16
  if missing is not None:
    for bus in fingerprint.values():
      bus.pop(missing, None)
  return CarInterface.get_params(candidate, fingerprint, [], alpha, release, False)


def update(ci, packer, tick, *, fault=0, moving=True, gear=5, cruise=True):
  wheels = dict.fromkeys(("WHL_SpdFLVal", "WHL_SpdFRVal", "WHL_SpdRLVal", "WHL_SpdRRVal"), 36.0 if moving else 0.0)
  values = {"ACCELERATOR": {"GEAR": gear}, "GEAR_SHIFTER": {"GEAR": gear}, "TCS": {"ACCEnable": 0, "ACC_REQ": int(cruise)},
            "WHEEL_SPEEDS": wheels, "MDPS": {"MDPS_ADAS_AciFltSig_Lv2": fault}, "STEERING_SENSORS": {},
            "DOORS_SEATBELTS": {"DRIVER_SEATBELT": 1}, "BLINKERS": {}, "CRUISE_BUTTONS": {},
            "SCC_CONTROL": {"ACCMode": int(cruise), "VSetDis": 80}}
  frames = [packer.make_can_msg(name, 1, fields) for name, fields in values.items()]
  frames += [packer.make_can_msg("LKAS_ALT", 2, {}), packer.make_can_msg("CAM_0x362", 2, {})]
  return ci.update([(tick * 10_000_000, frames)])


class TestIoniq5PEStock(unittest.TestCase):
  def test_final_stock_cp_and_topology_boundary(self):
    for alpha in (False, True):
      for release in (False, True):
        cp = params(alpha=alpha, release=release)
        self.assertTrue(qualified(cp))
        self.assertEqual(cp.safetyConfigs[0].safetyParam, 0x5491)
        self.assertFalse(cp.openpilotLongitudinalControl)
        self.assertFalse(cp.alphaLongitudinalAvailable)
        self.assertTrue(cp.pcmCruise)
        self.assertEqual(cp.alternativeExperience, 0)
        self.assertAlmostEqual(cp.wheelbase, 2.97)
        self.assertAlmostEqual(cp.longitudinalActuatorDelay, 0.35)
        self.assertTrue(cp.steerAtStandstill)
    for gear_metadata in (None, 0x40):
      cp = params(gear_metadata=gear_metadata)
      self.assertTrue(qualified(cp))
      ci = CarInterface(cp)
      self.assertEqual(ci.CS.gear_msg_canfd, "ACCELERATOR")
      packer = CANPacker(DBC[cp.carFingerprint][Bus.pt])
      ci.update([])
      for tick in range(1, 13):
        state = update(ci, packer, tick)
      self.assertTrue(state.canValid)
      self.assertEqual(state.gearShifter, structs.CarState.GearShifter.drive)
      self.assertEqual(cp.safetyConfigs[0].safetyParam, 0x5491)
    for topology in ("lka", "lfa"):
      self.assertTrue(params(topology=topology).dashcamOnly)
    for missing in (0x35, 0x110, 0x362, 0x1CF, 0x1A0):
      self.assertFalse(qualified(params(missing=missing)))

  def test_exact_profile_rejects_nonstock_and_other_identities(self):
    for field, value in (("passive", True), ("dashcamOnly", True), ("notCar", True),
                         ("openpilotLongitudinalControl", True), ("pcmCruise", False),
                         ("alternativeExperience", 32)):
      with self.subTest(field=field):
        cp = params()
        setattr(cp, field, value)
        self.assertFalse(qualified(cp))
    for candidate in (CAR.HYUNDAI_IONIQ_5, CAR.HYUNDAI_IONIQ_5_N, CAR.HYUNDAI_IONIQ_6):
      with self.subTest(candidate=candidate):
        cp = params(candidate=candidate)
        self.assertFalse(qualified(cp))
        self.assertNotEqual(cp.safetyConfigs[-1].safetyParam, 0x5491)
    cp = params()
    for fault in (False, True):
      state = structs.CarState()
      state.canValid = True
      state.cruiseState.enabled = True
      state.gearShifter = structs.CarState.GearShifter.drive
      state.steerFaultPermanent = fault
      command = structs.CarControl()
      command.latActive = True
      self.assertEqual(bool(replacement_requested(cp, command, state)), not fault)
      state.canTimeout = True
      self.assertFalse(replacement_requested(cp, command, state))

  def test_actual_state_fault_and_ordered_replacement_recipe(self):
    cp = params()
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


if __name__ == "__main__":
  unittest.main()
