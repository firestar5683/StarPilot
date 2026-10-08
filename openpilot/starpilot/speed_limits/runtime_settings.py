"""Reviewed saved-setting mapping for the opt-in system-longitudinal SLC runtime."""

import math
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from openpilot.starpilot.speed_limits import acceptance as acc
from openpilot.starpilot.speed_limits import lead_relaxation as lr
from openpilot.starpilot.speed_limits import offset_document as od
from openpilot.starpilot.speed_limits import selection as sel
from openpilot.starpilot.speed_limits import speed_domain as sd

MPH_TO_MPS = od.MPH_TO_MPS
KPH_TO_MPS = od.KPH_TO_MPS
IMPERIAL_BOUNDS = od.IMPERIAL_BOUNDS
METRIC_BOUNDS = od.METRIC_BOUNDS
LABELS = {"Dashboard": sel.Source.DASHBOARD, "Map Data": sel.Source.MAP, "Vision": sel.Source.VISION}


@dataclass(frozen=True)
class Settings:
  enabled: bool
  display: bool
  selection: sel.SelectionPolicy
  acceptance: acc.Policy
  offsets: sd.OffsetSchedule
  manual_override: bool
  set_speed_override: bool
  lead_policy: lr.Policy
  errors: tuple[str, ...] = ()
  # Preserve the validated saved choice for same-drive advisory consumers.
  # Append after errors so existing positional Settings construction is stable.
  fallback_choice: int = 2


def _bool(values: Mapping[str, object], key: str, default: bool = False) -> bool:
  value = values.get(key, default)
  if type(value) is not bool:
    raise ValueError(f"{key} must be Boolean")
  return value


def _number(values: Mapping[str, object], key: str, default: float = 0.0) -> float:
  value = values.get(key, default)
  if (type(value) is not int and type(value) is not float) or not math.isfinite(value):
    raise ValueError(f"{key} must be finite")
  return float(value)


def _disabled(reason: str) -> Settings:
  selection = sel.SelectionPolicy(sel.SelectionMode.ORDERED, (sel.Source.DASHBOARD, sel.Source.MAP), False)
  return Settings(False, False, selection, acc.Policy(display_only=True),
                  sd.OffsetSchedule((sd.OffsetBand(0.0, None, 0.0),)), False, False,
                  lr.Policy(0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, (0.0, 1.0), (1.0, 1.0)), (reason,))


def parse(values: Mapping[str, object]) -> Settings:
  """Translate saved labels without changing their meaning or enabling unsupported output."""
  try:
    control = _bool(values, "SpeedLimitController")
    display = control or _bool(values, "ShowSpeedLimits", True)
    document = od.validate(values['SLCOffsetSchedule']) if 'SLCOffsetSchedule' in values else None
    if document is od.NEEDS_REVIEW:
      raise ValueError('saved SLC offsets need review')
    metric = _bool(values, "IsMetric") if document is None else False  # presentation units do not own adopted control
    first = values.get("SLCPriority1", "Vision")
    second = values.get("SLCPriority2", "Dashboard")
    if type(first) is not str or type(second) is not str:
      raise ValueError("invalid saved SLC source priority")
    mode = {"Highest": sel.SelectionMode.HIGHEST, "Lowest": sel.SelectionMode.LOWEST}.get(first, sel.SelectionMode.ORDERED)
    if first not in (*LABELS, "Highest", "Lowest") or second not in LABELS:
      raise ValueError("invalid saved SLC source priority")
    slots = (LABELS.get(first), LABELS[second])
    fallback = values.get("SLCFallback", 2)
    override = values.get("SLCOverride", 1)
    if type(fallback) is not int or fallback not in (0, 1, 2):
      raise ValueError("invalid saved SLC fallback")
    if type(override) is not int or override not in (0, 1, 2):
      raise ValueError("invalid saved SLC override")
    # Only accepted-history fallback belongs to this control domain. Saved set
    # speed and experimental fallback choices never create a source observation.
    confirmation = _bool(values, "SLCConfirmation")
    policy = acc.Policy(confirm_lower=confirmation and _bool(values, "SLCConfirmationLower"),
                        confirm_higher=confirmation and _bool(values, "SLCConfirmationHigher"),
                        fallback_previous=fallback == 2, display_only=not control)
    offsets = (document if isinstance(document, od.OffsetDocument) else
               od.adopt_legacy(metric, tuple(_number(values, f"Offset{i + 1}") for i in range(7)))).schedule()
    lead_policy = lr.Policy(20 * MPH_TO_MPS, 30.0, 1.2, 0.35, 0.25, 0.001, 0.05,
                            tuple(v * MPH_TO_MPS for v in (0.0, 5.0, 10.0, 15.0)),
                            (0.7, 0.9, 1.15, 1.35))
    # SLCOverride was display-only; both pedal and selected-speed overrides remain active.
    return Settings(control, display, sel.SelectionPolicy(mode, slots, False), policy, offsets,
                    control, control, lead_policy, fallback_choice=fallback)
  except (ValueError, OverflowError) as error:
    return _disabled(str(error))


SAVED_KEYS = ("SpeedLimitController", "ShowSpeedLimits", "IsMetric", "SLCPriority1", "SLCPriority2",
              "SLCFallback", "SLCOverride", "SLCConfirmation", "SLCConfirmationHigher", "SLCConfirmationLower",
              *(f"Offset{i}" for i in range(1, 8)))


def read_params(params) -> Settings:
  values = {}
  try:
    with Path(params.get_param_path('SLCOffsetSchedule')).open('rb') as stream:
      raw_document = stream.read(od.MAX_DOCUMENT_BYTES + 1)
  except FileNotFoundError:
    raw_document = None
  except OSError:
    return _disabled('Invalid saved SLCOffsetSchedule')
  if raw_document is not None:
    try:
      values['SLCOffsetSchedule'] = od.decode(raw_document)
    except (ValueError, OverflowError):
      return _disabled('Invalid saved SLCOffsetSchedule')
  for key in SAVED_KEYS:
    if raw_document is not None and (key == 'IsMetric' or key.startswith('Offset')):
      continue
    # Typed Params reads turn malformed numbers/strings into absence and accept
    # any non-"1" Boolean as false. Neither may silently alter confirmation or
    # units. Decode the saved bytes explicitly; only an absent file uses defaults.
    try:
      raw = Path(params.get_param_path(key)).read_bytes()
      if key.startswith('Offset'):
        value = float(raw)
      elif key in ('SLCFallback', 'SLCOverride'):
        value = int(raw)
      elif key in ('SLCPriority1', 'SLCPriority2'):
        value = raw.decode('utf-8')
      else:
        if raw not in (b'0', b'1'):
          raise ValueError('invalid Boolean')
        value = raw == b'1'
      values[key] = value
    except FileNotFoundError:
      continue
    except (OSError, ValueError, OverflowError):
      return _disabled(f'Invalid saved {key}')
  return parse(values)
