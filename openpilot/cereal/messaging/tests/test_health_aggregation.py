"""Health aggregation is fresh and preserves lookup and exception ordering."""
import random
import unittest

from openpilot.cereal.messaging import SubMaster
from openpilot.cereal.services import SERVICE_LIST

SERVICES = ['carState', 'deviceState', 'carParams']
METHODS = ('all_alive', 'all_freq_ok', 'all_valid', 'all_checks')


class Reference:
  def _check_avg_freq(self, s):
    return SERVICE_LIST[s].frequency > 0.99 and (s not in self.ignore_average_freq) and (s not in self.ignore_alive)

  def all_alive(self, service_list=None):
    return all(self.alive[s] for s in (service_list or self.services) if s not in self.ignore_alive)

  def all_freq_ok(self, service_list=None):
    return all(self.freq_ok[s] for s in (service_list or self.services) if self._check_avg_freq(s))

  def all_valid(self, service_list=None):
    return all(self.valid[s] for s in (service_list or self.services) if s not in self.ignore_valid)

  def all_checks(self, service_list=None):
    return self.all_alive(service_list) and self.all_freq_ok(service_list) and self.all_valid(service_list)


def host(kind, seed=0):
  obj, rng = kind.__new__(kind), random.Random(seed)
  obj.services, obj.events = SERVICES[:], []
  for name in ('alive', 'freq_ok', 'valid'):
    setattr(obj, name, {s: bool(rng.getrandbits(1)) for s in SERVICES})
  for name in ('ignore_alive', 'ignore_average_freq', 'ignore_valid'):
    setattr(obj, name, [s for s in SERVICES if rng.randrange(4) == 0])
  return obj


def outcome(obj, method, selected):
  try:
    return getattr(obj, method)(selected), obj.events
  except Exception as exc:
    return (type(exc).__name__, str(exc), type(exc.__cause__).__name__, exc.__suppress_context__), obj.events


def traced(kind, fail=None, error=KeyError, first_false=False):
  obj = host(kind)
  def touch(operation, key):
    obj.events.append((operation, key))
    if operation == fail and key == 'deviceState':
      raise error('probe')
  class Truth:
    def __init__(self, key): self.key = key
    def __bool__(self):
      touch('truth', self.key)
      return not (first_false and self.key == 'carState')
  class Mapping(dict):
    def __getitem__(self, key):
      touch('get', key)
      return super().__getitem__(key)
  class Ignored(list):
    def __contains__(self, key):
      touch('contains', key)
      return super().__contains__(key)
  for name in ('alive', 'freq_ok', 'valid'):
    setattr(obj, name, Mapping({s: Truth(s) for s in SERVICES}))
  for name in ('ignore_alive', 'ignore_average_freq', 'ignore_valid'):
    setattr(obj, name, Ignored())
  return obj


class TestHealthAggregation(unittest.TestCase):
  def test_deterministic_maps_selection_ignores_and_mutation(self):
    for seed in range(16):
      for selected in (None, [], SERVICES[:2], [SERVICES[0], SERVICES[0]]):
        a, b = host(SubMaster, seed), host(Reference, seed)
        for method in METHODS:
          self.assertEqual(outcome(a, method, selected), outcome(b, method, selected))
          for name in ('alive', 'freq_ok', 'valid'):
            getattr(a, name)['carState'] = not getattr(a, name)['carState']
            getattr(b, name)['carState'] = not getattr(b, name)['carState']
          self.assertEqual(outcome(a, method, selected), outcome(b, method, selected))

  def test_custom_lookup_truth_membership_and_first_failure_order(self):
    for fail in (None, 'get', 'contains', 'truth'):
      for error in (KeyError, StopIteration):
        for first_false in (False, True):
          for method in METHODS:
            a, b = (traced(kind, fail, error, first_false) for kind in (SubMaster, Reference))
            self.assertEqual(outcome(a, method, None), outcome(b, method, None))
    for method in METHODS:
      self.assertEqual(outcome(traced(SubMaster), method, ['unknown']), outcome(traced(Reference), method, ['unknown']))

  def test_selection_stopiteration_stays_outside_generator(self):
    class TruthRaises(list):
      def __bool__(self): raise StopIteration('selection truth')
    class IterRaises(list):
      def __iter__(self): raise StopIteration('selection iter')
    for selected in (TruthRaises(SERVICES), IterRaises(SERVICES)):
      for method in METHODS:
        self.assertEqual(outcome(host(SubMaster), method, selected), outcome(host(Reference), method, selected))

  def test_ephemeral_truthy_value_is_released_before_next_lookup(self):
    def factory(kind):
      obj = host(kind)
      class Ephemeral:
        def __init__(self, key): self.key = key
        def __bool__(self):
          obj.events.append(('truth', self.key))
          return True
        def __del__(self):
          obj.events.append(('del', self.key))
      class Mapping:
        def __getitem__(self, key):
          obj.events.append(('get', key))
          return Ephemeral(key)
      for name in ('alive', 'freq_ok', 'valid'):
        setattr(obj, name, Mapping())
      for name in ('ignore_alive', 'ignore_average_freq', 'ignore_valid'):
        setattr(obj, name, [])
      return obj
    for method in METHODS:
      a, b = factory(SubMaster), factory(Reference)
      self.assertEqual(outcome(a, method, None), outcome(b, method, None))
      self.assertEqual(a.events[:6], [('get', 'carState'), ('truth', 'carState'), ('del', 'carState'),
                                     ('get', 'deviceState'), ('truth', 'deviceState'), ('del', 'deviceState')])

  def test_all_checks_retains_subclass_dispatch_and_short_circuit(self):
    selected = SERVICES[:1]
    for stop in range(4):
      results = []
      for base in (SubMaster, Reference):
        def override(index, stop=stop):
          def call(obj, services):
            obj.events.append((METHODS[index], services is selected))
            return index != stop
          return call
        cls = type('Overridden', (base,), {name: override(i) for i, name in enumerate(METHODS[:3])})
        results.append(outcome(host(cls), 'all_checks', selected))
      self.assertEqual(*results)


if __name__ == '__main__':
  unittest.main()
