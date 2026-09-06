"""Host-only evidence for residual nonparticipating readers/writers.

Execute the actual runtime selector functions/assignments via AST, without
importing native Params or starting services. Legacy UI readers and external
Dom writers still don't share the adapter lock. They cannot gain atomicity from
write ordering. Driving handoff coverage is in test_coherent_mode_handoff.py.
"""
import ast
from itertools import combinations_with_replacement, permutations, product
from pathlib import Path
from types import SimpleNamespace

import pytest

from test_longitudinal_mode import Params, mode
from openpilot.starpilot.common.longitudinal_mode import read_mode_values

ROOT = Path(__file__).resolve().parents[4]


def runtime_requested():
  path = ROOT / 'starpilot/common/experimental_state.py'
  tree = ast.parse(path.read_text())
  # Future annotations make Params only a type annotation. Do not import it.
  tree.body = [node for node in tree.body if not (
    isinstance(node, ast.ImportFrom) and node.module == 'openpilot.common.params')]
  namespace = {}
  exec(compile(tree, str(path), 'exec'), namespace)
  return namespace['requested_experimental_mode']


REQUESTED = runtime_requested()


def runtime_toggles(params):
  path = ROOT / 'starpilot/common/starpilot_variables.py'
  tree = ast.parse(path.read_text())
  names = {'conditional_experimental_mode', 'conditional_chill_mode'}
  nodes = [node for node in ast.walk(tree) if isinstance(node, ast.Assign)
           and len(node.targets) == 1 and isinstance(node.targets[0], ast.Attribute)
           and isinstance(node.targets[0].value, ast.Name)
           and node.targets[0].value.id == 'toggle' and node.targets[0].attr in names]
  assert len(nodes) == 2
  nodes.sort(key=lambda node: node.lineno)
  toggle = SimpleNamespace(openpilot_longitudinal=True, safe_mode=False)
  selection = ast.Module(body=[], type_ignores=[])
  first = next(node for node in ast.walk(tree) if isinstance(node, ast.Assign)
               and isinstance(node.targets[0], ast.Name) and node.targets[0].id == 'mode_values')
  selection.body.extend([first, *nodes])
  exec(compile(selection, str(path), 'exec'),
       {'toggle': toggle, 'self': SimpleNamespace(params=params), 'read_mode_values': read_mode_values})
  return toggle


class InterleavedParams(Params):
  def __init__(self, values, writes, schedule, manual=True):
    super().__init__(values)
    self.pending = list(writes)
    self.schedule = iter(schedule)
    self.applied = 0
    self.trace = []
    self.manual = manual

  def get_bool(self, key):
    if key in mode.MODE_KEYS:
      until = next(self.schedule, self.applied)
      while self.applied < until:
        name, enabled = self.pending[self.applied]
        self.values[name] = enabled
        self.applied += 1
      self.trace.append((key, self.values[key]))
    return super().get_bool(key)

  def get_int(self, key, default=0):
    # Both conditional modes request EXP for this manual override fixture.
    return {'PersistedCEStatus': 2, 'PersistedCCStatus': 1}.get(key, default) if self.manual else default


def observed_branch(params):
  for key, enabled in params.trace:
    if enabled:
      return next(name for name, value in mode.MODES.items() if value == key)
  return 'chill'


def outcomes(values, writes):
  result = set()
  # Reader visits at most three mode keys. Include every relative placement
  # of the ordered writer operations before/between those reads.
  for schedule in combinations_with_replacement(range(len(writes) + 1), 3):
    params = InterleavedParams(values, writes, schedule)
    REQUESTED(params)
    result.add(observed_branch(params))
  return result


@pytest.mark.parametrize('bits', list(product([False, True], repeat=3)))
@pytest.mark.parametrize('target', list(mode.MODES))
def test_adapter_cannot_protect_nonparticipating_ui_readers(bits, target):
  params = Params(dict(zip(mode.MODE_KEYS, bits)))
  before = params.values.copy()
  old = mode.selected_mode(before)
  result = mode.set_mode(params, target, before, lambda: True)
  seen = outcomes(before, params.writes)
  assert result['mode'] == target
  if old == target:
    assert not params.writes
    assert seen == {old}
  else:
    assert old in seen and target in seen
    # Nonparticipating legacy readers may still observe ordinary fallback;
    # the exact torn-read counterexample below is retained, not concealed.
    assert seen <= {old, target, 'chill', 'experimental'}


@pytest.mark.parametrize('writes', list(permutations([
  ('ConditionalExperimental', True), ('ConditionalChill', False)])))
def test_no_order_of_required_ccm_to_cem_writes_fixes_runtime_reader(writes):
  values = {'ConditionalExperimental': False, 'ConditionalChill': True, 'ExperimentalMode': False}
  assert outcomes(values, writes) == {'conditional_experimental', 'conditional_chill', 'chill'}


def test_dom_target_first_is_coherent_at_write_boundaries_but_not_between_reads():
  values = {'ConditionalExperimental': False, 'ConditionalChill': True, 'ExperimentalMode': False}
  writes = [('ConditionalExperimental', True), ('ConditionalChill', False)]
  params = Params(values)
  stored = [mode.selected_mode(params.values)]
  for key, value in writes:
    params.put_bool(key, value)
    stored.append(mode.selected_mode(params.values))
  assert stored == ['conditional_chill', 'conditional_experimental', 'conditional_experimental']
  # CEM read before both writes, CCM and EXP after both writes: a branch which
  # never existed in storage. Manual EXP in both endpoints becomes false.
  params = InterleavedParams(values, writes, [0, 2, 2])
  assert REQUESTED(params) is False
  assert observed_branch(params) == 'chill'
  for endpoint in [values, params.values]:
    assert REQUESTED(InterleavedParams(endpoint, [], [])) is True


def test_nonparticipating_writer_can_still_tear_a_shared_reader():
  params = InterleavedParams(
    {'ConditionalExperimental': True, 'ConditionalChill': False, 'ExperimentalMode': False},
    [('ConditionalChill', True), ('ConditionalExperimental', False)], [0, 0, 2])
  toggles = runtime_toggles(params)
  assert not toggles.conditional_experimental_mode
  assert not toggles.conditional_chill_mode
  assert mode.selected_mode(params.values) == 'conditional_chill'


def test_upstream_manual_and_default_semantics_are_not_aliases():
  cem = {'ConditionalExperimental': True, 'ConditionalChill': False, 'ExperimentalMode': True}
  ccm = {'ConditionalExperimental': False, 'ConditionalChill': True, 'ExperimentalMode': False}
  assert REQUESTED(InterleavedParams(cem, [], [], manual=False)) is False
  assert REQUESTED(InterleavedParams(ccm, [], [], manual=False)) is True
  assert REQUESTED(InterleavedParams(cem, [], [], manual=True)) is True
  assert REQUESTED(InterleavedParams({**ccm, 'SafeMode': True}, [], [], manual=True)) is False
