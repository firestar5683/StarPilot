"""Capture the complete two-profile offline UI shell with supplied scene data.

This desktop development preview never constructs a device service, Params,
camera IPC client, updater, installer or network manager. Images are evidence
under an explicit output directory and are not runtime UI assets.
"""

import argparse
import hashlib
import json
from pathlib import Path

import pyray as rl

from openpilot.starpilot.ui.device_state import DeviceState
from openpilot.starpilot.ui.onroad_state import AlertSize, OnroadAlert, OnroadState, SpeedLimitObservation
from openpilot.starpilot.ui.presentation import BitmapFonts, Profile
from openpilot.starpilot.ui.preview_home import reference_state
from openpilot.starpilot.ui.preview_settings import reference_settings_state
from openpilot.starpilot.ui.settings_state import Destination
from openpilot.starpilot.ui.software_state import SoftwareState
from openpilot.starpilot.ui.toggles_state import TogglesState
from openpilot.starpilot.ui.shell import ShellMode, ShellSnapshot, ShellView


LARGE_SCENES = ("home", "settings_starpilot", "settings_device", "settings_toggles", "settings_software",
                "onroad_engaged_no_camera", "onroad_disengaged_no_camera", "onroad_alert_small",
                "onroad_alert_mid", "onroad_alert_full")
COMPACT_SCENES = ("home", "settings", "onroad_engaged_no_camera", "onroad_disengaged_no_camera",
                  "onroad_alert_small", "onroad_alert_mid", "onroad_alert_full")


def reference_onroad(scene: str) -> OnroadState:
  alert = OnroadAlert()
  if scene.startswith("onroad_alert_"):
    size = AlertSize(scene.removeprefix("onroad_alert_"))
    alert = OnroadAlert(size=size, text1="TAKE CONTROL IMMEDIATELY" if size == AlertSize.FULL else "Baseline alert",
                        text2="Protected UI fixture", critical=size == AlertSize.FULL)
  engaged = scene == "onroad_engaged_no_camera"
  return OnroadState(engaged=engaged, camera_available=False,
                     speed_mps=20.0, cruise_kph=80.0, speed_limit=SpeedLimitObservation(), alert=alert,
                     personality=0, lateral_active=engaged, longitudinal_active=engaged,
                     slc_system_long_available=engaged)


class ShellViews:
  def __init__(self, profile: Profile, fonts: BitmapFonts, asset_directory: Path):
    self.profile = profile
    self.view = ShellView(fonts, asset_directory)

  def render(self, scene: str) -> None:
    if scene not in LARGE_SCENES + COMPACT_SCENES:
      raise ValueError(f"Unknown scene {scene}")
    if scene.startswith("onroad_"):
      mode, selected = ShellMode.ONROAD, Destination.STAR
    elif scene.startswith("settings"):
      mode = ShellMode.SETTINGS
      selected = {"settings_device": Destination.DEVICE, "settings_software": Destination.SOFTWARE,
                  "settings_toggles": Destination.TOGGLES}.get(scene, Destination.STAR)
    else:
      mode, selected = ShellMode.HOME, Destination.STAR
    self.view.render(ShellSnapshot(mode=mode, home=reference_state(), settings=reference_settings_state(),
                                   onroad=reference_onroad(scene), device=DeviceState(), software=SoftwareState(),
                                   toggles=TogglesState(), selected=selected))

  def close(self) -> None:
    self.view.close()


def main() -> None:
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument("--profile", type=Profile, choices=list(Profile), required=True)
  parser.add_argument("--font-directory", type=Path, required=True)
  parser.add_argument("--asset-directory", type=Path, required=True)
  parser.add_argument("--output", type=Path, required=True)
  args = parser.parse_args()
  if args.output.exists():
    raise ValueError("Refusing to overwrite shell evidence")
  args.output.mkdir(parents=True)
  width, height = args.profile.size
  canvas_width = min(width, 960)
  canvas_height = round(height * canvas_width / width)
  rl.set_config_flags(rl.ConfigFlags.FLAG_WINDOW_HIDDEN | rl.ConfigFlags.FLAG_MSAA_4X_HINT | rl.ConfigFlags.FLAG_WINDOW_HIGHDPI)
  rl.init_window(canvas_width, canvas_height, "Offline UI shell capture")
  if not rl.is_window_ready():
    raise RuntimeError("Unable to initialize native graphics")
  target = rl.load_render_texture(width, height)
  try:
    with BitmapFonts(args.profile, args.font_directory) as fonts:
      views = ShellViews(args.profile, fonts, args.asset_directory)
      try:
        report = {"profile": args.profile.value, "development_only": True, "dimensions": [width, height], "scenes": {}}
        for scene in LARGE_SCENES if args.profile == Profile.LARGE else COMPACT_SCENES:
          for _frame in range(18):
            rl.begin_texture_mode(target)
            rl.clear_background(rl.BLACK)
            views.render(scene)
            rl.end_texture_mode()
          image = rl.load_image_from_texture(target.texture)
          try:
            rl.image_format(image, rl.PixelFormat.PIXELFORMAT_UNCOMPRESSED_R8G8B8A8)
            rl.image_flip_vertical(image)
            path = args.output / f"{scene}.png"
            if not rl.export_image(image, str(path)):
              raise RuntimeError(f"Unable to export {scene}")
            report["scenes"][scene] = hashlib.sha256(bytes(rl.ffi.buffer(image.data, width * height * 4))).hexdigest()
          finally:
            rl.unload_image(image)
        (args.output / "results.json").write_text(json.dumps(report, indent=2) + "\n")
      finally:
        views.close()
  finally:
    rl.unload_render_texture(target)
    rl.close_window()


if __name__ == "__main__":
  main()
