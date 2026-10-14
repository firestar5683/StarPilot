"""Actual lane consumers and GM emitted demands; root runs under native custody."""
from dataclasses import replace
import inspect
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from opendbc.car.structs import car
from openpilot.cereal import log
from openpilot.starpilot.lateral.lane_change_preferences import KEY, LaneChangePolicy, LiveLaneChangePolicy, to_value
from openpilot.starpilot.lateral.lane_change_smoothing import LaneChangeSmoother, limit_rate
from openpilot.selfdrive.controls.lib.desire_helper import DesireHelper
from openpilot.selfdrive.controls.lib.drive_helpers import clip_curvature


class PathParams:
  def __init__(self, directory):
    self.directory = Path(directory)

  def get_param_path(self, key):
    return str(self.directory / key)

  def put(self, key, raw):
    (self.directory / key).write_bytes(raw)


def save(params, policy):
  params.put(KEY, json.dumps(to_value(policy)).encode())


def test_actual_modeld_and_controls_consume_same_live_document(tmp_path):
  from openpilot.selfdrive.modeld.modeld import refresh_lane_change_policy, main
  from openpilot.selfdrive.controls.controlsd import Controls
  params = PathParams(tmp_path)
  initial = LaneChangePolicy(duration_s=6.)
  save(params, initial)
  dh = DesireHelper()
  model_cache = LiveLaneChangePolicy(params, now_ns=1_000_000_000)
  controls = SimpleNamespace(lane_change_preferences=LiveLaneChangePolicy(params, now_ns=1_000_000_000))
  cs = car.CarState.new_message(vEgo=20., leftBlinker=True)
  model = SimpleNamespace(meta=SimpleNamespace(laneChangeState=log.LaneChangeState.off))

  def step(now, *, nudge=False, evidence=False):
    cs.steeringPressed, cs.steeringTorque = nudge, 1. if nudge else 0.
    refresh_lane_change_policy(model_cache, dh, cs, now, True)
    dh.update(cs, True, 1., auto_evidence=evidence, engaged=True)
    model.meta.laneChangeState = dh.lane_change_state
    return Controls.refresh_lane_change_policy(controls, cs, model, now)

  step(1_010_000_000)
  assert dh.lane_change_state == log.LaneChangeState.preLaneChange
  cs.leftBlindspot = True
  step(1_020_000_000, nudge=True)
  assert dh.lane_change_state == log.LaneChangeState.preLaneChange
  cs.leftBlindspot = False
  original = step(1_030_000_000, nudge=True)
  assert dh.lane_change_state == log.LaneChangeState.laneChangeStarting
  changed = replace(initial, duration_s=8., minimum_speed_mps=25., auto_lane_change=True, auto_delay_s=0.)
  save(params, changed)
  assert step(2_040_000_000, evidence=True) == original
  assert dh.policy == original  # No pace/minimum/auto change in a committed maneuver.
  smoother = LaneChangeSmoother()
  factor = smoother.factor(active=True, lane_change_state=dh.lane_change_state, speed=cs.vEgo,
                           minimum_speed=original.minimum_speed_mps, duration=original.duration_s,
                           previous=0., desired=.01)
  shaped = limit_rate(cs.vEgo, 0., .01, factor)
  output, _ = clip_curvature(cs.vEgo, 0., shaped, 0.)
  assert 0 < output <= 5. / cs.vEgo ** 2 * .01

  save(params, replace(changed, enabled=False))
  assert not step(3_050_000_000).enabled
  assert dh.lane_change_state == log.LaneChangeState.off
  save(params, changed)
  assert not step(4_060_000_000, evidence=True).enabled  # Held signal cannot reauthorize.
  cs.leftBlinker = False
  adopted = step(4_070_000_000)
  assert adopted.duration_s == 8. and dh.policy.minimum_speed_mps == 25.
  cs.vEgo = 30.
  cs.leftBlinker = True
  step(4_080_000_000, evidence=True)
  step(4_090_000_000, evidence=True)
  assert dh.lane_change_state == log.LaneChangeState.laneChangeStarting
  # The actual driving loops call these helpers before DesireHelper/smoother consumption.
  assert 'refresh_lane_change_policy(lane_preferences, DH, car_state' in inspect.getsource(main)
  state_control = inspect.getsource(Controls.state_control)
  assert state_control.index('self.refresh_lane_change_policy(') < state_control.index('self.lane_change_smoother.factor(')


