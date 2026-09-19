import tempfile
import unittest
from pathlib import Path

from persistent_assets import restore_links


class PersistentAssetsTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.data = Path(self.temp.name)
        self.root = self.data / 'checkout' / 'roadscore'
        self.root.mkdir(parents=True)

    def provision(self):
        for name in ('generated', 'results', 'assets'):
            (self.data / 'roadscore-event-state' / name).mkdir(parents=True)
        (self.data / 'roadscore-event-state/runtime.json').write_text('{}')
        for name in ('weights', 'vae_weights', 'profiles'):
            (self.data / 'roadscore-event-assets/ace' / name).mkdir(parents=True)

    def test_replaced_checkout_reconnects_without_copying_and_is_idempotent(self):
        self.provision()
        marker = self.data / 'roadscore-event-assets/ace/weights/model'
        marker.write_bytes(b'preserved')
        self.assertEqual(len(restore_links(self.root, self.data)), 7)
        self.assertEqual(restore_links(self.root, self.data), [])
        self.assertEqual((self.root / 'experiments/ace_chestnut_20260916/weights/model').read_bytes(), b'preserved')

    def test_optional_native_cache_and_build_reconnected(self):
        self.provision()
        for name in ('routes', 'native_build'):
            (self.data / 'roadscore-event-state' / name).mkdir()
        self.assertEqual(len(restore_links(self.root, self.data)), 9)
        self.assertTrue((self.root / 'routes').is_symlink())
        self.assertTrue((self.root / 'native_build').is_symlink())

    def test_existing_data_is_never_overwritten_or_partially_modified(self):
        self.provision()
        (self.root / 'runtime.json').write_text('local settings')
        with self.assertRaisesRegex(RuntimeError, 'overwrite'):
            restore_links(self.root, self.data)
        self.assertEqual((self.root / 'runtime.json').read_text(), 'local settings')
        self.assertFalse((self.root / 'generated').exists())

    def test_wrong_link_rejected_without_modifications(self):
        self.provision()
        (self.root / 'results').symlink_to(self.data / 'other')
        with self.assertRaisesRegex(RuntimeError, 'another link'):
            restore_links(self.root, self.data)
        self.assertFalse((self.root / 'generated').exists())

    def test_incomplete_persistent_installation_rejected_before_linking(self):
        self.provision()
        (self.data / 'roadscore-event-assets/ace/profiles').rmdir()
        with self.assertRaisesRegex(RuntimeError, 'missing'):
            restore_links(self.root, self.data)
        self.assertFalse((self.root / 'generated').exists())

    def test_unprovisioned_installation_unchanged(self):
        self.assertEqual(restore_links(self.root, self.data), [])
        self.assertEqual(list(self.root.iterdir()), [])


if __name__ == '__main__':
    unittest.main()
