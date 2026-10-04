import ast
from pathlib import Path

import numpy as np
import pytest

from openpilot.starpilot.audio.sound_pack import BUILTIN_FILES, SoundPackLoader, read_wav


def production_filenames():
  source = Path(__file__).resolve().parents[3] / 'selfdrive/ui/soundd.py'
  tree = ast.parse(source.read_text())
  sounds = next(node for node in tree.body if isinstance(node, ast.AnnAssign) and node.target.id == 'sound_list')
  return tuple(dict.fromkeys(value.elts[0].value for value in sounds.value.values))


@pytest.mark.parametrize('selection', [None, 'stock', 'starpilot'])
def test_complete_production_alerts_preserve_stock_critical_max(tmp_path, selection):
  class Params:
    def get_param_path(self, key):
      return str(tmp_path / key)

  if selection is not None:
    (tmp_path / 'SoundPack').write_text(selection)
  stock = Path(__file__).resolve().parents[3] / 'selfdrive/assets/sounds'
  loader = SoundPackLoader(Params(), stock, tmp_path / 'packs')
  filenames = production_filenames()
  assert 'dm_critical_max.wav' in filenames
  loaded = loader.refresh(filenames, 0)
  assert set(loaded) == set(filenames)
  for filename in filenames:
    path = stock.parent / 'sounds_starpilot' / BUILTIN_FILES[filename] if selection != 'stock' and filename in BUILTIN_FILES else stock / filename
    np.testing.assert_array_equal(loaded[filename], read_wav(path))
  assert not loader.is_builtin(loaded['dm_critical_max.wav'])
  assert loader.refresh(filenames, 1) is None


def test_required_stock_only_alert_is_not_silently_masked(tmp_path):
  class Params:
    def get_param_path(self, key):
      return str(tmp_path / key)

  loader = SoundPackLoader(Params(), tmp_path / 'missing', tmp_path / 'packs')
  with pytest.raises(ValueError, match='invalid WAV file'):
    loader.refresh(('dm_critical_max.wav',), 0)
