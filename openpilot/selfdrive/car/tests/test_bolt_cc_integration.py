from openpilot.starpilot.longitudinal.tests.extension_helpers import extension_state
import unittest
from unittest.mock import patch
from opendbc.car.gm.tests.test_bolt_cc import fixture, feed, control
from opendbc.car.gm.values import CAR


class TestBoltCcControls(unittest.TestCase):
  def test_actual_controls_gas_override_keeps_lateral(self):
    from openpilot.common.prefix import OpenpilotPrefix
    from openpilot.common.params import Params
    from openpilot.selfdrive.controls.controlsd import Controls
    from openpilot.selfdrive.selfdrived.events import Events, EventName
    from openpilot.cereal import log
    import os

    cp, ci, packer = fixture(CAR.CHEVROLET_BOLT_CC_2018_2021)
    out, _ = feed(ci, packer, 1_000_000_000, gas=True)
    with OpenpilotPrefix(), patch.dict(os.environ, {'SIMULATION': '1'}):
      Params().put('CarParams', cp.to_bytes(), block=True)
      controls = Controls()
      controls.sm.data['carState'] = out.as_reader()
      drive = log.SelfdriveState.new_message()
      drive.enabled = drive.active = True
      controls.sm.data['selfdriveState'] = drive.as_reader()
      events = Events()
      events.add(EventName.gasPressedOverride)
      controls.sm.data['onroadEvents'] = events.to_msg()
      command, _ = controls.state_control()
      self.assertTrue(command.enabled and command.latActive)
      self.assertFalse(command.longActive)
      controls.sm.data['onroadEvents'] = []
      command, _ = controls.state_control()
      self.assertTrue(command.latActive and command.longActive)

  def test_card_metric_startup_and_live_configuration(self):
    from openpilot.common.prefix import OpenpilotPrefix
    from openpilot.common.params import Params
    from openpilot.selfdrive.car.card import Car
    from opendbc.car.gm.radar_interface import RadarInterface
    from unittest.mock import Mock
    from openpilot.cereal import messaging
    import os

    for initial in (False, True):
      with OpenpilotPrefix(), patch.dict(os.environ, {'SIMULATION': '1'}):
        settings = Params()
        settings.put_bool('OpenpilotEnabledToggle', True, block=True)
        settings.put_bool('IsMetric', initial, block=True)
        cp, ci, packer = fixture(CAR.CHEVROLET_BOLT_CC_2018_2021)
        card = Car(CI=ci, RI=RadarInterface(cp))
        self.assertFalse(card.CP.passive)
        self.assertEqual(card.is_metric, initial)
        out, _ = feed(ci, packer, 1_000_000_000, speed=12, stock=12)
        self.assertTrue(out.canValid)
        card.ci_initialized = True
        card.publish_sendcan = Mock()
        cc = control()
        cc.actuators.accel = -0.17
        msg = messaging.new_message('carControl', valid=True)
        msg.carControl = cc
        card.sm.update_msgs(1.001, [messaging.log_from_bytes(msg.to_bytes())])
        ci.CC.frame = 104
        with patch('openpilot.selfdrive.car.card.time.monotonic', return_value=1.001):
          card.controls_update(out, cc.as_reader())
        self.assertEqual(ci.CC.bolt_cc_metric, initial)
        frames = card.publish_sendcan.call_args.args[0]
        buttons = [m for m in frames if m[0] == 0x1e1]
        self.assertEqual(len(buttons), 0 if initial else 1)
        settings.put_bool('IsMetric', not initial, block=True)
        event = Mock()
        event.is_set.side_effect = [False, True]
        with patch('openpilot.selfdrive.car.card.time.sleep'):
          card.params_thread(event)
        self.assertEqual(card.is_metric, not initial)
        with patch('openpilot.selfdrive.car.card.time.monotonic', return_value=1.002):
          card.controls_update(out, cc.as_reader())
        self.assertEqual(ci.CC.bolt_cc_metric, not initial)

  def test_actual_longcontrol_bolt_policy_and_pedal_neighbor(self):
    from opendbc.car import structs
    from opendbc.car.gm.tests.test_bolt_cc import params
    from opendbc.car.gm.bolt_cc import BoltCcLongitudinalPolicy
    from opendbc.car.gm.longitudinal import GMPedalLongitudinalPolicy
    from openpilot.selfdrive.controls.lib.longcontrol import LongControl
    from openpilot.common.realtime import DT_CTRL

    identities = (CAR.CHEVROLET_BOLT_CC_2017, CAR.CHEVROLET_BOLT_CC_2018_2021, CAR.CHEVROLET_BOLT_CC_2022_2023)
    for identity in identities:
      with self.subTest(identity=identity):
        cp = params(identity)
        controller = LongControl(cp)
        self.assertIsInstance(extension_state(controller, 'vehicle_policy'), BoltCcLongitudinalPolicy)
        self.assertIsNone(extension_state(controller, 'gm_start'))
        self.assertIsNone(extension_state(controller, 'vehicle_stop'))
        self.assertEqual(controller.stopping_decel_rate, 11.18)
        state = structs.CarState.new_message()
        for speed, expected_kp in ((10.7, 0.0), (10.75, 2.5), (10.8, 5.0), (19.4, 3.5), (28.0, 2.0)):
          controller.reset()
          state.vEgo = speed
          state.aEgo = 0.3
          controller.update(True, state, 0.4, False, (-10.0, 10.0))
          self.assertAlmostEqual(controller.pid.k_p, expected_kp, places=6)
          self.assertAlmostEqual(controller.pid.p, expected_kp * 0.1, places=6)
          self.assertAlmostEqual(controller.pid.f, 0.4)
        controller.last_output_accel = 0.0
        state.vEgo = 0.0
        output = controller.update(True, state, 0.0, True, (-10.0, 10.0))
        self.assertAlmostEqual(output, -11.18 * DT_CTRL)
        disabled = cp.as_reader().as_builder()
        disabled.openpilotLongitudinalControl = False
        self.assertIsNone(extension_state(LongControl(disabled), 'vehicle_policy'))

    neighbor = LongControl(params(CAR.CHEVROLET_BOLT_CC_2018_2021, present=True, pedal=True))
    self.assertIsInstance(extension_state(neighbor, 'vehicle_policy'), GMPedalLongitudinalPolicy)
    self.assertIsNone(extension_state(neighbor, 'gm_start'))
    self.assertNotEqual(neighbor.stopping_decel_rate, 11.18)
