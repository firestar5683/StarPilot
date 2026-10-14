from types import SimpleNamespace
import pytest
from openpilot.starpilot.flm.adaptive_profile import ApplicationOutcome
from openpilot.starpilot.flm.learned_lifecycle import decode, display, historical, remember, reset_scope


def profile(identity='a' * 64):
  parameter = SimpleNamespace(name='gain', stage_revision='actual-stage-v1', low=-0.1, high=0.1, max_step=0.1)
  return SimpleNamespace(identity=identity, policy='passive_stage_ridge_v1', parameters=(parameter,), coefficients=(0.02,))


def test_scoped_history_and_reset_do_not_create_receipt():
  first, second = profile(), profile('b' * 64)
  raw = remember(None, first, reset='generation1', validation_sha256='c' * 64)
  raw = remember(raw, second, reset='generation1', validation_sha256='d' * 64)
  assert historical(raw, identity=first.identity, parameters=first.parameters, reset='generation1') == (0.02,)
  assert historical(raw, identity=first.identity, parameters=first.parameters, reset='generation2') is None
  raw = reset_scope(raw, first.identity)
  assert historical(raw, identity=first.identity, parameters=first.parameters, reset='generation1') is None
  assert historical(raw, identity=second.identity, parameters=second.parameters, reset='generation1') == (0.02,)
  assert 'expires_ns' not in next(iter(decode(raw)['profiles'].values()))


@pytest.mark.parametrize('raw', [b'{"version":1,"version":1,"profiles":{}}', b'{"version":true,"profiles":{}}', b'x' * 32769])
def test_corrupt_document_refused(raw):
  with pytest.raises(ValueError):
    decode(raw)


def test_applied_status_requires_current_actual_outcome():
  args = {'identity': 'a' * 64, 'now_ns': 100, 'enabled': True, 'manual': False, 'eligible': True, 'active': True, 'healthy': True}
  assert display(**args, collecting=True)[0] == 'collecting'
  application = ApplicationOutcome('a' * 64, 1, 90, 'applied', (0.02,), 'actual_stage', 'baseline-v1', 'physical-v1')
  assert display(**args, application=application)[0] == 'applied'
  for change in (
    {'now_ns': 500_000_091},
    {'manual': True},
    {'enabled': False},
    {'eligible': False},
    {'active': False},
    {'healthy': False},
    {'identity': 'b' * 64},
  ):
    assert display(**(args | change), application=application)[0] == 'paused'


def test_multiple_objectives_keep_distinct_priors_and_exact_stage_binding():
  first = profile()
  second = profile()
  second.parameters = (SimpleNamespace(name='center', stage_revision='center-v1', low=-0.1, high=0.1, max_step=0.1),)
  second.coefficients = (0.03,)
  raw = remember(None, first, reset='generation1', validation_sha256='c' * 64)
  raw = remember(raw, second, reset='generation1', validation_sha256='d' * 64)
  assert len(decode(raw)['profiles']) == 2
  assert historical(raw, identity=first.identity, parameters=first.parameters, reset='generation1') == (0.02,)
  assert historical(raw, identity=second.identity, parameters=second.parameters, reset='generation1') == (0.03,)
  wrong = (SimpleNamespace(name='center', stage_revision='center-v2', low=-0.1, high=0.1, max_step=0.1),)
  assert historical(raw, identity=second.identity, parameters=wrong, reset='generation1') is None
  assert decode(reset_scope(raw, first.identity))['profiles'] == {}
