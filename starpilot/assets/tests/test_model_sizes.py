from pathlib import Path

import pytest

from openpilot.starpilot.assets.model_sizes import artifact_size, positive_size


@pytest.mark.parametrize('value', [None, True, False, 0, -1, '123', 'abc', 1.2, 2**60])
def test_invalid_declared_size(value):
  assert positive_size(value) is None


def test_monolithic_actual_size_precedes_chunks_and_reports_mismatch(tmp_path):
  path = tmp_path / 'model.pkl'
  path.write_bytes(b'actual model')
  Path(str(path) + '.chunkmanifest').write_text('1')
  Path(str(path) + '.chunk01of01').write_bytes(b'old chunk')
  result = artifact_size(path, 2)
  assert result['fileSizeBytes'] == len(b'actual model')
  assert result['downloadedBytes'] == len(b'actual model')
  assert result['sizeStatus'] == 'mismatch'


def test_complete_chunks_exclude_manifest_and_missing_chunk_is_partial(tmp_path):
  path = tmp_path / 'model.pkl'
  Path(str(path) + '.chunkmanifest').write_text('2')
  first, second = Path(str(path) + '.chunk01of02'), Path(str(path) + '.chunk02of02')
  first.write_bytes(b'abc')
  second.write_bytes(b'defg')
  assert artifact_size(path, 7)['fileSizeBytes'] == 7
  assert artifact_size(path, 7)['sizeStatus'] == 'complete'
  second.unlink()
  result = artifact_size(path, 7)
  assert result['sizeStatus'] == 'partial'
  assert result['fileSizeBytes'] is None
  assert result['downloadedBytes'] == 3 and result['declaredSizeBytes'] == 7


@pytest.mark.parametrize('manifest', ['0', '-1', 'bad', '100000000000000', '', '2.0'])
def test_malformed_chunk_manifest_is_not_complete(tmp_path, manifest):
  path = tmp_path / 'model.pkl'
  Path(str(path) + '.chunkmanifest').write_text(manifest)
  assert artifact_size(path)['fileSizeBytes'] is None
  assert artifact_size(path)['sizeStatus'] == 'partial'


def test_missing_manifest_and_missing_file(tmp_path):
  path = tmp_path / 'model.pkl'
  assert artifact_size(path, 20)['sizeStatus'] == 'declared'
  assert artifact_size(path)['sizeStatus'] == 'unknown'
  Path(str(path) + '.chunk01of02').write_bytes(b'partial')
  assert artifact_size(path)['sizeStatus'] == 'partial'
  assert artifact_size(path)['downloadedBytes'] == 7


def test_stat_failure_is_unknown(tmp_path, monkeypatch):
  path = tmp_path / 'model.pkl'
  path.write_bytes(b'x')
  def failed(*args, **kwargs):
    raise PermissionError('test denied')
  monkeypatch.setattr(Path, 'stat', failed)
  assert artifact_size(path, 10)['sizeStatus'] == 'unknown'


def test_zero_byte_artifact_is_not_valid_size(tmp_path):
  path = tmp_path / 'model.pkl'
  path.touch()
  assert artifact_size(path)['fileSizeBytes'] is None
  assert artifact_size(path)['sizeStatus'] == 'partial'
