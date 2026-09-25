"""Gateway Volt brake source and friction routing remain one configuration."""
import unittest

from opendbc.can import CANPacker
from opendbc.car import Bus
from opendbc.car.gm.carstate import CarState
from opendbc.car.gm.carcontroller import CarController
from opendbc.car.gm.longitudinal import volt_policy_for
from opendbc.car.gm.profiles import profiles_supported
from opendbc.car.gm.tests.test_bolt_volt_configurations import controller_messages, ordinary_params
from opendbc.car.gm.values import CAR, DBC, GMSafetyFlags, is_volt_gateway_alternate_brake


class TestVoltAlternateBrake(unittest.TestCase):
  def test_final_configuration_selection_both_alpha_modes(self):
    for alpha in (False, True):
      for accelerator in (False, True):
        cp = ordinary_params(CAR.CHEVROLET_VOLT, alpha=alpha, radar=True, accelerator=accelerator)
        expected = GMSafetyFlags.EV | GMSafetyFlags.VOLT_GATEWAY_LONG
        if not accelerator:
          expected |= GMSafetyFlags.VOLT_GATEWAY_ALT_BRAKE
        self.assertEqual(cp.safetyConfigs[0].safetyParam, expected)
        self.assertEqual(is_volt_gateway_alternate_brake(cp), not accelerator)
        self.assertTrue(cp.openpilotLongitudinalControl and not cp.pcmCruise and not cp.dashcamOnly)
        self.assertTrue(profiles_supported(cp))
        self.assertIsNotNone(volt_policy_for(cp))
      missing_radar = ordinary_params(CAR.CHEVROLET_VOLT, alpha=alpha, accelerator=False)
      self.assertFalse(is_volt_gateway_alternate_brake(missing_radar))
      self.assertTrue(missing_radar.dashcamOnly)
      for candidate in (CAR.CHEVROLET_VOLT_ASCM, CAR.CHEVROLET_VOLT_CAMERA, CAR.CHEVROLET_VOLT_2019,
                        CAR.CHEVROLET_BOLT_ACC_2022_2023, CAR.GMC_ACADIA):
        cp = ordinary_params(candidate, alpha=alpha, radar=True, accelerator=False)
        self.assertFalse(cp.safetyConfigs[0].safetyParam & GMSafetyFlags.VOLT_GATEWAY_ALT_BRAKE)
        self.assertFalse(is_volt_gateway_alternate_brake(cp))

  def test_unknown_host_flags_and_mixed_native_selectors_are_not_admitted(self):
    for accelerator in (False, True):
      for flags in (1, 2, 3, 1 << 31):
        cp = ordinary_params(CAR.CHEVROLET_VOLT, radar=True, accelerator=accelerator)
        cp.flags = flags
        self.assertFalse(is_volt_gateway_alternate_brake(cp))
        self.assertFalse(profiles_supported(cp))
        self.assertIsNone(volt_policy_for(cp))
        controller = CarController(DBC[cp.carFingerprint], cp)
        self.assertFalse(controller.volt_gateway_long)
        self.assertEqual(controller.params.MAX_GAS, 1018)
      for extra in (GMSafetyFlags.HW_CAM, GMSafetyFlags.PEDAL_LONG, GMSafetyFlags.NO_ACC, GMSafetyFlags.ASCM_INTERCEPT):
        cp = ordinary_params(CAR.CHEVROLET_VOLT, radar=True, accelerator=accelerator)
        cp.safetyConfigs[0].safetyParam |= int(extra)
        self.assertFalse(is_volt_gateway_alternate_brake(cp))
        self.assertFalse(profiles_supported(cp))
        self.assertIsNone(volt_policy_for(cp))

  def test_brake_input_threshold_and_wrong_source_isolation(self):
    for alpha in (False, True):
      cp = ordinary_params(CAR.CHEVROLET_VOLT, alpha=alpha, radar=True, accelerator=False)
      state = CarState(cp)
      parsers = state.get_can_parsers(cp)
      packer = CANPacker(DBC[cp.carFingerprint][Bus.pt])
      state.update(parsers)  # Subscribe all ordinary state fields.
      self.assertNotIn(0xbe, parsers[Bus.pt].addresses)
      self.assertEqual(parsers[Bus.pt].message_states[0xf1].frequency, 100)
      for index, raw in enumerate((0, 5, 6, 7, 208, 255, 0)):
        frames = [packer.make_can_msg('EBCMBrakePedalPosition', 0, {'BrakePedalPosition': raw}),
                  packer.make_can_msg('ECMEngineStatus', 0, {'BrakePressed': raw < 6}),
                  packer.make_can_msg('ECMAcceleratorPos', 0, {'BrakePedalPos': 255 if raw < 6 else 0}),
                  packer.make_can_msg('EBCMBrakePedalPosition', 2, {'BrakePedalPosition': 255 if raw < 6 else 0})]
        parsers[Bus.pt].update([(1_000_000_000 + index * 10_000_000, frames)])
        out = state.update(parsers)
        self.assertEqual(out.brakePressed, raw >= 6)

  def test_ebcm_brake_input_missing_and_stale_is_invalid(self):
    cp = ordinary_params(CAR.CHEVROLET_VOLT, radar=True, accelerator=False)
    parser = CarState.get_can_parsers(cp)[Bus.pt]
    packer = CANPacker(DBC[cp.carFingerprint][Bus.pt])
    wrong = packer.make_can_msg('ECMAcceleratorPos', 0, {'BrakePedalPos': 0})
    frame = packer.make_can_msg('EBCMBrakePedalPosition', 0, {'BrakePedalPosition': 0})
    for tick in range(5):
      parser.update([(1_000_000_000 + tick * 10_000_000, [wrong])])
      valid = parser.can_valid
    self.assertFalse(valid)
    parser.update([(1_100_000_000, [frame])])
    self.assertTrue(parser.can_valid)
    for tick in range(5):
      parser.update([(1_500_000_000 + tick * 10_000_000, [wrong])])
      valid = parser.can_valid
    self.assertFalse(valid)

  def test_controller_bytes_and_stop_release_only_change_brake_bus(self):
    for alpha in (False, True):
      normal = ordinary_params(CAR.CHEVROLET_VOLT, alpha=alpha, radar=True)
      alternate = ordinary_params(CAR.CHEVROLET_VOLT, alpha=alpha, radar=True, accelerator=False)
      # Independent wire literals cover moving regen and near-stop fixed braking.
      for cp, bus in ((normal, 2), (alternate, 0)):
        _, messages = controller_messages(cp, 4, accel=-.5, speed=2.)
        self.assertEqual([m for m in messages if m[0] == 0x315], [(0x315, bytes.fromhex('afed501201'), bus)])
        self.assertEqual([m for m in messages if m[0] == 0x2cb], [(0x2cb, bytes.fromhex('4142abe000bd541f'), 0)])
        controller = None
        for frame in range(4, 28):
          resume = frame >= 12
          active = frame < 20
          controller, messages = controller_messages(cp, frame, controller, accel=1., speed=0.,
                                                     stopping=True, resume=resume, standstill=True, long_active=active)
          brakes = [m for m in messages if m[0] == 0x315]
          if frame % 4:
            self.assertEqual(brakes, [])
          else:
            count = (frame // 4) % 4
            hold = not resume and active
            expected = bytes.fromhex(('df6a209600', 'df6a209501', 'df6a209402', 'df6a209303')[count]) if hold else \
                       bytes.fromhex(('1000f00000', '1000efff01', '1000effe02', '1000effd03')[count])
            self.assertEqual(brakes, [(0x315, expected, bus)])
            self.assertFalse(any(m[0] in (0x200, 0x1e1) for m in messages))


if __name__ == '__main__':
  unittest.main()
