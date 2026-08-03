from types import SimpleNamespace

from cereal import log

from openpilot.selfdrive.controls.lib.desire_helper import DesireHelper, LaneChangeDirection, LaneChangeState


def make_car_state(**overrides):
  defaults = {
    "vEgo": 20.0,
    "leftBlinker": False,
    "rightBlinker": False,
    "leftBlindspot": False,
    "rightBlindspot": False,
    "steeringPressed": False,
    "steeringTorque": 0.0,
    "standstill": False,
    "cruiseState": SimpleNamespace(enabled=True),
  }
  defaults.update(overrides)
  return SimpleNamespace(**defaults)


def make_toggles(**overrides):
  defaults = {
    "lane_changes": True,
    "lane_change_delay": 0.0,
    "lane_detection_width": 3.0,
    "minimum_lane_change_speed": 10.0,
    "nudgeless": True,
    "nudgeless_lane_change_only_when_engaged": False,
    "one_lane_change": False,
    "use_turn_desires": False,
    "lane_changes_require_cruise": False,
    "nav_desires_allowed": True,
  }
  defaults.update(overrides)
  return SimpleNamespace(**defaults)


def make_plan(**overrides):
  defaults = {
    "laneWidthLeft": 4.0,
    "laneWidthRight": 4.0,
  }
  defaults.update(overrides)
  return SimpleNamespace(**defaults)

def test_nav_desires_keep_left_when_route_requests_it():
  helper = DesireHelper()
  helper.nav_desires_allowed = True
  helper._update_nav_params = lambda: None
  helper._nav_instruction_state = {"valid": True, "maneuverModifier": "slightLeft"}

  helper.update(
    make_car_state(vEgo=20.0),
    True,
    0.0,
    make_plan(laneWidthLeft=4.2),
    make_toggles(nudgeless=True),
  )

  assert helper.desire == log.Desire.keepLeft


def test_nav_desires_turn_right_below_lane_change_speed():
  helper = DesireHelper()
  helper.nav_desires_allowed = True
  helper._update_nav_params = lambda: None
  helper._nav_instruction_state = {"valid": True, "maneuverModifier": "right", "maneuverDistance": 10.0}

  helper.update(
    make_car_state(vEgo=5.0),
    True,
    0.0,
    make_plan(),
    make_toggles(minimum_lane_change_speed=10.0),
  )

  assert helper.desire == log.Desire.turnRight


def test_nav_desires_turn_right_waits_until_turn_is_close():
  helper = DesireHelper()
  helper.nav_desires_allowed = True
  helper._update_nav_params = lambda: None
  helper._nav_instruction_state = {"valid": True, "maneuverModifier": "right", "maneuverDistance": 300.0}

  helper.update(
    make_car_state(vEgo=5.0),
    True,
    0.0,
    make_plan(),
    make_toggles(minimum_lane_change_speed=10.0),
  )

  assert helper.desire == log.Desire.none


def test_nav_desires_off_ramp_lane_guidance_becomes_keep_right():
  helper = DesireHelper()
  helper.nav_desires_allowed = True
  helper._update_nav_params = lambda: None
  helper._nav_instruction_state = {
    "valid": True,
    "maneuverType": "off ramp",
    "maneuverModifier": "right",
    "activeLaneDirection": "slightRight",
    "maneuverDistance": 120.0,
  }

  helper.update(
    make_car_state(vEgo=22.5),
    True,
    0.0,
    make_plan(laneWidthRight=4.2),
    make_toggles(nudgeless=True),
  )

  assert helper.desire == log.Desire.keepRight


def test_nav_desires_off_ramp_lane_guidance_waits_until_split_is_close():
  helper = DesireHelper()
  helper.nav_desires_allowed = True
  helper._update_nav_params = lambda: None
  helper._nav_instruction_state = {
    "valid": True,
    "maneuverType": "off ramp",
    "maneuverModifier": "right",
    "activeLaneDirection": "slightRight",
    "maneuverDistance": 300.0,
  }

  helper.update(
    make_car_state(vEgo=22.5),
    True,
    0.0,
    make_plan(laneWidthRight=4.2),
    make_toggles(nudgeless=True),
  )

  assert helper.desire == log.Desire.none


