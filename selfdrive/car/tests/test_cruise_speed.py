import pytest
import itertools
import math
import numpy as np

from parameterized import parameterized_class
from types import SimpleNamespace
from cereal import log
from openpilot.selfdrive.car.cruise import (
  VCruiseHelper, V_CRUISE_MIN, V_CRUISE_MAX, V_CRUISE_INITIAL, IMPERIAL_INCREMENT,
  is_speed_limit_confirmation_pending,
)
from cereal import car
from openpilot.common.constants import CV
from openpilot.selfdrive.test.longitudinal_maneuvers.maneuver import Maneuver

ButtonEvent = car.CarState.ButtonEvent
ButtonType = car.CarState.ButtonEvent.Type


@pytest.mark.parametrize(("speed_limit_changed", "unconfirmed_speed_limit", "expected"), [
  (False, 0.0, False),
  (True, 0.0, False),
  (True, 15.0, True),
])
def test_speed_limit_confirmation_pending(speed_limit_changed, unconfirmed_speed_limit, expected):
  plan = SimpleNamespace(
    speedLimitChanged=speed_limit_changed,
    unconfirmedSlcSpeedLimit=unconfirmed_speed_limit,
  )

  assert is_speed_limit_confirmation_pending(plan) is expected


def run_cruise_simulation(cruise, e2e, personality, t_end=20.):
  man = Maneuver(
    '',
    duration=t_end,
    initial_speed=max(cruise - 1., 0.0),
    lead_relevancy=True,
    initial_distance_lead=100,
    cruise_values=[cruise],
    prob_lead_values=[0.0],
    breakpoints=[0.],
    e2e=e2e,
    personality=personality,
  )
  valid, output = man.evaluate()
  assert valid
  return output[-1, 3]


@parameterized_class(("e2e", "personality", "speed"), itertools.product(
                      [True, False], # e2e
                      log.LongitudinalPersonality.schema.enumerants, # personality
                      [5,35])) # speed
class TestCruiseSpeed:
  def test_cruise_speed(self):
    print(f'Testing {self.speed} m/s')
    cruise_speed = float(self.speed)

    simulation_steady_state = run_cruise_simulation(cruise_speed, self.e2e, self.personality)
    assert simulation_steady_state == pytest.approx(cruise_speed, rel=.04, abs=.15), f'Did not approach {self.speed} m/s'


