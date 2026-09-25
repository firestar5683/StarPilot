"""Actual CAN/native acknowledgment and cruise consumers; synthetic transport clocks."""
import ast
import inspect
import textwrap
from types import SimpleNamespace
import unittest

from opendbc.car.hyundai.values import Buttons
from opendbc.safety.tests.test_hyundai_blended_alpha_paired_ack import AcknowledgedCancelStream
from openpilot.selfdrive.car.card import Car
from openpilot.selfdrive.car.cruise import VCruiseHelper, V_CRUISE_INITIAL
from openpilot.starpilot.vehicle_startup import VehicleStartupOwner


def reached_card_initialize():
  # Execute the exact reached Card initialization block, including its actual
  # facade call. The unrelated hardware/transport state_update loop is excluded.
  tree = ast.parse(textwrap.dedent(inspect.getsource(Car.state_update)))
  block = next(node for node in tree.body[0].body if isinstance(node, ast.If) and
               any(isinstance(call, ast.Call) and ast.unparse(call.func) == 'self.v_cruise_helper.initialize_v_cruise'
                   for call in ast.walk(node)))
  fn = ast.FunctionDef(name='initialize', args=ast.arguments(posonlyargs=[], args=[ast.arg(arg='self')],
                                                           kwonlyargs=[], kw_defaults=[], defaults=[]),
                       body=[block], decorator_list=[])
  namespace = {}
  exec(compile(ast.fix_missing_locations(ast.Module(body=[fn], type_ignores=[])), '<actual Card initialization>', 'exec'), namespace)
  return namespace['initialize']


class TestBlendedCruiseAcknowledgment(unittest.TestCase):

  def acknowledged(self, topology, button):
    stream = AcknowledgedCancelStream(topology)
    frames = stream.frames
    def moving_frames(*args):
      return [stream.packer.make_can_msg('WHL_SPD11', bus, dict.fromkeys(
        ('WHL_SPD_FL', 'WHL_SPD_FR', 'WHL_SPD_RL', 'WHL_SPD_RR'), 20)) if address == 0x386
        else (address, data, bus) for address, data, bus in frames(*args)]
    stream.frames = moving_frames
    stream.step(button=button)
    release = stream.step()
    self.assertFalse(release.buttonEnable)
    state = stream.wait_ack()
    self.assertTrue(state.buttonEnable)
    self.assertTrue(stream.safety.get_controls_allowed())
    self.assertEqual(list(state.buttonEvents), [])
    return stream, state

  def invoke_card(self, stream, previous):
    holder = VehicleStartupOwner()
    holder.owner = stream.owner
    helper = VCruiseHelper(stream.ci.CP)
    helper.v_cruise_kph = helper.v_cruise_kph_last = 90.
    instance = SimpleNamespace(sm={'carControl': SimpleNamespace(enabled=True)},
                               CC_prev=SimpleNamespace(enabled=False), CS_prev=previous,
                               experimental_mode=False, vehicle_startup=holder, v_cruise_helper=helper)
    reached_card_initialize()(instance)
    self.assertIsNone(holder.consume_cruise_resume())
    return helper.v_cruise_kph

  def test_actual_acknowledged_buttons_preserve_speed_across_feedback_delay(self):
    for topology in ('hdai', 'hdaii'):
      for button in (Buttons.CANCEL, Buttons.RES_ACCEL, Buttons.SET_DECEL):
        for delay in (1, 4):
          with self.subTest(topology=topology, button=button, delay=delay):
            stream, state = self.acknowledged(topology, button)
            previous = state
            for _ in range(delay):
              previous = stream.step()  # Actual fresh host-enabled acknowledgment must retain hint.
            result = self.invoke_card(stream, previous)
            self.assertEqual(result, V_CRUISE_INITIAL if button == Buttons.SET_DECEL else 90.)

  def test_acknowledged_hint_invalidation_and_single_consumption(self):
    for mode in ('edge', 'pedal', 'profile', 'expiry'):
      stream, state = self.acknowledged('hdai', Buttons.CANCEL)
      if mode == 'edge':
        stream.step(button=Buttons.CANCEL)
      elif mode == 'pedal':
        stream.step(brake=True)
      elif mode == 'profile':
        stream.step(evidence='wrong_profile')
      else:
        for _ in range(51):
          stream.step()
      self.assertIsNone(stream.owner.consume_cruise_resume(), mode)
    stream, state = self.acknowledged('hdaii', Buttons.RES_ACCEL)
    self.assertIs(stream.owner.consume_cruise_resume(), True)
    self.assertIsNone(stream.owner.consume_cruise_resume())

  def test_default_none_preserves_ordinary_initializer(self):
    from opendbc.car import structs
    from opendbc.car.hyundai.tests.test_palisade_2023 import params
    cp = params('hdai')
    cp.pcmCruise = False
    for button, expected in ((structs.CarState.ButtonEvent.Type.accelCruise, 90.),
                             (structs.CarState.ButtonEvent.Type.decelCruise, V_CRUISE_INITIAL)):
      state = structs.CarState()
      state.vEgo = 20 / 3.6
      state.buttonEvents = [structs.CarState.ButtonEvent(type=button, pressed=False)]
      for explicit_none in (False, True):
        helper = VCruiseHelper(cp)
        helper.v_cruise_kph = helper.v_cruise_kph_last = 90.
        helper.initialize_v_cruise(state, False, **({'resume': None} if explicit_none else {}))
        self.assertEqual(helper.v_cruise_kph, expected)
