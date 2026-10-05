"""Parked, source-bound owner for installed sound packs and alert levels."""

from collections.abc import Callable
from dataclasses import replace
import math
from pathlib import Path

from openpilot.starpilot.audio.sound_pack import DEFAULT_PACK, PACK_ROOT, installed_packs, read_selection
from openpilot.starpilot.saved_document import commit_exact

from openpilot.starpilot.audio.alert_volume import AUTO, SPECS, VOLUMES, read_volume
from openpilot.starpilot.ui.feature_settings_state import FeatureRow, FeatureSettingsRequest, FeatureSettingsState

AUTO_PREFIX = "sounds:auto:"
PACK_LABELS = {"starpilot": "StarPilot (Built-in)", "stock": "Stock (openpilot)"}


def choices(key: str) -> tuple[str, ...]:
  minimum = SPECS[key][1]
  return ("Auto",) + tuple(f"{value}%" for value in range(minimum, 101, 5))


class SoundsOwner:
  def __init__(self, params, parked: Callable[[], bool], pack_root: Path = PACK_ROOT):
    self.params = params
    self.parked = parked
    self.pack_root = pack_root

  def snapshot(self) -> FeatureSettingsState:
    parked = self.parked()
    raw, selected, readable = read_selection(self.params)
    packs = installed_packs(self.pack_root)
    valid = readable and selected in packs and (raw is None or raw == selected.encode())
    pack_row = FeatureRow("SoundPack", "Sound Pack", PACK_LABELS.get(selected, selected) if valid else "Unavailable Saved Pack", source=raw,
                          choices=tuple(PACK_LABELS.get(pack, pack) for pack in packs), available=parked and readable,
                          reason="Installed packs only; missing clips use stock sounds",
                          repair_value=DEFAULT_PACK if not valid and readable else "")
    rows = []
    for key, label, _ in VOLUMES:
      saved = read_volume(self.params, key)
      numeric = saved.valid and saved.value != AUTO
      value = "Auto" if saved.value == AUTO else str(saved.value) if saved.valid else "Invalid saved level"
      reason = (("StarPilot Auto keeps a 50% baseline and follows ambient sound" if selected == DEFAULT_PACK else
                  "Follows ambient sound") if saved.value == AUTO else
                "Fixed saved level" if saved.valid else
                "Saved level cannot be read" if not saved.readable else "Choose Auto to repair")
      if key == "WarningImmediateVolume" and saved.valid:
        reason = (("StarPilot Auto keeps a 50% baseline; ramps to full volume" if selected == DEFAULT_PACK else
                   "Follows ambient sound; ramps to full volume") if saved.value == AUTO else
                  "Minimum starting level; still ramps to full volume")
      rows.append(FeatureRow(key, label, value, source=saved.raw, choices=("Auto",) if numeric else choices(key),
                             step=5.0 if saved.valid else 0.0, minimum=float(SPECS[key][1]), maximum=100.0,
                             unit="%" if saved.valid else "",
                             available=parked and saved.readable, reason=reason,
                                repair_value="Auto" if not saved.valid and saved.readable else ""))
      if numeric:
        rows.append(FeatureRow(AUTO_PREFIX + key, "Use Auto " + label, "Follow ambient sound", source=saved.raw,
                               available=parked and saved.readable, repair_value="Auto"))
    rows.append(pack_row)
    defaults = dict.fromkeys(SPECS, 'Auto')
    defaults['SoundPack'] = PACK_LABELS.get(DEFAULT_PACK, DEFAULT_PACK)
    rows = tuple(replace(row, default_value=defaults[row.key]) if row.key in defaults else row for row in rows)
    return FeatureSettingsState(page="sounds", title="Sounds & Alerts",
                                subtitle="Installed sound packs and alert levels; Auto follows ambient sound.",
                                rows=tuple(rows), parked=parked)

  def apply(self, request: FeatureSettingsRequest) -> bool:
    if request.key.startswith(AUTO_PREFIX):
      if request.value != "Auto":
        return False
      request = replace(request, key=request.key.removeprefix(AUTO_PREFIX))
    if request.key == "SoundPack":
      request = replace(request, value=next((key for key, label in PACK_LABELS.items() if label == request.value), request.value))
      if request.value not in installed_packs(self.pack_root):
        return False
      result = commit_exact(self.params, key="SoundPack", max_bytes=128, raw=request.value.encode(),
                            expected=request.expected,
                            authorized=lambda: self.parked() and request.value in installed_packs(self.pack_root),
                            temp_prefix=".sound-pack-")
      return result.committed and result.verified
    if request.key not in SPECS or not self.parked():
      return False
    new = request.value
    if new == "Auto":
      selected = AUTO
    else:
      try:
        number = float(new.removesuffix("%"))
      except ValueError:
        return False
      if not math.isfinite(number) or not number.is_integer() or not SPECS[request.key][1] <= number <= 100:
        return False
      selected = int(number)
    first = read_volume(self.params, request.key)
    if not first.readable or first.raw != request.expected:
      return False
    # An explicit valid choice also repairs malformed bytes. There is no write
    # while reading state or opening either native page.
    if not self.parked():
      return False
    final = read_volume(self.params, request.key)
    if not final.readable or final.raw != request.expected:
      return False
    try:
      self.params.put(request.key, selected, block=True)
    except (OSError, KeyError, TypeError, ValueError):
      return False
    return read_volume(self.params, request.key).value == selected
