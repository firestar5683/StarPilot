"""Frozen Following + CEM slower-lead scene over explicit qualified owner inputs.

The output is diagnostic evidence only. It does not select a longitudinal mode.
"""

from __future__ import annotations

from dataclasses import dataclass
import math

import numpy as np

from openpilot.common.filter_simple import FirstOrderFilter
from openpilot.common.realtime import DT_MDL
from openpilot.selfdrive.controls.lib.longitudinal_mpc_lib.long_mpc import COMFORT_BRAKE
from openpilot.starpilot.conditional_mode.policy import LeadEvidence


MAX_SOURCE_AGE_S = 0.25
MAX_FRAME_GAP_S = 2 * DT_MDL
FILTER_TIME_S = 0.8
MPH_TO_MPS = 0.44704
MPS_TO_MPH = 1.0 / MPH_TO_MPS


@dataclass(frozen=True)
class SlowerLeadFrame:
  observed_mono_s: float
  now_mono_s: float
  speed_mps: float | None
  selected_follow_s: float | None
  long_active: bool | None
  lead: LeadEvidence | None
  slower_option: bool | None
  stopped_option: bool | None
  previous_experimental: bool | None
  traffic_mode: bool | None
  stop_sign_confirmed: bool | None
  committed_turn_scene: bool | None
  standstill: bool | None
  model_tick_mono_s: float | None = None


@dataclass(frozen=True)
class SlowerLeadObservation:
  following_slow: bool | None
  detected: bool | None
  stopped_candidate: bool | None
  vision_candidate: bool | None


def _finite(value: object, low: float, high: float) -> float | None:
  if isinstance(value, bool) or not isinstance(value, (float, int)):
    return None
  try:
    number = float(value)
  except (OverflowError, ValueError):
    return None
  return number if math.isfinite(number) and low <= number <= high else None


def _bool(value: object) -> bool | None:
  return value if type(value) is bool else None


def _threshold(speed_mps: float) -> float:
  return float(np.interp(speed_mps, [0.0, 17.9, 26.8, 35.8, 44.7], [0.58, 0.60, 0.62, 0.75, 0.90]))


def following_slow_lead(
  *, long_active: bool, tracking: bool, option: bool, speed_mps: float, lead_distance_m: float, lead_speed_mps: float, selected_follow_s: float
) -> bool:
  """Exact frozen StarPilotFollowing.update_follow_values slower_lead branch."""
  if not long_active or not tracking or not option or lead_speed_mps >= speed_mps:
    return False
  distance_factor = max(lead_distance_m - lead_speed_mps * selected_follow_s, 1.0)
  braking_offset = float(np.clip(min(speed_mps - lead_speed_mps, lead_speed_mps) - COMFORT_BRAKE, 1.0, distance_factor))
  return braking_offset > 1.0


