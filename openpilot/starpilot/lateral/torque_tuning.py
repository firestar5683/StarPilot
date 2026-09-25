"""Validated torque values for the optional Corolla upstream controller update.

Source selection lives in torque_runtime; this record does not infer a merge
order or interpret legacy gain fields.
"""

from dataclasses import dataclass
from enum import StrEnum
import math
from collections.abc import Mapping


class TorqueSource(StrEnum):
  VEHICLE = "vehicle"
  USER = "user"
  LEARNED = "learned"


_RECORD_FIELDS = frozenset({"source", "vehicle", "latAccelFactor", "latAccelOffset", "friction"})


def _finite_number(value: object, field: str) -> float:
  if isinstance(value, bool) or not isinstance(value, (int, float)):
    raise ValueError(f"{field} must be a finite number")
  try:
    result = float(value)
  except OverflowError as exc:
    raise ValueError(f"{field} must be a finite number") from exc
  if not math.isfinite(result):
    raise ValueError(f"{field} must be a finite number")
  return result


@dataclass(frozen=True)
class TorqueTuning:
  """One complete source's values in the upstream lateral acceleration domain."""

  source: TorqueSource
  vehicle: str
  lat_accel_factor: float
  lat_accel_offset: float
  friction: float

  def __post_init__(self) -> None:
    if not isinstance(self.source, TorqueSource):
      raise ValueError("source must be a TorqueSource")
    if not isinstance(self.vehicle, str) or not self.vehicle.strip():
      raise ValueError("vehicle must identify the selected platform")
    factor = _finite_number(self.lat_accel_factor, "latAccelFactor")
    offset = _finite_number(self.lat_accel_offset, "latAccelOffset")
    friction = _finite_number(self.friction, "friction")
    if factor <= 0.0:
      raise ValueError("latAccelFactor must be positive")
    if friction < 0.0:
      raise ValueError("friction must be nonnegative")
    object.__setattr__(self, "lat_accel_factor", factor)
    object.__setattr__(self, "lat_accel_offset", offset)
    object.__setattr__(self, "friction", friction)

  def upstream_update(self) -> tuple[float, float, float]:
    """Arguments for LatControlTorque.update_torque_parameters, in its API order."""
    return self.lat_accel_factor, self.lat_accel_offset, self.friction


def from_record(record: Mapping[str, object]) -> TorqueTuning:
  """Parse only the named fields; serialized legacy gains are deliberately rejected."""
  if not isinstance(record, Mapping) or set(record) != _RECORD_FIELDS:
    raise ValueError(f"torque record fields must be exactly {sorted(_RECORD_FIELDS)}")
  raw_source = record["source"]
  if not isinstance(raw_source, str):
    raise ValueError("unknown torque source")
  try:
    source = TorqueSource(raw_source)
  except (TypeError, ValueError) as exc:
    raise ValueError("unknown torque source") from exc
  vehicle = record["vehicle"]
  if not isinstance(vehicle, str):
    raise ValueError("vehicle must identify the selected platform")
  return TorqueTuning(source, vehicle,
                      _finite_number(record["latAccelFactor"], "latAccelFactor"),
                      _finite_number(record["latAccelOffset"], "latAccelOffset"),
                      _finite_number(record["friction"], "friction"))
