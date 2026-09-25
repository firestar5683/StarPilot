"""Retained-OS launcher/updater checks use only disposable files and fake hardware."""
import os
import re
from pathlib import Path
import subprocess
import sys
import tempfile
from types import ModuleType
import unittest
from unittest.mock import Mock, patch

from openpilot.system.updated.tests.test_vendored_update import load_updater

ROOT = Path(__file__).resolve().parents[4]


def shell_function(path, name):
  source = path.read_text()
  match = re.search(r'function ' + re.escape(name) + r'(?:\(\))? \{', source)
  assert match is not None
  start = match.start()
  return source[start:source.index('\n}\n', start) + 3]


class TestRetainedAgnos(unittest.TestCase):
  def setUp(self):
    self.directory = tempfile.TemporaryDirectory()
    self.addCleanup(self.directory.cleanup)
    self.root = Path(self.directory.name)
    self.environment = self.root / 'launch_env.sh'
    self.environment.write_text('export AGNOS_VERSION="19.8.2"\nexport AGNOS_UPDATE_POLICY="retain"\n')
    self.updater = load_updater()
    self.updater.OVERLAY_MERGED = str(self.root)
    self.updater.set_consistent_flag = Mock()
    self.updater.HARDWARE.get_os_version.return_value = '19.8.2'
    self.flash = Mock()
    self.slot = Mock(return_value=1)
    agnos = ModuleType('openpilot.common.hardware.comma.agnos')
    agnos.flash_agnos_update = self.flash
    agnos.get_target_slot_number = self.slot
    patcher = patch.dict(sys.modules, {agnos.__name__: agnos})
    patcher.start()
    self.addCleanup(patcher.stop)

  def test_retained_match_never_flashes_or_queries_slot(self):
    with patch.dict(os.environ, {'AGNOS_VERSION': 'unexpected', 'AGNOS_UPDATE_POLICY': 'auto'}):
      self.updater.handle_agnos_update()
    self.flash.assert_not_called()
    self.slot.assert_not_called()
    self.updater.set_consistent_flag.assert_not_called()

  def test_retained_mismatch_blocks_finalization_without_flash(self):
    for current in ('19.6.20', '19.8', '', '19.8.2 '):
      with self.subTest(current=current):
        self.updater.HARDWARE.get_os_version.return_value = current
        with self.assertRaisesRegex(RuntimeError, 'No OS update was attempted'):
          self.updater.handle_agnos_update()
        self.updater.set_consistent_flag.assert_called_with(False)
        self.flash.assert_not_called()
        self.slot.assert_not_called()

  def test_other_branch_auto_policy_uses_current_manifest_location(self):
    self.environment.write_text('export AGNOS_VERSION="19.8"\n')
    self.updater.handle_agnos_update()
    self.flash.assert_called_once_with(str(self.root / 'openpilot/common/hardware/comma/agnos.json'), 1, self.updater.cloudlog)
    self.assertTrue((ROOT / 'openpilot/common/hardware/comma/agnos.json').is_file())
    self.updater.set_consistent_flag.assert_called_once_with(False)

  def test_invalid_policy_cannot_finalize_or_flash(self):
    for document in ('export AGNOS_VERSION="19.8.2"\nexport AGNOS_UPDATE_POLICY="unknown"\n',
                     'export AGNOS_VERSION=""\n', 'echo unexpected-output\nexport AGNOS_VERSION="19.8.2"\n'):
      with self.subTest(document=document):
        self.environment.write_text(document)
        with self.assertRaises(ValueError):
          self.updater.handle_agnos_update()
        self.flash.assert_not_called()
        self.slot.assert_not_called()
        self.updater.set_consistent_flag.assert_called_with(False)

  def run_shell(self, function, tail, current):
    version = self.root / 'VERSION'
    version.write_text(current)
    marker = self.root / 'AGNOS'
    marker.touch()
    script = self.root / 'test.sh'
    # Replace only device observations in a copy of the actual function. Every
    # effectful command is a test double; no launch manager or device is run.
    function = function.replace('/VERSION', str(version)).replace('/AGNOS', str(marker))
    script.write_text('''source "$1/launch_env.sh"
DIR="$1"
OPENPILOT_ROOT="$1"
BOLD=''
log="$1/effects"
rm() { echo rm >> "$log"; }
sudo() { echo sudo >> "$log"; }
read() { echo prompt >> "$log"; return 1; }
op_run_command() { echo effect >> "$log"; }
''' + function + '\n' + tail + '\n')
    return subprocess.run(['bash', str(script), str(self.root)], capture_output=True, text=True, timeout=5)

  def test_launcher_refuses_mismatched_os_before_any_effect(self):
    result = self.run_shell(shell_function(ROOT / 'launch_chffrplus.sh', 'agnos_init'), 'agnos_init', '19.8')
    self.assertEqual(result.returncode, 1, result.stderr)
    self.assertIn('No OS update was attempted', result.stdout)
    self.assertFalse((self.root / 'effects').exists())

  def test_developer_helper_retained_match_or_mismatch_never_prompts(self):
    function = shell_function(ROOT / 'tools/op.sh', 'op_check_agnos_update')
    for current, code in (('19.8.2', 0), ('19.8', 1)):
      with self.subTest(current=current):
        result = self.run_shell(function, 'op_check_agnos_update', current)
        self.assertEqual(result.returncode, code, result.stderr)
        self.assertFalse((self.root / 'effects').exists())


if __name__ == '__main__':
  unittest.main()
