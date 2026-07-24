from enum import StrEnum

import pyray as rl

from openpilot.starpilot.common.experimental_state import requested_experimental_mode


class ModeBannerVariant(StrEnum):
  CHILL = "chill"
  EXPERIMENTAL = "experimental"


def get_mode_banner_variant(params, params_memory=None) -> ModeBannerVariant:
  if params.get_bool("SafeMode"):
    return ModeBannerVariant.CHILL
  if requested_experimental_mode(params, params_memory):
    return ModeBannerVariant.EXPERIMENTAL
  return ModeBannerVariant.CHILL


def _color(red: int, green: int, blue: int, alpha: int) -> rl.Color:
  return rl.Color(red, green, blue, alpha)


def _lerp_color(start: rl.Color, end: rl.Color, progress: float, alpha: int) -> rl.Color:
  progress = max(0.0, min(1.0, progress))
  return rl.Color(
    round(start.r + (end.r - start.r) * progress),
    round(start.g + (end.g - start.g) * progress),
    round(start.b + (end.b - start.b) * progress),
    alpha,
  )


def mode_banner_color(variant: ModeBannerVariant, progress: float, alpha: int = 255) -> rl.Color:
  progress = max(0.0, min(1.0, progress))
  if variant == ModeBannerVariant.CHILL:
    return _lerp_color(_color(20, 255, 171, alpha), _color(35, 149, 255, alpha), progress, alpha)
  return _lerp_color(_color(255, 155, 63, alpha), _color(219, 56, 34, alpha), progress, alpha)


def mode_atom_color(variant: ModeBannerVariant, progress: float, alpha: int = 255) -> rl.Color:
  # The compact atom reads left-to-right as blue to mint in fixed Chill mode.
  if variant == ModeBannerVariant.CHILL:
    progress = 1.0 - progress
  return mode_banner_color(variant, progress, alpha)


def draw_mode_banner_gradient(rect: rl.Rectangle, variant: ModeBannerVariant, alpha: int = 255) -> None:
  rl.draw_rectangle_gradient_h(
    int(rect.x), int(rect.y), int(rect.width), int(rect.height),
    mode_banner_color(variant, 0.0, alpha), mode_banner_color(variant, 1.0, alpha),
  )
