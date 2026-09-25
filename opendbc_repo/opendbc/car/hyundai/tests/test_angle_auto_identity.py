import unittest

from opendbc.car import gen_empty_fingerprint, structs
from opendbc.car.fw_versions import match_fw_to_car
from opendbc.car.hyundai.fingerprints import FW_VERSIONS
from opendbc.car.hyundai.interface import CarInterface
from opendbc.car.hyundai.values import CAR, HyundaiFlags, CANFD_ANGLE_MODEL_BITS


NINE = (CAR.GENESIS_GV70_2026,
        CAR.GENESIS_GV70_ELECTRIFIED_2ND_GEN,
        CAR.GENESIS_GV80_2025,
        CAR.HYUNDAI_AZERA_HEV_7TH_GEN,
        CAR.HYUNDAI_IONIQ_9,
        CAR.HYUNDAI_SANTA_FE_HEV_5TH_GEN,
        CAR.KIA_SORENTO_HEV_4TH_GEN_LFA2,
        CAR.KIA_SPORTAGE_2026,
        CAR.KIA_SPORTAGE_HEV_2026)


def observed_fw(car):
  return [structs.CarParams.CarFw(ecu=ecu, address=address, subAddress=sub or 0,
                                 fwVersion=versions[0], brand='hyundai')
          for (ecu, address, sub), versions in FW_VERSIONS[car].items()]


