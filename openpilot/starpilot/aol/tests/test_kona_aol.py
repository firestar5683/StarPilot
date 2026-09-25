"""Exact main-only Kona AOL identity, intent and actual Controls onset."""
import os
import unittest
from unittest.mock import patch
from opendbc.car import gen_empty_fingerprint, structs
from opendbc.car.hyundai.interface import CarInterface
from opendbc.car.hyundai.values import CAR, HyundaiFlags
from opendbc.car.hyundai.kona_aol import qualified, allow_lateral_onset, KONA_AOL_WORD
from openpilot.starpilot.aol.intent import AolSettings
from openpilot.starpilot.car.hyundai.aol import policy_for, create_intent, native_accepts_cp


def params(car=CAR.HYUNDAI_KONA_NON_SCC):
  return CarInterface.get_params(car, gen_empty_fingerprint(), [], False, False, False)


class TestKonaAol(unittest.TestCase):
  def test_exact_stock_factory_and_named_independent_profile(self):
    cp = params()
    self.assertTrue(qualified(cp))
    self.assertEqual(cp.safetyConfigs[0].safetyParam, 0x1040)
    self.assertFalse(cp.openpilotLongitudinalControl)
    self.assertTrue(cp.pcmCruise)
    policy = policy_for(cp)
    self.assertTrue(policy.settings_supported and policy.runtime_supported)
    cp.safetyConfigs[0].safetyParam |= policy.safety_param_addition
    cp.alternativeExperience |= policy.alternative_experience_addition
    self.assertEqual(cp.safetyConfigs[0].safetyParam, KONA_AOL_WORD)
    self.assertTrue(native_accepts_cp(cp, int(cp.safetyConfigs[0].safetyModel.raw), KONA_AOL_WORD))
    for flag in (HyundaiFlags.HAS_LDA_BUTTON, HyundaiFlags.EV, HyundaiFlags.HYBRID, HyundaiFlags.CANFD):
      bad = cp.as_reader().as_builder()
      bad.flags |= int(flag)
      self.assertFalse(qualified(bad))
    for car in (CAR.HYUNDAI_KONA_EV_NON_SCC, CAR.KIA_FORTE_2019_NON_SCC, CAR.HYUNDAI_KONA):
      self.assertFalse(qualified(params(car)))

  def test_actual_main_intent_fault_requires_off_on_and_no_lkas_expansion(self):
    owner = create_intent(params(), AolSettings(True, 0., 0, 0, (0, 0, 0), (0, 0, 0)))
    cs = structs.CarState(canValid=True, gearShifter='drive')
    cs.cruiseState.available = True
    owner.update(cs, fault_active=False, now_ns=1)
    self.assertTrue(owner.allowed_latch)
    owner.update(cs, fault_active=True, now_ns=2)
    self.assertFalse(owner.allowed_latch)
    owner.update(cs, fault_active=False, now_ns=3)
    self.assertFalse(owner.allowed_latch)
    cs.cruiseState.available = False
    owner.update(cs, fault_active=False, now_ns=4)
    cs.cruiseState.available = True
    owner.update(cs, fault_active=False, now_ns=5)
    self.assertTrue(owner.allowed_latch)
    self.assertFalse(owner.has_lkas)

  def test_actual_controls_native_permission_and_driver_release_retry(self):
    from openpilot.cereal import messaging
    from openpilot.common.params import Params
    from openpilot.common.prefix import OpenpilotPrefix
    from openpilot.selfdrive.controls.controlsd import Controls
    from openpilot.starpilot.aol.wire import SAFETY_SERVICE, SafetyState, encode_safety
    from openpilot.starpilot.lateral.tests.test_lane_runtime import feed
    cp = params()
    policy = policy_for(cp)
    cp.safetyConfigs[0].safetyParam |= policy.safety_param_addition
    cp.alternativeExperience |= policy.alternative_experience_addition
    with OpenpilotPrefix(), patch.dict(os.environ, {'REPLAY':'1','AOL_REPLAY_RUNTIME':'1'}), \
         patch('openpilot.selfdrive.controls.controlsd.messaging.PubMaster'):
      Params().put_bool('AlwaysOnLateral', True)
      Params().put('CarParams', cp.to_bytes(), block=True)
      controls = Controls()
      self.assertTrue(controls.aol_replay)
      # held onset -> release -> ongoing grip -> loss -> held retry -> normal.
      cases = ((False,True,True,False), (False,False,True,True), (False,True,True,True),
               (False,False,False,False), (False,True,True,False), (True,True,True,True))
      for tick,(enabled,pressed,allowed,expected) in enumerate(cases):
        now = 1_000_000_000 + tick*10_000_000
        feed(controls, now, tick, active=enabled, enabled=enabled, fault=False)
        cs = messaging.new_message('carState',valid=True,logMonoTime=now)
        cs.carState = controls.sm['carState']
        cs.carState.gearShifter = 'drive'
        cs.carState.steeringPressed = pressed
        cs.carState.canValid = True
        cs.carState.cruiseState.available = True
        controls.sm.data['carState'] = cs.carState.as_reader()
        axis = messaging.new_message('aolAxisState',valid=True,logMonoTime=now)
        axis.aolAxisState.qualified = True
        axis.aolAxisState.sessionId = 'kona-session'
        axis.aolAxisState.observedMonoTime = now
        axis.aolAxisState.validUntilMonoTime = now+30_000_000
        axis.aolAxisState.desiredLateral = True
        axis.aolAxisState.lateralActive = allowed
        axis.aolAxisState.nativeAcknowledged = allowed
        wire = messaging.new_message(SAFETY_SERVICE,0,valid=True,logMonoTime=now)
        wire.aolSafetyWire = encode_safety(SafetyState(protocolVersion=1,compatible=True,observedMonoTime=now,
          validUntilMonoTime=now+200_000_000,safetyModel=int(cp.safetyConfigs[0].safetyModel.raw),
          safetyParam=KONA_AOL_WORD,lateralAllowed=allowed,longitudinalAllowed=False,
          requestedLateral=True,requestedLongitudinal=False,pandaSerial='panda',axisSessionId='kona-session'))
        controls.sm.update_msgs(now/1e9,[axis.as_reader(),wire.as_reader()])
        command,_ = controls.state_control()
        self.assertEqual(command.latActive,expected)
        self.assertEqual(command.enabled,enabled)
        self.assertFalse(command.longActive)
        self.assertEqual(controls.aol_previous_lateral_active,expected)

  def test_no_permission_cannot_be_created_by_onset_guard(self):
    for enabled in (False,True):
      for pressed in (False,True):
        for previous in (False,True):
          self.assertFalse(allow_lateral_onset(permitted=False,normal_enabled=enabled,
                                             steering_pressed=pressed,previous_active=previous))
