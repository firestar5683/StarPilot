"""Dedicated Silverado interceptor admission, input and startup ownership."""
import os
import unittest
from types import SimpleNamespace
from dataclasses import replace
from unittest.mock import patch

from opendbc.can import CANPacker
from opendbc.car import Bus, gen_empty_fingerprint, structs
from opendbc.car.gm.interface import CarInterface
from opendbc.car.gm.gmcan import pedal_crc, create_pedal_command
from opendbc.car.gm.aol import qualified_gm
from opendbc.car.gm.lateral import lane_centering_supported
from opendbc.car.gm.feature_capabilities import longitudinal_supported, display_supported
from opendbc.car.gm.values import CAR, DBC, is_silverado_cc_pedal_profile, ORDINARY_CC_CAR
from opendbc.car.gm.radar_interface import RadarInterface, RADAR_HEADER_MSG
from opendbc.car.gm.startup_preferences import prepare_disable_longitudinal
from opendbc.car.gm.tests.test_cc_gateway_stock import pt_frames
from opendbc.car.gm.tests.test_conventional_pedal import pedal_frames
from openpilot.common.params import Params
from openpilot.common.prefix import OpenpilotPrefix
from openpilot.selfdrive.car.card import Car
from openpilot.starpilot.vehicle_preferences import VehicleStartupPreferences
from openpilot.starpilot.feature_runtime import enabled as feature_enabled
from openpilot.starpilot.ui.feature_settings_owner import FeatureSettingsOwner
from openpilot.starpilot.ui.feature_settings_state import row_change
from openpilot.starpilot.lateral.controller_selection import policy_for as lateral_policy_for
from openpilot.starpilot.longitudinal.vehicle_policy import policy_for as longitudinal_policy_for

IDENTITY = CAR.CHEVROLET_SILVERADO_CC

def fingerprint(*, removed=False, alternate=False):
  fp = gen_empty_fingerprint()
  fp[0].update({0x201: 6, 0xBE: 6, 0xC9: 8, 0x1C4: 8, 0x1E1: 7, 0x3D1: 8, 0x1F5: 8, 0x184: 8, 0x34A: 5})
  if alternate:
    fp[0].pop(0xBE)
    fp[0][0xF1] = 6
  if not removed:
    fp[2][0x320] = 6
  return fp


def params(*, disabled=False, removed=False, alternate=False, enabled=True, fp=None, release=False, alpha=False):
  fp = fingerprint(removed=removed, alternate=alternate) if fp is None else fp
  settings = type('Settings', (), {'get_bool': lambda self, key: enabled and key == 'GMPedalLongitudinal'})()
  with patch('opendbc.car.gm.interface.Params', return_value=settings):
    cp = CarInterface.get_params(IDENTITY, fp, [], alpha, release, False)
  prepare_disable_longitudinal(cp, disabled)
  return cp


