'Stock alert mapping, playback, selection migration and bounded cleanup.'

from pathlib import Path

from unittest.mock import patch

import numpy as np

from openpilot.common.basedir import BASEDIR

from openpilot.common.params import Params

from openpilot.selfdrive.ui.soundd import Soundd, AudibleAlert, CRITICAL_MAX, sound_list

from openpilot.starpilot.audio.sound_pack import read_wav, installed_packs, read_selection, migrate_removed_selection

EXPECTED = {
 AudibleAlert.engage: ('engage.wav', 1, 1.0),
 AudibleAlert.disengage: ('disengage.wav', 1, 1.0),
 AudibleAlert.refuse: ('refuse.wav', 1, 1.0),
 AudibleAlert.prompt: ('warning.wav', 1, 1.0),
 AudibleAlert.promptRepeat: ('warning.wav', None, 1.0),
 AudibleAlert.promptDistracted: ('dm_warning.wav', None, 1.0),
 AudibleAlert.preAlert: ('pre_alert.wav', 1, 1.0),
 AudibleAlert.warningSoft: ('critical.wav', None, 1.0),
 AudibleAlert.warningImmediate: ('dm_critical.wav', None, 1.0),
 CRITICAL_MAX: ('dm_critical_max.wav', None, 1.0),
}

def test_stock_every_event_current_upstream_mapping_and_callback(tmp_path):
  params = Params(str(tmp_path / 'params'))
  params.put('SoundPack', 'stock', block=True)
  sound = Soundd(params, pack_root=tmp_path / 'packs')
  assert sound_list == EXPECTED
  root = Path(BASEDIR) / 'openpilot/selfdrive/assets/sounds'
  for alert, (filename, _loops, _gain) in EXPECTED.items():
    expected = read_wav(root / filename)
    np.testing.assert_array_equal(sound.loaded_sounds[alert], expected)
    sound.current_alert, sound.current_sound, sound.current_sound_frame, sound.current_volume = (alert, alert, 0, 0.5)
    output = np.zeros((len(expected), 1), dtype=np.float32)
    with patch('pathlib.Path.open', side_effect=AssertionError('callback disk access')):
      sound.callback(output, len(expected), None, None)
    np.testing.assert_array_equal(output[:, 0], expected * 0.5)
  assert params.get('SoundPack') == 'stock'

def test_removed_installed_selection_migrates_default_and_cannot_shadow(tmp_path):
  params = Params(str(tmp_path / 'params'))
  root = tmp_path / 'packs'
  for name in ('stalin', 'STALIN'):
    (root / name / 'sounds').mkdir(parents=True)
  params.put('SoundPack', 'STALIN', block=True)
  assert installed_packs(root) == ('starpilot', 'stock')
  sound = Soundd(params, pack_root=root)
  assert params.get('SoundPack') == 'starpilot'
  assert read_selection(params)[1] == 'starpilot'
  assert not migrate_removed_selection(params, root)
  assert len(sound.pack_loader.builtin_sounds) == 5

def test_parked_cleanup_preserves_custom_renamed_symlink_and_missing(tmp_path):
  from openpilot.starpilot.audio.sound_pack import cleanup_removed_packs
  root = tmp_path / 'packs'
  root.mkdir()
  obsolete = root / 'stalin'
  (obsolete / 'sounds').mkdir(parents=True)
  (obsolete / 'sounds' / 'legacy.wav').write_bytes(b'obsolete')
  custom = root / 'custom'
  (custom / 'sounds').mkdir(parents=True)
  (custom / 'sounds' / 'keep.wav').write_bytes(b'keep')
  renamed = root / 'retained_user_pack'
  renamed.mkdir()
  (renamed / 'keep').write_bytes(b'keep')
  (root / 'STALIN').symlink_to(custom, target_is_directory=True)
  assert cleanup_removed_packs(root, parked=lambda: False) == ()
  assert obsolete.exists()
  assert set(cleanup_removed_packs(root, parked=lambda: True)) == {'stalin', 'STALIN'}
  assert not obsolete.exists()
  assert (custom / 'sounds' / 'keep.wav').read_bytes() == b'keep'
  assert (renamed / 'keep').read_bytes() == b'keep'
  assert not (root / 'STALIN').exists()
  assert cleanup_removed_packs(root, parked=lambda: True) == ()
  assert cleanup_removed_packs(tmp_path / 'missing', parked=lambda: True) == ()

