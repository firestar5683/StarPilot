import unittest
from itertools import product

from opendbc.can import CANPacker
from opendbc.car import Bus, gen_empty_fingerprint, structs
from opendbc.car.hyundai.carcontroller import CarController
from opendbc.car.hyundai.carstate import CarState
from opendbc.car.hyundai.hyundaicanfd import CanBus
from opendbc.car.hyundai.interface import CarInterface
from opendbc.car.hyundai.values import CAR, DBC, HyundaiFlags


class TestCcncAngleLv2Fault(unittest.TestCase):
  def test_packed_mdps_fault_inhibits_angle_request_and_recovers(self):
    for car_model, lka_alt in ((CAR.HYUNDAI_SANTA_FE_HEV_5TH_GEN, True),
                               (CAR.KIA_SPORTAGE_2026, False)):
      fingerprint = gen_empty_fingerprint()
      if lka_alt:
        fingerprint[2][0x110] = 32
      cp = CarInterface.get_params(car_model, fingerprint, [], False, False, False)
      self.assertTrue(cp.flags & HyundaiFlags.CANFD_ANGLE_STEERING)
      self.assertEqual(bool(cp.flags & HyundaiFlags.CANFD_LKA_STEER_MSG_ALT), lka_alt)
      state = CarState(cp)
      parsers = state.get_can_parsers(cp)
      packer = CANPacker(DBC[car_model][Bus.pt])
      can = CanBus(cp)
      controller = CarController(DBC[car_model], cp)
      control = structs.CarControl()
      control.enabled = control.latActive = True
      control.actuators.steeringAngleDeg = 10.0
      fuel = "ACCELERATOR_ALT" if cp.flags & HyundaiFlags.HYBRID else "ACCELERATOR_BRAKE_ALT"
      setup = [(fuel, {}), (state.gear_msg_canfd, {"GEAR": 5}),
               ("TCS", {"ACCEnable": 0, "ACC_REQ": 1}), ("WHEEL_SPEEDS", {}),
               ("STEERING_SENSORS", {}), ("DOORS_SEATBELTS", {"DRIVER_SEATBELT": 1}),
               ("BLINKERS", {})]
      cases = [*product(range(8), (0, 1)), (0, 0)]
      for index, (lv2_fault, base_fault) in enumerate(cases):
        with self.subTest(car_model=car_model, lv2_fault=lv2_fault, base_fault=base_fault):
          now_ns = (index + 1) * 10_000_000
          messages = [packer.make_can_msg(name, can.ECAN, values) for name, values in
                      [*setup, ("MDPS", {"MDPS_ADAS_AciFltSig_Lv2": lv2_fault,
                                          "MDPS_LkaFailSta": base_fault})]]
          mdps_bytes = messages[-1][1]
          self.assertEqual((mdps_bytes[18] >> 4) & 7, lv2_fault)
          self.assertEqual(bool(mdps_bytes[18] & 0x20), bool(lv2_fault & 2))
          parsers[Bus.pt].update((now_ns, messages))
          if cp.flags & HyundaiFlags.CANFD_CAMERA_SCC:
            parsers[Bus.cam].update((now_ns, [packer.make_can_msg("SCC_CONTROL", can.CAM, {"ACCMode": 1})]))
          else:
            parsers[Bus.pt].update((now_ns, [packer.make_can_msg("SCC_CONTROL", can.ECAN, {"ACCMode": 1})]))
          state.out = state.update(parsers)
          expected_fault = bool((lv2_fault & 2) or base_fault)
          self.assertEqual(state.out.steerFaultTemporary, expected_fault)
          self.assertFalse(state.out.steerFaultPermanent)
          _, sent = controller.update(control.as_reader(), state, now_ns)
          angle_addresses = {0x110} if lka_alt else {0x12a}
          angle_frames = [(address, data) for address, data, _ in sent if address in angle_addresses]
          self.assertTrue(angle_frames)
          self.assertEqual((angle_frames[0][1][9] >> 4) & 3, 1 if expected_fault else 2)

  def test_torque_car_ignores_lv2_fault(self):
    car_model = CAR.HYUNDAI_IONIQ_6
    cp = CarInterface.get_params(car_model, gen_empty_fingerprint(), [], False, False, False)
    self.assertFalse(cp.flags & HyundaiFlags.CANFD_ANGLE_STEERING)
    state = CarState(cp)
    parsers = state.get_can_parsers(cp)
    packer = CANPacker(DBC[car_model][Bus.pt])
    can = CanBus(cp)
    setup = [("ACCELERATOR", {"GEAR": 5}), ("TCS", {"ACCEnable": 0, "ACC_REQ": 1}),
             ("WHEEL_SPEEDS", {}), ("STEERING_SENSORS", {}),
             ("DOORS_SEATBELTS", {"DRIVER_SEATBELT": 1}), ("BLINKERS", {})]
    for index, (lv2_fault, base_fault) in enumerate(product(range(8), (0, 1))):
      with self.subTest(lv2_fault=lv2_fault, base_fault=base_fault):
        messages = [packer.make_can_msg(name, can.ECAN, values) for name, values in
                    [*setup, ("MDPS", {"MDPS_ADAS_AciFltSig_Lv2": lv2_fault,
                                        "MDPS_LkaFailSta": base_fault})]]
        parsers[Bus.pt].update(((index + 1) * 10_000_000, messages))
        state.out = state.update(parsers)
        self.assertEqual(state.out.steerFaultTemporary, bool(base_fault))
        self.assertFalse(state.out.steerFaultPermanent)


if __name__ == "__main__":
  unittest.main()
