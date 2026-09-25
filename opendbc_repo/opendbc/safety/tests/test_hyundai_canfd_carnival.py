import unittest

from opendbc.can import CANPacker
from opendbc.car import Bus, structs
from opendbc.car.hyundai.carcontroller import CarController
from opendbc.car.hyundai.carstate import CarState
from opendbc.car.hyundai.hyundaicanfd import CanBus, hkg_can_fd_checksum
from opendbc.car.hyundai.tests.test_ccnc_six import params
from opendbc.car.hyundai.values import CAR, DBC, HyundaiFlags, HyundaiSafetyFlags
from opendbc.car.structs import CarParams
from opendbc.safety.tests.libsafety import libsafety_py


class TestCarnivalAltResumeNative(unittest.TestCase):
  def test_raw_long_flag_never_enables_stock_resume(self):
    safety = libsafety_py.libsafety
    cp = params(CAR.KIA_CARNIVAL_2025, alt_buttons=True)
    packer = CANPacker(DBC[cp.carFingerprint][Bus.pt])
    raw_param = cp.safetyConfigs[-1].safetyParam | HyundaiSafetyFlags.LONG
    safety.set_safety_hooks(CarParams.SafetyModel.hyundaiCanfd, raw_param)
    safety.init_tests()
    address, raw, _ = packer.make_can_msg("CRUISE_BUTTONS_ALT", 0, {"COUNTER": 1, "SET_ME_1": 1})
    source = bytearray(raw)
    source[0:2] = hkg_can_fd_checksum(address, None, source).to_bytes(2, "little")
    self.assertTrue(safety.safety_rx_hook(libsafety_py.make_CANPacket(address, 0, source)))
    safety.set_controls_allowed(True)
    from opendbc.car.hyundai.hyundaicanfd import create_carnival_alt_resume
    candidate = create_carnival_alt_resume(packer, cp, CanBus(cp), {"COUNTER": 1, "SET_ME_1": 1})
    self.assertFalse(safety.safety_tx_hook(libsafety_py.make_CANPacket(candidate[0], candidate[2], candidate[1])))

  def test_packed_host_resume_guard(self):
    # Use the safety library selected by the vehicle runner (DEBUG or RELEASE).
    from opendbc.car.hyundai.tests.test_ccnc_six import TestCcncSix

    TestCcncSix()._check_packed_carnival_resume(libsafety_py.libsafety)

  def test_controller_frame_requires_real_stock_arming(self):
    safety = libsafety_py.libsafety
    for car in (CAR.KIA_CARNIVAL_2025, CAR.KIA_CARNIVAL_HEV_4TH_GEN):
      for hda2, alt_lka in ((False, False), (True, False), (True, True)):
        with self.subTest(car=car, hda2=hda2, alt_lka=alt_lka):
          self._check_controller_frame(safety, car, hda2, alt_lka)

  def _check_controller_frame(self, safety, car, hda2, alt_lka):
    cp = params(car, hda2=hda2, alt_buttons=True, alt_lka=alt_lka)
    can = CanBus(cp)
    packer = CANPacker(DBC[cp.carFingerprint][Bus.pt])
    state = CarState(cp)
    parsers = state.get_can_parsers(cp)
    safety.set_safety_hooks(CarParams.SafetyModel.hyundaiCanfd, cp.safetyConfigs[-1].safetyParam)
    safety.init_tests()

    def frame(name, bus, values):
      address, raw, bus = packer.make_can_msg(name, bus, values)
      data = bytearray(raw)
      if len(data) in (16, 24, 32):
        data[0:2] = hkg_can_fd_checksum(address, None, data).to_bytes(2, "little")
      return address, bytes(data), bus

    def receive(name, bus, values):
      address, data, bus = frame(name, bus, values)
      return safety.safety_rx_hook(libsafety_py.make_CANPacket(address, bus, data))

    # Populate the ordinary safety RX checks, including the selected fuel path.
    fuel = "ACCELERATOR_ALT" if cp.flags & HyundaiFlags.HYBRID else "ACCELERATOR_BRAKE_ALT"
    for name in (fuel, "TCS", "WHEEL_SPEEDS", "MDPS"):
      self.assertTrue(receive(name, can.ECAN, {}), name)
    self.assertTrue(receive("SCC_CONTROL", can.ECAN if hda2 else can.CAM, {"ACCMode": 0}))
    self.assertTrue(receive("CRUISE_BUTTONS_ALT", can.ECAN, {"COUNTER": 20, "CRUISE_BUTTONS": 2}))
    self.assertTrue(receive("SCC_CONTROL", can.ECAN if hda2 else can.CAM, {"ACCMode": 1, "COUNTER": 1}))
    self.assertTrue(safety.get_controls_allowed())

    stock = frame("CRUISE_BUTTONS_ALT", can.ECAN, {"COUNTER": 21, "SET_ME_1": 1, "CRUISE_BUTTONS": 0})
    self.assertTrue(safety.safety_rx_hook(libsafety_py.make_CANPacket(stock[0], stock[2], stock[1])))
    parsers[Bus.pt].update((1_000_000_000, [stock]))
    state.out = state.update(parsers)
    control = structs.CarControl()
    control.cruiseControl.resume = True
    controller = CarController(DBC[cp.carFingerprint], cp)
    controller.frame = 26
    _, emitted = controller.update(control.as_reader(), state, 1_050_000_000)
    resume = [message for message in emitted if message[0] == 0x1AA]
    self.assertEqual(len(resume), 1)
    address, data, bus = resume[0]
    safety.safety_tick()
    self.assertTrue(safety.get_controls_allowed())
    self.assertFalse(safety.safety_tx_hook(libsafety_py.make_CANPacket(address, can.ECAN if not hda2 else can.CAM, data)))
    self.assertFalse(safety.safety_tx_hook(libsafety_py.make_CANPacket(address, bus, data[:12])))
    corrupt = bytearray(data)
    corrupt[0] ^= 1
    self.assertFalse(safety.safety_tx_hook(libsafety_py.make_CANPacket(address, bus, corrupt)))
    self.assertTrue(safety.safety_tx_hook(libsafety_py.make_CANPacket(address, bus, data)))
    self.assertFalse(safety.safety_tx_hook(libsafety_py.make_CANPacket(address, bus, data)))
    self.assertTrue(receive("SCC_CONTROL", can.ECAN if hda2 else can.CAM, {"ACCMode": 0, "COUNTER": 2}))
    self.assertFalse(safety.get_controls_allowed())
    self.assertFalse(safety.safety_tx_hook(libsafety_py.make_CANPacket(address, bus, data)))
