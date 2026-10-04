"""Strict saved Torque policy shared by the optional host and native settings UI."""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import StrEnum
import json
import math
from typing import cast

from openpilot.starpilot.lateral.torque_supported import BOLT_VEHICLES, SUPPORTED_VEHICLES

DOCUMENT_KEY = "TorqueOverrideDocument"
LEGACY_KEYS = ("SteerLatAccel", "SteerFriction", "SteerLatAccelStock", "SteerFrictionStock")
MAX_DOCUMENT_BYTES = 16_384


@dataclass(frozen=True)
class FieldChoice:
  mode: str = "source"
  custom_value: float | None = None


@dataclass(frozen=True)
class GainBasis:
  controller: str
  source_table: tuple[tuple[float, ...], tuple[float, ...]]
  torque_basis: tuple[float, float, float]


@dataclass(frozen=True)
class PlatformProfile:
  basis: tuple[float, float, float]
  factor: FieldChoice
  friction: FieldChoice
  proportional_gain: FieldChoice = FieldChoice()
  gain_basis: GainBasis | None = None


class LegacyMode(StrEnum):
  ABSENT = "absent"
  STOCK = "stock"
  CUSTOM = "custom"


@dataclass(frozen=True)
class LegacyChoice:
  factor: float | None
  friction: float | None
  factor_mode: LegacyMode
  friction_mode: LegacyMode
  factor_saved: float | None
  friction_saved: float | None


def bounds(basis: tuple[float, float, float], field: str) -> tuple[float, float]:
  factor, _, friction = basis
  if field == "factor":
    return 0.5 * factor, 1.5 * factor
  if field == "friction":
    return 0.0, min(1.0, max(0.1, 2.0 * friction))
  raise ValueError("Unknown torque field")


def _finite_number(value: object) -> bool:
  if type(value) not in (float, int):
    return False
  try:
    return math.isfinite(cast(float | int, value))
  except OverflowError:
    return False


def valid_basis(basis: tuple[float, float, float]) -> bool:
  return (len(basis) == 3 and all(_finite_number(v) for v in basis) and
          basis[0] > 0 and basis[2] >= 0)


def _number(raw: bytes | None) -> float | None:
  if raw is None:
    return None
  value = float(raw)
  if not math.isfinite(value):
    raise ValueError("Invalid torque number")
  return value


def interpret_legacy(raw: dict[str, bytes | None], basis: tuple[float, float, float]) -> LegacyChoice:
  """Preserve the old stock-marker and two-decimal CP equality semantics."""
  if not valid_basis(basis):
    raise ValueError("Invalid torque basis")
  values = {key: _number(raw.get(key)) for key in LEGACY_KEYS}
  result: list[float | None] = []
  modes: list[LegacyMode] = []
  saved: list[float | None] = []
  for key, marker_key, field, stock in ((LEGACY_KEYS[0], LEGACY_KEYS[2], "factor", basis[0]),
                                        (LEGACY_KEYS[1], LEGACY_KEYS[3], "friction", basis[2])):
    value, marker = values[key], values[marker_key]
    saved.append(value)
    if value is None:
      result.append(None)
      modes.append(LegacyMode.ABSENT)
    elif round(value, 2) == round(stock, 2) or marker is not None and math.isclose(value, marker, abs_tol=1e-6):
      result.append(None)
      modes.append(LegacyMode.STOCK)
    else:
      low, high = bounds(basis, field)
      if not low <= value <= high:
        raise ValueError("Out-of-range torque setting")
      result.append(value)
      modes.append(LegacyMode.CUSTOM)
  return LegacyChoice(result[0], result[1], modes[0], modes[1], saved[0], saved[1])


def empty_document() -> dict:
  return {"schemaVersion": 1, "vehicles": {}}


def _pairs(items: list[tuple[str, object]]) -> dict:
  result = {}
  for key, value in items:
    if key in result:
      raise ValueError("Duplicate torque document member")
    result[key] = value
  return result


def _bad_constant(_value: str):
  raise ValueError("Nonfinite torque document number")


