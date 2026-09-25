"""Select the reviewed native presentation before acquiring a graphics context."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path

from openpilot.starpilot.ui.presentation import FontRole, Profile, default_font_directory, font_filename, font_path, validate_bitmap_font


@dataclass(frozen=True)
class UiSelection:
  custom: bool
  reason: str


def validate_fonts(profile: Profile, font_dir: str | None) -> None:
  directory = Path(font_dir) if font_dir else default_font_directory()
  for filename in {font_filename(profile, role) for role in FontRole}:
    validate_bitmap_font(font_path(directory, filename))


def validate_artwork() -> None:
  assets = Path(__file__).parents[2] / "selfdrive/assets"
  for manifest_name in ("home-assets.json", "settings-assets.json", "toggles-assets.json", "onroad-assets.json"):
    manifest = json.loads(Path(__file__).with_name(manifest_name).read_text())
    for record in manifest["files"]:
      source = assets / record["file"]
      with source.open("rb") as stream:
        data = stream.read(record["bytes"] + 1)
      if len(data) != record["bytes"] or hashlib.sha256(data).hexdigest() != record["sha256"]:
        raise ValueError(f"Unreviewed runtime artwork: {record['file']}")


def select_ui(profile: Profile, environment: Mapping[str, str]) -> UiSelection:
  """The recovery override wins; a forced developer launch fails visibly."""
  if environment.get("STARPILOT_UI") == "upstream":
    return UiSelection(False, "upstream recovery override")
  forced = environment.get("STARPILOT_UI_DEV") == "1"
  try:
    validate_fonts(profile, environment.get("STARPILOT_UI_FONT_DIR"))
    validate_artwork()
  except (OSError, ValueError, RuntimeError, KeyError, TypeError) as error:
    if forced:
      raise RuntimeError(f"Forced StarPilot UI requires reviewed assets: {error}") from error
    return UiSelection(False, f"reviewed StarPilot assets unavailable: {error}")
  return UiSelection(True, "reviewed StarPilot assets verified")


def slc_action_transport_enabled(environment: Mapping[str, str], params=None) -> bool:
  """Keep the UI sender available before an offroad saved choice changes.

  The dispatcher checks the current pending decision and vehicle authority for
  each action; merely constructing its publisher cannot accept a speed limit.
  """
  del environment, params
  return True
