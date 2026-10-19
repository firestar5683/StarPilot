"""Immutable bounded caches preserve original digest and reject mutated maps."""

from collections.abc import MutableMapping
from typing import cast

import hashlib
from unittest.mock import patch
import pytest
from openpilot.starpilot.flm import canonical_surface_adapter as a
from openpilot.starpilot.flm import torque_surface as source


def zero():
  return dict.fromkeys(a.NAMES, 0.0)


def expected_anchor(base):
  original = tuple((name, float(source._GM_NEUTRAL[name])) for name in a.NAMES)
  return hashlib.sha256(repr((a.MANIFEST_SHA256, base, original)).encode()).hexdigest()


def test_anchors_and_fullmap_wire_digest_exactly_preserved_after_warm_cache():
  for base in ('a' * 64, 'b' * 64):
    for value in (0.0, -0.0, 0.005, -0.005):
      full = zero()
      full['ff_gain_left'] = value
      original = expected_anchor(base)
      expected = hashlib.sha256(repr((original, tuple((n, float(full[n])) for n in a.NAMES))).encode()).hexdigest()
      for _ in range(3):
        assert a.full_original_anchor(base) == original
        assert a.full_profile_sha256(base, full) == expected
        assert a.original_anchor(base, ('ff_gain_left',)) == hashlib.sha256(repr((original, ('ff_gain_left',))).encode()).hexdigest()


def test_mutable_dictionary_changes_cannot_reuse_a_previously_valid_digest():
  full = zero()
  first = a.full_profile_sha256('a' * 64, full)
  full['ff_gain_left'] = 0.005
  second = a.full_profile_sha256('a' * 64, full)
  assert first != second
  for bad in (True, float('nan'), float('inf'), 0.251):
    full['ff_gain_left'] = bad
    with pytest.raises(ValueError):
      a.full_profile_sha256('a' * 64, full)
  full['ff_gain_left'] = 0.005
  assert a.full_profile_sha256('a' * 64, full) == second
  del full['ff_gain_right']
  with pytest.raises(ValueError):
    a.full_profile_sha256('a' * 64, full)


def test_signed_zero_is_distinct_in_exact_wire_digest_even_when_python_tuple_equal():
  first = zero()
  second = zero()
  second['ff_gain_left'] = -0.0
  assert first == second
  assert a.full_profile_sha256('a' * 64, first) != a.full_profile_sha256('a' * 64, second)


def test_cached_inputs_never_skip_original_type_validation():
  a.full_original_anchor('a' * 64)
  for bad in (b'a' * 64, 'a' * 63, None, True):
    with pytest.raises(ValueError):
      a.full_original_anchor(bad)
  a.parameters_for(('ff_gain_left',))
  with pytest.raises(ValueError):
    a.parameters_for(('STEER_MAX',))
  with pytest.raises(ValueError):
    a.parameters_for(('ff_gain_left', 'ff_gain_left'))
  with pytest.raises(ValueError):
    a.full_profile_sha256('a' * 64, zero() | {'STEER_MAX': 0.0})


def test_immutable_parameter_tuple_cache_and_fixed_bounds():
  first = a.parameters_for(('ff_gain_left', 'turn_in_boost_left'))
  second = a.parameters_for(('ff_gain_left', 'turn_in_boost_left'))
  assert first is second
  with pytest.raises((AttributeError, TypeError)):
    first[0].high = 0.9
  with pytest.raises(TypeError):
    cast(MutableMapping[str, tuple[float, float]], a._COORDINATE_BOUNDS)['center_taper_max'] = (0.0, 0.9)
  assert a.coordinate_bounds('center_taper_max') == (0.0, 0.18)


def test_caches_are_bounded_and_source_manifest_changes_invalidate_identity():
  assert a._full_original_anchor_cached.cache_info().maxsize == 32
  assert a._original_anchor_cached.cache_info().maxsize == 32
  assert a._parameters_for_cached.cache_info().maxsize == 64
  assert a._full_profile_sha256_cached.cache_info().maxsize == 128
  before = a.full_original_anchor('a' * 64)
  with patch.object(a, 'MANIFEST_SHA256', 'f' * 64):
    assert a.full_original_anchor('a' * 64) != before
  assert a.full_original_anchor('a' * 64) == before
