import json
from pathlib import Path


ASSETS = Path(__file__).parent / 'assets/navigation'
MANIFEST = {row['file']: row for row in json.loads(Path(__file__).with_name('navigation-assets.json').read_text())['files']}


def icon_name(maneuver_type: str, modifier: str) -> str:
  kind = {'rotary': 'roundabout', 'new name': 'turn', 'continue': 'turn'}.get(maneuver_type, maneuver_type).replace(' ', '_')
  suffix = {'slightLeft': 'slight_left', 'slightRight': 'slight_right', 'sharpLeft': 'sharp_left',
            'sharpRight': 'sharp_right'}.get(modifier, modifier).replace(' ', '_')
  candidate = 'direction_uturn.png' if suffix == 'uturn' else f'direction_{kind}{"_" + suffix if suffix else ""}.png'
  return candidate if candidate in MANIFEST else 'direction_turn_straight.png'
