"""Launch the current native StarPilot UI from an isolated host-tool runtime."""

from __future__ import annotations

import os
from pathlib import Path
import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
  from openpilot.starpilot.ui.presentation import Profile


def font_directory(env: dict[str, str]) -> Path:
  from openpilot.starpilot.ui.presentation import FontRole, Profile, default_font_directory, font_filename, font_path, validate_bitmap_font
  configured = env.get("STARPILOT_UI_FONT_DIR")
  candidate = Path(configured) if configured else default_font_directory()
  if not candidate.is_dir():
    raise RuntimeError("Set STARPILOT_UI_FONT_DIR to the complete reviewed UI bitmap font directory")
  try:
    for profile in Profile:
      for name in {font_filename(profile, role) for role in FontRole}:
        validate_bitmap_font(font_path(candidate, name))
  except ValueError as error:
    raise RuntimeError(f"UI bitmap font bundle is incomplete: {error}. Set STARPILOT_UI_FONT_DIR to the reviewed bundle") from error
  return candidate.resolve()


def launch_environment(profile: Profile, source: dict[str, str]) -> dict[str, str]:
  from openpilot.starpilot.ui.presentation import Profile
  from openpilot.starpilot.ui.developer_preview import encode_flags, parse_flags
  if source.get("SP_HOST_RUNTIME") != "1":
    raise RuntimeError("Start this UI through ./c3 or ./c4 in the isolated host runtime")
  prefix = source.get("OPENPILOT_PREFIX", "")
  if not prefix or (prefix != source.get("SP_HOST_PREFIX") and not prefix.startswith("replay-")):
    raise RuntimeError("Host UI requires the runner prefix or a dedicated replay- prefix")
  root = source.get("PARAMS_ROOT", "")
  if not root or not Path(root).is_absolute():
    raise RuntimeError("Host UI requires an isolated absolute PARAMS_ROOT")
  preview = source.get("SP_ONROAD_VISUAL_PREVIEW", "")
  if preview:
    from openpilot.tools.replay.onroad import PREFIX_RE
    if PREFIX_RE.fullmatch(prefix) is None:
      raise RuntimeError("Onroad visual preview requires a private replay prefix")
    preview = encode_flags(parse_flags(preview))
  result = dict(source)
  if preview:
    result["SP_ONROAD_VISUAL_PREVIEW"] = preview
  else:
    result.pop("SP_ONROAD_VISUAL_PREVIEW", None)
  result["BIG"] = "1" if profile == Profile.LARGE else "0"
  result["STARPILOT_UI_DEV"] = "1"
  result["STARPILOT_UI_FONT_DIR"] = str(font_directory(result))
  result.update(NOBOARD="1", SIMULATION="1", SKIP_FW_QUERY="1", USE_WEBCAM="1")
  return result


def seed_developer_defaults() -> None:
  """Only initialize absent keys inside the runner's private Params namespace."""
  from openpilot.common.params import Params
  from openpilot.common.version import terms_version, training_version
  params = Params()
  defaults = (("HasAcceptedTerms", terms_version), ("CompletedTrainingVersion", training_version),
              ("LanguageSetting", "en"), ("OpenpilotEnabledToggle", True), ("IsDriverViewEnabled", False))
  for key, value in defaults:
    if params.get(key) is None:
      params.put(key, value, block=True)


def main(argv: list[str] | None = None) -> int:
  args = list(sys.argv[1:] if argv is None else argv)
  if not args or any(arg in ("-h", "--help") for arg in args):
    print("Usage: ./c3 [jobs] or ./c4 [jobs] (isolated host native UI)")
    return 0 if args else 2
  profile_name = args.pop(0)
  if profile_name not in ("large", "compact"):
    raise ValueError("expected large or compact UI profile")
  from openpilot.starpilot.ui.presentation import Profile
  profile = Profile.LARGE if profile_name == "large" else Profile.COMPACT
  compile_only = os.environ.get("SP_C3_COMPILE_ONLY" if profile == Profile.LARGE else "SP_C4_COMPILE_ONLY") == "1"
  if compile_only:
    print(f"{profile.value} host UI runtime artifacts prepared")
    return 0
  env = launch_environment(profile, dict(os.environ))
  seed_developer_defaults()
  os.execvpe(sys.executable, [sys.executable, "-m", "openpilot.selfdrive.ui.ui", *args], env)
  return 0


if __name__ == "__main__":
  try:
    raise SystemExit(main())
  except (OSError, RuntimeError, ValueError) as error:
    print(f"Host UI: {error}", file=sys.stderr)
    raise SystemExit(2) from None
