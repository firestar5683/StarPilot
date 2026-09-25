"""Generated Python-only angle trim defaults; no native bound or registry changes."""
from typing import TypedDict


class TrimDefaults(TypedDict):
  enabled: bool
  offset_m: float
  gain: float


class TrimBounds(TypedDict):
  offset_m: list[float]
  gain: list[float]
  width_m: list[float]
  width_tolerance: list[float]
  std: list[float]
  std_tolerance: list[float]
  confidence: list[float]
  speed_mps: list[float]
  speed_authority: list[float]
  lookahead_m: list[float]
  raw_correction: float
  tau_s: float
  period_s: float
  correction_delta: float


SOURCE_REVISION = 'e22afa6be9b881fa784c92ebb316db47728a3d81'
DEFAULTS: TrimDefaults = {'enabled': False, 'offset_m': 0.0, 'gain': 0.25}
BOUNDS: TrimBounds = {
  'offset_m': [-0.5, 0.5],
  'gain': [0.0, 1.0],
  'width_m': [2.4, 2.8, 3.75, 4.25],
  'width_tolerance': [0.0, 0.81, 0.81, 0.59],
  'std': [0.3, 0.5],
  'std_tolerance': [0.81, 0.0],
  'confidence': [0.6, 0.8],
  'speed_mps': [0.0, 9.0, 15.0],
  'speed_authority': [0.0, 0.0, 1.0],
  'lookahead_m': [8.0, 35.0],
  'raw_correction': 0.004,
  'tau_s': 0.4,
  'period_s': 0.05,
  'correction_delta': 0.00015,
}