# TODO: test pcmCruise
@parameterized_class(('pcm_cruise',), [(False,)])
class TestVCruiseHelper:
  def setup_method(self):
    self.CP = car.CarParams(pcmCruise=self.pcm_cruise)
    self.v_cruise_helper = VCruiseHelper(self.CP)
    self.starpilot_toggles = SimpleNamespace(
      cruise_increase=1,
      cruise_increase_long=5,
      is_metric=False,
      set_speed_limit=False,
    )
    self.reset_cruise_speed_state()

  def reset_cruise_speed_state(self):
    # Two resets previous cruise speed
    for _ in range(2):
      self.v_cruise_helper.update_v_cruise(
        car.CarState(cruiseState={"available": False}),
        enabled=False,
        is_metric=False,
        speed_limit_changed=False,
        starpilot_toggles=self.starpilot_toggles,
      )

  def enable(self, v_ego, experimental_mode):
    # Simulates user pressing set with a current speed
    self.v_cruise_helper.initialize_v_cruise(
      car.CarState(vEgo=v_ego),
      experimental_mode,
      False,
      self.starpilot_toggles,
    )

  def test_adjust_speed(self):
    """
    Asserts speed changes on falling edges of buttons.
    """

    self.enable(V_CRUISE_INITIAL * CV.KPH_TO_MS, False)

    for btn in (ButtonType.accelCruise, ButtonType.decelCruise):
      for pressed in (True, False):
        CS = car.CarState(cruiseState={"available": True})
        CS.buttonEvents = [ButtonEvent(type=btn, pressed=pressed)]

        self.v_cruise_helper.update_v_cruise(
          CS,
          enabled=True,
          is_metric=False,
          speed_limit_changed=False,
          starpilot_toggles=self.starpilot_toggles,
        )
        assert pressed == (self.v_cruise_helper.v_cruise_kph == self.v_cruise_helper.v_cruise_kph_last)

  def test_accel_stops_at_slc_target_before_crossing_it(self):
    self.starpilot_toggles.cruise_increase = 5
    self.v_cruise_helper.v_cruise_kph = 30
    self.v_cruise_helper.v_cruise_cluster_kph = 30
    slc_target_with_offset = 33 * CV.KPH_TO_MS

    # A 30 km/h limit with a +3 km/h SLC offset should be an intermediate stop.
    for expected_kph in (33, 35, 40):
      for pressed in (True, False):
        CS = car.CarState(cruiseState={"available": True})
        CS.buttonEvents = [ButtonEvent(type=ButtonType.accelCruise, pressed=pressed)]
        self.v_cruise_helper.update_v_cruise(
          CS,
          enabled=True,
          is_metric=True,
          speed_limit_changed=False,
          starpilot_toggles=self.starpilot_toggles,
          slc_target_with_offset=slc_target_with_offset,
        )

      assert self.v_cruise_helper.v_cruise_kph == pytest.approx(expected_kph)

  def test_accel_uses_normal_interval_without_an_active_slc_target(self):
    self.starpilot_toggles.cruise_increase = 5
    self.v_cruise_helper.v_cruise_kph = 30
    self.v_cruise_helper.v_cruise_cluster_kph = 30

    # Card passes zero when SLC is disabled or has no active speed-limit source.
    for pressed in (True, False):
      CS = car.CarState(cruiseState={"available": True})
      CS.buttonEvents = [ButtonEvent(type=ButtonType.accelCruise, pressed=pressed)]
      self.v_cruise_helper.update_v_cruise(
        CS,
        enabled=True,
        is_metric=True,
        speed_limit_changed=False,
        starpilot_toggles=self.starpilot_toggles,
      )

    assert self.v_cruise_helper.v_cruise_kph == pytest.approx(35)

  def test_hard_press_uses_long_press_interval(self):
    self.enable(52 * CV.MPH_TO_MS, False)
    initial_v_cruise_kph = self.v_cruise_helper.v_cruise_kph

    pressed_cs = car.CarState(cruiseState={"available": True})
    pressed_cs.buttonEvents = [ButtonEvent(type=ButtonType.accelCruise, pressed=True)]
    starpilot_car_state = SimpleNamespace(accelHardCruise=True, decelHardCruise=False)
    self.v_cruise_helper.update_v_cruise(
      pressed_cs,
      enabled=True,
      is_metric=False,
      speed_limit_changed=False,
      starpilot_toggles=self.starpilot_toggles,
      starpilot_car_state=starpilot_car_state,
    )

    released_cs = car.CarState(cruiseState={"available": True})
    released_cs.buttonEvents = [ButtonEvent(type=ButtonType.accelCruise, pressed=False)]
    self.v_cruise_helper.update_v_cruise(
      released_cs,
      enabled=True,
      is_metric=False,
      speed_limit_changed=False,
      starpilot_toggles=self.starpilot_toggles,
      starpilot_car_state=starpilot_car_state,
    )

    hard_interval = self.starpilot_toggles.cruise_increase_long * IMPERIAL_INCREMENT
    expected_kph = math.ceil(initial_v_cruise_kph / hard_interval) * hard_interval
    assert self.v_cruise_helper.v_cruise_kph == pytest.approx(expected_kph)

  def test_hard_decel_press_uses_long_press_interval(self):
    self.enable(52 * CV.MPH_TO_MS, False)
    initial_v_cruise_kph = self.v_cruise_helper.v_cruise_kph

    pressed_cs = car.CarState(cruiseState={"available": True})
    pressed_cs.buttonEvents = [ButtonEvent(type=ButtonType.decelCruise, pressed=True)]
    starpilot_car_state = SimpleNamespace(accelHardCruise=False, decelHardCruise=True)
    self.v_cruise_helper.update_v_cruise(
      pressed_cs,
      enabled=True,
      is_metric=False,
      speed_limit_changed=False,
      starpilot_toggles=self.starpilot_toggles,
      starpilot_car_state=starpilot_car_state,
    )

    released_cs = car.CarState(cruiseState={"available": True})
    released_cs.buttonEvents = [ButtonEvent(type=ButtonType.decelCruise, pressed=False)]
    self.v_cruise_helper.update_v_cruise(
      released_cs,
      enabled=True,
      is_metric=False,
      speed_limit_changed=False,
      starpilot_toggles=self.starpilot_toggles,
      starpilot_car_state=starpilot_car_state,
    )

    hard_interval = self.starpilot_toggles.cruise_increase_long * IMPERIAL_INCREMENT
    expected_kph = math.floor(initial_v_cruise_kph / hard_interval) * hard_interval
    assert self.v_cruise_helper.v_cruise_kph == pytest.approx(expected_kph)

  def test_rising_edge_enable(self):
    """
    Some car interfaces may enable on rising edge of a button,
    ensure we don't adjust speed if enabled changes mid-press.
    """

    # NOTE: enabled is always one frame behind the result from button press in controlsd
    for enabled, pressed in ((False, False),
                             (False, True),
                             (True, False)):
      CS = car.CarState(cruiseState={"available": True})
      CS.buttonEvents = [ButtonEvent(type=ButtonType.decelCruise, pressed=pressed)]
      self.v_cruise_helper.update_v_cruise(
        CS,
        enabled=enabled,
        is_metric=False,
        speed_limit_changed=False,
        starpilot_toggles=self.starpilot_toggles,
      )
      if pressed:
        self.enable(V_CRUISE_INITIAL * CV.KPH_TO_MS, False)

      # Expected diff on enabling. Speed should not change on falling edge of pressed
      assert not pressed == self.v_cruise_helper.v_cruise_kph == self.v_cruise_helper.v_cruise_kph_last

  def test_resume_in_standstill(self):
    """
    Asserts we don't increment set speed if user presses resume/accel to exit cruise standstill.
    """

    self.enable(0, False)

    for standstill in (True, False):
      for pressed in (True, False):
        CS = car.CarState(cruiseState={"available": True, "standstill": standstill})
        CS.buttonEvents = [ButtonEvent(type=ButtonType.accelCruise, pressed=pressed)]
        self.v_cruise_helper.update_v_cruise(
          CS,
          enabled=True,
          is_metric=False,
          speed_limit_changed=False,
          starpilot_toggles=self.starpilot_toggles,
        )

        # speed should only update if not at standstill and button falling edge
        should_equal = standstill or pressed
        assert should_equal == (self.v_cruise_helper.v_cruise_kph == self.v_cruise_helper.v_cruise_kph_last)

  def test_set_gas_pressed(self):
    """
    Asserts pressing set while enabled with gas pressed sets
    the speed to the maximum of vEgo and current cruise speed.
    """

    for v_ego in np.linspace(0, 100, 101):
      self.reset_cruise_speed_state()
      self.enable(V_CRUISE_INITIAL * CV.KPH_TO_MS, False)

      # first decrement speed, then perform gas pressed logic
      expected_v_cruise_kph = self.v_cruise_helper.v_cruise_kph - IMPERIAL_INCREMENT
      expected_v_cruise_kph = max(expected_v_cruise_kph, v_ego * CV.MS_TO_KPH)  # clip to min of vEgo
      expected_v_cruise_kph = float(np.clip(round(expected_v_cruise_kph, 1), V_CRUISE_MIN, V_CRUISE_MAX))

      CS = car.CarState(vEgo=float(v_ego), gasPressed=True, cruiseState={"available": True})
      CS.buttonEvents = [ButtonEvent(type=ButtonType.decelCruise, pressed=False)]
      self.v_cruise_helper.update_v_cruise(
        CS,
        enabled=True,
        is_metric=False,
        speed_limit_changed=False,
        starpilot_toggles=self.starpilot_toggles,
      )

      # TODO: fix skipping first run due to enabled on rising edge exception
      if v_ego == 0.0:
        continue
      assert expected_v_cruise_kph == self.v_cruise_helper.v_cruise_kph

  def test_initialize_v_cruise(self):
    """
    Asserts allowed cruise speeds on enabling with SET.
    """

    for experimental_mode in (True, False):
      for v_ego in np.linspace(0, 100, 101):
        self.reset_cruise_speed_state()
        assert not self.v_cruise_helper.v_cruise_initialized

        self.enable(float(v_ego), experimental_mode)
        assert V_CRUISE_MIN <= self.v_cruise_helper.v_cruise_kph <= V_CRUISE_MAX
        assert self.v_cruise_helper.v_cruise_initialized

  def test_initialize_v_cruise_matches_speed_limit(self):
    self.reset_cruise_speed_state()
    self.starpilot_toggles.set_speed_limit = True

    desired_speed_limit = 55 * CV.MPH_TO_MS
    self.v_cruise_helper.initialize_v_cruise(
      car.CarState(vEgo=70 * CV.MPH_TO_MS),
      experimental_mode=False,
      resume_prev_button=False,
      starpilot_toggles=self.starpilot_toggles,
      desired_speed_limit=desired_speed_limit,
    )

    assert self.v_cruise_helper.v_cruise_kph == round(55 * CV.MPH_TO_KPH, 1)

  def test_initialize_v_cruise_keeps_exact_speed_limit_offset(self):
    self.reset_cruise_speed_state()
    self.starpilot_toggles.set_speed_limit = True
    self.starpilot_toggles.cruise_increase = 5

    desired_speed_limit = 38 * CV.MPH_TO_MS
    self.v_cruise_helper.initialize_v_cruise(
      car.CarState(vEgo=70 * CV.MPH_TO_MS),
      experimental_mode=False,
      resume_prev_button=False,
      starpilot_toggles=self.starpilot_toggles,
      desired_speed_limit=desired_speed_limit,
    )

    assert self.v_cruise_helper.v_cruise_kph == round(38 * CV.MPH_TO_KPH, 1)

  def test_speed_limit_confirmation_does_not_adjust_cruise(self):
    self.enable(V_CRUISE_INITIAL * CV.KPH_TO_MS, False)
    initial_v_cruise_kph = self.v_cruise_helper.v_cruise_kph

    pressed_cs = car.CarState(cruiseState={"available": True})
    pressed_cs.buttonEvents = [ButtonEvent(type=ButtonType.decelCruise, pressed=True)]
    self.v_cruise_helper.update_v_cruise(
      pressed_cs,
      enabled=True,
      is_metric=False,
      speed_limit_changed=False,
      starpilot_toggles=self.starpilot_toggles,
    )

    released_cs = car.CarState(cruiseState={"available": True})
    released_cs.buttonEvents = [ButtonEvent(type=ButtonType.decelCruise, pressed=False)]
    self.v_cruise_helper.update_v_cruise(
      released_cs,
      enabled=True,
      is_metric=False,
      speed_limit_changed=True,
      starpilot_toggles=self.starpilot_toggles,
    )

    assert self.v_cruise_helper.v_cruise_kph == initial_v_cruise_kph

  def test_speed_limit_confirmation_press_release_does_not_leak_after_acceptance(self):
    for button_type in (ButtonType.accelCruise, ButtonType.decelCruise):
      self.enable(V_CRUISE_INITIAL * CV.KPH_TO_MS, False)
      initial_v_cruise_kph = self.v_cruise_helper.v_cruise_kph

      pressed_cs = car.CarState(cruiseState={"available": True})
      pressed_cs.buttonEvents = [ButtonEvent(type=button_type, pressed=True)]
      self.v_cruise_helper.update_v_cruise(
        pressed_cs,
        enabled=True,
        is_metric=False,
        speed_limit_changed=True,
        starpilot_toggles=self.starpilot_toggles,
      )

      # The planner may have consumed the confirmation by the time the physical
      # button release arrives. The release must remain confirmation-only.
      released_cs = car.CarState(cruiseState={"available": True})
      released_cs.buttonEvents = [ButtonEvent(type=button_type, pressed=False)]
      self.v_cruise_helper.update_v_cruise(
        released_cs,
        enabled=True,
        is_metric=False,
        speed_limit_changed=False,
        starpilot_toggles=self.starpilot_toggles,
      )

      assert self.v_cruise_helper.v_cruise_kph == initial_v_cruise_kph

  def test_stale_speed_limit_change_does_adjust_cruise(self):
    self.enable(V_CRUISE_INITIAL * CV.KPH_TO_MS, False)
    initial_v_cruise_kph = self.v_cruise_helper.v_cruise_kph
    plan = SimpleNamespace(speedLimitChanged=True, unconfirmedSlcSpeedLimit=0.0)

    pressed_cs = car.CarState(cruiseState={"available": True})
    pressed_cs.buttonEvents = [ButtonEvent(type=ButtonType.accelCruise, pressed=True)]
    self.v_cruise_helper.update_v_cruise(
      pressed_cs,
      enabled=True,
      is_metric=False,
      speed_limit_changed=is_speed_limit_confirmation_pending(plan),
      starpilot_toggles=self.starpilot_toggles,
    )

    released_cs = car.CarState(cruiseState={"available": True})
    released_cs.buttonEvents = [ButtonEvent(type=ButtonType.accelCruise, pressed=False)]
    self.v_cruise_helper.update_v_cruise(
      released_cs,
      enabled=True,
      is_metric=False,
      speed_limit_changed=is_speed_limit_confirmation_pending(plan),
      starpilot_toggles=self.starpilot_toggles,
    )

    assert self.v_cruise_helper.v_cruise_kph > initial_v_cruise_kph

  def test_missing_custom_cruise_toggles_fall_back_to_single_step(self):
    self.enable(V_CRUISE_INITIAL * CV.KPH_TO_MS, False)
    initial_v_cruise_kph = self.v_cruise_helper.v_cruise_kph
    self.starpilot_toggles.cruise_increase = None
    self.starpilot_toggles.cruise_increase_long = None

    pressed_cs = car.CarState(cruiseState={"available": True})
    pressed_cs.buttonEvents = [ButtonEvent(type=ButtonType.accelCruise, pressed=True)]
    self.v_cruise_helper.update_v_cruise(
      pressed_cs,
      enabled=True,
      is_metric=False,
      speed_limit_changed=False,
      starpilot_toggles=self.starpilot_toggles,
    )

    released_cs = car.CarState(cruiseState={"available": True})
    released_cs.buttonEvents = [ButtonEvent(type=ButtonType.accelCruise, pressed=False)]
    self.v_cruise_helper.update_v_cruise(
      released_cs,
      enabled=True,
      is_metric=False,
      speed_limit_changed=False,
      starpilot_toggles=self.starpilot_toggles,
    )

    assert self.v_cruise_helper.v_cruise_kph == pytest.approx(initial_v_cruise_kph + IMPERIAL_INCREMENT)

  def test_zero_custom_cruise_toggles_fall_back_to_single_step(self):
    self.enable(V_CRUISE_INITIAL * CV.KPH_TO_MS, False)
    initial_v_cruise_kph = self.v_cruise_helper.v_cruise_kph
    self.starpilot_toggles.cruise_increase = 0
    self.starpilot_toggles.cruise_increase_long = 0

    pressed_cs = car.CarState(cruiseState={"available": True})
    pressed_cs.buttonEvents = [ButtonEvent(type=ButtonType.accelCruise, pressed=True)]
    self.v_cruise_helper.update_v_cruise(
      pressed_cs,
      enabled=True,
      is_metric=False,
      speed_limit_changed=False,
      starpilot_toggles=self.starpilot_toggles,
    )

    released_cs = car.CarState(cruiseState={"available": True})
    released_cs.buttonEvents = [ButtonEvent(type=ButtonType.accelCruise, pressed=False)]
    self.v_cruise_helper.update_v_cruise(
      released_cs,
      enabled=True,
      is_metric=False,
      speed_limit_changed=False,
      starpilot_toggles=self.starpilot_toggles,
    )

    assert self.v_cruise_helper.v_cruise_kph == pytest.approx(initial_v_cruise_kph + IMPERIAL_INCREMENT)

  @pytest.mark.parametrize("openpilot_longitudinal", [False, True])
  def test_pcm_cruise_uses_pcm_speed(self, openpilot_longitudinal):
    CP = car.CarParams(pcmCruise=True, openpilotLongitudinalControl=openpilot_longitudinal)
    helper = VCruiseHelper(CP)
    toggles = SimpleNamespace(cruise_increase=5, cruise_increase_long=1, set_speed_limit=False)
    pcm_speed_kph = 72.0
    pcm_cluster_speed_kph = 71.0

    helper.initialize_v_cruise(car.CarState(vEgo=40 * CV.KPH_TO_MS), False, False, toggles)
    assert not helper.v_cruise_initialized

    cs = car.CarState(
      cruiseState={
        "available": True,
        "speed": pcm_speed_kph * CV.KPH_TO_MS,
        "speedCluster": pcm_cluster_speed_kph * CV.KPH_TO_MS,
      },
    )

    helper.update_v_cruise(cs, True, True, False, toggles)
    assert helper.v_cruise_kph == pytest.approx(pcm_speed_kph)
    assert helper.v_cruise_cluster_kph == pytest.approx(pcm_cluster_speed_kph)

    next_pcm_speed_kph = 74.0
    next_cs = car.CarState(
      cruiseState={
        "available": True,
        "speed": next_pcm_speed_kph * CV.KPH_TO_MS,
        "speedCluster": next_pcm_speed_kph * CV.KPH_TO_MS,
      },
      buttonEvents=[{"type": ButtonType.accelCruise, "pressed": False}],
    )
    helper.update_v_cruise(next_cs, True, True, False, toggles)
    assert helper.v_cruise_kph == pytest.approx(next_pcm_speed_kph)


