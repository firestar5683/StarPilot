"""Saved lane-centering preferences and fresh host authority, opt-in at startup."""

import math
import os
from pathlib import Path

from openpilot.cereal.services import SERVICE_LIST
from openpilot.common.realtime import DT_CTRL
from openpilot.common.params import UnknownKeyName
from openpilot.starpilot.lateral.lane_centering import ControlMode, LaneCenteringRequest, LaneCenteringSettings, STRENGTH_BASELINE, STRENGTH_MAX
from openpilot.starpilot.longitudinal.ioniq6_start import eligible as ioniq6_long_eligible


def read_settings(params) -> LaneCenteringSettings:
  def raw(key, default):
    try:
      return Path(params.get_param_path(key)).read_bytes()
    except FileNotFoundError:
      return default

  def boolean(key, default):
    value = raw(key, default)
    if value not in (b'0', b'1'):
      raise ValueError('Invalid lane preference')
    return value == b'1'

  try:
    enabled = boolean('LaneCentering', b'0')
    pause = boolean('LaneCenteringPauseOnSignal', b'1')
    offset = float(raw('LaneCenterOffset', b'0.0'))
    authority = float(raw('LaneCenteringE2EAuthority', b'1.0'))
    try:
      strength = float(raw('LaneCenteringStrength', str(STRENGTH_BASELINE).encode()))
    except UnknownKeyName:
      strength = STRENGTH_BASELINE
    if not math.isfinite(strength) or not 0.5 <= strength <= STRENGTH_MAX:
      raise ValueError('Invalid lane strength')
    if not math.isfinite(offset) or not -0.3 <= offset <= 0.3 or not math.isfinite(authority) or not 0 <= authority <= 1:
      raise ValueError('Invalid lane tuning')
    return LaneCenteringSettings(enabled, offset, authority, pause, strength)
  except (OSError, ValueError):
    return LaneCenteringSettings()


def runtime_supported(CP) -> bool:
  """Keep the preference reader available when a supported drive starts Off."""
  from openpilot.starpilot.lateral.bolt_policy import supported_cp as bolt_supported_cp
  from opendbc.car.gm.lateral import lane_centering_supported as gm_supported_cp
  return (os.getenv('LANE_CENTERING_REPLAY_RUNTIME') == '1' or
          ioniq6_long_eligible(CP) or (CP is not None and bolt_supported_cp(CP)) or gm_supported_cp(CP))


class LaneCenteringHost:
  REFRESH_NS = 1_000_000_000
  MAX_TICK_NS = 50_000_000
  REQUIRED = ('carState', 'selfdriveState', 'modelV2', 'vehicleParameters')

  def __init__(self, params):
    self.params = params
    self.settings = LaneCenteringSettings()
    self.last_refresh_ns: int | None = None
    self.last_tick_ns: int | None = None

  def sample(self, sm, *, now_ns: int, lateral_active: bool, longitudinal_active: bool) -> LaneCenteringRequest | None:
    previous = self.last_tick_ns
    self.last_tick_ns = now_ns
    discontinuity = previous is not None and not 0 < now_ns - previous <= self.MAX_TICK_NS
    if now_ns <= 0:
      self.settings = LaneCenteringSettings()
      self.last_refresh_ns = None
      return None
    if self.last_refresh_ns is None or now_ns < self.last_refresh_ns or now_ns - self.last_refresh_ns >= self.REFRESH_NS:
      self.settings = read_settings(self.params)
      self.last_refresh_ns = now_ns
    if not self.settings.enabled or not sm['carState'].canValid or sm['carState'].canTimeout:
      return None
    if not sm.all_checks(list(self.REQUIRED)) or any(
      int(sm.logMonoTime[name]) <= 0 or not 0 <= now_ns - int(sm.logMonoTime[name]) <= int(2.5e9 / SERVICE_LIST[name].frequency)
      for name in self.REQUIRED
    ):
      return None
    mode = (ControlMode.COMBINED if longitudinal_active else ControlMode.LATERAL_ONLY) if lateral_active else (
      ControlMode.LONGITUDINAL_ONLY if longitudinal_active else ControlMode.OFF)
    dt = DT_CTRL if previous is None or discontinuity else (now_ns - previous) / 1e9
    return LaneCenteringRequest(mode, self.settings, dt, discontinuity)