class TestSilveradoCcPedal(unittest.TestCase):
  def test_exact_geometry_tune_and_four_profiles(self):
    self.assertNotIn(IDENTITY, ORDINARY_CC_CAR)
    for removed in (False, True):
      for alternate in (False, True):
        for disabled in (False, True):
          for release in (False, True):
            for alpha in (False, True):
              cp = params(disabled=disabled, removed=removed, alternate=alternate, release=release, alpha=alpha)
              self.assertTrue(is_silverado_cc_pedal_profile(cp))
              self.assertEqual(cp.safetyConfigs[0].safetyParam, (0xC184 if disabled else 0xC182) + int(removed))
              self.assertEqual((cp.mass, cp.wheelbase), (3130., 3.75))
              self.assertAlmostEqual(cp.steerRatio, 16.3, places=5)
              self.assertAlmostEqual(cp.lateralTuning.torque.latAccelFactor, 1.9, places=6)
              self.assertAlmostEqual(cp.lateralTuning.torque.friction, .112, places=6)
              self.assertEqual(cp.openpilotLongitudinalControl, not disabled)
              self.assertFalse(cp.pcmCruise)
              self.assertFalse(cp.alphaLongitudinalAvailable)
              self.assertEqual(lateral_policy_for(cp), 'silverado_cc')
              self.assertEqual(longitudinal_policy_for(cp) is not None, not disabled)
              self.assertEqual(cp.minEnableSpeed, -1.)
              self.assertEqual(cp.longitudinalActuatorDelay, .5)
              self.assertEqual(cp.stopAccel, -2.)

  def test_explicit_selected_source_negatives_remain_denied(self):
    negative = []
    for address in (0x201, 0xBE, 0x184, 0x34A, 0xC9, 0x3D1, 0x1E1, 0x1C4, 0x1F5):
      for length in (None, 1):
        fp = fingerprint()
        if length is None:
          fp[0].pop(address)
        else:
          fp[0][address] = length
        negative.append(fp)
    for length in (None, 1, 8):
      fp = fingerprint(alternate=True)
      if length is None:
        fp[0].pop(0xF1)
      else:
        fp[0][0xF1] = length
      negative.append(fp)
    fp = fingerprint()
    fp[2][0x320] = 1
    negative.append(fp)
    fp = fingerprint()
    fp[1][RADAR_HEADER_MSG] = 8
    negative.append(fp)
    for fp in negative:
      cp = params(fp=fp)
      self.assertTrue(cp.dashcamOnly)
      self.assertFalse(is_silverado_cc_pedal_profile(cp))
      self.assertIsNone(lateral_policy_for(cp))
      self.assertIsNone(longitudinal_policy_for(cp))
    self.assertFalse(is_silverado_cc_pedal_profile(params(enabled=False)))

  def test_actual_card_saved_disable_and_default_off_setup(self):
    for removed in (False, True):
      for disabled in (False, True):
        with OpenpilotPrefix(), patch.dict(os.environ, {'SIMULATION': '1', 'AOL_REPLAY_RUNTIME': '0'}):
          store = Params()
          store.put_bool('OpenpilotEnabledToggle', True, block=True)
          store.put_bool('DisableOpenpilotLongitudinal', disabled, block=True)
          fp = fingerprint(removed=removed)
          cp = CarInterface.get_params(IDENTITY, fp, [], False, False, False)
          self.assertTrue(cp.dashcamOnly)
          self.assertIsNone(store.get('GMPedalLongitudinal'))
          owner = FeatureSettingsOwner(store, lambda group: True,
                                       vehicle_fingerprint=lambda: IDENTITY, vehicle_params=lambda cp=cp: cp)
          row = next(r for r in owner.snapshot('vehicle', parked=True, system_long=False,
                                               lateral_context=False, metric=False).rows if r.key == 'GMPedalLongitudinal')
          self.assertEqual(row.value, 'Off')
          self.assertTrue(row.available)
          request = row_change(row, 1)
          self.assertFalse(owner.apply(request))
          self.assertTrue(owner.apply(replace(request, confirmation=True)))
          self.assertTrue(cp.dashcamOnly)
          cp = CarInterface.get_params(IDENTITY, fp, [], False, False, False)
          card = Car(CI=CarInterface(cp), RI=RadarInterface(cp))
          self.assertFalse(card.CP.passive)
          self.assertTrue(qualified_gm(card.CP))
          self.assertTrue(lane_centering_supported(card.CP))
          self.assertTrue(display_supported(card.CP))
          self.assertEqual(longitudinal_supported(card.CP), not disabled)
          self.assertEqual(feature_enabled(store, card.CP, 'conditional', {}), not disabled)
          self.assertFalse(feature_enabled(store, card.CP, 'aol', {}))
          self.assertIsNone(card.aol_card_intent)
          self.assertEqual(card.CP.alternativeExperience, 0)
          self.assertTrue(is_silverado_cc_pedal_profile(card.CP))
          self.assertEqual(card.CP.openpilotLongitudinalControl, not disabled)
          self.assertEqual(card.CP.safetyConfigs[0].safetyParam, (0xC184 if disabled else 0xC182) + int(removed))
          absent = fingerprint(removed=removed)
          absent[0].pop(0x201)
          denied = CarInterface.get_params(IDENTITY, absent, [], False, False, False)
          self.assertTrue(denied.dashcamOnly)

  def test_actual_sensor_threshold_and_digital_brake_sources(self):
    for alternate in (False, True):
      cp = params(alternate=alternate)
      ci = CarInterface(cp)
      packer = CANPacker(DBC[IDENTITY][Bus.pt])
      for tick in range(24):
        frames = pt_frames(packer, cruise=True, acc_cruise=4, counter=tick % 4)
        frames = [f for f in frames if f[0] != 0xC9 and (not alternate or f[0] != 0xBE)]
        frames.append(packer.make_can_msg('ECMEngineStatus', 0, {'CruiseMainOn': 1, 'BrakePressed': int(tick >= 18)}))
        if alternate:
          frames.append(packer.make_can_msg('EBCMBrakePedalPosition', 0, {'BrakePedalPosition': 208}))
        frames += pedal_frames(packer, tick, removed=False)
        frames = [f for f in frames if f[0] != 0x201]
        sensor = packer.make_can_msg('GAS_SENSOR', 0, {'INTERCEPTOR_GAS': 22 if tick < 12 else 24,
                   'INTERCEPTOR_GAS2': 22 if tick < 12 else 24, 'STATE': 0, 'COUNTER_PEDAL': tick % 16})
        raw = bytearray(sensor[1])
        raw[-1] = pedal_crc(raw)
        frames.append((sensor[0], bytes(raw), sensor[2]))
        out = ci.update([(1_000_000_000 + tick * 10_000_000, frames)])
        self.assertTrue(out.canValid)
        self.assertEqual(out.gasPressed, tick >= 12)
        self.assertEqual(out.brakePressed, tick >= 18)
        self.assertTrue(out.cruiseState.enabled)
        self.assertTrue(out.cruiseState.standstill)

  def test_settings_confirmation_park_cas_and_next_startup(self):
    with OpenpilotPrefix():
      store = Params()
      cp = params()
      parked = [True]
      owner = FeatureSettingsOwner(store, lambda group: parked[0], vehicle_fingerprint=lambda: IDENTITY, vehicle_params=lambda cp=cp: cp)
      row = next(r for r in owner.snapshot('vehicle', parked=True, system_long=True,
                                          lateral_context=True, metric=False).rows if r.key == 'DisableOpenpilotLongitudinal')
      request = replace(row_change(row, 1), confirmation=True)
      parked[0] = False
      self.assertFalse(owner.apply(request))
      parked[0] = True
      self.assertFalse(owner.apply(replace(request, capability=('stale',))))
      self.assertTrue(owner.apply(request))
      self.assertTrue(cp.openpilotLongitudinalControl)
      VehicleStartupPreferences.read(store, enabled=True).prepare(cp)
      self.assertFalse(cp.openpilotLongitudinalControl)
      self.assertEqual(cp.safetyConfigs[0].safetyParam, 0xC184)
      self.assertEqual(lateral_policy_for(cp), 'silverado_cc')
      self.assertIsNone(longitudinal_policy_for(cp))

  def test_original_speed_based_accel_limits(self):
    cp = params()
    for speed, floor, ceiling in ((0., -.95, .60), (1.5, -1.3, .85), (4., -1.85, 1.15),
                                  (8., -2.3, 1.60), (15., -2.6, 2.), (30., -2.8, 2.)):
      self.assertEqual(CarInterface.get_pid_accel_limits(cp, speed, 35.), (floor, ceiling))


  def test_reached_float32_stopping_rate_through_actual_longcontrol(self):
    from openpilot.selfdrive.controls.lib.longcontrol import LongControl
    from opendbc.car.gm.tests.test_conventional_pedal import params as ordinary_params
    cs = SimpleNamespace(vEgo=.3, aEgo=0., brakePressed=False, gasPressed=False, canValid=True,
                         canTimeout=False, cruiseState=SimpleNamespace(standstill=True))
    for cp in (params(), ordinary_params(CAR.CADILLAC_CT6_CC)):
      control = LongControl(cp)
      self.assertEqual(control.stopping_decel_rate, .800000011920929)
      control.last_output_accel = -1.
      output = control.update(True, cs, -1.8, True, (-4., 2.))
      self.assertEqual(control.long_control_state, structs.CarControl.Actuators.LongControlState.stopping)
      self.assertEqual(output, -1.0080000001192093)

  def test_actual_card_aol_preference_and_exact_profile_negatives(self):
    for removed in (False, True):
      for disabled in (False, True):
        with OpenpilotPrefix(), patch.dict(os.environ, {'SIMULATION': '1', 'AOL_REPLAY_RUNTIME': '0'}):
          store = Params()
          store.put_bool('OpenpilotEnabledToggle', True, block=True)
          store.put_bool('GMPedalLongitudinal', True, block=True)
          store.put_bool('DisableOpenpilotLongitudinal', disabled, block=True)
          store.put_bool('AlwaysOnLateral', True, block=True)
          cp = CarInterface.get_params(IDENTITY, fingerprint(removed=removed), [], False, False, False)
          card = Car(CI=CarInterface(cp), RI=RadarInterface(cp))
          self.assertTrue(qualified_gm(card.CP))
          self.assertTrue(feature_enabled(store, card.CP, 'aol', {}))
          self.assertIsNotNone(card.aol_card_intent)
          self.assertEqual(card.CP.alternativeExperience, 32)
          self.assertEqual(card.CP.safetyConfigs[0].safetyParam, (0xC184 if disabled else 0xC182) + int(removed))
          for mutation in ('word', 'identity', 'dashcam', 'flags'):
            bad = card.CP.as_reader().as_builder()
            if mutation == 'word':
              bad.safetyConfigs[0].safetyParam ^= 8
            elif mutation == 'identity':
              bad.carFingerprint = CAR.CADILLAC_CT6_CC
            elif mutation == 'dashcam':
              bad.dashcamOnly = True
            else:
              bad.flags |= 1 << 30
            self.assertFalse(qualified_gm(bad), mutation)
            self.assertFalse(lane_centering_supported(bad), mutation)
            self.assertFalse(feature_enabled(store, bad, 'conditional', {}), mutation)
            self.assertFalse(feature_enabled(store, bad, 'aol', {}), mutation)

  def test_actual_caller_physical_memory_and_invalid_sng_recovery(self):
    cp = params(removed=True)
    ci = CarInterface(cp)
    packer = CANPacker(DBC[IDENTITY][Bus.pt])
    cc = structs.CarControl(enabled=True, latActive=True, longActive=True)
    cc.actuators.accel = 1.8
    cc.actuators.longControlState = structs.CarControl.Actuators.LongControlState.pid
    wheels = [packer.make_can_msg('EBCMWheelSpdFront', 0, {'FLWheelSpd': 0, 'FRWheelSpd': 0}),
              packer.make_can_msg('EBCMWheelSpdRear', 0, {'RLWheelSpd': 0, 'RRWheelSpd': 0})]
    tick = [0]
    def step(*, brake=False, bad_crc=False):
      n = tick[0]
      tick[0] += 1
      frames = pt_frames(packer, cruise=True, acc_cruise=4, counter=n % 4)
      frames = [f for f in frames if f[0] not in {0xC9, *(w[0] for w in wheels)}]
      frames += wheels + [packer.make_can_msg('ECMEngineStatus', 0, {'CruiseMainOn': 1, 'BrakePressed': int(brake)})]
      frames += pedal_frames(packer, n, removed=True, bad_crc=bad_crc)
      now = 1_000_000_000 + n * 40_000_000
      ci.update([(now, frames)])
      ci.CC.frame = n * 4
      _, messages = ci.apply(cc.as_reader(), now)
      return next(m for m in messages if m[0] == 0x200), n % 4
    for _ in range(24):
      emitted, counter = step()
    self.assertEqual(emitted, create_pedal_command(packer, 18. / 255., counter))
    steady, active = ci.CC.pedal_steady, ci.CC.pedal_active_last
    emitted, counter = step(brake=True)
    self.assertEqual(emitted, create_pedal_command(packer, 0., counter))
    self.assertEqual((ci.CC.pedal_steady, ci.CC.pedal_active_last), (steady, active))
    emitted, counter = step(bad_crc=True)
    self.assertEqual(emitted, create_pedal_command(packer, 0., counter))
    self.assertEqual((ci.CC.pedal_steady, ci.CC.pedal_active_last), (0., True))
    emitted, counter = step()
    # Immutable original rise at speed0/accel1.8: .007 + .011*.9 + .006.
    self.assertEqual(emitted, create_pedal_command(packer, .0229, counter))
    cc.longActive = False
    emitted, counter = step()
    self.assertEqual(emitted, create_pedal_command(packer, 0., counter))
    cc.longActive = True
    emitted, counter = step()
    self.assertEqual(emitted, create_pedal_command(packer, .0229, counter))
