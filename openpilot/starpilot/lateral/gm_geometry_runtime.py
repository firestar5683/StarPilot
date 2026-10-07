"""Canonical exact-GM geometry projection and explicit learner intent."""
from dataclasses import dataclass
import time

from openpilot.starpilot.lateral.torque_settings import DOCUMENT_KEY, MAX_DOCUMENT_BYTES, GeometryProfile, parse_document
from openpilot.starpilot.saved_source import read_saved


@dataclass(frozen=True)
class GeometrySelection:
  profile: GeometryProfile | None = None
  force_off: bool = False

  @property
  def force_auto(self):
    return self.profile is not None and self.profile.learning == 'force_auto' and not self.force_off


def geometry_basis(CP):
  return float(CP.steerRatio), float(CP.steerActuatorDelay) + .2


def read_geometry(params, CP):
  from openpilot.starpilot.lateral.torque_runtime import gm_manual_supported_cp
  if not gm_manual_supported_cp(CP):
    return GeometrySelection()
  try:
    raw, readable = read_saved(params, DOCUMENT_KEY, MAX_DOCUMENT_BYTES)
    if not readable or raw is None:
      return GeometrySelection()
    profile = parse_document(raw).get(str(CP.carFingerprint))
    tune = CP.lateralTuning.torque
    if (profile is None or profile.geometry is None or
        profile.basis != (tune.latAccelFactor, tune.latAccelOffset, tune.friction) or
        profile.geometry.basis != geometry_basis(CP)):
      return GeometrySelection()
    off, readable = read_saved(params, 'ForceAutoTuneOff', 1)
    if not readable or off not in (None, b'0', b'1'):
      return GeometrySelection()
    return GeometrySelection(profile.geometry, off == b'1' or profile.geometry.learning == 'force_off')
  except (OSError, ValueError, TypeError, UnicodeError, OverflowError):
    return GeometrySelection()


class GeometryPublicationOwner:
  """Project a copy only; estimator messages/state/cache remain upstream-owned."""
  def __init__(self, params, CP):
    self.params, self.CP = params, CP
    self.last_read_ns = None
    self.selected = GeometrySelection()

  def selection(self):
    now = time.monotonic_ns()
    if self.last_read_ns is None or not 0 <= now - self.last_read_ns < 1_000_000_000:
      self.selected = read_geometry(self.params, self.CP)
      self.last_read_ns = now
    return self.selected

  def parameters(self, original):
    selection = self.selection()
    profile = selection.profile
    if profile is None:
      return original
    ratio = profile.ratio.custom_value if profile.ratio.mode == 'custom' and not selection.force_auto else None
    if selection.force_off and ratio is None:
      ratio = profile.basis[0]
    if ratio is None and not selection.force_off:
      return original
    message = original.as_reader().as_builder()
    if ratio is not None:
      message.vehicleParameters.steerRatio = ratio
    if selection.force_off:
      message.vehicleParameters.stiffnessFactor = 1.
    return message

  def delay(self, original):
    profile = self.selection().profile
    if profile is None or profile.automatic_delay:
      return original
    message = original.as_reader().as_builder()
    message.lateralDelay.lateralDelay = profile.full_delay.custom_value if profile.full_delay.mode == 'custom' else profile.basis[1]
    return message
