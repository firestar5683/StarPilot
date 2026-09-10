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


def test_catalog_annotation_is_independent_of_statistics(tmp_path):
  from openpilot.starpilot.assets.model_sizes import ModelSizes
  (tmp_path / 'builtin.pkl').write_bytes(b'123')
  (tmp_path / 'gpu_driving_tinygrad.pkl').write_bytes(b'12345')
  (tmp_path / 'gpu_accel.pkl').write_bytes(b'1234567')
  models = [{'value': 'stock', 'builtin': True}, {'value': 'gpu', 'builtin': False}]
  result = ModelSizes().annotate(models, tmp_path, tmp_path / 'builtin.pkl',
    {'gpu': {'artifact_size': 5, 'accelerator_artifacts': {'chestnut': {'artifact_size': 7}}}}, lambda key: key + '_accel.pkl')
  assert result[0]['fileSizeBytes'] == 3
  assert result[1]['fileSizeBytes'] == 5
  assert result[1]['modelLabFileSize']['fileSizeBytes'] == 7
  assert all('stats' not in model for model in result)


def test_size_cache_refresh_and_bound(tmp_path, monkeypatch):
  from openpilot.starpilot.assets import model_sizes
  now = [0]
  monkeypatch.setattr(model_sizes.time, 'monotonic', lambda: now[0])
  service = model_sizes.ModelSizes()
  path = tmp_path / 'model.pkl'
  assert service.size(path, None)['fileSizeBytes'] is None
  path.write_bytes(b'123')
  assert service.size(path, None)['fileSizeBytes'] is None
  now[0] = 3
  assert service.size(path, None)['fileSizeBytes'] == 3
  for index in range(1002):
    service.size(tmp_path / str(index), None)
  assert len(service.sizes) <= 1001
