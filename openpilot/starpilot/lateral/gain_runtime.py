"""Startup-selected manual gain ownership; torque parameter learning stays independent."""

from __future__ import annotations

import time

from openpilot.starpilot.lateral.bolt_policy import supported_cp
from openpilot.starpilot.lateral.torque_settings import DOCUMENT_KEY, MAX_DOCUMENT_BYTES, GainBasis, parse_document
from openpilot.starpilot.saved_source import read_saved

REFRESH_NS = 1_000_000_000


def gain_basis(cp, controller) -> GainBasis:
  tune = cp.lateralTuning.torque
  return GainBasis(str(controller.controller_mode),
                   tuple(tuple(row) for row in controller.pid._k_p),
                   (tune.latAccelFactor, tune.latAccelOffset, tune.friction))


def _selected(params, cp, basis: GainBasis) -> float | None:
  try:
    advanced, readable = read_saved(params, "AdvancedLateralTune", 64)
    if not readable or advanced != b"1":
      return None
    raw, readable = read_saved(params, DOCUMENT_KEY, MAX_DOCUMENT_BYTES)
    if not readable or raw is None:
      return None
    profile = parse_document(raw).get(str(cp.carFingerprint))
    if profile is None or profile.gain_basis != basis or profile.proportional_gain.mode != "custom":
      return None
    return profile.proportional_gain.custom_value
  except (OSError, ValueError, TypeError, UnicodeError, OverflowError):
    return None


class GenericGainOwner:
  def __init__(self, params, cp, controller, basis: GainBasis, value: float):
    self.params = params
    self.cp = cp
    self.pid = controller.pid
    self.basis = basis
    self.last_refresh_ns: int | None = None
    self.current_table = basis.source_table
    self._apply(value)

  def _apply(self, value: float | None) -> None:
    table = self.basis.source_table if value is None else ((0.0,), (value,))
    if table != self.current_table:
      self.pid._k_p = [list(row) for row in table]
      self.current_table = table

  def refresh(self, *, now_ns: int | None = None) -> None:
    now_ns = time.monotonic_ns() if now_ns is None else now_ns
    if self.last_refresh_ns is not None and 0 <= now_ns - self.last_refresh_ns < REFRESH_NS:
      return
    self.last_refresh_ns = now_ns
    self._apply(_selected(self.params, self.cp, self.basis))


def create_gain_owner(params, cp, controller) -> GenericGainOwner | None:
  if not supported_cp(cp):
    return None
  basis = gain_basis(cp, controller)
  value = _selected(params, cp, basis)
  return None if value is None else GenericGainOwner(params, cp, controller, basis, value)
