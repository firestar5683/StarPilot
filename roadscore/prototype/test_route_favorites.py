import json
from pathlib import Path
import tempfile
import unittest
from route_favorites import resolve_favorite


class FavoriteTests(unittest.TestCase):
    def test_ids_do_not_require_alias_file(self):
        route = '0123456789abcdef/00000001--1234567890'
        self.assertEqual(resolve_favorite(route, '/missing'), (route, 0))

    def test_shortcut_keeps_route_and_excerpt_together(self):
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory) / 'favorites.json'
            route = '0123456789abcdef/00000001--1234567890'
            p.write_text(json.dumps({'route1': {'route': route, 'start': 149}}))
            self.assertEqual(resolve_favorite('route1', p), (route, 149))
            with self.assertRaisesRegex(ValueError, 'Unknown'):
                resolve_favorite('route2', p)
            p.write_text(json.dumps({'route1': {'route': route, 'start': -1}}))
            with self.assertRaisesRegex(ValueError, 'nonnegative'):
                resolve_favorite('route1', p)
