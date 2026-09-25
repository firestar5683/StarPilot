import unittest
from unittest.mock import patch

from opendbc.car import Bus, gen_empty_fingerprint, structs
from opendbc.car.fw_versions import match_fw_to_car
from opendbc.car.hyundai.fingerprints import FW_VERSIONS
from opendbc.car.hyundai.interface import CarInterface
from opendbc.car.hyundai.values import CAR, DBC, HyundaiFlags
from opendbc.car.hyundai.hyundaicanfd import CanBus


def params(*, alternate=False, topology='lfa', alpha=False, release=False, adas=False, radar_length=None, hybrid=False):
  fp = gen_empty_fingerprint()
  if topology == 'lka':
    fp[2][0x50] = 16
  elif topology == 'lka_alt':
    fp[2][0x110] = 32
  if hybrid:
    fp[0][0xFA] = 8
  fp[0][0x1AA if alternate else 0x1CF] = 16 if alternate else 8
  if radar_length is not None:
    fp[0][0x210] = radar_length
  if adas:
    fp[2][0xCB] = 24
  return CarInterface.get_params(CAR.KIA_EV6_2025, fp, [], alpha, release, False)


class TestEv62025(unittest.TestCase):
  def test_stock_profiles_preserve_identity_without_long_or_optional_hardware(self):
    for alternate in (False, True):
      for alpha in (False, True):
        for release in (False, True):
          for adas in (False, True):
            cp = params(alternate=alternate, alpha=alpha, release=release, adas=adas)
            self.assertEqual(cp.carFingerprint, CAR.KIA_EV6_2025)
            self.assertEqual(cp.steerControlType, structs.CarParams.SteerControlType.angle)
            self.assertEqual(cp.safetyConfigs[-1].safetyParam, 0x7829 if alternate else 0x7809)
            self.assertFalse(cp.flags & HyundaiFlags.SEND_LFA)
            self.assertFalse(cp.alphaLongitudinalAvailable)
            self.assertFalse(cp.openpilotLongitudinalControl)
            self.assertTrue(cp.pcmCruise)
            self.assertFalse(cp.dashcamOnly)
            self.assertEqual((CanBus(cp).ECAN, CanBus(cp).CAM), (0, 2))
            self.assertAlmostEqual(cp.wheelbase, 2.9, places=6)
            self.assertAlmostEqual(cp.steerRatio, 14.26, places=5)
            ci = CarInterface(cp)
            self.assertEqual(ci.CS.accelerator_msg_canfd, 'ACCELERATOR')
            self.assertEqual(ci.can_parsers[Bus.cam].message_states[0x1A0].frequency, 50)
            self.assertTrue(ci.can_parsers[Bus.pt].message_states[0x2E0].ignore_alive)
            with patch('opendbc.car.hyundai.interface.disable_ecu') as disable:
              ci.init(cp, list, lambda _: None)
            disable.assert_not_called()

  def test_contradictory_lka_topology_has_no_output_or_diagnostic_transaction(self):
    for topology, hybrid in (('lka', False), ('lka_alt', False), ('lfa', True)):
      cp = params(topology=topology, hybrid=hybrid, alpha=True)
      self.assertTrue(cp.dashcamOnly)
      self.assertEqual(cp.safetyConfigs[-1].safetyModel, structs.CarParams.SafetyModel.noOutput)
      self.assertFalse(cp.openpilotLongitudinalControl)
      ci = CarInterface(cp)
      control = structs.CarControl()
      control.enabled = control.latActive = control.longActive = True
      control.cruiseControl.cancel = control.cruiseControl.resume = True
      _, frames = ci.CC.update(control.as_reader(), ci.CS, 1_000_000_000)
      self.assertEqual(frames, [])
      with patch('opendbc.car.hyundai.interface.disable_ecu') as disable:
        ci.init(cp, list, lambda _: None)
      disable.assert_not_called()

  def test_mrr30_real_dbc_layout_units_and_cycle_freshness(self):
    from opendbc.can import CANPacker
    from opendbc.car.hyundai.radar_interface import RadarInterface

    for length, available in ((None, False), (8, False), (24, False), (32, True)):
      self.assertEqual(not params(radar_length=length).radarUnavailable, available)
    cp = params(radar_length=32)
    radar = RadarInterface(cp)
    self.assertEqual(radar.rcp.bus, 0)
    self.assertEqual((radar.start_addr, radar.msg_count), (0x210, 16))
    packer = CANPacker(DBC[CAR.KIA_EV6_2025][Bus.radar])
    frames = [packer.make_can_msg(f'RADAR_TRACK_{addr:x}', 0, {}) for addr in range(0x210, 0x220)]
    frames[0] = packer.make_can_msg('RADAR_TRACK_210', 0, {
      '1_STATE': 3, '1_LONG_DIST': 42.5, '1_LAT_DIST': -1.25, '1_REL_SPEED': -2.5,
      '2_STATE': 4, '2_LONG_DIST': 18.0, '2_LAT_DIST': 1.5, '2_REL_SPEED': 3.25,
    })
    self.assertEqual(len(frames[0][1]), 32)
    self.assertIsNone(radar.update((1_000_000_000, [(addr, data, 1) for addr, data, _ in frames])))
    self.assertIsNone(radar.update((1_010_000_000, [(addr, data[:24], bus) for addr, data, bus in frames])))
    result = radar.update((1_020_000_000, frames))
    self.assertFalse(result.errors.canError)
    self.assertEqual(len(result.points), 2)
    self.assertAlmostEqual(result.points[0].dRel, 42.5)
    self.assertAlmostEqual(result.points[0].yRel, -1.25)
    self.assertAlmostEqual(result.points[0].vRel, -2.5)
    self.assertAlmostEqual(result.points[1].dRel, 18.0)
    self.assertAlmostEqual(result.points[1].yRel, 1.5)
    self.assertAlmostEqual(result.points[1].vRel, 3.25)
    self.assertEqual(len(radar.update((1_040_000_000, [frames[-1]])).points), 0)
    self.assertIsNone(radar.update((1_050_000_000, [frames[0]])))
    self.assertEqual(len(radar.update((1_100_000_000, [frames[-1]])).points), 0)

  def test_original_camera_radar_versions_identify_distinct_vehicle(self):
    entries = FW_VERSIONS[CAR.KIA_EV6_2025]
    self.assertEqual(sum(map(len, entries.values())), 4)
    for radar in entries[(structs.CarParams.Ecu.fwdRadar, 0x7d0, None)]:
      for camera in entries[(structs.CarParams.Ecu.fwdCamera, 0x7c4, None)]:
        fw = []
        for ecu, address, version in ((structs.CarParams.Ecu.fwdRadar, 0x7d0, radar),
                                     (structs.CarParams.Ecu.fwdCamera, 0x7c4, camera)):
          fw.append(structs.CarParams.CarFw(ecu=ecu, address=address, fwVersion=version, brand='hyundai'))
        _, matched = match_fw_to_car(fw, '', log=False)
        self.assertEqual(matched, {CAR.KIA_EV6_2025})
    self.assertEqual(DBC[CAR.KIA_EV6_2025][Bus.radar], 'hyundai_mrr30_radar_generated')


if __name__ == '__main__':
  unittest.main()