def test_cleanup_parked_callback_failure_and_revocation(tmp_path):
  from openpilot.starpilot.audio.sound_pack import cleanup_removed_packs
  root = tmp_path / 'packs'
  pack = root / 'stalin' / 'sounds'
  pack.mkdir(parents=True)
  (pack / 'keep.wav').write_bytes(b'old')

  def failed():
    raise RuntimeError('parked source unavailable')
  assert cleanup_removed_packs(root, parked=failed) == ()
  assert (pack / 'keep.wav').exists()
  calls = [0]

  def revoked():
    calls[0] += 1
    return calls[0] < 5
  assert cleanup_removed_packs(root, parked=revoked) == ()
  assert (pack / 'keep.wav').exists()

def test_cleanup_oversized_depth_and_growth_are_not_walked_or_deleted(tmp_path):
  from openpilot.starpilot.audio.sound_pack import cleanup_removed_packs
  root = tmp_path / 'packs'
  pack = root / 'stalin'
  pack.mkdir(parents=True)
  for i in range(65):
    (pack / f'{i}.wav').write_bytes(b'old')
  assert cleanup_removed_packs(root, parked=lambda: True) == ()
  assert len(tuple(pack.iterdir())) == 65
  for path in pack.iterdir():
    path.unlink()
  deep = pack / 'a' / 'b' / 'c' / 'd'
  deep.mkdir(parents=True)
  (deep / 'old').write_bytes(b'old')
  assert cleanup_removed_packs(root, parked=lambda: True) == ()
  assert (deep / 'old').exists()

def test_cleanup_swap_before_delete_preserves_replacement_and_renamed_pack(tmp_path):
  from openpilot.starpilot.audio.sound_pack import cleanup_removed_packs
  root = tmp_path / 'packs'
  pack = root / 'stalin'
  pack.mkdir(parents=True)
  (pack / 'old.wav').write_bytes(b'old')
  custom = root / 'custom'
  custom.mkdir()
  (custom / 'keep').write_bytes(b'keep')
  calls = [0]

  def replace_pack():
    calls[0] += 1
    if calls[0] == 4:
      pack.rename(root / 'renamed_old')
      custom.rename(pack)
    return True
  assert cleanup_removed_packs(root, parked=replace_pack) == ()
  assert (root / 'renamed_old' / 'old.wav').read_bytes() == b'old'
  assert (pack / 'keep').read_bytes() == b'keep'

def test_cleanup_growth_before_delete_is_not_added_to_deletion_plan(tmp_path):
  from openpilot.starpilot.audio.sound_pack import cleanup_removed_packs
  root = tmp_path / 'packs'
  pack = root / 'stalin'
  pack.mkdir(parents=True)
  (pack / 'old.wav').write_bytes(b'old')
  calls = [0]

  def growth():
    calls[0] += 1
    if calls[0] == 4:
      (pack / 'new_user_file').write_bytes(b'keep')
    return True
  assert cleanup_removed_packs(root, parked=growth) == ()
  assert (pack / 'old.wav').exists()
  assert (pack / 'new_user_file').read_bytes() == b'keep'

def test_existing_download_owner_survives_parked_callback_failure(tmp_path):
  import pytest
  from openpilot.starpilot.audio.downloads import SoundDownloads, SoundDownloadError

  def failed():
    raise RuntimeError('parked source unavailable')
  owner = SoundDownloads(failed, root=tmp_path / 'packs')
  assert owner.snapshot()['parked'] is False
  with pytest.raises(SoundDownloadError):
    owner.action('install', {'id': 'duck'})
  owner.close()
