from types import SimpleNamespace as NS

import pytest

from openpilot.starpilot.aol.runtime import decide_axes
from openpilot.starpilot.aol.tests.test_ioniq_availability import car_state


@pytest.mark.parametrize('speed', [-0.002, 0.0, 0.002])
@pytest.mark.parametrize('threshold', [0.0, 1.0])
@pytest.mark.parametrize('grant', [False, True])
def test_zero_disables_speed_pause_without_granting_native_or_longitudinal(speed, threshold, grant):
  state = car_state()
  state.vEgo, state.brakePressed, state.standstill = speed, True, False
  result = decide_axes(
    standard_lateral=False,
    standard_longitudinal=False,
    intent=NS(allowedLatch=True, pauseLateral=False, pauseLongitudinal=True),
    native=NS(requestedLateral=True, lateralAllowed=grant, requestedLongitudinal=False, longitudinalAllowed=False),
    car_state=state,
    initialized=True,
    model_ready=True,
    no_entry=False,
    immediate_disable=False,
    dm_lockout=False,
    pause_brake_mps=threshold,
  )
  assert result.desired_lateral == (threshold == 0.0)
  assert result.lateral_active == (threshold == 0.0 and grant)
  assert not result.desired_longitudinal and not result.longitudinal_active
