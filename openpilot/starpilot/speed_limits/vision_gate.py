"""Availability of the optional camera speed-limit source."""

from collections.abc import Mapping
from openpilot.starpilot.car.hyundai.aol import ioniq6_settings_capable
from opendbc.car.gm.feature_capabilities import display_supported as gm_display_supported


def diagnostic_choice_enabled(environment: Mapping[str, str], cp=None) -> bool:
  # A saved source choice does not itself authorize Vision speed control.
  return ((environment.get("SLC_REPLAY_RUNTIME") == "1" and environment.get("SLC_VISION_DEVELOPMENT") == "1") or
          (cp is not None and (ioniq6_settings_capable(cp) or gm_display_supported(cp))))
