"""Saved V-ASM editor state; runtime observation and OEM BSM are separate."""

from collections.abc import Callable
from dataclasses import replace

from openpilot.starpilot.spot_monitor.actions import WriteResult, commit
from openpilot.starpilot.spot_monitor.policy import Annotation, decode_annotation
from openpilot.starpilot.spot_monitor.preferences import Preferences, encode, read_preferences
from openpilot.starpilot.ui.feature_settings_state import FeatureRow, FeatureSettingsRequest, FeatureSettingsState


RESET = "vasm:reset"
ANNOTATION = "vasm:annotation"
ENABLED = "vasm:enabled"
CONFIDENCE = "vasm:confidence"
SMOOTH = "vasm:smooth"
CAMERA_FORMATS = ((1928, 1208), (1344, 760))


def validated_annotation(raw: str) -> Annotation | None:
  try:
    if type(raw) is not str or len(raw.encode("utf-8")) > 8192:
      return None
    value = decode_annotation(raw)
  except (UnicodeError, ValueError, TypeError, OverflowError):
    return None
  return value if (value.width, value.height) in CAMERA_FORMATS else None


class VASMOwner:
  def __init__(self, params, parked: Callable[[], bool]):
    self.params, self.parked = params, parked
    self.last_write = WriteResult(False, False)

  def snapshot(self) -> FeatureSettingsState:
    saved = read_preferences(self.params)
    parked = self.parked()
    allowed = parked and saved.readable
    rows: list[FeatureRow] = []
    if not saved.readable:
      rows.append(FeatureRow("", "Saved spot-monitor settings", "Unavailable",
                             reason="Saved source cannot be read; no changes allowed"))
    elif not saved.valid:
      rows.extend((FeatureRow("", "Saved spot-monitor settings", "Invalid",
                              reason="Existing saved bytes remain unchanged until explicit reset"),
                   FeatureRow(RESET, "Reset saved spot-monitor settings", "Off and unconfigured", saved.raw,
                              available=allowed, reason="Replace invalid settings with defaults")))
    else:
      preferences = saved.preferences
      configured = preferences.annotation is not None
      reason = ("" if allowed else
                "Fresh parked evidence required to edit")
      rows.extend((FeatureRow(ENABLED, "Use visual spot monitoring", "On" if preferences.enabled else "Off",
                              saved.raw, ("Off", "On"), available=allowed and configured,
                              reason=reason if configured else "Annotate at least one camera side first"),
                   FeatureRow(CONFIDENCE, "Detection confidence", f"{preferences.confidence:.2f}", saved.raw,
                              step=0.01, minimum=0.8, maximum=1.0, available=allowed and configured,
                              reason="Higher values require stronger model evidence" if allowed else reason),
                   FeatureRow(SMOOTH, "Warning smoothing", f"{preferences.smooth_seconds:.2f}", saved.raw,
                              step=0.01, minimum=0.01, maximum=0.5, unit="s", available=allowed and configured,
                              reason="Higher values make warnings change more slowly" if allowed else reason),
                   FeatureRow(ANNOTATION, "Camera window regions", "Configured" if configured else "Not configured",
                              saved.raw, available=allowed,
                              reason="Draw on a local still or an empty camera-sized canvas; image stays on this device browser"),))
      if saved.raw is not None:
        rows.append(FeatureRow(RESET, "Clear saved spot-monitor settings", "Off and unconfigured", saved.raw,
                               available=allowed, reason="Clear saved regions and choices"))
    initial = Preferences()
    defaults = {ENABLED: 'Off', CONFIDENCE: f'{initial.confidence:.2f}', SMOOTH: f'{initial.smooth_seconds:.2f}'}
    rows = [replace(row, default_value=defaults[row.key]) if row.key in defaults else row for row in rows]
    return FeatureSettingsState(page="vasm", title="V-ASM spot monitoring",
                                subtitle="Saved visual settings only; no live camera or warning status is shown here.",
                                rows=tuple(rows), parked=parked)

  def editor_with_source(self) -> tuple[dict, bytes | None]:
    saved = read_preferences(self.params)
    annotation = saved.preferences.annotation if saved.readable and saved.valid else None
    def points(side: str) -> list[list[float]]:
      if annotation is None:
        return []
      source = getattr(annotation, f"camera_{side}_source")
      return [list(point) for point in source] if source is not None else []
    return ({"configured": annotation is not None,
             "width": annotation.width if annotation else 1928,
             "height": annotation.height if annotation else 1208,
             "cameraLeft": points("left"), "cameraRight": points("right")}, saved.raw)

  def apply(self, request: FeatureSettingsRequest) -> bool:
    self.last_write = WriteResult(False, False)
    if not request.confirmation or not self.parked():
      return False
    saved = read_preferences(self.params)
    if not saved.readable or saved.raw != request.expected:
      return False
    if request.key == RESET:
      if saved.raw is None or request.value != "confirm":
        return False
      raw = encode(Preferences())
    elif request.key == ANNOTATION:
      if not saved.valid:
        return False
      annotation = validated_annotation(request.value)
      if annotation is None:
        return False
      try:
        raw = encode(replace(saved.preferences, annotation=annotation))
      except (ValueError, TypeError, OverflowError):
        return False
    else:
      if not saved.valid or saved.preferences.annotation is None:
        return False
      preferences = saved.preferences
      if request.key == ENABLED:
        if request.value not in ("On", "Off"):
          return False
        target = replace(preferences, enabled=request.value == "On")
      elif request.key in (CONFIDENCE, SMOOTH):
        try:
          number = float(request.value)
        except (ValueError, TypeError, OverflowError):
          return False
        target = replace(preferences, **{"confidence" if request.key == CONFIDENCE else "smooth_seconds": number})
      else:
        return False
      try:
        raw = encode(target)
      except (ValueError, TypeError, OverflowError):
        return False
    self.last_write = commit(self.params, raw, saved.raw, self.parked)
    return self.last_write.verified
