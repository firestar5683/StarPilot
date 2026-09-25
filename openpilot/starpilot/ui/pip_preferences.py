"""Strict, bounded saved PiP preferences; reads never adopt or repair data."""

from dataclasses import dataclass
import json

from openpilot.starpilot.saved_source import read_saved
from openpilot.starpilot.ui.pip_sidecam import Mask


ENABLED = "PIPPreviewEnabled"
MASK = "PIPPreviewMask"
BLINKER = "PIPPreviewShowOnBlinker"
BSM = "PIPPreviewShowOnBSM"
INVERT = "PIPPreviewInvert"
BOOL_KEYS = (ENABLED, BLINKER, BSM, INVERT)
KEYS = (ENABLED, MASK, BLINKER, BSM, INVERT)
DEFAULT_MASK = {"width": 1928, "height": 1208, "center_left": [315, 548],
                "center_right": [1571, 539], "crop_size": 580}
CAMERA_FORMATS = ((1928, 1208), (1344, 760))
MAX_MASK_BYTES = 4096


def starting_mask(width: int, height: int) -> Mask:
  """Proportional starting crop; device alignment still needs visual review."""
  if (width, height) not in CAMERA_FORMATS:
    raise ValueError("unsupported camera format")
  base = Mask.parse(DEFAULT_MASK)
  assert base is not None and base.center_left is not None and base.center_right is not None
  if (width, height) == CAMERA_FORMATS[0]:
    return base
  sx, sy = width / base.width, height / base.height
  document = {"width": width, "height": height, "crop_size": round(base.crop_size * min(sx, sy)),
              "center_left": [round(base.center_left[0] * sx), round(base.center_left[1] * sy)],
              "center_right": [round(base.center_right[0] * sx), round(base.center_right[1] * sy)]}
  mask = Mask.parse(document)
  assert mask is not None
  return mask


@dataclass(frozen=True)
class SavedPiP:
  values: tuple[tuple[str, bytes | None, bool], ...]
  enabled: bool | None
  mask: Mask | None
  on_blinker: bool | None
  on_bsm: bool | None
  invert: bool | None

  def source(self, key: str) -> tuple[bytes | None, bool]:
    return next((raw, readable) for name, raw, readable in self.values if name == key)


def _unique_pairs(pairs: list[tuple[str, object]]) -> dict[str, object]:
  result: dict[str, object] = {}
  for key, value in pairs:
    if key in result:
      raise ValueError("duplicate mask field")
    result[key] = value
  return result


def decode_mask(raw: bytes | None) -> Mask | None:
  if raw is None:
    return Mask.parse(DEFAULT_MASK)
  if len(raw) > MAX_MASK_BYTES:
    return None
  try:
    document = json.loads(raw, object_pairs_hook=_unique_pairs,
                          parse_constant=lambda _: (_ for _ in ()).throw(ValueError("nonfinite mask")))
    return Mask.parse(document)
  except (UnicodeDecodeError, ValueError, RecursionError, OverflowError, TypeError):
    return None


def encode_mask(mask: Mask) -> bytes:
  document = {"width": mask.width, "height": mask.height,
              "center_left": list(mask.center_left) if mask.center_left is not None else None,
              "center_right": list(mask.center_right) if mask.center_right is not None else None,
              "crop_size": mask.crop_size}
  if Mask.parse(document) != mask:
    raise ValueError("invalid PiP mask")
  encoded = json.dumps(document, separators=(",", ":"), allow_nan=False).encode()
  if len(encoded) > MAX_MASK_BYTES:
    raise ValueError("oversized PiP mask")
  return encoded


def read_pip(params) -> SavedPiP:
  values = tuple((key, *read_saved(params, key, MAX_MASK_BYTES if key == MASK else 16)) for key in KEYS)

  def boolean(key: str) -> bool | None:
    raw, readable = next((raw, readable) for name, raw, readable in values if name == key)
    if not readable:
      return None
    if raw is None or raw == b"0":
      return False
    if raw == b"1":
      return True
    return None

  mask_raw, mask_readable = next((raw, readable) for name, raw, readable in values if name == MASK)
  return SavedPiP(values, boolean(ENABLED), decode_mask(mask_raw) if mask_readable else None,
                  boolean(BLINKER), boolean(BSM), boolean(INVERT))