class TestVCruiseHelperRedneck:
  def setup_method(self):
    self.CP = car.CarParams(pcmCruise=True)
    self.FPCP = SimpleNamespace(pcmCruiseSpeed=False, redneckCruiseAvailable=True)
    self.v_cruise_helper = VCruiseHelper(self.CP, self.FPCP)
    self.starpilot_toggles = SimpleNamespace(
      cruise_increase=1,
      cruise_increase_long=5,
      is_metric=False,
      set_speed_limit=False,
    )

  def enable(self, v_ego, experimental_mode):
    self.v_cruise_helper.initialize_v_cruise(
      car.CarState(vEgo=v_ego),
      experimental_mode,
      False,
      self.starpilot_toggles,
    )

  def test_initialize_v_cruise_uses_cluster_speed(self):
    cs = car.CarState(
      vEgo=55 * CV.MPH_TO_MS,
      cruiseState={"speedCluster": 62 * CV.MPH_TO_MS},
    )
    self.v_cruise_helper.initialize_v_cruise(cs, experimental_mode=False, resume_prev_button=False,
                                             starpilot_toggles=self.starpilot_toggles)
    assert self.v_cruise_helper.v_cruise_kph == pytest.approx(62 * CV.MPH_TO_KPH)
    assert self.v_cruise_helper.v_cruise_cluster_kph == pytest.approx(62 * CV.MPH_TO_KPH)

  def test_update_v_cruise_does_not_follow_stock_pcm_speed(self):
    cs = car.CarState(
      vEgo=55 * CV.MPH_TO_MS,
      cruiseState={"speedCluster": 62 * CV.MPH_TO_MS},
    )
    self.v_cruise_helper.initialize_v_cruise(cs, experimental_mode=False, resume_prev_button=False,
                                             starpilot_toggles=self.starpilot_toggles)

    update_cs = car.CarState(
      cruiseState={"available": True, "speed": 50 * CV.MPH_TO_MS, "speedCluster": 50 * CV.MPH_TO_MS},
    )
    self.v_cruise_helper.update_v_cruise(update_cs, enabled=True, is_metric=False,
                                         speed_limit_changed=False, starpilot_toggles=self.starpilot_toggles)

    assert self.v_cruise_helper.v_cruise_kph == pytest.approx(62 * CV.MPH_TO_KPH)
    assert self.v_cruise_helper.v_cruise_cluster_kph == pytest.approx(62 * CV.MPH_TO_KPH)

  def test_resume_keeps_previous_internal_max_speed(self):
    engage_cs = car.CarState(
      vEgo=75 * CV.MPH_TO_MS,
      cruiseState={"speedCluster": 75 * CV.MPH_TO_MS},
    )
    self.v_cruise_helper.initialize_v_cruise(engage_cs, experimental_mode=False, resume_prev_button=False,
                                             starpilot_toggles=self.starpilot_toggles)

    disabled_cs = car.CarState(
      cruiseState={"available": True, "speedCluster": 38 * CV.MPH_TO_MS},
    )
    self.v_cruise_helper.update_v_cruise(disabled_cs, enabled=False, is_metric=False,
                                         speed_limit_changed=False, starpilot_toggles=self.starpilot_toggles)

    resume_cs = car.CarState(
      vEgo=38 * CV.MPH_TO_MS,
      cruiseState={"speedCluster": 38 * CV.MPH_TO_MS},
    )
    self.v_cruise_helper.initialize_v_cruise(resume_cs, experimental_mode=False, resume_prev_button=True,
                                             starpilot_toggles=self.starpilot_toggles)

    assert self.v_cruise_helper.v_cruise_kph == pytest.approx(75 * CV.MPH_TO_KPH)
    assert self.v_cruise_helper.v_cruise_cluster_kph == pytest.approx(75 * CV.MPH_TO_KPH)
