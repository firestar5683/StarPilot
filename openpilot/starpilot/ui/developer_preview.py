"""Immutable, explicitly synthetic onroad visuals for private host replay."""

from dataclasses import dataclass
import math


FLAGS = frozenset(("cem", "csc"))
ORDER = ("cem", "csc")
CEM_REASONS = ("CURVE", "LEAD", "STOP LIGHT", "SPEED")
CSC_CURVATURE = (0.0, 0.008, 0.0115, 0.0200)


@dataclass(frozen=True)
class OnroadVisualPreview:
  cem_reason: str | None = None
  curve_curvature: float | None = None
  label: str = "SYNTHETIC REPLAY PREVIEW"


def parse_flags(raw: str) -> frozenset[str]:
  if raw == "":
    return frozenset()
  parts = raw.split(",")
  if any(part not in FLAGS for part in parts) or len(parts) != len(set(parts)):
    raise ValueError("Unknown or duplicate private onroad visual preview")
  return frozenset(parts)


def encode_flags(flags: frozenset[str]) -> str:
  if not flags <= FLAGS:
    raise ValueError("Unknown private onroad visual preview")
  return ",".join(flag for flag in ORDER if flag in flags)


def preview_at(flags: frozenset[str], elapsed_s: float) -> OnroadVisualPreview | None:
  if not flags <= FLAGS or not math.isfinite(elapsed_s) or elapsed_s < 0:
    raise ValueError("Invalid private onroad visual preview")
  if not flags:
    return None
  phase = int(elapsed_s // 2) % 4
  return OnroadVisualPreview(CEM_REASONS[phase] if "cem" in flags else None,
                             CSC_CURVATURE[phase] if "csc" in flags else None)
