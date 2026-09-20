"""Local saved-demo registry. Entries identify original core audio and route assets."""
import json
import re
from pathlib import Path


def entry(root, alias):
  root = Path(root)
  if not isinstance(alias, str) or not re.fullmatch(r'route[1-9][0-9]*', alias):
    raise ValueError('Choose a registered demo route alias')
  path = root / 'assets/demo_catalog.json'
  try:
    catalog = json.loads(path.read_text())
  except (OSError, ValueError) as error:
    raise ValueError('Saved demo catalog is unavailable') from error
  if catalog.get('version') != 1 or not isinstance(catalog.get('routes'), dict):
    raise ValueError('Unsupported saved demo catalog')
  item = catalog['routes'].get(alias)
  if not isinstance(item, dict) or item.get('ready') is not True:
    raise ValueError(f'{alias} has not been prepared as a saved demo')
  if not isinstance(item.get('route'), str) or not item['route']:
    raise ValueError('Saved demo is missing its route identity')
  result = {**item, 'alias': alias}
  for key in ('archive', 'curve_plan'):
    value = item.get(key)
    if key == 'curve_plan' and value is None:
      continue
    if not isinstance(value, str) or not value:
      raise ValueError('Saved demo is missing its core archive')
    asset = Path(value)
    result[key] = str((asset if asset.is_absolute() else root / asset).resolve())
    if not Path(result[key]).exists():
      raise ValueError(f'Saved demo asset is missing: {key}')
  return result
