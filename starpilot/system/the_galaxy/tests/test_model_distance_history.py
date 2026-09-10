"""Pure aggregation tests; no native imports, Params, or device writes."""
import ast
import copy
import math
from pathlib import Path
import re
import unittest

SOURCE = Path(__file__).resolve().parents[1] / 'utilities.py'
NAMES = {'_build_model_distances', '_model_usage_key', '_clean_model_label'}
namespace = {'math': math, 're': re,
             'canonical_model_key': lambda value: str(value or '').strip(),
             '_dashboard_time_is_valid': lambda value: value == 'valid'}
tree = ast.parse(SOURCE.read_text())
exec(compile(ast.Module(body=[node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in NAMES], type_ignores=[]), str(SOURCE), 'exec'), namespace)
aggregate = namespace['_build_model_distances']


def route(key='a', distance=1000, **overrides):
  return dict(dict(modelKey=key, model=key.upper(), distanceMeters=distance,
                   date='valid', analysisComplete=True), **overrides)


class ModelDistanceHistoryTests(unittest.TestCase):
  def test_legacy_routes_need_no_model_tracker(self):
    self.assertEqual(aggregate({'routes': {'r': route()}}),
                     [{'key': 'a', 'name': 'A', 'distanceMeters': 1000, 'drives': 1}])

  def test_aggregate_once_per_retained_route(self):
    data = {'routes': {'a1': route(), 'a2': route(distance=2000), 'b1': route('b', 4000)},
            'modelUsage': {'a': {'drives': 99}}, 'stats': {'assistedMeters': 9000}}
    before = copy.deepcopy(data)
    rows = aggregate(data)
    self.assertEqual([(r['key'], r['distanceMeters'], r['drives']) for r in rows], [('b', 4000, 1), ('a', 3000, 2)])
    self.assertEqual(data, before)
    self.assertTrue(all('interventions' not in row and 'assistedMeters' not in row for row in rows))

  def test_excluded_pending_and_invalid_dates(self):
    data = {'routes': {'ignored': route(), 'pending': route(analysisComplete=False),
                       'bad_date': route(date='invalid'), 'valid': route()}, 'ignoredRoutes': ['ignored']}
    self.assertEqual(aggregate(data)[0]['drives'], 1)

  def test_reject_invalid_distances(self):
    for distance in [None, -1, 0, True, '10', math.inf, math.nan]:
      with self.subTest(distance=distance):
        self.assertEqual(aggregate({'routes': {'r': route(distance=distance)}}), [])

  def test_fallback_name_and_unknown_model(self):
    self.assertEqual(aggregate({'routes': {'r': route('', model='Legacy Model')}})[0]['key'], 'legacy-model')
    self.assertEqual(aggregate({'routes': {'r': route('', model='Unknown model')}}), [])

  def test_no_top_three_by_count_preselection(self):
    rows = aggregate({'routes': {str(n): route(str(n), n + 1) for n in range(6)}})
    self.assertEqual([r['key'] for r in rows], ['5', '4', '3', '2', '1', '0'])

  def test_empty_and_malformed_documents(self):
    for data in [None, [], {}, {'routes': []}, {'routes': {'bad': None}}]:
      self.assertEqual(aggregate(data), [])

  def test_distance_field_exposed_in_both_dashboard_paths(self):
    self.assertEqual(SOURCE.read_text().count('"modelDistances": _build_model_distances(persistent_stats)'), 2)


if __name__ == '__main__':
  unittest.main()
