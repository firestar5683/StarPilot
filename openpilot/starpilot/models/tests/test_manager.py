import hashlib
import io
import json
import multiprocessing
from pathlib import Path
import tempfile
import threading
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from openpilot.starpilot.models.catalog import ARTIFACT_ABI, BUNDLED_CURRENT, CATALOG_PATH, DEFAULT_SMALL
from openpilot.starpilot.models.manager import (
  ModelError, ModelManager, atomic_json, catalog, preferences, randomize_next_start, resolve_runtime, validate_manifest,
)


def run_download_owner(root, manifest, data, entered, release, result):
  class BlockedPart(io.BytesIO):
    def read(self, size=-1):
      entered.set()
      if not release.wait(5):
        raise OSError('fixture stalled')
      return super().read(size)

  def opener(url, timeout):
    if '/manifests/' in url:
      return io.BytesIO(json.dumps(manifest).encode())
    if url.endswith('chunk01of02'):
      return io.BytesIO(data[:10])
    return BlockedPart(data[10:])

  manager = ModelManager(root=Path(root), parked=lambda: True, gpu_present=lambda: False, opener=opener)
  with patch('openpilot.starpilot.models.manager.shutil.disk_usage', return_value=SimpleNamespace(free=1024**3)):
    try:
      manager.action('download', {'model': 'gwm8223'})
      manager.worker.join(6)
      result.put(manager.snapshot())
    finally:
      manager.close()


