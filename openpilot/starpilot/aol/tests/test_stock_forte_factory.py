"""Joined adapter-factory regression for stock CAN-FD and classic lateral policies."""
import unittest

from opendbc.car.structs import car
from opendbc.car.hyundai.values import CAR, HyundaiFlags
from openpilot.starpilot.aol.intent import AolSettings
from openpilot.starpilot.aol.vehicle import create_intent, native_matches_cp, policy_for
from openpilot.starpilot.car.hyundai.forte_intent import ForteCardIntent
from openpilot.starpilot.aol.tests.test_forte_intent import params as forte_params, state as forte_state

Button = car.CarState.ButtonEvent.Type


def stock(alternate):
  cp = car.CarParams.new_message()
  cp.brand, cp.carFingerprint = 'hyundai', CAR.HYUNDAI_IONIQ_6
  cp.flags = int(HyundaiFlags.CANFD | HyundaiFlags.EV | HyundaiFlags.CANFD_LKA_STEER_MSG)
  if alternate:
    cp.flags |= int(HyundaiFlags.CANFD_LKA_STEER_MSG_ALT)
  cp.pcmCruise, cp.openpilotLongitudinalControl, cp.radarUnavailable = True, False, False
  cp.safetyConfigs = [{'safetyModel': car.CarParams.SafetyModel.hyundaiCanfd,
                       'safetyParam': 0x91 if alternate else 0x11}]
  return cp


def settings(lkas=9, main=0):
  return AolSettings(True, 0., lkas, main, (0, 0, 0), (0, 0, 0))


class TestStockForteFactory(unittest.TestCase):
  def test_actual_dispatcher_stock_factory_retains_latch_before_marker(self):
    for alternate in (False, True):
      with self.subTest(alternate=alternate):
        cp = stock(alternate)
        policy = policy_for(cp)
        intent = create_intent(cp, settings(), policy)
        self.assertTrue(policy.intent_supported and policy.explicit_latch)
        self.assertTrue(intent.explicit_latch)
        self.assertFalse(intent.allowed_latch)
        model, original = int(cp.safetyConfigs[0].safetyModel.raw), int(cp.safetyConfigs[0].safetyParam)
        self.assertFalse(native_matches_cp(cp, model, original))
        cp.safetyConfigs[0].safetyParam |= policy.safety_param_addition
        serialized = cp.as_reader().as_builder()
        self.assertEqual(serialized.safetyConfigs[0].safetyParam, original | 0x0800)
        self.assertTrue(native_matches_cp(serialized, model, original | 0x0800))
        self.assertFalse(native_matches_cp(serialized, model, original))
        self.assertTrue(serialized.pcmCruise)
        self.assertFalse(serialized.openpilotLongitudinalControl)
        disabled = create_intent(stock(alternate), AolSettings(False, 0., 9, 0, (0, 0, 0), (0, 0, 0)), policy)
        self.assertTrue(disabled.explicit_latch)
        self.assertFalse(disabled.allowed_latch)

  def test_forte_dispatcher_retains_direct_button_state_machine(self):
    for platform in (CAR.KIA_FORTE_2019_NON_SCC, CAR.KIA_FORTE_2021_NON_SCC):
      for source in (0, 0x391, 0x50c):
        for main_action in (0, 9):
          with self.subTest(platform=platform, source=source, main_action=main_action):
            cp = forte_params(platform, source)
            configured = settings(main=main_action)
            dispatched = create_intent(cp, configured, policy_for(cp))
            direct = ForteCardIntent(cp, configured)
            self.assertIs(type(dispatched), ForteCardIntent)
            for tick, events in enumerate(((), ((Button.lkas, False),), ((Button.lkas, True),),
                                           ((Button.lkas, False),), ((Button.lkas, True),),
                                           ((Button.lkas, False),)), 1):
              cs = forte_state(main=True, cruise=tick > 1, events=events)
              for intent in (dispatched, direct):
                intent.update(cs, now_ns=tick)
              for attribute in ('allowed_latch', 'pause_lateral', 'pause_longitudinal',
                                'physical_latch', 'fault_rearm', 'neutral_seen'):
                self.assertEqual(getattr(dispatched, attribute), getattr(direct, attribute), attribute)
