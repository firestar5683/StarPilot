import math

import pytest

from openpilot.selfdrive.car.cruise import VCruiseHelper, IMPERIAL_INCREMENT
from openpilot.starpilot.controllers.cruise_action import CruiseActionPublisher, CruiseActionConsumer
from openpilot.starpilot.controllers.tests.test_cruise_action import State, Publisher, cp
from opendbc.car.structs import car


@pytest.mark.parametrize('metric,value,target', [(True, 55, 55 / 3.6), (False, 30, 30 * 0.44704)])
def test_real_absolute_request_changes_software_speed_without_physical_button(metric, value, target):
  now = 5_000_000_000
  params, sm = cp(), State(now)
  state = car.CarState.new_message(canValid=True, cruiseState={'available': True})
  helper = VCruiseHelper(params)
  helper.v_cruise_kph = 80
  publisher = Publisher()
  sender, consumer = CruiseActionPublisher(), CruiseActionConsumer()
  assert sender.dispatch(True, sm, params, publisher, now_ns=now, target_mps=target)
  assert str(publisher.message.slcAction.kind) == 'cruiseSet'
  assert consumer.apply(publisher.message, params, state, sm, helper, now_ns=now, is_metric=metric, enabled=True)
  assert helper.v_cruise_kph == pytest.approx(value if metric else value * IMPERIAL_INCREMENT)
  assert not list(state.buttonEvents)
  assert not consumer.apply(publisher.message, params, state, sm, helper, now_ns=now + 100_000_000,
                            is_metric=metric, enabled=True)


@pytest.mark.parametrize('target', [math.nan, math.inf, -1, 0, 100, True])
def test_bad_absolute_request_never_publishes(target):
  now = 5_000_000_000
  publisher = Publisher()
  assert not CruiseActionPublisher().dispatch(True, State(now), cp(), publisher, now_ns=now, target_mps=target)
  assert not hasattr(publisher, 'message')