def test_nav_desires_ambiguous_off_ramp_waits_longer_before_keep_right():
  helper = DesireHelper()
  helper.nav_desires_allowed = True
  helper._update_nav_params = lambda: None
  helper._nav_instruction_state = {
    "valid": True,
    "maneuverType": "off ramp",
    "maneuverModifier": "right",
    "activeLaneDirection": "slightRight",
    "sameSideLaneCount": 3,
    "maneuverDistance": 120.0,
  }

  helper.update(
    make_car_state(vEgo=22.5),
    True,
    0.0,
    make_plan(laneWidthRight=4.2),
    make_toggles(nudgeless=True),
  )

  assert helper.desire == log.Desire.none


def test_nav_desires_edge_exit_lane_with_shared_transition_lane_does_not_keep_right():
  helper = DesireHelper()
  helper.nav_desires_allowed = True
  helper._update_nav_params = lambda: None
  helper._nav_instruction_state = {
    "valid": True,
    "maneuverType": "off ramp",
    "maneuverModifier": "right",
    "activeLaneDirection": "slightRight",
    "laneCount": 3,
    "sameSideLaneCount": 2,
    "activeLaneAtRoadEdge": True,
    "hasSharedSameSideLane": True,
    "maneuverDistance": 10.0,
  }

  helper.update(
    make_car_state(vEgo=22.5),
    True,
    0.0,
    make_plan(laneWidthRight=4.2),
    make_toggles(nudgeless=True),
  )

  assert helper.desire == log.Desire.none


def test_nav_desires_wide_highway_edge_exit_lane_keeps_right():
  helper = DesireHelper()
  helper.nav_desires_allowed = True
  helper._update_nav_params = lambda: None
  helper._nav_instruction_state = {
    "valid": True,
    "maneuverType": "off ramp",
    "maneuverModifier": "right",
    "activeLaneDirection": "slightRight",
    "laneCount": 7,
    "sameSideLaneCount": 2,
    "activeLaneAtRoadEdge": True,
    "hasSharedSameSideLane": True,
    "maneuverDistance": 105.0,
  }

  helper.update(
    make_car_state(vEgo=19.0),
    True,
    0.0,
    make_plan(laneWidthRight=4.2),
    make_toggles(nudgeless=True),
  )

  assert helper.desire == log.Desire.keepRight


def test_nav_desires_shared_transition_lane_keeps_when_active_lane_is_not_outermost():
  helper = DesireHelper()
  helper.nav_desires_allowed = True
  helper._update_nav_params = lambda: None
  helper._nav_instruction_state = {
    "valid": True,
    "maneuverType": "off ramp",
    "maneuverModifier": "right",
    "activeLaneDirection": "slightRight",
    "sameSideLaneCount": 2,
    "activeLaneAtRoadEdge": False,
    "hasSharedSameSideLane": True,
    "maneuverDistance": 10.0,
  }

  helper.update(
    make_car_state(vEgo=22.5),
    True,
    0.0,
    make_plan(laneWidthRight=4.2),
    make_toggles(nudgeless=True),
  )

  assert helper.desire == log.Desire.keepRight


def test_nav_desires_ambiguous_fork_slight_right_only_keeps_close_to_split():
  helper = DesireHelper()
  helper.nav_desires_allowed = True
  helper._update_nav_params = lambda: None
  helper._nav_instruction_state = {
    "valid": True,
    "maneuverType": "fork",
    "maneuverModifier": "slightRight",
    "activeLaneDirection": "slightRight",
    "sameSideLaneCount": 3,
    "maneuverDistance": 60.0,
  }

  helper.update(
    make_car_state(vEgo=22.5),
    True,
    0.0,
    make_plan(laneWidthRight=4.2),
    make_toggles(nudgeless=True),
  )

  assert helper.desire == log.Desire.keepRight


