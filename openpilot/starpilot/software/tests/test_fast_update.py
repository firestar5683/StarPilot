import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[3]


def load(name, path):
  spec = importlib.util.spec_from_file_location(name, path)
  assert spec is not None and spec.loader is not None
  module = importlib.util.module_from_spec(spec)
  sys.modules[name] = module
  spec.loader.exec_module(module)
  return module


vendor = load('openpilot.common.vendor_manifest', ROOT / 'common/vendor_manifest.py')
prebuilt = load('openpilot.common.prebuilt_manifest', ROOT / 'common/prebuilt_manifest.py')
owner = load('fast_update_owner', ROOT / 'starpilot/software/fast_update.py')


class Params:
  def __init__(self):
    self.calls = []

  def put_bool(self, *args, **kwargs):
    self.calls.append((args, kwargs))


class TestFastUpdate(unittest.TestCase):
  def git(self, repo, *args):
    return subprocess.check_output(['git', '-C', str(repo), *args], stderr=subprocess.STDOUT).decode().strip()

  def setUp(self):
    self.temp = tempfile.TemporaryDirectory()
    self.addCleanup(self.temp.cleanup)
    base = Path(self.temp.name)
    self.remote, self.repo = base / 'remote', base / 'repo'
    self.remote.mkdir()
    self.git(self.remote, 'init', '-b', 'Dom')
    self.git(self.remote, 'config', 'user.name', 'Test')
    self.git(self.remote, 'config', 'user.email', 'test@example.invalid')
    dependencies = []
    for name in sorted(vendor.DEPENDENCIES):
      (self.remote / name).mkdir()
      (self.remote / name / 'source').write_text('vendored')
      dependencies.append({'path': name, 'commit': '1' * 40, 'tree': '2' * 40, 'url': 'https://example.invalid/source', 'exclude': []})
    manifest = {'schema_version': 1, 'upstream': {'commit': '3' * 40, 'url': 'https://example.invalid/upstream'}, 'dependencies': dependencies}
    (self.remote / 'upstream-sync.json').write_text(json.dumps(manifest))
    (self.remote / 'launch_env.sh').write_text('export AGNOS_VERSION="19.8.1"\n')
    (self.remote / 'prebuilt').write_text('')
    (self.remote / 'openpilot/starpilot/ui').mkdir(parents=True)
    (self.remote / 'openpilot/starpilot/ui/source.py').write_text('old')
    self.git(self.remote, 'add', '.')
    self.git(self.remote, 'commit', '-m', 'initial')
    self.git(base, 'clone', '--no-local', str(self.remote), str(self.repo))
    self.previous = self.git(self.repo, 'rev-parse', 'HEAD')
    (self.remote / 'openpilot/starpilot/ui/source.py').write_text('new')
    self.git(self.remote, 'commit', '-am', 'update')
    self.target = self.git(self.remote, 'rev-parse', 'HEAD')
    self.params = Params()
    self.invalidations = []

  def update(self, **kwargs):
    arguments = {
      'params': self.params,
      'parked': lambda: True,
      'expected_commit': self.git(self.repo, 'rev-parse', 'HEAD'),
      'current_os': '19.8.1',
      'invalidate': lambda: self.invalidations.append(True),
      'sleep': lambda _: None,
    }
    arguments.update(kwargs)
    return owner.fast_update(self.repo, 'Dom', **arguments)

  def test_applies_exact_revision_and_retains_untracked_models(self):
    (self.repo / 'models').mkdir()
    (self.repo / 'models' / 'download').write_bytes(b'model')
    commands = []

    def traced(command, cwd):
      commands.append(command)
      return owner.run(command, cwd)

    self.assertEqual(self.update(run=traced), 'reboot-requested')
    fetch = next(command for command in commands if 'fetch' in command)
    self.assertIn('gc.auto=0', fetch)
    self.assertIn('maintenance.auto=false', fetch)
    self.assertIn('--depth=1', fetch)
    self.assertIn('--no-tags', fetch)
    self.assertEqual(self.git(self.repo, 'rev-parse', 'HEAD'), self.target)
    self.assertEqual(self.git(self.repo, 'rev-parse', 'refs/starpilot/previous'), self.previous)
    self.assertEqual((self.repo / 'models' / 'download').read_bytes(), b'model')
    self.assertEqual(self.params.calls, [(('DoReboot', True), {'block': True})])
    self.assertEqual(self.update(), 'up-to-date')
    self.assertEqual(len(self.invalidations), 1)

  def test_actual_updater_owned_transaction_and_durable_restart_state(self):
    from openpilot.system.updated import updated
    from openpilot.starpilot.drive_state import evidence
    from openpilot.starpilot.software import fast_update as production

    from openpilot.common.params import Params as NativeParams
    params = NativeParams(str(Path(self.temp.name) / 'params'))
    params.put_bool('IsOffroad', True, block=True)
    source = type('Physical', (), {'allowed': lambda self: True, 'effective': lambda self: False, 'close': lambda self: None})()
    updater = updated.Updater.__new__(updated.Updater)
    updater.params = params
    finalized = Path(self.temp.name) / 'finalized'
    finalized.mkdir()
    marker = finalized / '.overlay_consistent'
    marker.touch()
    overlay = self.repo / '.overlay_init'
    overlay.touch()
    with (
      patch.object(updated, 'BASEDIR', str(self.repo)),
      patch.object(updated, 'FINALIZED', str(finalized)),
      patch.object(updated, 'OVERLAY_INIT', overlay),
      patch.object(updated, 'dismount_overlay'),
      patch.object(updated.HARDWARE, 'get_os_version', return_value='19.8.1'),
      patch.object(evidence, 'PhysicalSource', return_value=source),
      patch.object(production.time, 'sleep'),
    ):
      result = updater.fast_update('Dom', self.previous)
    self.assertEqual(result, 'reboot-requested')
    self.assertEqual(self.git(self.repo, 'rev-parse', 'HEAD'), self.target)
    self.assertFalse(marker.exists())
    self.assertFalse(overlay.exists())
    self.assertEqual(params.get('UpdaterFastState')['stage'], 'complete')
    self.assertTrue(params.get_bool('DoReboot'))
    updated.recover_fast_state(params)
    self.assertEqual(params.get('UpdaterFastState')['stage'], 'complete')
    params.put('UpdaterFastState', {'version': 1, 'stage': 'applying', 'detail': 'Applying fetched commit...'}, block=True)
    updated.recover_fast_state(params)
    self.assertEqual(params.get('UpdaterFastState')['stage'], 'error')
    self.assertEqual(self.git(self.repo, 'rev-parse', 'HEAD'), self.target)
    params.put('UpdaterFastState', {'version': 1, 'stage': 'complete', 'detail': 'Already up to date.'}, block=True)
    updated.recover_fast_state(params)
    self.assertEqual(params.get('UpdaterFastState')['stage'], 'complete')

  def test_expected_commit_changed_rejected_before_fetch(self):
    commands = []

    def traced(command, cwd):
      commands.append(command)
      return owner.run(command, cwd)

    with self.assertRaises(owner.FastUpdateError):
      self.update(expected_commit='1' * 40, run=traced)
    self.assertFalse(any('fetch' in command for command in commands))

  def test_source_only_ui_update_admitted(self):
    folder = self.remote / 'openpilot/starpilot/ui'
    folder.mkdir(parents=True, exist_ok=True)
    (folder / 'runtime_app.py').write_text('value = 1')
    self.git(self.remote, 'add', '.')
    self.git(self.remote, 'commit', '-m', 'UI update')
    self.assertEqual(self.update(), 'reboot-requested')

  def test_vendored_extension_update_and_rollback_preserve_downloaded_model(self):
    self.git(self.remote, 'reset', '--hard', self.previous)
    manifest_path = self.remote / 'upstream-sync.json'
    manifest = json.loads(manifest_path.read_text())
    manifest['dependencies'] = [entry for entry in manifest['dependencies'] if entry['path'] != 'jetlink_repo']
    manifest.pop('vendored_extensions', None)
    if (self.remote / 'jetlink_repo').exists():
      self.git(self.remote, 'rm', '-r', 'jetlink_repo')
    manifest_path.write_text(json.dumps(manifest))
    self.git(self.remote, 'add', '.')
    self.receipt_commit()
    self.previous = self.git(self.remote, 'rev-parse', 'HEAD')
    self.git(self.repo, 'fetch', 'origin', 'Dom')
    self.git(self.repo, 'reset', '--hard', self.previous)
    model = self.repo / 'models' / 'download'
    model.parent.mkdir()
    model.write_bytes(b'downloaded model')

    extension = self.remote / 'jetlink_repo'
    extension.mkdir()
    (extension / 'source.py').write_text('API_VERSION = 1\n')
    manifest['vendored_extensions'] = [{'path': 'jetlink_repo', 'commit': '4' * 40, 'tree': '5' * 40,
                                      'url': 'https://example.invalid/jetlink', 'exclude': []}]
    manifest_path.write_text(json.dumps(manifest))
    self.git(self.remote, 'add', '.')
    self.receipt_commit()
    target = self.git(self.remote, 'rev-parse', 'HEAD')

    self.assertEqual(self.update(), 'reboot-requested')
    self.assertEqual(self.git(self.repo, 'rev-parse', 'HEAD'), target)
    self.assertEqual((self.repo / 'jetlink_repo/source.py').read_text(), 'API_VERSION = 1\n')
    self.assertEqual(model.read_bytes(), b'downloaded model')
    self.assertEqual(self.update(rollback=True), 'reboot-requested')
    self.assertEqual(self.git(self.repo, 'rev-parse', 'HEAD'), self.previous)
    self.assertFalse((self.repo / 'jetlink_repo').exists())
    self.assertEqual(model.read_bytes(), b'downloaded model')
    self.assertEqual(len(self.invalidations), 2)

  def test_native_source_change_rejected_without_artifact_proof(self):
    (self.remote / 'native.cc').write_text('int main() {}')
    self.git(self.remote, 'add', '.')
    self.git(self.remote, 'commit', '-m', 'native update')
    with self.assertRaisesRegex(owner.FastUpdateError, 'full validated update'):
      self.update()
    self.assertEqual(self.git(self.repo, 'rev-parse', 'HEAD'), self.previous)
    self.assertFalse(self.invalidations)

  def receipt_commit(self):
    prebuilt.write_receipt(self.remote)
    self.git(self.remote, 'add', 'prebuilt.json')
    self.git(self.remote, 'commit', '-m', 'validated receipt')

  def test_matching_receipt_admits_native_source_and_artifacts(self):
    (self.remote / 'native.cc').write_text('int source;')
    (self.remote / 'native.so').write_bytes(b'compiled artifact fixture')
    self.git(self.remote, 'add', '.')
    self.receipt_commit()
    self.assertEqual(self.update(), 'reboot-requested')

  def test_receipt_stale_source_rejected(self):
    (self.remote / 'native.cc').write_text('int source;')
    self.git(self.remote, 'add', '.')
    self.receipt_commit()
    (self.remote / 'native.cc').write_text('int changed;')
    self.git(self.remote, 'commit', '-am', 'stale source')
    with self.assertRaisesRegex(owner.FastUpdateError, 'matching build receipt'):
      self.update()
    self.assertFalse(self.invalidations)

  def test_receipt_stale_artifact_rejected(self):
    (self.remote / 'native.so').write_bytes(b'artifact')
    self.git(self.remote, 'add', '.')
    self.receipt_commit()
    (self.remote / 'native.so').write_bytes(b'changed artifact')
    self.git(self.remote, 'commit', '-am', 'stale artifact')
    with self.assertRaisesRegex(owner.FastUpdateError, 'matching build receipt'):
      self.update()
    self.assertFalse(self.invalidations)

  def test_receipt_working_content_and_modes_match_committed_tree(self):
    (self.remote / 'native.cc').write_text('int unstaged;')
    self.git(self.remote, 'add', '.')
    (self.remote / 'native.cc').write_text('int working;')
    (self.remote / 'native.cc').chmod(0o755)
    (self.remote / 'native-link').symlink_to('native.cc')
    self.git(self.remote, 'add', 'native-link')
    prebuilt.write_receipt(self.remote)
    self.git(self.remote, 'add', '.')
    self.git(self.remote, 'commit', '-m', 'receipt content and modes')

    def git(*args):
      return subprocess.check_output(['git', '-C', str(self.remote), *args]).decode()

    self.assertTrue(prebuilt.valid_receipt(git, 'HEAD'))

  def test_missing_prebuilt_rejected_without_removing_local_marker(self):
    self.git(self.remote, 'rm', 'prebuilt')
    self.git(self.remote, 'commit', '-m', 'nonprebuilt')
    with self.assertRaisesRegex(owner.FastUpdateError, 'prebuilt'):
      self.update()
    self.assertTrue((self.repo / 'prebuilt').exists())

  def test_wrong_os_rejected_before_mutation(self):
    with self.assertRaises(owner.FastUpdateError):
      self.update(current_os='19.8.2')
    self.assertEqual(self.git(self.repo, 'rev-parse', 'HEAD'), self.previous)
    self.assertFalse(self.invalidations)
    self.assertFalse(self.params.calls)

  def test_dirty_tracked_source_rejected(self):
    (self.repo / 'openpilot/starpilot/ui/source.py').write_text('local repair')
    with self.assertRaises(owner.FastUpdateError):
      self.update()
    self.assertEqual((self.repo / 'openpilot/starpilot/ui/source.py').read_text(), 'local repair')

  def test_staged_source_rejected(self):
    (self.repo / 'openpilot/starpilot/ui/source.py').write_text('staged repair')
    self.git(self.repo, 'add', 'openpilot/starpilot/ui/source.py')
    with self.assertRaises(owner.FastUpdateError):
      self.update()
    self.assertEqual((self.repo / 'openpilot/starpilot/ui/source.py').read_text(), 'staged repair')
    self.assertFalse(self.invalidations)

  def test_reboot_write_failure_rolls_back(self):
    def failing(*args, **kwargs):
      raise RuntimeError('params write failed')

    with patch.object(self.params, "put_bool", side_effect=failing), self.assertRaisesRegex(RuntimeError, 'params write failed'):
      self.update()
    self.assertEqual(self.git(self.repo, 'rev-parse', 'HEAD'), self.previous)

  def test_fetch_failure_does_not_mutate(self):
    def failing(command, cwd):
      if 'fetch' in command:
        raise RuntimeError('fetch failed')
      return owner.run(command, cwd)

    with self.assertRaisesRegex(RuntimeError, 'fetch failed'):
      self.update(run=failing)
    self.assertEqual(self.git(self.repo, 'rev-parse', 'HEAD'), self.previous)
    self.assertFalse(self.invalidations)

  def test_apply_failure_rolls_back(self):
    failed = False

    def failing(command, cwd):
      nonlocal failed
      if 'reset' in command and command[-1] == self.target and not failed:
        failed = True
        owner.run(command, cwd)
        raise RuntimeError('apply failed after reset')
      return owner.run(command, cwd)

    with self.assertRaisesRegex(RuntimeError, 'apply failed'):
      self.update(run=failing)
    self.assertEqual(self.git(self.repo, 'rev-parse', 'HEAD'), self.previous)
    self.assertEqual((self.repo / 'openpilot/starpilot/ui/source.py').read_text(), 'old')
    self.assertFalse(self.params.calls)

  def test_lost_parked_before_reboot_rolls_back(self):
    states = iter([True, True, True, False])
    with self.assertRaises(owner.FastUpdateError):
      self.update(parked=lambda: next(states))
    self.assertEqual(self.git(self.repo, 'rev-parse', 'HEAD'), self.previous)
    self.assertFalse(self.params.calls)

  def test_lost_parked_before_source_mutation(self):
    states = iter([True, False])
    with self.assertRaises(owner.FastUpdateError):
      self.update(parked=lambda: next(states))
    self.assertEqual(self.git(self.repo, 'rev-parse', 'HEAD'), self.previous)
    self.assertFalse(self.invalidations)

  def test_invalid_vendor_target_rejected_before_checkout(self):
    (self.remote / 'upstream-sync.json').write_text('{}')
    self.git(self.remote, 'commit', '-am', 'invalid')
    with self.assertRaises(ValueError):
      self.update()
    self.assertEqual(self.git(self.repo, 'rev-parse', 'HEAD'), self.previous)
    self.assertFalse(self.invalidations)

  def test_selected_branch_applies_and_rollback_restores_exact_branch_and_commit(self):
    self.git(self.remote, 'checkout', '-b', 'Other')
    (self.remote / 'openpilot/starpilot/ui/source.py').write_text('other')
    self.git(self.remote, 'commit', '-am', 'other branch')
    other = self.git(self.remote, 'rev-parse', 'HEAD')
    stages = []
    arguments = {
      'params': self.params,
      'parked': lambda: True,
      'expected_commit': self.previous,
      'current_os': '19.8.1',
      'invalidate': lambda: None,
      'sleep': lambda seconds: stages.append(('sleep', seconds)),
      'progress': lambda stage, detail: stages.append((stage, detail)),
    }
    self.assertEqual(owner.fast_update(self.repo, 'Other', **arguments), 'reboot-requested')
    self.assertEqual(self.git(self.repo, 'symbolic-ref', '--short', 'HEAD'), 'Other')
    self.assertEqual(self.git(self.repo, 'rev-parse', 'HEAD'), other)
    self.assertEqual(self.git(self.repo, 'config', '--get', 'starpilot.previousVersion'), f'{self.previous} Dom')
    self.assertIn(('sleep', 6.0), stages)
    arguments['expected_commit'] = other
    self.assertEqual(owner.fast_update(self.repo, 'Other', rollback=True, **arguments), 'reboot-requested')
    self.assertEqual(self.git(self.repo, 'symbolic-ref', '--short', 'HEAD'), 'Dom')
    self.assertEqual(self.git(self.repo, 'rev-parse', 'HEAD'), self.previous)

  def test_failed_branch_apply_restores_source_and_previous_version_receipt(self):
    self.git(self.remote, 'branch', 'Other')
    self.git(self.repo, 'update-ref', 'refs/starpilot/previous', self.previous)
    self.git(self.repo, 'config', 'starpilot.previousVersion', f'{self.previous} Retained')

    def failed(command, cwd):
      if 'checkout' in command and 'Other' in command:
        raise subprocess.CalledProcessError(1, command)
      return owner.run(command, cwd)

    with self.assertRaises(subprocess.CalledProcessError):
      owner.fast_update(
        self.repo,
        'Other',
        params=self.params,
        parked=lambda: True,
        expected_commit=self.previous,
        current_os='19.8.1',
        invalidate=lambda: None,
        run=failed,
        sleep=lambda _: None,
      )
    self.assertEqual(self.git(self.repo, 'rev-parse', 'HEAD'), self.previous)
    self.assertEqual(self.git(self.repo, 'config', '--get', 'starpilot.previousVersion'), f'{self.previous} Retained')
    self.assertFalse(self.params.calls)

  def test_incomplete_previous_version_receipt_rejected_without_source_mutation(self):
    self.git(self.repo, 'update-ref', 'refs/starpilot/previous', self.previous)
    self.git(self.repo, 'config', 'starpilot.previousVersion', f"{'1' * 40} Dom")
    with self.assertRaisesRegex(owner.FastUpdateError, 'receipt is incomplete'):
      self.update(rollback=True)
    self.assertEqual(self.git(self.repo, 'rev-parse', 'HEAD'), self.previous)
    self.assertFalse(self.invalidations)
    self.assertFalse(self.params.calls)

  def test_restart_notice_rechecks_parked_and_rolls_back(self):
    waits = []
    parked = [True]

    def notice(seconds):
      waits.append(seconds)
      parked[0] = False

    with self.assertRaises(owner.FastUpdateError):
      self.update(parked=lambda: parked[0], sleep=notice)
    self.assertEqual(waits, [6.0])
    self.assertEqual(self.git(self.repo, 'rev-parse', 'HEAD'), self.previous)
    self.assertFalse(self.params.calls)

  def test_untracked_collision_rejected(self):
    (self.repo / 'new-model').write_bytes(b'model')
    (self.remote / 'new-model').write_text('tracked update')
    self.git(self.remote, 'add', 'new-model')
    self.receipt_commit()
    with self.assertRaisesRegex(owner.FastUpdateError, 'overwrite untracked data'):
      self.update()
    self.assertEqual((self.repo / 'new-model').read_bytes(), b'model')
    self.assertFalse(self.invalidations)

  def test_post_apply_validation_failure_rolls_back(self):
    original = owner.validate_revision

    def validate(repo, revision):
      if revision == 'HEAD':
        raise ValueError('post-check failed')
      return original(repo, revision)

    with patch.object(owner, 'validate_revision', validate):
      with self.assertRaisesRegex(ValueError, 'post-check failed'):
        self.update()
    self.assertEqual(self.git(self.repo, 'rev-parse', 'HEAD'), self.previous)
    self.assertFalse(self.params.calls)


if __name__ == '__main__':
  unittest.main()
