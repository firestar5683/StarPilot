from pathlib import Path

import pytest
from openpilot.common.params import Params
from openpilot.selfdrive.car.card import alpha_long_requested


@pytest.mark.parametrize('release', [False, True])
@pytest.mark.parametrize('raw', [None, b'0', b'1'])
def test_retained_choice_is_separate_from_release_runtime_authority(tmp_path, release, raw):
  params = Params(str(tmp_path))
  path = Path(params.get_param_path('AlphaLongitudinalEnabled'))
  if raw is not None:
    path.write_bytes(raw)
  assert alpha_long_requested(params, is_release=release) == (raw == b'1' and not release)
  assert (path.read_bytes() if path.exists() else None) == raw
  # Returning to a supported development branch restores intent without a rewrite.
  assert alpha_long_requested(params, is_release=False) == (raw == b'1')
