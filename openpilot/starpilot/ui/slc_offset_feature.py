"""Native SLC offset editor and global unit-change owner over strict SI documents."""

from __future__ import annotations

from dataclasses import dataclass
import math
import threading
import time

from openpilot.starpilot.speed_limits import offset_document as od
from openpilot.starpilot.ui.feature_settings_state import FeatureRow, FeatureSettingsRequest
from openpilot.starpilot.saved_source import read_saved

DOCUMENT_KEY = "SLCOffsetSchedule"
OFFSET_KEYS = tuple(f"Offset{i}" for i in range(1, 8))
_LOCK = threading.RLock()


def native_parked(ui) -> bool:
  """Use fresh device and panda evidence, not only UIState.started."""
  from openpilot.starpilot.ui.runtime_snapshot import current_message
  now_ns = time.monotonic_ns()
  device = current_message(ui.sm, "deviceState", now_ns)
  pandas = current_message(ui.sm, "pandaStates", now_ns)
  return bool(not ui.started and device is not None and not device.started and pandas is not None and
              not any(p.ignitionLine or p.ignitionCan for p in pandas))


@dataclass(frozen=True)
class OffsetSnapshot:
  raw_document: bytes | None
  raw_unit: bytes | None
  raw_control: bytes | None
  raw_legacy: tuple[bytes | None, ...]
  document: od.OffsetDocument | od.NeedsReview | None
  metric: bool | None
  valid: bool


def _strict_unit(raw: bytes | None) -> bool | None:
  if raw is None or raw == b"0":
    return False
  if raw == b"1":
    return True
  return None


def _legacy(raw: tuple[bytes | None, ...], metric: bool) -> od.OffsetDocument:
  values = []
  for value in raw:
    number = 0.0 if value is None else float(value)
    if not math.isfinite(number):
      raise ValueError("Invalid saved SLC offset")
    values.append(number)
  return od.adopt_legacy(metric, tuple(values))


def _unit_factor(metric: bool) -> float:
  return od.KPH_TO_MPS if metric else od.MPH_TO_MPS


def _display(value: float) -> str:
  return f"{value:.2f}".rstrip("0").rstrip(".")


def _capability(cp) -> tuple | None:
  try:
    if cp is None or not cp.carFingerprint or not cp.openpilotLongitudinalControl or cp.pcmCruise or \
       cp.notCar or cp.dashcamOnly or cp.passive:
      return None
    return (str(cp.carFingerprint), bool(cp.openpilotLongitudinalControl), bool(cp.pcmCruise),
            bool(cp.notCar), bool(cp.dashcamOnly), bool(cp.passive))
  except (AttributeError, TypeError, ValueError):
    return None