class SlowerLeadDetector:
  """One source-bound model-tick CEM slow-lead continuity/filter owner."""

  def __init__(self):
    self.reset()

  def reset(self) -> None:
    self.filter = FirstOrderFilter(0.0, FILTER_TIME_S, DT_MDL)
    self.detected = False
    self.prev_tracking = False
    self.clear_since_s = 0.0
    self.continuity_until_s = 0.0
    self.last_observed_mono_s: float | None = None
    self.last_model_tick_mono_s: float | None = None

  def _clear(self, tracking: bool) -> None:
    self.filter.update(False)
    self.detected = False
    self.clear_since_s = 0.0
    self.continuity_until_s = 0.0
    self.prev_tracking = tracking

  def _retune_next_tick(self, frame: SlowerLeadFrame, speed: float) -> None:
    # Stop detection runs afterward and sets alpha for the next model tick.
    if not frame.traffic_mode and not frame.stop_sign_confirmed and not frame.committed_turn_scene:
      speed_mph = speed * MPS_TO_MPH
      rc = float(np.interp(speed_mph, [0.0, 35.0, 45.0], [0.0, 0.0, 0.8]))
      self.filter.update_alpha(rc)

  def step(self, frame: SlowerLeadFrame) -> SlowerLeadObservation:
    unknown = SlowerLeadObservation(None, None, None, None)
    observed = _finite(frame.observed_mono_s, 0.0, 1e12)
    model_tick = _finite(frame.model_tick_mono_s, 0.0, 1e12) if frame.model_tick_mono_s is not None else observed
    now = _finite(frame.now_mono_s, 0.0, 1e12)
    speed = _finite(frame.speed_mps, 0.0, 80.0)
    headway = _finite(frame.selected_follow_s, 0.0, 5.0)
    lead = frame.lead
    long_active = _bool(frame.long_active)
    slower_option = _bool(frame.slower_option)
    if (
      observed is None
      or model_tick is None
      or now is None
      or not 0.0 <= now - observed <= MAX_SOURCE_AGE_S
      or not observed <= model_tick <= now
      or speed is None
      or headway is None
      or lead is None
      or long_active is None
      or slower_option is None
      or _bool(frame.stopped_option) is None
      or _bool(frame.previous_experimental) is None
      or _bool(frame.traffic_mode) is None
      or _bool(frame.stop_sign_confirmed) is None
      or _bool(frame.committed_turn_scene) is None
      or _bool(frame.standstill) is None
      or _bool(lead.present) is None
      or _bool(lead.tracked) is None
      or _bool(lead.radar) is None
    ):
      self.reset()
      return unknown
    if frame.standstill:
      self.reset()  # Old consensus cannot cross a pause in condition updates.
      return unknown
    if self.last_model_tick_mono_s is not None:
      elapsed = model_tick - self.last_model_tick_mono_s
      if elapsed <= 0.0:
        return unknown
      if elapsed > MAX_FRAME_GAP_S:
        self.reset()
        return unknown
    if not lead.present:
      # A fresh radar event can prove absence without supplying meaningful
      # distance/speed/probability. Release prior consensus on model ticks;
      # stale or missing radar still takes the unknown/reset path above.
      self.last_observed_mono_s = observed
      self.last_model_tick_mono_s = model_tick
      if lead.tracked:
        if self.clear_since_s == 0.0:
          self.clear_since_s = now
        if now - self.clear_since_s >= 0.75:
          self._clear(True)
        else:
          self.filter.update(False)
          self.detected = bool(self.filter.x >= _threshold(speed))
      else:
        self._clear(False)
      self.prev_tracking = lead.tracked
      self._retune_next_tick(frame, speed)
      return SlowerLeadObservation(False, self.detected, False, False)
    distance = _finite(lead.distance_m, 0.0, 500.0)
    lead_speed = _finite(lead.speed_mps, -30.0, 100.0)
    probability = _finite(lead.model_probability, 0.0, 1.0)
    if None in (distance, lead_speed, probability):
      self.reset()
      return unknown
    assert distance is not None and lead_speed is not None and probability is not None
    self.last_observed_mono_s = observed
    self.last_model_tick_mono_s = model_tick
    tracking = lead.tracked
    following_slow = following_slow_lead(
      long_active=long_active,
      tracking=tracking,
      option=slower_option,
      speed_mps=speed,
      lead_distance_m=distance,
      lead_speed_mps=lead_speed,
      selected_follow_s=headway,
    )
    closing = max(0.0, speed - lead_speed)
    minimum_closing = max(0.75, 0.04 * speed)
    if not frame.stopped_option and speed < 2.5:
      self._clear(tracking)
      self._retune_next_tick(frame, speed)
      return SlowerLeadObservation(following_slow, False, False, False)
    radar_range = not lead.radar or distance < max(40.0, speed * 2.5)
    slower = frame.slower_option and following_slow and radar_range
    stopped = frame.stopped_option and lead.present and lead_speed < 1.0 and distance < max(40.0, speed * 4.0)
    vision = (
      lead.present
      and not lead.radar
      and probability >= 0.85
      and distance < max(40.0, speed * 4.0)
      and closing >= minimum_closing
      and lead_speed < max(speed - 0.5, 2.0)
    )
    adjusted_threshold = _threshold(speed) * (1.0 + 0.2 * (1.0 - probability))
    if lead.present and not slower and not stopped and closing < minimum_closing * 0.5:
      self._clear(tracking)
      self._retune_next_tick(frame, speed)
      return SlowerLeadObservation(following_slow, False, bool(stopped), bool(vision))
    if tracking and (slower or stopped or vision):
      self.continuity_until_s = now + 1.25
    elif self.prev_tracking and not tracking and self.detected and vision:
      self.continuity_until_s = now + 1.25
    raw_vision = frame.slower_option and not tracking and now < self.continuity_until_s and vision
    tracked_vision = frame.slower_option and tracking and frame.previous_experimental and vision
    active = slower or raw_vision or stopped or tracked_vision
    if active:
      self.clear_since_s = 0.0
      self.filter.update(True)
      self.detected = bool(self.filter.x >= adjusted_threshold)
    elif tracking:
      if self.clear_since_s == 0.0:
        self.clear_since_s = now
      if now - self.clear_since_s >= 0.75:
        self._clear(tracking)
      else:
        self.filter.update(False)
        self.detected = bool(self.filter.x >= adjusted_threshold)
    else:
      self._clear(tracking)
    self.prev_tracking = tracking
    self._retune_next_tick(frame, speed)
    return SlowerLeadObservation(following_slow, self.detected, bool(stopped), bool(vision))
