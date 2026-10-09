"""Bitmap typography for the two device layouts, independent of application state."""

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
import hashlib
import json

import pyray as rl


class Profile(StrEnum):
  LARGE = "large"
  COMPACT = "compact"

  @property
  def size(self) -> tuple[int, int]:
    return (2160, 1080) if self == Profile.LARGE else (536, 240)

  @property
  def font_scale(self) -> float:
    return 1.242 if self == Profile.LARGE else 1.16


class FontRole(StrEnum):
  NORMAL = "normal"
  MEDIUM = "medium"
  BOLD = "bold"
  SEMI_BOLD = "semi_bold"
  BRAND = "brand"
  ROMAN = "roman"
  DISPLAY = "display"
  SPEED = "speed"
  FALLBACK = "fallback"


@dataclass(frozen=True)
class TextSize:
  width: float
  height: float


def font_filename(profile: Profile, role: FontRole) -> str:
  if role == FontRole.NORMAL:
    return "Inter-Regular.fnt" if profile == Profile.LARGE else "Inter-Medium.fnt"
  return {
    FontRole.MEDIUM: "Inter-Medium.fnt",
    FontRole.BOLD: "Inter-Bold.fnt",
    FontRole.SEMI_BOLD: "Inter-SemiBold.fnt",
    FontRole.BRAND: "Sora-800.fnt",
    FontRole.ROMAN: "Inter-Regular.fnt",
    FontRole.DISPLAY: "Inter-Bold.fnt",
    FontRole.SPEED: "DINish-Speed.fnt" if profile == Profile.LARGE else "Inter-Bold.fnt",
    FontRole.FALLBACK: "unifont.fnt",
  }[role]


def default_font_directory() -> Path:
  return Path(__file__).parent / "assets/fonts"


def font_path(directory: Path, filename: str) -> Path:
  # Keep the supplied Sora wordmark pinned to its bundled asset. The other
  # fonts use the bundled directory by default or a validated caller override.
  return default_font_directory() / filename if filename in ("Sora-800.fnt", "DINish-Speed.fnt") else directory / filename


def validate_bitmap_font(path: Path) -> None:
  """Accept only reviewed descriptor/atlas bytes before the native BMFont parser.

  This manifest pins appearance as well as parser inputs. Changing either file
  requires an explicit asset review; accepting a partial descriptor grammar is
  insufficient to protect the native parser from malformed input.
  """
  manifest_name = {"Sora-800.fnt": "sora-brand-font.json", "DINish-Speed.fnt": "dinish-speed-font.json"}.get(path.name, "bitmap-fonts.json")
  manifest = json.loads(Path(__file__).with_name(manifest_name).read_text())
  expected = {entry["file"]: entry for entry in manifest["files"]}
  try:
    if path.suffix != ".fnt" or path.name not in expected:
      raise ValueError("descriptor is not in the reviewed font manifest")
    for asset in (path, path.with_suffix(".png")):
      record = expected[asset.name]
      with asset.open("rb") as stream:
        data = stream.read(record["bytes"] + 1)
      if len(data) != record["bytes"] or hashlib.sha256(data).hexdigest() != record["sha256"]:
        raise ValueError(f"{asset.name} differs from the reviewed font manifest")
  except (OSError, KeyError, ValueError) as error:
    raise ValueError(f"Invalid bitmap font {path.name}: {error}") from error


class BitmapFonts:
  """Own font textures without changing global text APIs or loading device services.

  Construct after creating a native graphics context and close before destroying
  it. A caller chooses the fallback explicitly; the brand always retains its own
  glyphs. Raw draw calls avoid a second scale if an application installed its own
  text wrapper. Text containing emoji is outside this component's contract.
  """

  def __init__(self, profile: Profile, directory: Path, *, headless_context: bool = False):
    if not (rl.is_window_ready() or headless_context):
      raise RuntimeError("Bitmap fonts require an initialized graphics context")
    self._headless_context = headless_context
    self.profile = Profile(profile)
    self._fonts: dict[str, rl.Font] = {}
    self._measurements: dict[tuple, TextSize] = {}
    self._vertical_ink: dict[tuple, tuple[float, float]] = {}
    default_texture_id = rl.get_font_default().texture.id
    try:
      for filename in dict.fromkeys(font_filename(self.profile, role) for role in FontRole):
        path = font_path(directory, filename)
        if not path.is_file():
          raise FileNotFoundError(path)
        validate_bitmap_font(path)
        font = rl.load_font(str(path))
        # Failed font/atlas loads may return Raylib's shared default resource.
        # Never accept it as a requested bitmap or take ownership of its texture.
        if font.texture.id in (0, default_texture_id) or font.glyphCount == 0:
          raise RuntimeError(f"Unable to load bitmap font {filename}")
        self._fonts[filename] = font
        if filename != "unifont.fnt":
          rl.gen_texture_mipmaps(font.texture)
          rl.set_texture_filter(font.texture, rl.TextureFilter.TEXTURE_FILTER_TRILINEAR)
    except Exception:
      self.close()
      raise

  def font(self, role: FontRole, *, fallback: bool = False) -> rl.Font:
    if not self._fonts:
      raise RuntimeError("Bitmap font resources are closed")
    if fallback and role != FontRole.BRAND:
      role = FontRole.FALLBACK
    return self._fonts[font_filename(self.profile, role)]

  def measure(self, text: str, role: FontRole, size: float, *, spacing: float = 0, fallback: bool = False) -> TextSize:
    font = self.font(role, fallback=fallback)
    spacing = round(spacing, 4)
    key = font.texture.id, text, size, spacing
    if key not in self._measurements:
      measured = rl.measure_text_ex(font, text, size * self.profile.font_scale, spacing)  # noqa: TID251
      if len(self._measurements) >= 1024:
        self._measurements.clear()
      self._measurements[key] = TextSize(measured.x, measured.y)
    return self._measurements[key]

  def vertical_ink(self, text: str, role: FontRole, size: float) -> tuple[float, float]:
    """Visible glyph top/bottom, independent of the font's padded line box."""
    key = (text, role, size)
    if key not in self._vertical_ink:
      font = self.font(role)
      glyphs = [rl.get_glyph_index(font, ord(char)) for char in text if not char.isspace()]
      scale = size * self.profile.font_scale / font.baseSize
      top = min((font.glyphs[index].offsetY for index in glyphs), default=0)
      bottom = max((font.glyphs[index].offsetY + font.recs[index].height for index in glyphs), default=0)
      if len(self._vertical_ink) >= 1024:
        self._vertical_ink.clear()
      self._vertical_ink[key] = (top * scale, bottom * scale)
    return self._vertical_ink[key]

  def draw(self, text: str, role: FontRole, size: float, x: float, y: float, color: rl.Color = rl.WHITE,
           *, spacing: float = 0, fallback: bool = False) -> None:
    draw = getattr(rl, "_orig_draw_text_ex", rl.draw_text_ex)
    draw(self.font(role, fallback=fallback), text, rl.Vector2(x, y), size * self.profile.font_scale, spacing, color)

  def close(self) -> None:
    if rl.is_window_ready() or self._headless_context:
      for font in self._fonts.values():
        rl.unload_font(font)
    self._fonts.clear()
    self._vertical_ink.clear()
    self._measurements.clear()

  def __enter__(self):
    return self

  def __exit__(self, *_):
    self.close()
