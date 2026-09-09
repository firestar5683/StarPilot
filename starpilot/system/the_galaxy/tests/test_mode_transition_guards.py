"""Mode writes stop immediately when safety/road-state eligibility changes."""
import pytest

from test_longitudinal_mode import Params, mode


@pytest.mark.parametrize('after_write', [1, 2, 3])
@pytest.mark.parametrize('key,value', [('IsOnroad', True), ('IsOffroad', False), ('SafeMode', True)])
def test_guard_transition_during_write_stops_further_writes(after_write, key, value):
  params = Params()
  original_put = params.put_bool
  def put(name, enabled):
    original_put(name, enabled)
    if len(params.writes) == after_write:
      params.values[key] = value
  params.put_bool = put
  with pytest.raises(mode.ModeError):
    mode.set_mode(params, 'experimental', params.values.copy(), lambda: True, acknowledged=True)
  assert len(params.writes) == after_write
  assert mode.selected_mode(params.values) in {'conditional_experimental', 'experimental'}


def test_multi_key_write_boundaries_never_expose_intermediate_chill():
  # Target first: partial failure cannot select an unrelated stored mode.
  params = Params({'ConditionalExperimental': True, 'ConditionalChill': False, 'ExperimentalMode': False})
  observed = []
  original_put = params.put_bool
  def put(name, enabled):
    original_put(name, enabled)
    observed.append(mode.selected_mode({key: params.get_bool(key) for key in mode.MODE_KEYS}))
  params.put_bool = put
  mode.set_mode(params, 'conditional_chill', params.values.copy(), lambda: True)
  assert observed == ['conditional_experimental', 'conditional_chill', 'conditional_chill']
