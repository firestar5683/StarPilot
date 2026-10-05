"""Vehicle-provided AOL capabilities; the default grants no authority."""

from dataclasses import dataclass


@dataclass(frozen=True)
class AolVehiclePolicy:
  intent_supported: bool = False
  settings_supported: bool = False
  runtime_supported: bool = False
  normal_runtime_supported: bool = False
  ordinary_axis_ack_required: bool = False
  cruise_main_required: bool = True
  explicit_latch: bool = False
  distance_personality: bool = False
  fixed_cruise_buttons: bool = False
  physical_stalk_owner: bool = False
  distance_pause_only: bool = False
  paddle_pause: bool = False
  safety_param_addition: int = 0
  alternative_experience_addition: int = 0
  full_axis_runtime_required: bool = False