class SlcOffsetOwner:
  def __init__(self, params, parked, vehicle_params, repair_parked=None):
    self.params = params
    self.parked = parked
    self.repair_parked = repair_parked or parked
    self.vehicle_params = vehicle_params

  def capability(self) -> tuple | None:
    return _capability(self.vehicle_params())

  def _raw(self, key: str) -> bytes | None:
    return read_saved(self.params, key, od.MAX_DOCUMENT_BYTES)[0]

  def _readable(self, key: str) -> bool:
    return read_saved(self.params, key, od.MAX_DOCUMENT_BYTES)[1]

  def snapshot(self) -> OffsetSnapshot:
    raw_doc = self._raw(DOCUMENT_KEY)
    raw_unit = self._raw("IsMetric")
    raw_control = self._raw("SpeedLimitController")
    raw_legacy = tuple(self._raw(key) for key in OFFSET_KEYS) if raw_doc is None else (None,) * 7
    metric = _strict_unit(raw_unit)
    try:
      if not all(self._readable(key) for key in (DOCUMENT_KEY, "IsMetric", "SpeedLimitController")):
        raise ValueError("Unreadable SLC setting")
      if raw_doc is not None:
        document = od.decode(raw_doc)
      elif metric is not None and all(self._readable(key) for key in OFFSET_KEYS):
        document = _legacy(raw_legacy, metric)
      else:
        document = None
      return OffsetSnapshot(raw_doc, raw_unit, raw_control, raw_legacy, document, metric,
                            document is not None and metric is not None)
    except (ValueError, OSError, OverflowError):
      return OffsetSnapshot(raw_doc, raw_unit, raw_control, raw_legacy, None, metric, False)

  def ready_to_enable(self) -> bool:
    snap = self.snapshot()
    return snap.raw_document is not None and isinstance(snap.document, od.OffsetDocument)

  def rows(self, allowed: bool, *, repair_allowed: bool | None = None) -> tuple[bool, tuple[FeatureRow, ...]]:
    snap = self.snapshot()
    capable = self.capability()
    available = allowed and capable is not None
    repair_available = available if repair_allowed is None else repair_allowed and capable is not None
    deps = (("IsMetric", snap.raw_unit), ("SpeedLimitController", snap.raw_control))
    if snap.raw_document is None:
      deps += tuple(zip(OFFSET_KEYS, snap.raw_legacy, strict=True))
    if snap.raw_document is None and isinstance(snap.document, od.OffsetDocument):
      mode = "Saved legacy schedule"
      action = FeatureRow("slc_adopt", "Adopt fixed offsets", "Keep these offsets and speed ranges when units change", None,
                          available=repair_available, related_source=snap.raw_unit,
                          capability=capable, dependencies=deps)
    elif isinstance(snap.document, od.OffsetDocument):
      mode = "Fixed speed ranges"
      action = None
    elif snap.document is od.NEEDS_REVIEW:
      mode = "Saved offsets need review; SLC control is paused"
      action = None
    else:
      mode = "Invalid saved offsets; SLC control is paused"
      action = None
    rows = [FeatureRow("", "Offset policy", mode)]
    if action is not None:
      rows.append(action)
    if isinstance(snap.document, od.OffsetDocument) and snap.metric is not None:
      unit = "km/h" if snap.metric else "mph"
      scale = 1 / _unit_factor(snap.metric)
      display_bounds = ((0, 25, 35, 45, 55, 65, 75, 100) if not snap.metric and snap.document.bounds_mps == od.IMPERIAL_BOUNDS else
                        (0, 30, 50, 60, 80, 100, 120, 140) if snap.metric and snap.document.bounds_mps == od.METRIC_BOUNDS else
                        tuple(round(bound * scale) for bound in snap.document.bounds_mps))
      for index in range(7):
        # Round presentation only: the stored SI boundaries remain authoritative.
        label = f"{display_bounds[index]}–{display_bounds[index + 1]} {unit}"
        value = _display(snap.document.offsets_mps[index] * scale)
        rows.append(FeatureRow(OFFSET_KEYS[index], label + " offset", value, snap.raw_document,
                               step=1 if snap.raw_document is not None else 0, unit=unit,
                               minimum=-150 if snap.metric else -99, maximum=150 if snap.metric else 99,
                               available=available and snap.raw_document is not None,
                               reason="Legacy value; adopt to edit" if snap.raw_document is None else
                                      "Speed ranges are rounded for display; saved limits keep their exact values",
                               related_source=snap.raw_unit, capability=capable, dependencies=deps,
                               display_unit=unit))
      rows.append(FeatureRow("", "Above final band", "Zero offset"))
    else:
      for index, key in enumerate(OFFSET_KEYS, start=1):
        label = f"Band {index} offset (invalid saved units)" if snap.metric is None else f"Band {index} offset"
        rows.append(FeatureRow(key, label, "Invalid saved offset or document", snap.raw_document,
                               reason="Unavailable until saved source is repaired"))
    reset_needed = snap.raw_document is not None or snap.document is None
    reset_available = (repair_available and reset_needed and snap.metric is not None and
                       all(self._readable(key) for key, _ in deps) and self._readable(DOCUMENT_KEY))
    if reset_needed:
      reset_ranges = ("Keep saved speed ranges" if isinstance(snap.document, od.OffsetDocument) else
                      f"Use default {'km/h' if snap.metric else 'mph'} speed ranges" if snap.metric is not None else
                      "Repair saved units first")
      rows.append(FeatureRow("slc_reset", "Reset saved offsets", reset_ranges, snap.raw_document,
                             available=reset_available, related_source=snap.raw_unit, capability=capable,
                             dependencies=deps))
    return snap.raw_document is not None and isinstance(snap.document, od.OffsetDocument), tuple(rows)

  def _same(self, request: FeatureSettingsRequest, snap: OffsetSnapshot, *, require_capability: bool) -> bool:
    expected_deps = (("IsMetric", snap.raw_unit), ("SpeedLimitController", snap.raw_control))
    if snap.raw_document is None:
      expected_deps += tuple(zip(OFFSET_KEYS, snap.raw_legacy, strict=True))
    authority = self.repair_parked if request.key in ("slc_adopt", "slc_reset") else self.parked
    return (authority() and (not require_capability or request.capability is not None and request.capability == self.capability()) and
            request.dependencies == expected_deps and
            self._raw(DOCUMENT_KEY) == request.expected and self._readable(DOCUMENT_KEY) and
            self._raw("IsMetric") == request.related_source and self._readable("IsMetric") and
            all(self._raw(key) == raw and self._readable(key) for key, raw in request.dependencies) and
            snap.raw_control == self._raw("SpeedLimitController"))

  def apply(self, request: FeatureSettingsRequest) -> bool:
    if request.key not in ("slc_adopt", "slc_reset", *OFFSET_KEYS):
      return False
    with _LOCK:
      snap = self.snapshot()
      if not self._same(request, snap, require_capability=True):
        return False
      try:
        if request.key == "slc_adopt":
          if not request.confirmation or request.expected is not None or not isinstance(snap.document, od.OffsetDocument):
            return False
          result = snap.document
        elif request.key == "slc_reset":
          if not request.confirmation or snap.metric is None or \
             request.expected is None and isinstance(snap.document, od.OffsetDocument):
            return False
          if isinstance(snap.document, od.OffsetDocument):
            result = od.OffsetDocument(snap.document.bounds_mps, (0.0,) * 7)
          else:
            result = od.adopt_legacy(snap.metric, (0.0,) * 7)
        else:
          if not isinstance(snap.document, od.OffsetDocument) or request.expected is None or snap.metric is None or \
             request.direction not in (-1, 0, 1) or request.display_unit != ("km/h" if snap.metric else "mph"):
            return False
          if request.key not in OFFSET_KEYS:
            return False
          index = OFFSET_KEYS.index(request.key)
          current = snap.document.offsets_mps[index]
          shown = current / _unit_factor(snap.metric)
          candidate_display = float(request.value) if request.direction == 0 else shown + request.direction
          low, high = (-150.0, 150.0) if snap.metric else (-99.0, 99.0)
          if not math.isfinite(candidate_display) or not low <= candidate_display <= high:
            return False
          new_offsets = list(snap.document.offsets_mps)
          new_offsets[index] = (candidate_display * _unit_factor(snap.metric) if request.direction == 0 else
                                current + request.direction * _unit_factor(snap.metric))
          result = od.OffsetDocument(snap.document.bounds_mps, tuple(new_offsets))
        value = od.to_value(result)
        if not self._same(request, snap, require_capability=True):
          return False
        self.params.put(DOCUMENT_KEY, value, block=True)
        saved = self._raw(DOCUMENT_KEY)
        return saved is not None and od.decode(saved) == result
      except (OSError, ValueError, TypeError, OverflowError):
        return False

  def change_units(self, desired: bool, expected_unit: bytes | None) -> bool:
    """Preserve an adopted SI schedule before the global presentation change."""
    if type(desired) is not bool:
      return False
    with _LOCK:
      snap = self.snapshot()
      if not self._readable("IsMetric") or snap.raw_unit != expected_unit:
        return False
      if snap.metric is not None and snap.metric == desired:
        return True
      try:
        protected_capability = None
        written_document = None
        if snap.raw_document is None:
          if isinstance(snap.document, od.OffsetDocument):
            if not self.repair_parked() or self.capability() is None:
              return False
            protected_capability = self.capability()
            if not self._same_unit_source(snap, protected_capability):
              return False
            self.params.put(DOCUMENT_KEY, od.to_value(snap.document), block=True)
            written_document = snap.document
          elif snap.raw_control not in (None, b"0"):
            if not self.repair_parked() or self.capability() is None or not self._same_unit_source(snap, self.capability()):
              return False
            protected_capability = self.capability()
            self.params.put(DOCUMENT_KEY, od.to_value(od.NEEDS_REVIEW), block=True)
            written_document = od.NEEDS_REVIEW
        if not self._readable("IsMetric") or self._raw("IsMetric") != expected_unit:
          return False
        if snap.raw_document is None:
          written = self._raw(DOCUMENT_KEY)
          if written_document is not None:
            if written is None or not self._readable(DOCUMENT_KEY) or od.decode(written) != written_document:
              return False
          elif written is not None or not self._readable(DOCUMENT_KEY):
            return False
        elif self._raw(DOCUMENT_KEY) != snap.raw_document or not self._readable(DOCUMENT_KEY):
          return False
        if (snap.raw_document is None and
            (not self._readable("SpeedLimitController") or self._raw("SpeedLimitController") != snap.raw_control) or
            protected_capability is not None and (not self.repair_parked() or self.capability() != protected_capability)):
          return False
        if snap.raw_document is None and written_document is None and not self._same_unit_source(snap, None):
          return False
        self.params.put_bool("IsMetric", desired, block=True)
        return self._raw("IsMetric") == (b"1" if desired else b"0")
      except (OSError, ValueError, TypeError, OverflowError):
        return False

  def _same_unit_source(self, snap: OffsetSnapshot, capability: tuple | None) -> bool:
    return (self._readable(DOCUMENT_KEY) and self._raw(DOCUMENT_KEY) == snap.raw_document and
            self._readable("IsMetric") and self._raw("IsMetric") == snap.raw_unit and
            self._readable("SpeedLimitController") and self._raw("SpeedLimitController") == snap.raw_control and
            all(self._readable(key) and self._raw(key) == raw for key, raw in zip(OFFSET_KEYS, snap.raw_legacy, strict=True)) and
            (capability is None or self.repair_parked() and self.capability() == capability))