def test_nav_desires_ambiguous_fork_slight_right_does_not_nudge_too_early():
  helper = DesireHelper()
  helper.nav_desires_allowed = True
  helper._update_nav_params = lambda: None
  helper._nav_instruction_state = {
    "valid": True,
    "maneuverType": "fork",
    "maneuverModifier": "slightRight",
    "activeLaneDirection": "slightRight",
    "sameSideLaneCount": 3,
    "maneuverDistance": 120.0,
  }

  helper.update(
    make_car_state(vEgo=22.5),
    True,
    0.0,
    make_plan(laneWidthRight=4.2),
    make_toggles(nudgeless=True),
  )

  assert helper.desire == log.Desire.none


def test_nav_desires_fork_with_active_straight_lane_does_not_turn_left():
  helper = DesireHelper()
  helper.nav_desires_allowed = True
  helper._update_nav_params = lambda: None
  helper._nav_instruction_state = {
    "valid": True,
    "maneuverType": "fork",
    "maneuverModifier": "left",
    "activeLaneDirection": "straight",
    "maneuverDistance": 15.0,
  }

  helper.update(
    make_car_state(vEgo=5.0),
    True,
    0.0,
    make_plan(laneWidthLeft=4.2),
    make_toggles(nudgeless=True, minimum_lane_change_speed=10.0),
  )

  assert helper.desire == log.Desire.none


def test_nav_desires_do_not_override_lane_change_state_machine():
  helper = DesireHelper()
  helper.nav_desires_allowed = True
  helper._update_nav_params = lambda: None
  helper._nav_instruction_state = {"valid": True, "maneuverModifier": "slightRight"}
  helper.lane_change_state = LaneChangeState.laneChangeStarting
  helper.lane_change_direction = LaneChangeDirection.left
  helper.lane_change_ll_prob = 0.5

  helper.update(
    make_car_state(vEgo=25.0, leftBlinker=True),
    True,
    0.5,
    make_plan(),
    make_toggles(),
  )

  assert helper.desire == log.Desire.laneChangeLeft


def test_lane_changes_require_cruise_blocks_blinker_lane_change_without_cruise():
  helper = DesireHelper()

  helper.update(
    make_car_state(leftBlinker=True, cruiseState=SimpleNamespace(enabled=False)),
    True,
    0.0,
    make_plan(),
    make_toggles(lane_changes_require_cruise=True),
  )

  assert helper.lane_change_state == LaneChangeState.off
  assert helper.lane_change_direction == LaneChangeDirection.none
  assert helper.desire == log.Desire.none


def test_lane_changes_require_cruise_allows_blinker_lane_change_with_cruise():
  helper = DesireHelper()

  helper.update(
    make_car_state(leftBlinker=True, cruiseState=SimpleNamespace(enabled=True)),
    True,
    0.0,
    make_plan(),
    make_toggles(lane_changes_require_cruise=True),
  )

  assert helper.lane_change_state == LaneChangeState.preLaneChange
  assert helper.lane_change_direction == LaneChangeDirection.left


def test_lane_changes_without_cruise_requirement_keep_existing_behavior():
  helper = DesireHelper()

  helper.update(
    make_car_state(leftBlinker=True, cruiseState=SimpleNamespace(enabled=False)),
    True,
    0.0,
    make_plan(),
    make_toggles(lane_changes_require_cruise=False),
  )

  assert helper.lane_change_state == LaneChangeState.preLaneChange
  assert helper.lane_change_direction == LaneChangeDirection.left


def test_nudgeless_only_when_engaged_allows_automatic_lane_change_when_engaged():
  helper = DesireHelper()

  for _ in range(2):
    helper.update(
      make_car_state(leftBlinker=True),
      True,
      0.0,
      make_plan(),
      make_toggles(nudgeless_lane_change_only_when_engaged=True),
      controls_enabled=True,
    )

  assert helper.lane_change_state == LaneChangeState.laneChangeStarting
  assert helper.lane_change_direction == LaneChangeDirection.left


