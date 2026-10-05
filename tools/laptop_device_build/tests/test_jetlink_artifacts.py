"""Separate Jetlink artifact admission rejects stale or modified captures."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tools.laptop_device_build import jetlink_artifacts as artifacts


class TestJetlinkArtifacts(unittest.TestCase):
  def setUp(self):
    self.temp = tempfile.TemporaryDirectory()
    self.addCleanup(self.temp.cleanup)
    self.root = Path(self.temp.name) / 'root'
    self.package = Path(self.temp.name) / 'package'
    self.root.mkdir()
    self.package.mkdir()
    self.source = {'jetlink_repo/jetlink/openpilot/warp.py': 'known-source'}
    self.rows = {}
    for name in artifacts.warp_names():
      p = self.package / name
      p.write_bytes(('independently-captured:' + name).encode())
      self.rows[name] = {'sha256': artifacts.sha(p), 'size': p.stat().st_size}
    self.manifest = {'version': 1, 'sources': self.source, 'artifacts': self.rows}
    self.write_manifest()
    self.target = self.root / artifacts.MODEL_DIR / artifacts.warp_names()[0]

  def write_manifest(self):
    (self.package / 'manifest.json').write_text(json.dumps(self.manifest))

  def admit(self):
    # Backend capture validation belongs to the actual QCOM build. This test
    # checks the independent source/digest/geometry guards around that boundary.
    with patch.object(artifacts, 'sources', return_value=self.source), patch.object(artifacts, 'require_jetlink_qcom_pickle') as capture:
      artifacts.import_artifact(self.package, self.root, self.target)
      return capture

  def test_verified_capture_is_copied_only_to_declared_geometry(self):
    capture = self.admit()
    self.assertEqual(self.target.read_bytes(), (self.package / self.target.name).read_bytes())
    capture.assert_called_once_with(self.package / self.target.name)
    self.target = self.root / 'other' / self.target.name
    with self.assertRaisesRegex(ValueError, 'Unexpected'):
      self.admit()

  def test_changed_bytes_or_source_never_replaces_target(self):
    self.admit()
    previous = self.target.read_bytes()
    (self.package / self.target.name).write_bytes(b'changed')
    with self.assertRaisesRegex(ValueError, 'digest or size'):
      self.admit()
    self.assertEqual(self.target.read_bytes(), previous)
    self.manifest['sources'] = {'jetlink_repo/jetlink/openpilot/warp.py': 'old-source'}
    self.write_manifest()
    with self.assertRaisesRegex(ValueError, 'source closure'):
      self.admit()
    self.assertEqual(self.target.read_bytes(), previous)

  def test_incomplete_or_extra_geometry_is_rejected(self):
    for change in ('remove', 'extra'):
      with self.subTest(change=change):
        rows = dict(self.rows)
        if change == 'remove':
          rows.pop(artifacts.warp_names()[-1])
        else:
          rows['jetlink_warp_unsupported.pkl'] = {}
        self.manifest['artifacts'] = rows
        self.write_manifest()
        with self.assertRaisesRegex(ValueError, 'geometry set'):
          self.admit()


class TestBareJetlinkCapture(unittest.TestCase):
  def test_shipped_qcom_captures_have_exact_input_and_output_signatures(self):
    from tools.laptop_device_build.jetlink_pickle import require_jetlink_qcom_pickle
    root = Path(__file__).resolve().parents[3]
    for name in artifacts.warp_names():
      with self.subTest(name=name):
        require_jetlink_qcom_pickle(root / artifacts.MODEL_DIR / name)

  def test_foreign_backend_dtype_and_wrong_geometry_are_rejected(self):
    from tools.laptop_device_build.jetlink_pickle import require_jetlink_qcom_pickle
    root = Path(__file__).resolve().parents[3]
    original = (root / artifacts.MODEL_DIR / 'jetlink_warp_1344x760_512x256.pkl').read_bytes()
    cases = (
      ('jetlink_warp_1344x760_512x256.pkl', original.replace(b'QCOM', b'AMD!', 1)),
      ('jetlink_warp_1344x760_512x256.pkl', original.replace(b'unsigned char', b'unsigned long', 1)),
      ('jetlink_warp_1344x760_1024x512.pkl', original),
      ('jetlink_warp_1928x1208_512x256.pkl', original),
    )
    with tempfile.TemporaryDirectory() as directory:
      for name, data in cases:
        with self.subTest(name=name, changed=data != original):
          path = Path(directory) / name
          path.write_bytes(data)
          with self.assertRaises(ValueError):
            require_jetlink_qcom_pickle(path)

  def test_bare_capture_does_not_relax_ordinary_wrapped_validator(self):
    from tools.laptop_device_build.validate_artifacts import require_qcom_pickle
    root = Path(__file__).resolve().parents[3]
    with self.assertRaises(ValueError):
      require_qcom_pickle(root / artifacts.MODEL_DIR / artifacts.warp_names()[0])

  def test_unexpected_pickle_globals_are_rejected_without_execution(self):
    import pickle
    from tools.laptop_device_build.jetlink_pickle import require_jetlink_qcom_pickle
    with tempfile.TemporaryDirectory() as directory:
      path = Path(directory) / artifacts.warp_names()[0]
      path.write_bytes(pickle.dumps(eval))
      with self.assertRaisesRegex(ValueError, 'Unexpected Jetlink pickle global'):
        require_jetlink_qcom_pickle(path)