def test_invalid_document_clock_rollback_and_bounded_reads(tmp_path):
  from openpilot.starpilot.lateral import lane_change_preferences as preferences
  params = PathParams(tmp_path)
  save(params, LaneChangePolicy(auto_lane_change=True))
  with patch.object(preferences, 'read_saved', wraps=preferences.read_saved) as read:
    cache = LiveLaneChangePolicy(params, now_ns=1_000_000_000)
    for tick in range(99):
      assert cache.sample(1_000_000_000 + tick * 10_000_000).enabled
    assert read.call_count == 1
    params.put(KEY, b'{"enabled": true}')
    assert not cache.sample(2_000_000_000).enabled
    assert not cache.sample(1_999_000_000).enabled
    assert not cache.sample(0).enabled
    save(params, LaneChangePolicy())
    assert not cache.sample(3_000_000_000, signaling=True).enabled
    assert cache.sample(3_010_000_000).enabled


def test_grade_worker_live_preference_reaches_actual_gm_can(tmp_path):
  from opendbc.car.gm.carcontroller import CarController
  from opendbc.car.gm.tests.test_ascm_intercept import params as vehicle_params
  from opendbc.car.gm.tests import test_volt_grade as fixture
  from opendbc.car.gm.values import CAR
  from openpilot.starpilot.car.gm.tune_preferences import GradeCompensationPreference
  params = PathParams(tmp_path)
  params.put('OpenpilotEnabledToggle', b'1')
  preference = GradeCompensationPreference(params)
  cp = vehicle_params(CAR.CHEVROLET_BOLT_EUV, alpha=True, radar=False, sascm=False)
  assert cp.openpilotLongitudinalControl
  safety = (int(cp.flags), int(cp.alternativeExperience), tuple((s.safetyModel.raw, s.safetyParam) for s in cp.safetyConfigs))

  def emit(enabled):
    def create(*args):
      controller = CarController(*args)
      controller.long_pitch = enabled
      return controller
    with patch.object(fixture, 'CarController', side_effect=create):
      actual, messages = fixture.command(cp, accel=-.5, speed=12., orientation=[0., -.03, 0.], frame=4)
    return (actual.apply_gas, actual.apply_brake), [m for m in messages if m[0] in (0x2cb, 0x315)]

  on = emit(preference.update(1_000_000_000))
  params.put('LongPitch', b'0')
  assert preference.update(1_500_000_000)  # No reads between worker refreshes.
  off = emit(preference.update(2_000_000_000))
  assert on[1] and off[1]  # Prove both branches emitted actual gas/brake CAN.
  assert on != off
  params.put('LongPitch', b'1')
  assert emit(preference.update(3_000_000_000)) == on
  params.put('LongPitch', b'invalid')
  assert emit(preference.update(4_000_000_000)) == on
  assert safety == (int(cp.flags), int(cp.alternativeExperience), tuple((s.safetyModel.raw, s.safetyParam) for s in cp.safetyConfigs))
  from openpilot.selfdrive.car.card import Car
  assert 'pitch_input.update(time.monotonic_ns())' in inspect.getsource(Car.params_thread)
  update = inspect.getsource(CarController.update)
  assert 'long_pitch = self.long_pitch' in update
  assert 'get_param_path' not in update and 'GradeCompensationPreference' not in update


def test_actual_card_worker_publishes_grade_without_controller_params_reads(tmp_path):
  import threading
  from opendbc.car.gm.carcontroller import CarController
  from opendbc.car.gm.tests.test_ascm_intercept import params as vehicle_params
  from opendbc.car.gm.values import CAR, DBC
  from openpilot.selfdrive.car import card
  from openpilot.starpilot.car.gm.tune_preferences import GradeCompensationPreference
  saved = PathParams(tmp_path)
  saved.put('OpenpilotEnabledToggle', b'1')
  saved.put('LongPitch', b'0')
  cp = vehicle_params(CAR.CHEVROLET_BOLT_EUV)
  cc = CarController(DBC[cp.carFingerprint], cp)
  cc.long_pitch_input = GradeCompensationPreference(saved)
  worker = card.Car.__new__(card.Car)
  worker.CP, worker.CI = cp, SimpleNamespace(CC=cc)
  worker.params = SimpleNamespace(get_bool=lambda key: False)
  worker.aol_card_intent = None
  worker.v_cruise_helper = SimpleNamespace(intervals=None)
  event = threading.Event()

  def publish(now_ns):
    event.clear()
    with patch.object(card.Car, 'read_slc_configuration', return_value=None), \
         patch.object(card, 'read_cruise_intervals', return_value='unchanged-cruise-intervals'), \
         patch.object(card.time, 'monotonic', return_value=now_ns / 1e9), \
         patch.object(card.time, 'monotonic_ns', return_value=now_ns), \
         patch.object(card.time, 'sleep', side_effect=lambda seconds: event.set()):
      card.Car.params_thread(worker, event)
    assert worker.v_cruise_helper.intervals == 'unchanged-cruise-intervals'

  publish(1_000_000_000)
  assert not cc.long_pitch
  saved.put('LongPitch', b'1')
  publish(2_000_000_000)
  assert cc.long_pitch
