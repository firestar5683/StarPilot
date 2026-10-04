"""GM pedal events through the stock control state and native TX checks."""
import ast
from pathlib import Path
from types import SimpleNamespace as NS
import unittest

from openpilot.cereal import log
from opendbc.car.structs import car
from openpilot.selfdrive.selfdrived.events import Events
from openpilot.selfdrive.selfdrived.state import StateMachine
from openpilot.starpilot.aol.runtime import ordinary_lateral_requested
from opendbc.car.gm import gmcan
from opendbc.car.gm.values import CC_GATEWAY_STOCK_CAR, is_ordinary_cc_profile
from opendbc.safety.tests import test_gm_cc_gateway_stock as stock


def pedal_event_expression():
  # Compile the reached producer predicate rather than inventing pedal semantics.
  import openpilot.selfdrive.selfdrived.selfdrived as module
  tree = ast.parse(Path(module.__file__).read_text())
  matches = [node.test for node in ast.walk(tree) if isinstance(node, ast.If)
             and any(isinstance(call, ast.Call) and isinstance(call.func, ast.Attribute)
                     and call.func.attr == "add" and call.args
                     and isinstance(call.args[0], ast.Attribute)
                     and call.args[0].attr == "pedalPressed"
                     for statement in node.body if isinstance(statement, ast.Expr)
                     for call in (statement.value,))]
  if len(matches) != 1:
    raise AssertionError("SelfdriveD pedal predicate changed; review its caller")
  return compile(ast.Expression(matches[0]), "SelfdriveD.pedalPressed", "eval")


class TestGMStockCaller(unittest.TestCase):
  def test_decoded_pedals_normal_axis_and_adversarial_native_boundary(self):
    predicate = pedal_event_expression()
    fixture = stock.TestGmCcGatewayStock()
    fixture.setUp()
    self.addCleanup(fixture.safety.set_safety_hooks, car.CarParams.SafetyModel.noOutput, 0)
    self.addCleanup(fixture.safety.set_alternative_experience, 0)
    for identity in sorted(CC_GATEWAY_STOCK_CAR):
      for brake, gas, accelerator_disengage in ((False, False, False), (True, False, False),
                                               (False, True, False), (False, True, True)):
        with self.subTest(identity=identity, brake=brake, gas=gas, accelerator_disengage=accelerator_disengage):
          # Capture the real decoded CS and CP via the actual CI/controller fixture.
          packer, frames, _ = fixture.joined(identity, brake=brake, gas=gas, active=False, cancel=False)
          cp, ci, cs = fixture.joined_cp, fixture.joined_interface, fixture.joined_state
          self.assertEqual(cs.brakePressed, brake)
          self.assertEqual(cs.gasPressed, gas)
          self.assertFalse(cs.standstill)
          previous = car.CarState.new_message()
          events = Events()
          producer = NS(CS_prev=previous, disengage_on_accelerator=accelerator_disengage)
          if eval(predicate, {"CS": cs, "self": producer}):
            events.add(log.OnroadEvent.EventName.pedalPressed)
          machine = StateMachine()
          machine.state = log.SelfdriveState.OpenpilotState.enabled
          enabled, active = machine.update(events)
          self.assertEqual(active, not (brake or (gas and accelerator_disengage)))
          requested = ordinary_lateral_requested(active, cs, cp)
          control = car.CarControl.new_message()
          control.enabled = enabled
          control.latActive = requested
          control.actuators.torque = .03
          # Disabled steering is 10 Hz. Advance ten real 100-Hz input frames,
          # keeping physical sources fresh before the next eligible TX slot.
          for tick in range(1, 11):
            stamp = 1_050_000_000 + tick * 10_000_000
            current_frames = [frame for frame in frames if frame[0] != 0x1E1]
            if tick % 3 == 0:
              current_frames.append(gmcan.create_buttons(packer, 0, (2 + tick // 3) % 4, 1))
            cs = ci.update([(stamp, current_frames)])
            self.assertTrue(cs.canValid)
            fixture.safety.set_timer(stamp // 1000)
            fixture.feed(current_frames)
          ci.CC.frame = 30
          _, commands = ci.CC.update(control.as_reader(), ci.CS, stamp)
          steering = next(msg for msg in commands if msg[0] == 0x180)
          torque = ((steering[1][0] & 7) << 8) | steering[1][1]
          self.assertEqual(torque > 0, requested and (not gas or is_ordinary_cc_profile(cp)))
          self.assertTrue(fixture.safety.safety_tx_hook(fixture.packet(steering)))