class TestAngleAutoIdentity(unittest.TestCase):
  def test_joint_exact_discovery_requires_camera_and_radar(self):
    for car in NINE:
      fw = observed_fw(car)
      exact, matches = match_fw_to_car(fw, '', allow_fuzzy=False, log=False)
      self.assertTrue(exact)
      self.assertEqual(matches, {car})
      for item in fw:
        self.assertNotIn(car, match_fw_to_car([item], '', allow_fuzzy=False, log=False)[1])
      for other in NINE:
        if other == car:
          continue
        other_fw = observed_fw(other)
        for replaced_ecu in (structs.CarParams.Ecu.fwdCamera, structs.CarParams.Ecu.fwdRadar):
          replacements = [item for item in other_fw if item.ecu == replaced_ecu]
          expected = {version for (ecu, _, _), versions in FW_VERSIONS[car].items()
                      if ecu == replaced_ecu for version in versions}
          if all(item.fwVersion in expected for item in replacements):
            continue
          mixed = [item for item in fw if item.ecu != replaced_ecu] + replacements
          self.assertNotIn(car, match_fw_to_car(mixed, '', allow_fuzzy=False, log=False)[1])

  def test_existing_complete_firmware_sets_do_not_gain_angle_matches(self):
    for car in FW_VERSIONS:
      if car in NINE:
        continue
      matches = match_fw_to_car(observed_fw(car), '', allow_fuzzy=False, log=False)[1]
      self.assertFalse(set(NINE) & matches, car)

  def source_profile(self, car):
    from opendbc.safety.tests import test_hyundai_mrr35_angle_four as mrr35
    from opendbc.safety.tests import test_hyundai_angle_hybrids_three as hybrids
    from opendbc.safety.tests import test_hyundai_ccnc_angle_two as ccnc
    if car in mrr35.ANGLE_CARS:
      topology = 'lka_alt'
      cp = mrr35.params(car, topology)
      packer, frames = mrr35.TestHyundaiMRR35AngleFour.source_frames(cp, topology)
    elif car in hybrids.CARS:
      topology = 'lka_alt'
      cp = hybrids.params(car, topology, hybrid=True)
      packer, frames = hybrids.source_frames(cp, topology)
    else:
      topology = 'lfa'
      cp = ccnc.params(car, topology, hybrid=car == CAR.HYUNDAI_SANTA_FE_HEV_5TH_GEN)
      packer, frames = ccnc.source_frames(cp, topology)
    fw = observed_fw(car)
    self.assertEqual(match_fw_to_car(fw, '', allow_fuzzy=False, log=False)[1], {car})
    fp = gen_empty_fingerprint()
    ecan = 1 if topology.startswith('lka') else 0
    fp[ecan][0x1CF] = 8
    if topology == 'lka_alt':
      fp[2][0x110] = 32
    if cp.flags & HyundaiFlags.HYBRID:
      fp[ecan][0xFA] = 8
    discovered_cp = CarInterface.get_params(car, fp, fw, False, False, False)
    self.assertEqual(discovered_cp.flags, cp.flags)
    self.assertEqual(discovered_cp.safetyConfigs[-1].safetyParam, cp.safetyConfigs[-1].safetyParam)
    return discovered_cp, packer, frames

  def fresh_frames(self, packer, templates):
    from opendbc.can.parser import MessageState
    frames = []
    for address, data, bus in templates:
      message = packer.dbc.addr_to_msg[address]
      signals = list(message.sigs.values())
      state = MessageState(address, message.name, message.size, signals,
                           ignore_checksum=True, ignore_counter=True)
      self.assertTrue(state.parse(1, data))
      values = {signal.name: value for signal, value in zip(signals, state.vals, strict=True)
                if signal.type == 0 and signal.name != 'COUNTER'}
      frames.append(packer.make_can_msg(message.name, bus, values))
    return frames

  def test_discovered_stock_profile_whole_parser_lazy_sources_and_loss(self):
    from opendbc.car.hyundai.hyundaicanfd import CanBus
    for car in NINE:
      for wrong_bus in (False, True):
        with self.subTest(car=car, wrong_bus=wrong_bus):
          cp, packer, frames = self.source_profile(car)
          ci = CarInterface(cp)
          for tick in range(40):
            out = ci.update([(1_000_000_000 + tick * 10_000_000, self.fresh_frames(packer, frames))])
          self.assertTrue(out.canValid)
          self.assertFalse(out.canTimeout)
          source = packer.make_can_msg('WHEEL_SPEEDS', CanBus(cp).ECAN, {})[0]
          self.assertTrue(any(frame[0] == source and frame[2] == CanBus(cp).ECAN for frame in frames))
          missing = [frame for frame in frames if frame[0] != source]
          if wrong_bus:
            missing += [(address, data, (bus + 1) % 3) for address, data, bus in frames if address == source]
          for tick in range(40, 140):
            out = ci.update([(1_000_000_000 + tick * 10_000_000, self.fresh_frames(packer, missing))])
          self.assertFalse(out.canValid)
          for tick in range(140, 180):
            out = ci.update([(1_000_000_000 + tick * 10_000_000, self.fresh_frames(packer, frames))])
          self.assertTrue(out.canValid)

  def test_discovered_card_to_controls_retains_angle_constructor(self):
    import gc
    import os
    from unittest.mock import patch
    from openpilot.common.params import Params
    from openpilot.common.prefix import OpenpilotPrefix
    from openpilot.selfdrive.car.card import Car
    from openpilot.selfdrive.controls.controlsd import Controls
    from openpilot.selfdrive.controls.lib.latcontrol_angle import LatControlAngle
    from opendbc.car.hyundai.radar_interface import RadarInterface
    for car in NINE:
      with self.subTest(car=car), OpenpilotPrefix(), patch.dict(os.environ, {'SIMULATION': '1'}):
        cp, packer, frames = self.source_profile(car)
        saved = Params()
        saved.put_bool('OpenpilotEnabledToggle', True, block=True)
        ci = CarInterface(cp)
        for tick in range(40):
          out = ci.update([(1_000_000_000 + tick * 10_000_000, self.fresh_frames(packer, frames))])
        self.assertTrue(out.canValid)
        card = Car(CI=ci, RI=RadarInterface(cp))
        self.assertEqual(card.CP.carFingerprint, car)
        self.assertFalse(card.CP.openpilotLongitudinalControl)
        with structs.CarParams.from_bytes(saved.get('CarParams')) as published:
          self.assertEqual(published.to_dict(), card.CP.to_dict())
        controls = Controls()
        self.assertEqual(controls.CP.carFingerprint, car)
        self.assertIsInstance(controls.LaC, LatControlAngle)
        self.assertFalse(controls.CP.openpilotLongitudinalControl)
        del controls, card, ci
        gc.collect()

  def test_documented_final_cp_retains_stock_scc_and_geometry(self):
    for car in NINE:
      hda2_options = (False,) if car == CAR.KIA_SPORTAGE_2026 else (False, True) if car == CAR.HYUNDAI_SANTA_FE_HEV_5TH_GEN else (True,)
      for hda2 in hda2_options:
        for alpha in (False, True):
          for release in (False, True):
            with self.subTest(car=car, hda2=hda2, alpha=alpha, release=release):
              fp = gen_empty_fingerprint()
              bus = 1 if hda2 else 0
              fp[bus][0x1cf] = 8
              if hda2:
                fp[2][0x50] = 16
              if car in (CAR.HYUNDAI_AZERA_HEV_7TH_GEN, CAR.HYUNDAI_SANTA_FE_HEV_5TH_GEN,
                         CAR.KIA_SORENTO_HEV_4TH_GEN_LFA2, CAR.KIA_SPORTAGE_HEV_2026):
                fp[bus][0xFA] = 8
              fw = observed_fw(car)
              if hda2:
                fw.append(structs.CarParams.CarFw(ecu=structs.CarParams.Ecu.adas))
              cp = CarInterface.get_params(car, fp, fw, alpha, release, False)
              self.assertEqual(cp.carFingerprint, car)
              self.assertFalse(cp.openpilotLongitudinalControl or cp.alphaLongitudinalAvailable or cp.dashcamOnly)
              self.assertTrue(cp.pcmCruise)
              self.assertEqual(cp.steerControlType, structs.CarParams.SteerControlType.angle)
              self.assertTrue(cp.flags & HyundaiFlags.CANFD_ANGLE_STEERING)
              self.assertEqual(cp.safetyConfigs[-1].safetyParam & (8192 | 4096 | 2048 | 1024),
                               CANFD_ANGLE_MODEL_BITS[str(car)])
