"""Exact-platform torque source selection for native controlsd."""

from __future__ import annotations

from dataclasses import dataclass
import math
import os
from pathlib import Path

from opendbc.car import structs
from openpilot.cereal.services import SERVICE_LIST
from openpilot.starpilot.lateral.torque_tuning import TorqueSource, TorqueTuning
from openpilot.starpilot.lateral.torque_supported import BOLT_VEHICLES, IONIQ6_VEHICLES, TOYOTA_VEHICLES
from openpilot.starpilot.lateral.torque_settings import (
  DOCUMENT_KEY, LEGACY_KEYS, MAX_DOCUMENT_BYTES, interpret_legacy, parse_document, resolve_document,
)
LEARNER_VERSION = 1
REFRESH_NS = 1_000_000_000


def _move(old: float, new: float, step: float) -> float:
  return min(max(new, old - step), old + step)


def supported_cp(CP) -> bool:
  fingerprint = str(CP.carFingerprint)
  if fingerprint in BOLT_VEHICLES:
    from openpilot.starpilot.lateral.bolt_policy import supported_cp as bolt_supported_cp
    return bolt_supported_cp(CP)
  platform = ((fingerprint in TOYOTA_VEHICLES and str(CP.brand) == 'toyota') or
              (fingerprint in IONIQ6_VEHICLES and str(CP.brand) == 'hyundai'))
  return (platform and
          CP.steerControlType == structs.CarParams.SteerControlType.torque and not CP.dashcamOnly and
          CP.lateralTuning.which() == 'torque' and
          math.isfinite(float(CP.lateralTuning.torque.latAccelFactor)) and
          float(CP.lateralTuning.torque.latAccelFactor) > 0 and
          math.isfinite(float(CP.lateralTuning.torque.latAccelOffset)) and
          math.isfinite(float(CP.lateralTuning.torque.friction)) and
          float(CP.lateralTuning.torque.friction) >= 0)


def production_supported_cp(CP) -> bool:
  """Exact production consumer scope shared by the host and settings editor."""
  return (supported_cp(CP) and str(CP.carFingerprint) in IONIQ6_VEHICLES | BOLT_VEHICLES and
          not CP.passive and not CP.notCar)


def manual_overrides_present(CP, params) -> bool:
  """Numeric intent alone admits the custom host and invalidates stale learning."""
  if params is None:
    return False
  if str(CP.carFingerprint) in BOLT_VEHICLES:
    if not runtime_enabled(CP, params):
      return False
  elif not (production_supported_cp(CP) or os.getenv('TORQUE_REPLAY_RUNTIME') == '1' and supported_cp(CP)):
    return False
  settings = read_settings(params, TorqueHost(params, CP).vehicle)
  return settings.valid and (settings.user_factor is not None or settings.user_friction is not None)


def runtime_enabled(CP, params=None) -> bool:
  if not supported_cp(CP):
    return False
  if str(CP.carFingerprint) in BOLT_VEHICLES:
    if params is None:
      return False
    settings = read_settings(params, TorqueHost(params, CP).vehicle)
    return settings.valid and settings.user_friction is not None
  if os.getenv('TORQUE_REPLAY_RUNTIME') == '1':
    return True
  # Preserve native/default startup behavior. A first custom edit is saved for
  # the next drive; a custom host already admitted can refresh/reset live.
  return manual_overrides_present(CP, params)


development_enabled = runtime_enabled


@dataclass(frozen=True)
class TorqueSettings:
  force_auto_off: bool = False
  user_factor: float | None = None
  user_friction: float | None = None
  valid: bool = True


def _raw(params, key: str) -> bytes | None:
  try:
    with Path(params.get_param_path(key)).open('rb') as source:
      return source.read(MAX_DOCUMENT_BYTES + 1) if key == DOCUMENT_KEY else source.read()
  except FileNotFoundError:
    return None


def _bool(raw: bytes | None, default: bool) -> bool:
  if raw is None:
    return default
  if raw not in (b'0', b'1'):
    raise ValueError('Malformed torque setting')
  return raw == b'1'


def read_settings(params, vehicle: TorqueTuning, *, allow_learning: bool | None = None) -> TorqueSettings:
  try:
    force_off = _bool(_raw(params, 'ForceAutoTuneOff'), False) if allow_learning is None else not allow_learning
    basis = (vehicle.lat_accel_factor, vehicle.lat_accel_offset, vehicle.friction)
    document = _raw(params, DOCUMENT_KEY)
    if vehicle.vehicle in BOLT_VEHICLES and document is None:
      return TorqueSettings(valid=False)
    if document is None:
      legacy = interpret_legacy({key: _raw(params, key) for key in LEGACY_KEYS}, basis)
      factor, friction = legacy.factor, legacy.friction
    else:
      factor, friction, review = resolve_document(parse_document(document), vehicle.vehicle, basis)
      if review:
        return TorqueSettings(valid=False)
    return TorqueSettings(force_off, factor, friction)
  except (OSError, ValueError, OverflowError):
    return TorqueSettings(valid=False)


