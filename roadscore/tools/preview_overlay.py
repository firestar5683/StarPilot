"""Render synthetic overlay states with the repo's font atlas, entirely on CPU.

Requires Pillow. No device, network, audio, replay, worker, or window is opened.
"""
import argparse
import re
import sys
from pathlib import Path
from types import SimpleNamespace

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'roadscore/prototype'))
from overlay_view import draw_panel


class Canvas:
  WHITE = (255, 255, 255, 255)
  Color = staticmethod(lambda *rgba: rgba)
  Rectangle = staticmethod(lambda x, y, w, h: (x, y, x + w, y + h))
  Vector2 = staticmethod(lambda x, y: SimpleNamespace(x=x, y=y))

  def __init__(self, image, font_path):
    self.image = image
    self.atlas = Image.open(font_path.with_suffix('.png')).convert('RGBA')
    lines = font_path.read_text().splitlines()
    self.base = abs(int(re.search(r'size=(-?\d+)', lines[0])[1]))
    self.glyphs = {}
    for line in lines:
      if line.startswith('char '):
        glyph = {key: int(value) for key, value in re.findall(r'(\w+)=(-?\d+)', line)}
        self.glyphs[glyph['id']] = glyph

  def measure_text_ex(self, font, text, size, spacing):
    return SimpleNamespace(x=sum(self.glyphs[ord(c)]['xadvance'] for c in text) * size / self.base)

  def draw_text_ex(self, font, text, pos, size, spacing, color):
    scale = size / self.base
    for char in text:
      g = self.glyphs[ord(char)]
      if g['width'] and g['height']:
        mask = self.atlas.crop((g['x'], g['y'], g['x'] + g['width'], g['y'] + g['height'])).getchannel('A')
        mask = mask.resize((max(1, round(g['width'] * scale)), max(1, round(g['height'] * scale))))
        ink = Image.new('RGBA', mask.size, color)
        self.image.paste(ink, (round(pos.x + g['xoffset'] * scale), round(pos.y + g['yoffset'] * scale)), mask)
      pos.x += g['xadvance'] * scale

  def draw_rectangle_rounded(self, rect, roundness, segments, color):
    layer = Image.new('RGBA', self.image.size)
    ImageDraw.Draw(layer).rounded_rectangle(rect, radius=6, fill=color)
    self.image.alpha_composite(layer)

  def draw_circle(self, x, y, radius, color):
    ImageDraw.Draw(self.image).ellipse((x-radius, y-radius, x+radius, y+radius), fill=color)


def main():
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument('--output', type=Path, required=True)
  args = parser.parse_args()
  base = dict(composer='ace', style='Prism', readiness='READY', section='VERSE / CONTINUOUS',
              next_section='PRECHORUS', form_labels_are_intent=True, buffered=64)
  cases = [{}, base, dict(base, job_inflight=True, generation_elapsed_seconds=23.4, turn_signal_music=True),
           dict(base, readiness='DEGRADED', holding_accepted_music=True, job_inflight=True, buffered=18),
           dict(base, worker_failed=True, buffered=0),
           dict(readiness='READY', style='Stored score', section='ARCHIVED SCORE', compute='none', buffered=92)]
  board = Image.new('RGBA', (728, 564), '#080e16')
  for index, state in enumerate(cases):
    panel = Image.new('RGBA', (364, 188), '#080e16')
    draw_panel(Canvas(panel, ROOT / 'selfdrive/assets/fonts/Inter-Medium.fnt'), None, state, 364, 176)
    board.paste(panel, ((index % 2) * 364, (index // 2) * 188))
  args.output.parent.mkdir(parents=True, exist_ok=True)
  board.convert('RGB').save(args.output)
  print(args.output)


if __name__ == '__main__':
  main()