def _choice(value: object) -> FieldChoice:
  if not isinstance(value, dict) or set(value) != {"mode", "customValue"}:
    raise ValueError("Malformed torque field")
  mode, custom = value["mode"], value["customValue"]
  if mode not in ("source", "custom") or (custom is not None and not _finite_number(custom)) or \
     (mode == "custom" and custom is None):
    raise ValueError("Malformed torque field")
  return FieldChoice(mode, custom)


def parse_document(raw: bytes) -> dict[str, PlatformProfile]:
  if len(raw) > MAX_DOCUMENT_BYTES:
    raise ValueError("Oversized torque document")
  try:
    document = json.loads(raw.decode("utf-8"), object_pairs_hook=_pairs, parse_constant=_bad_constant)
  except (RecursionError, OverflowError) as exc:
    raise ValueError("Malformed torque document") from exc
  if not isinstance(document, dict) or set(document) != {"schemaVersion", "vehicles"} or \
     type(document["schemaVersion"]) is not int or document["schemaVersion"] not in (1, 2) or \
     not isinstance(document["vehicles"], dict) or len(document["vehicles"]) > len(SUPPORTED_VEHICLES):
    raise ValueError("Malformed torque document")
  profiles: dict[str, PlatformProfile] = {}
  for fingerprint, value in document["vehicles"].items():
    expected = {"basis", "factor", "friction"}
    if document["schemaVersion"] == 2 and isinstance(value, dict) and "proportionalGain" in value:
      expected |= {"proportionalGain", "gainBasis"}
    if fingerprint not in SUPPORTED_VEHICLES or not isinstance(value, dict) or set(value) != expected:
      raise ValueError("Malformed torque profile")
    basis_obj = value["basis"]
    if not isinstance(basis_obj, dict) or set(basis_obj) != {"latAccelFactor", "latAccelOffset", "friction"}:
      raise ValueError("Malformed torque basis")
    basis = tuple(basis_obj[key] for key in ("latAccelFactor", "latAccelOffset", "friction"))
    if not valid_basis(basis):
      raise ValueError("Malformed torque basis")
    gain = FieldChoice()
    gain_basis = None
    if "proportionalGain" in value:
      if fingerprint not in BOLT_VEHICLES:
        raise ValueError("Unsupported gain profile")
      gain = _choice(value["proportionalGain"])
      gain_basis = parse_gain_basis(value["gainBasis"])
      if gain.mode == "custom" and (gain.custom_value is None or not 0.3 <= gain.custom_value <= 0.9):
        raise ValueError("Out-of-range proportional gain")
    profiles[fingerprint] = PlatformProfile(basis, _choice(value["factor"]), _choice(value["friction"]), gain, gain_basis)
  return profiles