class TorqueHost:
  """Choose one complete source and rate-bound changes to the native controller."""
  def __init__(self, params, CP, *, allow_learning: bool | None = None):
    if not supported_cp(CP):
      raise ValueError('Unsupported torque host')
    tune = CP.lateralTuning.torque
    self.vehicle = TorqueTuning(TorqueSource.VEHICLE, str(CP.carFingerprint),
                                float(tune.latAccelFactor), float(tune.latAccelOffset), float(tune.friction))
    self.params = params
    # An exact controller supplies its startup decision. None preserves the
    # existing live manual preference for other optional replay-host vehicles.
    self.allow_learning = allow_learning
    self.settings = TorqueSettings()
    self.last_refresh_ns: int | None = None
    self.last_tick_ns: int | None = None
    self.applied = self.vehicle
    self.selected = self.vehicle
    self.applied_controller = None
    self.last_application = self.vehicle

  def apply(self, controller, tune: TorqueTuning) -> bool:
    """Apply a complete source transition, preserving an untouched vehicle tune.

    This host exclusively owns parameter updates on its controller. Reapplying
    the initial vehicle values is not a harmless refresh: the Ioniq controller
    intentionally retains its original startup PID limits until an actual
    learned/custom update. Source identity matters even when numbers are equal.
    """
    if not isinstance(tune, TorqueTuning) or tune.vehicle != self.vehicle.vehicle:
      raise ValueError('Torque application does not match vehicle')
    if controller is not self.applied_controller:
      self.applied_controller = controller
      self.last_application = self.vehicle
    if tune == self.last_application:
      return False
    controller.update_torque_parameters(*tune.upstream_update())
    self.last_application = tune
    return True

  def _learned(self, sm, now_ns: int) -> TorqueTuning | None:
    name = 'lateralTorqueParameters'
    stamp = int(sm.logMonoTime[name])
    if not sm.all_checks([name]) or stamp <= 0 or not 0 <= now_ns - stamp <= int(2e9 / SERVICE_LIST[name].frequency):
      return None
    state = sm[name]
    if not state.useParams or not state.valid or int(state.version) != LEARNER_VERSION:
      return None
    factor = float(state.latAccelFactorFiltered)
    offset = float(state.latAccelOffsetFiltered)
    friction = float(state.frictionCoefficientFiltered)
    vehicle = self.vehicle
    if (not all(math.isfinite(v) for v in (factor, offset, friction)) or
        not 0.7 * vehicle.lat_accel_factor <= factor <= 1.3 * vehicle.lat_accel_factor or
        abs(offset) > min(0.5, 0.5 * vehicle.lat_accel_factor) or
        not 0.5 * vehicle.friction <= friction <= max(0.1, 1.5 * vehicle.friction)):
      return None
    return TorqueTuning(TorqueSource.LEARNED, vehicle.vehicle, factor, offset, friction)

  def _select(self, sm, now_ns: int) -> TorqueTuning:
    vehicle = self.vehicle
    settings = self.settings
    if not settings.valid:
      return vehicle
    allow_learning = not settings.force_auto_off if self.allow_learning is None else self.allow_learning
    learned = self._learned(sm, now_ns) if allow_learning else None
    base = learned or vehicle
    if settings.user_factor is None and settings.user_friction is None:
      return base
    return TorqueTuning(TorqueSource.USER, vehicle.vehicle,
                        settings.user_factor if settings.user_factor is not None else base.lat_accel_factor,
                        vehicle.lat_accel_offset if settings.user_factor is not None else base.lat_accel_offset,
                        settings.user_friction if settings.user_friction is not None else base.friction)

  def sample(self, sm, *, now_ns: int, lat_active: bool) -> TorqueTuning:
    if now_ns <= 0 or (self.last_tick_ns is not None and not 0 < now_ns - self.last_tick_ns <= 50_000_000):
      self.applied = self.vehicle
      self.last_refresh_ns = None
      self.last_tick_ns = now_ns
      self.selected = self.vehicle
      return self.vehicle
    dt = 0.01 if self.last_tick_ns is None else (now_ns - self.last_tick_ns) / 1e9
    self.last_tick_ns = now_ns
    if self.last_refresh_ns is None or now_ns - self.last_refresh_ns >= REFRESH_NS:
      self.settings = read_settings(self.params, self.vehicle, allow_learning=self.allow_learning)
      self.last_refresh_ns = now_ns
    if not lat_active or not self.settings.valid:
      self.applied = self.selected = self.vehicle
      return self.vehicle
    self.selected = self._select(sm, now_ns)
    prior, target = self.applied, self.selected
    factor_step = 0.5 * self.vehicle.lat_accel_factor * dt
    offset_step = 0.1 * dt
    friction_step = max(0.05, self.vehicle.friction) * dt
    self.applied = TorqueTuning(target.source, target.vehicle,
                                _move(prior.lat_accel_factor, target.lat_accel_factor, factor_step),
                                _move(prior.lat_accel_offset, target.lat_accel_offset, offset_step),
                                _move(prior.friction, target.friction, friction_step))
    return self.applied