def test_nudgeless_only_when_engaged_requires_nudge_when_aol_only():
  helper = DesireHelper()
  toggles = make_toggles(nudgeless_lane_change_only_when_engaged=True)

  for _ in range(2):
    helper.update(
      make_car_state(leftBlinker=True),
      True,
      0.0,
      make_plan(),
      toggles,
      controls_enabled=False,
    )

  assert helper.lane_change_state == LaneChangeState.preLaneChange
  assert helper.lane_change_direction == LaneChangeDirection.left

  helper.update(
    make_car_state(leftBlinker=True, steeringPressed=True, steeringTorque=1.0),
    True,
    0.0,
    make_plan(),
    toggles,
    controls_enabled=False,
  )

  assert helper.lane_change_state == LaneChangeState.laneChangeStarting
  assert helper.lane_change_direction == LaneChangeDirection.left


def test_nav_desires_nudgeless_only_when_engaged_blocks_keep_when_aol_only():
  helper = DesireHelper()
  helper.nav_desires_allowed = True
  helper._update_nav_params = lambda: None
  helper._nav_instruction_state = {"valid": True, "maneuverModifier": "slightLeft"}

  helper.update(
    make_car_state(vEgo=20.0),
    True,
    0.0,
    make_plan(laneWidthLeft=4.2),
    make_toggles(nudgeless=True, nudgeless_lane_change_only_when_engaged=True),
    controls_enabled=False,
  )

  assert helper.desire == log.Desire.none


def test_turn_desire_fires_below_lane_change_speed_when_no_stop():
  helper = DesireHelper()

  helper.update(
    make_car_state(vEgo=5.0, rightBlinker=True),
    True,
    0.0,
    make_plan(),
    make_toggles(use_turn_desires=True, minimum_lane_change_speed=10.0),
  )

  assert helper.desire == log.Desire.turnRight


def test_turn_desire_held_while_stopping_for_red_light():
  helper = DesireHelper()

  helper.update(
    make_car_state(vEgo=5.0, rightBlinker=True),
    True,
    0.0,
    make_plan(redLight=True),
    make_toggles(use_turn_desires=True, minimum_lane_change_speed=10.0),
  )

  assert helper.turn_stop_hold
  assert helper.desire == log.Desire.none


def test_turn_desire_released_after_stop_completes():
  helper = DesireHelper()
  toggles = make_toggles(use_turn_desires=True, minimum_lane_change_speed=10.0)

  helper.update(make_car_state(vEgo=5.0, rightBlinker=True), True, 0.0, make_plan(redLight=True), toggles)
  assert helper.desire == log.Desire.none

  helper.update(make_car_state(vEgo=0.0, rightBlinker=True, standstill=True), True, 0.0, make_plan(redLight=True), toggles)
  assert not helper.turn_stop_hold

  helper.update(make_car_state(vEgo=2.0, rightBlinker=True), True, 0.0, make_plan(), toggles)
  assert helper.desire == log.Desire.turnRight


def test_nav_desires_disabled_leave_desire_unchanged():
  helper = DesireHelper()
  helper._update_nav_params = lambda: None
  helper._nav_instruction_state = {"valid": True, "maneuverModifier": "left"}

  helper.update(
    make_car_state(vEgo=5.0),
    True,
    0.0,
    make_plan(),
    make_toggles(minimum_lane_change_speed=10.0, nav_desires_allowed=False),
  )

  assert helper.desire == log.Desire.none


def test_disabling_nav_desires_clears_active_route_desire_immediately():
  helper = DesireHelper()
  helper._update_nav_params = lambda: None
  helper._nav_instruction_state = {"valid": True, "maneuverModifier": "slightRight"}
  car_state = make_car_state(vEgo=20.0)
  plan = make_plan(laneWidthRight=4.2)

  helper.update(car_state, True, 0.0, plan, make_toggles(nav_desires_allowed=True))
  assert helper.desire == log.Desire.keepRight

  helper.update(car_state, True, 0.0, plan, make_toggles(nav_desires_allowed=False))
  assert helper.desire == log.Desire.none
