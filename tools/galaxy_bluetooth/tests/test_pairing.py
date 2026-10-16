import asyncio
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "bridge"))
from pairing import ensure_key, load_key, rotate_key, qr_payload
from server import Gateway
from protocol import packets, seal
from dbus_next import Variant, DBusError


class PairingTests(unittest.IsolatedAsyncioTestCase):
    async def test_existing_key_preserved_rotation_revokes_old_requests(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "pairing.json"
            old = ensure_key(path)
            self.assertEqual(ensure_key(path), old)
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            self.assertEqual(json.loads(qr_payload(old))["key"], old.hex())

            class Proxy:
                calls = 0
                def handle(self, request):
                    self.calls += 1
                    return {"id": request["id"], "status": 200, "headers": {}, "body": ""}

            proxy = Proxy()
            gateway = Gateway(old, proxy, path)
            options = {"device": Variant("o", "/org/bluez/hci0/dev_test")}
            state = gateway.session(options)
            new = rotate_key(path)
            self.assertNotEqual(old, new)
            gateway.refresh_key()
            self.assertTrue(state.closed)
            self.assertFalse(gateway.sessions)
            self.assertEqual(load_key(path), new)
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)

            # Old credentials cannot change settings, even with a fresh challenge.
            fresh = gateway.session(options)
            request = {"id": "test", "session": fresh.challenge.hex(), "counter": 1,
                       "path": "/api/params", "method": "PUT", "body": ""}
            for packet in packets(seal(request, old, "request")):
                gateway.write(packet, options)
            await fresh.task
            self.assertEqual(proxy.calls, 0)
            for packet in packets(seal(request, new, "request")):
                gateway.write(packet, options)
            await fresh.task
            self.assertEqual(proxy.calls, 1)

    async def test_bad_or_missing_file_revokes_sessions_and_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "pairing.json"
            key = ensure_key(path)
            gateway = Gateway(key, None, path)
            options = {"device": Variant("o", "/org/bluez/hci0/dev_test")}
            state = gateway.session(options)
            os.chmod(path, 0o644)
            with self.assertRaises(DBusError):
                gateway.session(options)
            self.assertTrue(state.closed)
            with self.assertRaises(ValueError):
                ensure_key(path)  # Never silently replace a damaged existing credential.
            path.unlink()
            with self.assertRaises(DBusError):
                gateway.session(options)

    async def test_symlink_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "pairing.json"
            ensure_key(path)
            link = Path(directory) / "link.json"
            link.symlink_to(path)
            with self.assertRaises(OSError):
                load_key(link)


if __name__ == "__main__":
    unittest.main()
