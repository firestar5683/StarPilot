"""Local route shortcuts; private route identities stay out of source control."""
import json
from pathlib import Path


def resolve_favorite(value, path=None):
    path = Path(path) if path else Path(__file__).resolve().parents[1] / 'routes/favorites.json'
    if '/' in value or '|' in value:
        return value, 0
    if not path.is_file():
        raise ValueError(f'Unknown route shortcut {value!r}; configure {path}')
    favorites = json.loads(path.read_text())
    entry = favorites.get(value)
    if not isinstance(entry, dict):
        raise ValueError(f'Unknown route shortcut {value!r}; available: {", ".join(sorted(favorites))}')
    from route_library import identity
    route = entry['route']
    identity(route)
    start = entry.get('start', 0)
    if type(start) is not int or start < 0:
        raise ValueError('Favorite start must be nonnegative whole seconds')
    return route, start
