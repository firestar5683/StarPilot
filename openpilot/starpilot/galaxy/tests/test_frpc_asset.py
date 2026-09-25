import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from openpilot.starpilot.galaxy import frpc_asset


class FrpcAssetTests(unittest.TestCase):
  def test_bundled_linux_arm64_binary_matches_pinned_release(self):
    with patch.object(frpc_asset.platform, 'system', return_value='Linux'), \
         patch.object(frpc_asset.platform, 'machine', return_value='aarch64'):
      self.assertEqual(frpc_asset.bundled_frpc_path(), str(frpc_asset.FRPC_BINARY))
    self.assertEqual(hashlib.sha256(frpc_asset.FRPC_BINARY.read_bytes()).hexdigest(), frpc_asset.FRPC_BINARY_SHA256)
    self.assertIn('Apache License', (frpc_asset.FRPC_BINARY.parent / 'LICENSE.frp').read_text())

  def test_unsupported_platform_or_modified_binary_is_rejected(self):
    with patch.object(frpc_asset.platform, 'system', return_value='Darwin'):
      self.assertIsNone(frpc_asset.bundled_frpc_path())
    with tempfile.TemporaryDirectory() as temporary:
      altered = Path(temporary) / 'frpc_linux_arm64'
      altered.write_bytes(b'not the pinned frpc')
      altered.chmod(0o755)
      with patch.object(frpc_asset.platform, 'system', return_value='Linux'), \
           patch.object(frpc_asset.platform, 'machine', return_value='aarch64'), \
           patch.object(frpc_asset, 'FRPC_BINARY', altered):
        self.assertIsNone(frpc_asset.bundled_frpc_path())
