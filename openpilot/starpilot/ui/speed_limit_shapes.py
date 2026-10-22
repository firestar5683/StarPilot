"""One cached atlas for joined arrows and antialiased speed-limit sign edges."""

from pathlib import Path

import pyray as rl


ATLAS_PATH = Path(__file__).with_name('assets') / 'speed_limit_shapes.png'
ATLAS_SIZE = (256, 176)
SPRITES = {
  'disc': (0, 0, 128, 128), 'ring': (128, 0, 128, 128),
  'arrow_large': (0, 128, 32, 40), 'arrow_compact': (32, 128, 16, 24),
}


class SpeedLimitShapes:
  def __init__(self, scale=1, *, headless_context=False):
    self.scale = scale
    self._headless_context = headless_context
    self.texture = None
    self.sources = {name: rl.Rectangle(*rect) for name, rect in SPRITES.items()}
    self.origins = {name: rl.Vector2(rect[2] * scale / 2, rect[3] * scale / 2) for name, rect in SPRITES.items()}

  def _load(self):
    if self.texture is not None:
      return
    if not (rl.is_window_ready() or self._headless_context):
      raise RuntimeError('Speed-limit shapes require a graphics context')
    image = rl.load_image(str(ATLAS_PATH))
    try:
      if image.data == rl.ffi.NULL or (image.width, image.height) != ATLAS_SIZE:
        raise ValueError('Invalid speed-limit shape atlas')
      self.texture = rl.load_texture_from_image(image)
      if not self.texture.id:
        self.texture = None
        raise RuntimeError('Unable to upload speed-limit shapes')
      rl.set_texture_filter(self.texture, rl.TextureFilter.TEXTURE_FILTER_BILINEAR)
      rl.set_texture_wrap(self.texture, rl.TextureWrap.TEXTURE_WRAP_CLAMP)
    except BaseException:
      self.close()
      raise
    finally:
      if image.data != rl.ffi.NULL:
        rl.unload_image(image)

  def _draw(self, name, x, y, color, rotation=0):
    self._load()
    source = self.sources[name]
    rl.draw_texture_pro(self.texture, source, rl.Rectangle(x, y, source.width * self.scale, source.height * self.scale),
                        self.origins[name], rotation, color)

  def circle(self, x, y, color):
    self._draw('disc', x, y, rl.WHITE)
    self._draw('ring', x, y, color)

  def arrow(self, size, x, y, direction, color):
    self._draw('arrow_large' if size == 'large' else 'arrow_compact', x, y, color, 180 if direction < 0 else 0)

  def close(self):
    if self.texture is not None and (rl.is_window_ready() or self._headless_context):
      rl.unload_texture(self.texture)
    self.texture = None
