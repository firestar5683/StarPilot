"""Bake the pinned DINish numeric subset; runtime needs only the bitmap pair."""
from pathlib import Path
import hashlib
import json

from PIL import Image, ImageDraw, ImageFont


DIRECTORY = Path(__file__).parent / 'fonts'
GLYPHS = ' 0123456789+-.?–−'


def main():
  source = DIRECTORY / 'DINish-Medium.ttf'
  font = ImageFont.truetype(str(source), 177)
  records, x, y, row_height = [], 6, 6, 0
  for char in GLYPHS:
    left, top, right, bottom = font.getbbox(char, anchor='ls', features=['tnum'])
    width, height = max(1, right - left), max(1, bottom - top)
    if x + width + 6 > 512:
      x, y, row_height = 6, y + row_height + 8, 0
    records.append((char, x, y, width, height, left, top, round(font.getlength(char, features=['tnum']))))
    x, row_height = x + width + 8, max(row_height, height)
  assert y + row_height + 6 <= 512
  assert len({record[-1] for record in records if record[0].isdigit()}) == 1
  atlas = Image.new('RGBA', (512, 512), (255, 255, 255, 0))
  for char, x, y, width, height, left, top, _ in records:
    mask = Image.new('L', (width, height))
    ImageDraw.Draw(mask).text((-left, -top), char, font=font, anchor='ls', fill=255, features=['tnum'])
    glyph = Image.new('RGBA', mask.size, 'white')
    glyph.putalpha(mask)
    atlas.paste(glyph, (x, y))
  atlas.save(DIRECTORY / 'DINish-Speed.png')
  lines = ['info face="DINish-Speed" size=-200 bold=0 italic=0 charset="" unicode=1 stretchH=100 smooth=1 aa=1 padding=0,0,0,0 spacing=0,0 outline=0',
           'common lineHeight=200 base=200 scaleW=512 scaleH=512 pages=1 packed=0 alphaChnl=0 redChnl=4 greenChnl=4 blueChnl=4',
           'page id=0 file="DINish-Speed.png"', f'chars count={len(records)}']
  lines.extend(f'char id={ord(char)} x={x} y={y} width={width} height={height} xoffset={left} yoffset={160 + top} xadvance={advance} page=0 chnl=15'
               for char, x, y, width, height, left, top, advance in records)
  (DIRECTORY / 'DINish-Speed.fnt').write_text('\n'.join(lines) + '\n')
  def record(path):
    data = path.read_bytes()
    return {'file': path.name, 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
  manifest = {'format': 1, 'source': {**record(source), 'url': 'https://github.com/playbeing/dinish/blob/main/fonts/ttf/DINish/DINish-Medium.ttf'},
              'generation': {'font_pixels': 177, 'bitmap_base': 200, 'baseline': 160, 'glyphs': GLYPHS, 'features': ['tnum'],
                             'atlas': [512, 512], 'notice': 'fonts/notices/DINish-OFL-1.1.txt'},
              'files': [record(DIRECTORY / name) for name in ('DINish-Speed.fnt', 'DINish-Speed.png')]}
  DIRECTORY.parents[1].joinpath('dinish-speed-font.json').write_text(json.dumps(manifest, indent=2) + '\n')


if __name__ == '__main__':
  main()
