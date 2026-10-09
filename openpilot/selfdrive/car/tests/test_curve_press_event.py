import time
import unittest
from types import SimpleNamespace as NS
from unittest.mock import patch

from openpilot.cereal import messaging
from openpilot.selfdrive.car.card import Car, curve_press_receipt
from openpilot.selfdrive.car.tests.publication_fixture import initialize_publication_sources
from openpilot.selfdrive.car.cruise import VCruiseHelper
from opendbc.car.structs import car


ACCEL = car.CarState.ButtonEvent.Type.accelCruise
RESUME = car.CarState.ButtonEvent.Type.resumeCruise


def car_state(*, press=True, button=ACCEL):
  state = car.CarState(canValid=True, vCruise=100.0, cruiseState={'available': True})
  state.buttonEvents = [car.CarState.ButtonEvent(type=button, pressed=press)]
  return state


class Publisher:
  def __init__(self):
    self.events = []

  def send(self, service, event):
    self.events.append((service, event.to_bytes()))


class CurvePressEventTests(unittest.TestCase):
  def setUp(self):
    self.cp = car.CarParams(openpilotLongitudinalControl=True, pcmCruise=False)
    self.helper = VCruiseHelper(self.cp)
    self.sm = {'slcState': NS(hasPending=False)}

  def receipt(self, state, *, curve_replay=True, slc_replay=False, host_long_active=True):
    return curve_press_receipt(state, self.helper, self.sm, curve_replay=curve_replay,
                               slc_replay=slc_replay, host_long_active=host_long_active,
                               observed_ns=123)

  def test_physical_press_without_speed_change_and_pcm_exclusion(self):
    state = car_state()
    self.helper.v_cruise_kph_last = 90.0
    self.helper.v_cruise_kph = 90.0
    self.assertEqual(self.receipt(state), ('curveAccelPress', None, 25.0, 25.0, 123))
    self.helper.v_cruise_kph = 93.6
    self.assertAlmostEqual(self.receipt(state)[3], 26.0)
    self.assertIsNone(self.receipt(state, curve_replay=False))
    self.assertIsNone(self.receipt(state, host_long_active=False))
    self.assertIsNone(self.receipt(car_state(press=False)))
    state.canTimeout = True
    self.assertTrue(state.canValid)
    self.assertIsNone(self.receipt(state))

  def test_every_slc_confirmation_attempt_reserves_press(self):
    state = car_state()
    self.sm['slcState'].hasPending = True  # stale or rejected for qualification still owns this presentation press
    self.assertIsNone(self.receipt(state, slc_replay=True))
    self.sm['slcState'].hasPending = False
    with patch.object(self.helper, "slc_consumed_button", object()):
      self.assertIsNone(self.receipt(state, slc_replay=True))
    self.helper.slc_suppressed_buttons.add(ACCEL)
    self.assertIsNone(self.receipt(state, slc_replay=True))

  def test_resume_press_and_simultaneous_buttons_emit_one_receipt(self):
    resume = car_state(button=RESUME)
    self.assertEqual(self.receipt(resume)[0], 'curveAccelPress')
    self.helper.slc_suppressed_buttons.add(RESUME)
    self.assertIsNone(self.receipt(resume, slc_replay=True))
    self.helper.slc_suppressed_buttons.clear()
    simultaneous = car_state()
    simultaneous.buttonEvents = [car.CarState.ButtonEvent(type=ACCEL, pressed=True),
                                 car.CarState.ButtonEvent(type=RESUME, pressed=True)]
    self.assertEqual(self.receipt(simultaneous)[0], 'curveAccelPress')
    self.helper.slc_suppressed_buttons.add(ACCEL)
    self.assertIsNone(self.receipt(simultaneous, slc_replay=True))

  def card(self, **overrides):
    publisher = Publisher()
    card = Car.__new__(Car)
    values = {'sm': NS(frame=1, all_checks=lambda _names: True), 'pm': publisher, 'CP': self.cp,
              'slc_replay': False, 'curve_replay': True, 'aol_replay': False, 'slc_cruise_event_id': 0,
              'slc_producer_session': 'card-session', 'last_actuators_output': car.CarControl.Actuators(),
              'can_rcv_cum_timeout_counter': 0, 'rk': NS(remaining=0.0), 'v_cruise_helper': self.helper}
    for name, value in (values | overrides).items():
      self.enterContext(patch.object(card, name, value, create=True))
    initialize_publication_sources(card)
    return card, publisher

  def test_curve_only_replay_preserves_recorded_car_and_event_time(self):
    fake, publisher = self.card(can_log_mono_time=8_000_000_000,
                                slc_receipts=[('curveAccelPress', None, 25.0, 25.0, 8_000_000_000)])
    with patch('openpilot.selfdrive.car.card.REPLAY', True):
      Car.state_publish(fake, car_state(), None)
    frames = {name: messaging.log_from_bytes(payload) for name, payload in publisher.events}
    self.assertEqual(frames['carState'].logMonoTime, 8_000_000_000)
    self.assertEqual(frames['slcCruiseEvent'].logMonoTime, 8_000_000_000)

  def test_card_publishes_ordered_typed_press_and_driver_change(self):
    fake, publisher = self.card()
    observed = time.monotonic_ns()
    self.helper.v_cruise_kph_last = 90.0
    self.helper.v_cruise_kph = 90.0
    fake.slc_receipts = [curve_press_receipt(car_state(), self.helper, self.sm, curve_replay=True,
                                             slc_replay=False, host_long_active=True, observed_ns=observed)]
    self.helper.slc_cruise_change = (25.0, 26.0, 'decel', False)
    Car.state_publish(fake, car_state(), None)
    decoded = [messaging.log_from_bytes(payload) for service, payload in publisher.events if service == 'slcCruiseEvent']
    self.assertEqual(len(decoded), 2)
    press, change = (message.slcCruiseEvent for message in decoded)
    self.assertEqual((press.eventId, change.eventId), (1, 2))
    self.assertEqual((str(press.kind), str(press.button)), ('curveAccelPress', 'accel'))
    self.assertEqual((press.previousMps, press.selectedMps), (25.0, 25.0))
    self.assertEqual((str(change.kind), str(change.button)), ('driverChange', 'decel'))
    self.assertEqual((change.previousMps, change.selectedMps), (25.0, 26.0))
    self.assertEqual(decoded[0].logMonoTime, decoded[1].logMonoTime)


if __name__ == '__main__':
  unittest.main()