class ModelManagerTest(unittest.TestCase):
  def setUp(self):
    disk_usage = patch('openpilot.starpilot.models.manager.shutil.disk_usage', return_value=SimpleNamespace(free=1024**3))
    self.disk_usage = disk_usage.start()
    self.addCleanup(disk_usage.stop)
    self.temp = tempfile.TemporaryDirectory()
    self.addCleanup(self.temp.cleanup)
    self.root = Path(self.temp.name)
    shipped = patch('openpilot.starpilot.models.manager.SHIPPED_MODELS', self.root / 'shipped')
    shipped.start()
    self.addCleanup(shipped.stop)
    self.parked = True
    self.data = b'a verified compiled artifact'
    from openpilot.common.file_chunker import package_file
    source = self.root / 'shipped-source.pkl'
    source.write_bytes(self.data)
    package_file(source, self.root / 'shipped/rdf43_driving_tinygrad.pkl')
    source.unlink()
    for attribute, value in (('DEFAULT_SMALL_SHA256', hashlib.sha256(self.data).hexdigest()), ('DEFAULT_SMALL_SIZE', len(self.data))):
      identity = patch('openpilot.starpilot.models.manager.' + attribute, value)
      identity.start()
      self.addCleanup(identity.stop)
    self.manifest = json.loads(CATALOG_PATH.read_text())
    self.row = next(x for x in self.manifest['models'] if x['id'] == 'gwm8223')
    self.row.update(artifact_format=ARTIFACT_ABI, artifact_sha256=hashlib.sha256(self.data).hexdigest(),
                    artifact_size=len(self.data), artifact_chunk_count=2)
    self.urls = []
    self.bad = False

    def request(url, timeout):
      self.assertTrue(url.startswith('https://huggingface.co/buckets/StarPilot-Driving/StarPilot-Resources/resolve/'))
      self.urls.append(url)
      if '/manifests/' in url:
        return io.BytesIO(json.dumps(self.manifest).encode())
      if url.endswith('chunk01of02'):
        return io.BytesIO(self.data[:10])
      if url.endswith('chunk02of02'):
        return io.BytesIO(b'corrupt' if self.bad else self.data[10:])
      raise OSError('missing fixture')

    self.manager = ModelManager(root=self.root, parked=lambda: self.parked, gpu_present=lambda: True, opener=request)
    self.addCleanup(self.manager.close)

  def download(self):
    self.manager.action('download', {'model': 'gwm8223'})
    self.manager.worker.join(3)
    self.assertFalse(self.manager.worker.is_alive())

  def model_status(self):
    return next(x for x in self.manager.snapshot()['models'] if x['value'] == 'gwm8223')

  def wait_for_check(self):
    deadline = time.monotonic() + 3
    while time.monotonic() < deadline:
      row = self.model_status()
      if not row['checking']:
        return row
      time.sleep(0.01)
    self.fail('Artifact verification did not finish')

  def test_selected_gpu_status_verifies_download_without_bundled_model_or_job_writes(self):
    from openpilot.starpilot.models.manager import artifact_path

    mid = 'cinquev3'
    entry = {'artifact_sha256': hashlib.sha256(self.data).hexdigest(), 'artifact_size': len(self.data)}
    path = artifact_path(mid, self.root)
    path.parent.mkdir(parents=True)
    path.write_bytes(self.data)
    atomic_json(self.root / 'preferences.json', {'big': mid})
    with patch('openpilot.starpilot.models.manager.catalog', return_value={mid: entry}), \
         patch.object(self.manager, '_job_status', side_effect=AssertionError('Read-only status must not change jobs')):
      assert self.manager.selected_gpu_status() == (False, True)
      deadline = time.monotonic() + 3
      while time.monotonic() < deadline:
        state = self.manager.selected_gpu_status()
        if state != (False, True):
          break
        time.sleep(.01)
      assert state == (True, False)
      path.write_bytes(b'x' * len(self.data))
      assert self.manager.selected_gpu_status() == (False, True)
      deadline = time.monotonic() + 3
      while time.monotonic() < deadline:
        state = self.manager.selected_gpu_status()
        if state != (False, True):
          break
        time.sleep(.01)
      assert state == (False, False)
      atomic_json(self.root / 'preferences.json', {'big': ''})
      assert self.manager.selected_gpu_status() == (False, False)
      atomic_json(self.root / 'preferences.json', {'big': mid})
      path.unlink()
      assert self.manager.selected_gpu_status() == (False, False)
    assert not (self.root / '.download-job.json').exists()

  def test_chunk_download_verifies_and_selects_next_start(self):
    self.download()
    self.assertEqual(self.manager.progress, 'Downloaded!')
    self.assertEqual(preferences(self.root)['small'], DEFAULT_SMALL)
    self.manager.action('active', {'profile': 'small', 'model': 'gwm8223'})
    selected = resolve_runtime(True, root=self.root)
    self.assertEqual(selected.small_id, 'gwm8223')
    self.assertEqual(selected.small_path.read_bytes(), self.data)
    self.assertTrue(all('/v26/' in u or 'model_names_v26.json' in u for u in self.urls))

  def test_corruption_never_publishes_or_selects(self):
    self.bad = True
    self.download()
    self.assertIn('checksum', self.manager.progress)
    self.assertFalse(list(self.root.rglob('*.pkl')))
    with self.assertRaises(ModelError):
      self.manager.action('active', {'profile': 'small', 'model': 'gwm8223'})

  def test_insufficient_storage_preserves_installed_model_and_selection(self):
    self.download()
    self.manager.action('active', {'profile': 'small', 'model': 'gwm8223'})
    other = next(row for row in self.manifest['models'] if row['id'] == 'pop223')
    other.update({key: self.row[key] for key in ('artifact_format', 'artifact_sha256', 'artifact_size', 'artifact_chunk_count')})
    self.urls.clear()
    self.disk_usage.return_value = SimpleNamespace(free=256 * 1024 * 1024 + len(self.data) - 1)
    self.manager.action('download', {'model': 'pop223'})
    self.manager.worker.join(3)
    self.assertFalse(self.manager.worker.is_alive())
    self.assertEqual(self.manager.progress, 'Not enough storage for this model')
    self.assertTrue(self.urls)
    self.assertTrue(all('/manifests/' in url for url in self.urls))
    self.assertEqual(preferences(self.root)['small'], 'gwm8223')
    self.assertEqual(resolve_runtime(True, root=self.root).small_path.read_bytes(), self.data)
    self.assertFalse(list((self.root / 'pop223').glob('.download-*')))

  def test_changed_installed_bytes_fall_back_and_ui_rechecks(self):
    self.download()
    self.manager.action('active', {'profile': 'small', 'model': 'gwm8223'})
    self.assertTrue(self.wait_for_check()['installed'])
    (self.root/'gwm8223/gwm8223_driving_tinygrad.pkl').write_bytes(b'x' * len(self.data))
    self.assertEqual(resolve_runtime(True, root=self.root).small_id, DEFAULT_SMALL)
    self.assertFalse(self.model_status()['installed'])
    self.assertFalse(self.wait_for_check()['installed'])

  def test_snapshot_does_not_wait_for_artifact_hash(self):
    self.download()
    self.manager.checked.clear()
    entered, release = threading.Event(), threading.Event()
    from openpilot.starpilot.models import manager as manager_module
    original = manager_module.verified_artifact

    def slow_verify(*args, **kwargs):
      entered.set()
      self.assertTrue(release.wait(3))
      return original(*args, **kwargs)

    with patch.object(manager_module, 'verified_artifact', side_effect=slow_verify):
      started = time.monotonic()
      first = self.model_status()
      self.assertLess(time.monotonic() - started, 0.5)
      self.assertTrue(first['checking'])
      self.assertFalse(first['installed'])
      self.assertFalse(first['selectable'])
      self.assertEqual(first['unavailableReason'], 'Checking artifact')
      self.assertTrue(entered.wait(1))
      started = time.monotonic()
      second = self.model_status()
      self.assertLess(time.monotonic() - started, 0.5)
      self.assertTrue(second['checking'])
      release.set()
      self.assertTrue(self.wait_for_check()['installed'])

  def test_replaced_artifact_invalidates_cached_validity(self):
    self.download()
    self.assertTrue(self.wait_for_check()['installed'])
    path = self.root/'gwm8223/gwm8223_driving_tinygrad.pkl'
    replacement = path.with_suffix('.replacement')
    replacement.write_bytes(b'x' * len(self.data))
    replacement.replace(path)
    row = self.model_status()
    self.assertFalse(row['installed'])
    self.assertFalse(row['selectable'])
    self.assertFalse(self.wait_for_check()['installed'])
    replacement.write_bytes(self.data)
    replacement.replace(path)
    self.assertFalse(self.model_status()['installed'])
    self.assertTrue(self.wait_for_check()['installed'])

  def test_offroad_authority_rechecked_after_validation(self):
    self.download()
    samples = iter([True, False])
    self.manager.parked = lambda: next(samples)
    with self.assertRaises(ModelError):
      self.manager.action('active', {'profile': 'small', 'model': 'gwm8223'})
    self.assertEqual(preferences(self.root)['small'], DEFAULT_SMALL)

  def test_hardware_profiles_and_selected_delete(self):
    self.download()
    with self.assertRaises(ModelError):
      self.manager.action('active', {'profile': 'big', 'model': 'gwm8223'})
    self.manager.action('active', {'profile': 'small', 'model': 'gwm8223'})
    with self.assertRaises(ModelError):
      self.manager.action('delete', {'model': 'gwm8223'})
    self.manager.action('active', {'profile': 'big', 'model': ''})
    self.assertFalse(resolve_runtime(True, root=self.root).allow_big)

  def test_manifest_rejects_old_generation_and_hardware_change(self):
    self.manifest['generation'] = 'v25'
    with self.assertRaises(ModelError):
      validate_manifest(self.manifest)
    self.manifest['generation'] = 'v26'
    self.row['uses_external_gpu'] = True
    with self.assertRaises(ModelError):
      validate_manifest(self.manifest)

  def runtime_artifact(self, revision=2):
    fields = ('artifact_format', 'artifact_sha256', 'artifact_size', 'artifact_chunk_count')
    artifact = {name: self.row.pop(name) for name in fields}
    self.row['runtime_artifacts'] = [dict(artifact, min_runner_revision=revision)]
    return artifact

  def test_runner_revision_gates_download_and_runtime_selection(self):
    self.runtime_artifact()
    self.download()
    self.manager.action('active', {'profile': 'small', 'model': 'gwm8223'})
    self.assertEqual(resolve_runtime(True, root=self.root).small_id, 'gwm8223')
    with patch('openpilot.starpilot.models.manager.MODEL_RUNNER_REVISION', 1):
      self.assertNotIn('artifact_sha256', validate_manifest(self.manifest)['gwm8223'])
      self.assertEqual(resolve_runtime(True, root=self.root).small_id, DEFAULT_SMALL)
      self.assertFalse(self.model_status()['downloadAvailable'])
    self.assertEqual(resolve_runtime(True, root=self.root).small_id, 'gwm8223')

  def test_future_runner_variant_preserves_existing_artifact(self):
    previous = self.runtime_artifact(3)
    self.assertNotIn('artifact_sha256', validate_manifest(self.manifest)['gwm8223'])
    self.row.update(previous)
    self.assertEqual(validate_manifest(self.manifest)['gwm8223']['artifact_sha256'], previous['artifact_sha256'])
    self.download()
    self.assertEqual(self.manager.progress, 'Downloaded!')

  def test_runtime_variant_rejects_invalid_contract(self):
    self.runtime_artifact()
    valid = dict(self.row['runtime_artifacts'][0])
    for field, value in [('min_runner_revision', True), ('min_runner_revision', 0),
                         ('artifact_sha256', 'bad'), ('artifact_size', 0), ('unknown_feature', True)]:
      self.row['runtime_artifacts'] = [dict(valid, **{field: value})]
      with self.subTest(field=field, value=value), self.assertRaises(ModelError):
        validate_manifest(self.manifest)
    self.row['runtime_artifacts'] = [valid, valid]
    with self.assertRaises(ModelError):
      validate_manifest(self.manifest)

  def test_runtime_variant_keeps_download_checksum_validation(self):
    self.runtime_artifact()
    self.bad = True
    self.download()
    self.assertIn('checksum', self.manager.progress)
    self.assertFalse(list(self.root.rglob('*.pkl')))

  def test_missing_big_download_uses_small_and_leaves_request(self):
    atomic_json(self.root/'preferences.json', {'small': BUNDLED_CURRENT, 'big': 'cinquev3'})
    self.assertFalse(resolve_runtime(True, root=self.root).allow_big)
    self.assertEqual(preferences(self.root)['big'], 'cinquev3')

  def test_preferences_and_unknown_payloads(self):
    self.manager.action('preferences', {'userFavorites': ['gwm8223'], 'sortMode': 'series'})
    self.assertEqual(preferences(self.root)['userFavorites'], ['gwm8223'])
    for action, payload in [('active', {'profile': 'small', 'model': []}), ('download', {'model': '../bad'}),
                            ('delete', {'model': BUNDLED_CURRENT}), ('preferences', {'userFavorites': ['unknown']})]:
      with self.subTest(action=action), self.assertRaises(ModelError):
        self.manager.action(action, payload)

  def other_manager(self, opener=None):
    manager = ModelManager(root=self.root, parked=lambda: self.parked, gpu_present=lambda: True,
                           opener=opener or self.manager.opener)
    self.addCleanup(manager.close)
    return manager

  def test_another_manager_observes_progress_and_cancels_owner_job(self):
    entered, release = threading.Event(), threading.Event()
    original = self.manager.opener

    class BlockedPart(io.BytesIO):
      def read(inner, size=-1):
        entered.set()
        if not release.wait(3):
          raise OSError('fixture stalled')
        return super().read(size)

    def opener(url, timeout):
      return BlockedPart(self.data[10:]) if url.endswith('chunk02of02') else original(url, timeout)

    self.manager.opener = opener
    observer = self.other_manager()
    self.manager.action('download', {'model': 'gwm8223'})
    try:
      self.assertTrue(entered.wait(1))
      view = observer.snapshot()
      self.assertTrue(view['downloading'])
      self.assertEqual(view['modelToDownload'], 'gwm8223')
      self.assertIn('%', view['progress'])
      self.assertEqual(view['jobId'], self.manager.job_id)
      for action, payload in [('download', {'model': 'gwm8223'}), ('refresh_manifest', {}),
                              ('active', {'profile': 'small', 'model': BUNDLED_CURRENT}), ('delete', {'model': 'gwm8223'})]:
        with self.subTest(action=action), self.assertRaises(ModelError):
          observer.action(action, payload)
      observer.action('cancel', {'jobId': view['jobId']})
      self.assertTrue(observer.snapshot()['cancelRequested'])
    finally:
      release.set()
      self.manager.worker.join(3)
    self.assertFalse(self.manager.worker.is_alive())
    self.assertEqual(observer.snapshot()['progress'], 'Download cancelled')
    self.assertFalse(observer.snapshot()['downloading'])
    self.assertFalse(list(self.root.rglob('*.pkl')))
    self.assertFalse(list((self.root / 'gwm8223').glob('.download-*')))
    observer.action('refresh_manifest', {})
    observer.worker.join(3)
    self.assertEqual(observer.snapshot()['progress'], 'Catalog updated')
    self.assertNotEqual(observer.snapshot()['jobId'], view['jobId'])
    with self.assertRaises(ModelError):
      observer.action('cancel', {'jobId': view['jobId']})

  def test_another_process_observes_and_cancels_download(self):
    context = multiprocessing.get_context('spawn')
    entered, release, result = context.Event(), context.Event(), context.Queue()
    owner = context.Process(target=run_download_owner,
                            args=(str(self.root), self.manifest, self.data, entered, release, result))
    owner.start()
    try:
      self.assertTrue(entered.wait(5))
      view = self.manager.snapshot()
      self.assertTrue(view['downloading'])
      self.assertEqual(view['modelToDownload'], 'gwm8223')
      self.assertIn('%', view['progress'])
      with self.assertRaises(ModelError):
        self.manager.action('refresh_manifest', {})
      self.manager.action('cancel', {'jobId': view['jobId']})
      release.set()
      terminal = result.get(timeout=5)
      owner.join(5)
      self.assertEqual(owner.exitcode, 0)
      self.assertFalse(terminal['downloading'])
      self.assertEqual(terminal['progress'], 'Download cancelled')
      self.assertFalse(list(self.root.rglob('*.pkl')))
      self.assertFalse(self.manager.snapshot()['downloading'])
    finally:
      release.set()
      owner.join(5)
      if owner.is_alive():
        owner.terminate()
        owner.join(5)
      result.close()

  def test_simultaneous_managers_accept_exactly_one_job(self):
    entered, release = threading.Event(), threading.Event()
    original = self.manager.opener

    def opener(url, timeout):
      entered.set()
      if not release.wait(3):
        raise OSError('fixture stalled')
      return original(url, timeout)

    self.manager.opener = opener
    other = self.other_manager(opener)
    barrier = threading.Barrier(3)
    accepted, rejected = [], []

    def start(manager):
      barrier.wait()
      try:
        manager.action('download', {'model': 'gwm8223'})
        accepted.append(manager)
      except ModelError as error:
        rejected.append(str(error))

    callers = [threading.Thread(target=start, args=(manager,)) for manager in (self.manager, other)]
    for caller in callers:
      caller.start()
    barrier.wait()
    try:
      for caller in callers:
        caller.join(1)
        self.assertFalse(caller.is_alive())
      self.assertTrue(entered.wait(1))
      self.assertEqual(len(accepted), 1)
      self.assertEqual(len(rejected), 1)
      self.assertIn('Another model manager', rejected[0])
      self.assertEqual(self.manager.snapshot()['jobId'], other.snapshot()['jobId'])
      self.assertTrue(other.snapshot()['downloading'])
    finally:
      release.set()
      for manager in (self.manager, other):
        if manager.worker is not None:
          manager.worker.join(3)
    self.assertEqual(other.snapshot()['progress'], 'Downloaded!')
    self.assertFalse(other.snapshot()['downloading'])

  def test_closing_observer_does_not_cancel_other_manager_job(self):
    entered, release = threading.Event(), threading.Event()
    original = self.manager.opener

    def opener(url, timeout):
      if '/manifests/' in url:
        entered.set()
        if not release.wait(3):
          raise OSError('fixture stalled')
      return original(url, timeout)

    self.manager.opener = opener
    observer = self.other_manager()
    self.manager.action('download', {'model': 'gwm8223'})
    try:
      self.assertTrue(entered.wait(1))
      observer.close()
      self.assertFalse(self.manager.snapshot()['cancelRequested'])
      self.assertFalse(self.manager.cancelled.is_set())
    finally:
      release.set()
      self.manager.worker.join(3)
    self.assertEqual(self.manager.progress, 'Downloaded!')
    self.assertTrue(self.wait_for_check()['installed'])

  def test_stale_journal_and_completed_job_do_not_block_new_downloads(self):
    observer = self.other_manager()
    atomic_json(self.root / '.download-job.json', {
      'schemaVersion': 1, 'jobId': 'a' * 32, 'state': 'running', 'model': 'gwm8223',
      'downloadAll': True, 'progress': 'Old download', 'cancelRequested': True,
    })
    view = observer.snapshot()
    self.assertFalse(view['downloading'])
    self.assertEqual(view['progress'], 'Previous model download was interrupted')
    self.assertEqual(observer.action('cancel', {})['message'], 'No model download is running')
    observer.action('download', {'model': 'gwm8223'})
    observer.worker.join(3)
    self.assertEqual(observer.snapshot()['progress'], 'Downloaded!')
    self.assertFalse(observer.snapshot()['downloading'])
    observer.action('refresh_manifest', {})
    observer.worker.join(3)
    self.assertEqual(observer.snapshot()['progress'], 'Catalog updated')
    self.assertFalse(observer.snapshot()['downloading'])

  def install_fixture(self, mid):
    row = next(x for x in self.manifest['models'] if x['id'] == mid)
    row.update(artifact_format=ARTIFACT_ABI, artifact_sha256=hashlib.sha256(self.data).hexdigest(),
               artifact_size=len(self.data), artifact_chunk_count=0)
    path = self.root / mid / f'{mid}_driving_tinygrad.pkl'
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(self.data)
    atomic_json(self.root / 'catalog.json', self.manifest)
    return path

  def test_randomizer_off_is_read_only_and_opt_in(self):
    self.install_fixture('gwm8223')
    self.assertEqual(resolve_runtime(False, root=self.root, randomize=True).small_id, DEFAULT_SMALL)
    self.assertFalse((self.root / 'preferences.json').exists())
    self.manager.action('active', {'profile': 'small', 'model': BUNDLED_CURRENT})
    self.manager.action('preferences', {'randomizer': True})
    self.assertEqual(resolve_runtime(False, root=self.root).small_id, DEFAULT_SMALL)
    self.assertEqual(resolve_runtime(False, root=self.root, randomize=True).small_id, 'gwm8223')
    self.assertEqual(preferences(self.root)['small'], 'gwm8223')

  def test_randomizer_avoids_repeat_ignores_favorites_and_respects_exclusions(self):
    self.install_fixture('gwm8223')
    self.install_fixture('rdf43')
    self.manager.action('preferences', {'randomizer': True, 'userFavorites': ['gwm8223'],
                                       'blacklistedModels': ['gwm8223', BUNDLED_CURRENT]})
    self.assertEqual(randomize_next_start(False, root=self.root)['small'], 'rdf43')
    self.assertEqual(randomize_next_start(False, root=self.root)['small'], 'rdf43')
    self.manager.action('preferences', {'blacklistedModels': []})
    seen = []
    def choose(options):
      seen.extend(options)
      return options[0]
    randomize_next_start(False, root=self.root, chooser=choose)
    self.assertNotIn('rdf43', seen)
    self.assertIn('gwm8223', seen)
    self.assertEqual(seen, ['gwm8223'])

  def test_randomizer_no_chestnut_changes_only_small(self):
    self.install_fixture('gwm8223')
    self.install_fixture('cinquev3')
    atomic_json(self.root / 'preferences.json', {'randomizer': True, 'big': 'cinquev3', 'small': BUNDLED_CURRENT})
    selected = resolve_runtime(False, root=self.root, randomize=True)
    self.assertEqual(selected.small_id, 'gwm8223')
    self.assertFalse(selected.allow_big)
    self.assertIsNone(selected.big_path)
    self.assertEqual(preferences(self.root)['big'], 'cinquev3')
    selected = resolve_runtime(True, root=self.root, randomize=True)
    self.assertEqual(selected.big_id, 'cinquev3')
    self.assertEqual(selected.big_path.read_bytes(), self.data)
    self.assertTrue(selected.allow_big)

  def test_randomizer_empty_corrupt_pool_has_safe_fallback(self):
    path = self.install_fixture('gwm8223')
    path.write_bytes(b'x' * len(self.data))
    atomic_json(self.root / 'preferences.json', {'randomizer': True, 'small': 'gwm8223',
                                               'blacklistedModels': [BUNDLED_CURRENT]})
    self.assertEqual(resolve_runtime(False, root=self.root, randomize=True).small_id, DEFAULT_SMALL)
    self.manager.action('preferences', {'blacklistedModels': []})
    atomic_json(self.root / 'preferences.json', {'randomizer': True, 'big': 'cinquev3', 'small': 'gwm8223'})
    selected = resolve_runtime(True, root=self.root, randomize=True)
    self.assertFalse(selected.allow_big)
    self.assertEqual(selected.small_id, DEFAULT_SMALL)
    self.assertEqual(preferences(self.root)['big'], '')

  def test_selection_preferences_require_parked_and_strict_values(self):
    for payload in ({'randomizer': 1}, {'blacklistedModels': ['unknown']}, {'blacklistedModels': 'gwm8223'}):
      with self.subTest(payload=payload), self.assertRaises(ModelError):
        self.manager.action('preferences', payload)
    self.parked = False
    for payload in ({'randomizer': True}, {'blacklistedModels': ['gwm8223']}):
      with self.subTest(payload=payload), self.assertRaises(ModelError):
        self.manager.action('preferences', payload)
    self.manager.action('preferences', {'userFavorites': ['gwm8223']})
    self.parked = True
    self.manager.action('preferences', {'randomizer': True})
    with self.assertRaises(ModelError):
      self.manager.action('active', {'profile': 'small', 'model': BUNDLED_CURRENT})
    self.assertTrue(self.manager.snapshot()['randomizer'])
    self.manager.parked = iter([True, False]).__next__
    with self.assertRaises(ModelError):
      self.manager.action('preferences', {'randomizer': False})
    self.assertTrue(preferences(self.root)['randomizer'])

  def test_unpublished_catalog_is_visible_but_not_selectable(self):
    self.assertEqual(len(catalog(self.root)), 99)
    self.manager.snapshot()
    if self.manager.verify_worker is not None:
      self.manager.verify_worker.join(2)
    models = self.manager.snapshot()['models']
    self.assertEqual(sum(row['selectable'] for row in models), 1)
    self.assertTrue(all(row.get('unavailableReason') for row in models if not row['selectable']))

  def test_fresh_install_knows_published_downloads_without_network_or_gpu(self):
    self.manager.gpu_present = lambda: False
    models = {row['value']: row for row in self.manager.snapshot()['models']}
    self.assertTrue(models['gwm8223']['downloadAvailable'])
    self.assertEqual(models['gwm8223']['unavailableReason'], 'Download required')
    self.assertFalse(models['gwm8223']['selectable'])
    self.assertFalse(models['gwm6223']['downloadAvailable'])
    self.assertEqual(models['gwm6223']['unavailableReason'], 'v26 download not published')
    big = next(row for row in models.values() if row.get('requiresGpu') and row.get('downloadAvailable'))
    self.assertFalse(big['gpuAvailable'])
    self.assertEqual(big['unavailableReason'], 'Download required')
    self.assertEqual(self.urls, [])
    self.assertFalse((self.root / 'catalog.json').exists())


if __name__ == '__main__':
  unittest.main()