def serialize_document(profiles: dict[str, PlatformProfile]) -> bytes:
  vehicles: dict[str, dict] = {}
  version = 2 if any(p.gain_basis is not None for p in profiles.values()) else 1
  for fingerprint, profile in profiles.items():
    vehicles[fingerprint] = {
      "basis": dict(zip(("latAccelFactor", "latAccelOffset", "friction"), profile.basis, strict=True)),
      "factor": {"mode": profile.factor.mode, "customValue": profile.factor.custom_value},
      "friction": {"mode": profile.friction.mode, "customValue": profile.friction.custom_value},
    }
    if profile.gain_basis is None and profile.proportional_gain != FieldChoice():
      raise ValueError("Gain choice requires a bound basis")
    if profile.gain_basis is not None:
      vehicles[fingerprint]["proportionalGain"] = {"mode": profile.proportional_gain.mode, "customValue": profile.proportional_gain.custom_value}
      vehicles[fingerprint]["gainBasis"] = {"controller": profile.gain_basis.controller,
                                            "sourceTable": profile.gain_basis.source_table,
                                            "torqueBasis": profile.gain_basis.torque_basis}
  raw = json.dumps({"schemaVersion": version, "vehicles": vehicles}, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
  parse_document(raw)
  return raw


def resolve_document(profiles: dict[str, PlatformProfile], fingerprint: str,
                     basis: tuple[float, float, float]) -> tuple[float | None, float | None, bool]:
  profile = profiles.get(fingerprint)
  if profile is None:
    return None, None, False
  if (profile.factor.mode == "custom" or profile.friction.mode == "custom") and profile.basis != basis:
    return None, None, True
  if fingerprint in BOLT_VEHICLES and profile.factor.mode == "custom":
    return None, None, True
  result = []
  for field, choice in (("factor", profile.factor), ("friction", profile.friction)):
    if choice.mode == "custom":
      low, high = bounds(basis, field)
      if choice.custom_value is None or not low <= choice.custom_value <= high:
        raise ValueError("Out-of-range torque profile")
      result.append(None if round(choice.custom_value, 2) == round(basis[0 if field == "factor" else 2], 2) else choice.custom_value)
    else:
      result.append(None)
  return result[0], result[1], False


def replace_field(profiles: dict[str, PlatformProfile], fingerprint: str, basis: tuple[float, float, float],
                  field: str, mode: str, value: float | None) -> dict[str, PlatformProfile]:
  if fingerprint in BOLT_VEHICLES and field == "factor":
    raise ValueError("Bolt factor editing is not supported")
  if mode not in ("source", "custom") or field not in ("factor", "friction") or not valid_basis(basis):
    raise ValueError("Invalid torque edit")
  if value is not None and not _finite_number(value):
    raise ValueError("Invalid torque edit")
  if mode == "custom":
    low, high = bounds(basis, field)
    if value is None or not low <= value <= high:
      raise ValueError("Out-of-range torque edit")
  profile = profiles.get(fingerprint, PlatformProfile(basis, FieldChoice(), FieldChoice()))
  if profile.basis != basis and (profile.factor.mode == "custom" or profile.friction.mode == "custom"):
    raise ValueError("Torque basis needs review")
  current = profile.factor if field == "factor" else profile.friction
  choice = FieldChoice(mode, current.custom_value if mode == "source" else value)
  updated = replace(profile, basis=basis, factor=choice if field == "factor" else profile.factor,
                    friction=choice if field == "friction" else profile.friction)
  result = dict(profiles)
  result[fingerprint] = updated
  return result


def parse_gain_basis(value: object) -> GainBasis:
  if not isinstance(value, dict) or set(value) != {"controller", "sourceTable", "torqueBasis"}:
    raise ValueError("Malformed gain basis")
  table, basis = value["sourceTable"], value["torqueBasis"]
  if (value["controller"] not in ("standard", "starpilot") or
      not isinstance(table, (list, tuple)) or len(table) != 2 or
      any(not isinstance(row, (list, tuple)) or not row for row in table) or
      len(table[0]) != len(table[1]) or len(table[0]) > 32 or
      any(not _finite_number(n) for row in table for n in row) or
      any(a >= b for a, b in zip(table[0], table[0][1:], strict=False)) or
      any(n <= 0 for n in table[1]) or
      not isinstance(basis, (list, tuple)) or not valid_basis(tuple(basis))):
    raise ValueError("Malformed gain basis")
  return GainBasis(value["controller"], (tuple(table[0]), tuple(table[1])), tuple(basis))


def replace_gain(profiles: dict[str, PlatformProfile], fingerprint: str, basis: GainBasis,
                 mode: str, value: float | None, *, review: bool = False) -> dict[str, PlatformProfile]:
  if fingerprint not in BOLT_VEHICLES or mode not in ("source", "custom"):
    raise ValueError("Unsupported gain edit")
  if value is not None and (not _finite_number(value) or not 0.3 <= value <= 0.9):
    raise ValueError("Out-of-range proportional gain")
  if mode == "custom" and value is None:
    raise ValueError("Missing proportional gain")
  prior = profiles.get(fingerprint, PlatformProfile(basis.torque_basis, FieldChoice(), FieldChoice()))
  if mode == "custom" and prior.proportional_gain.mode == "custom" and prior.gain_basis != basis and not review:
    raise ValueError("Gain basis needs review")
  result = dict(profiles)
  result[fingerprint] = replace(prior, proportional_gain=FieldChoice(mode, value if mode == "custom" else prior.proportional_gain.custom_value),
                                gain_basis=basis)
  return result
