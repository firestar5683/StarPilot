import json
import os
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "bridge"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "vendor"))
from pairing import app_only, link_address, remove_by_address, add_phone, ensure_store, forget_all, introduce, load_keys, load_phones, remove_phone, LEGACY_ID
from server import Gateway
from protocol import packets, seal
from dbus_next import Variant, DBusError


class Proxy:
  def __init__(self):
    self.calls = 0

  def handle(self, request):
    self.calls += 1
    return {"id": request["id"], "status": 200, "headers": {}, "body": ""}


async def send(gateway, options, key, counter=1):
  state = gateway.session(options)
  request = {"id": "test", "session": state.challenge.hex(), "counter": counter, "path": "/api/params", "method": "PUT", "body": ""}
  for packet in packets(seal(request, key, "request")):
    gateway.write(packet, options)
  await state.task
  return state


class PairingTests(unittest.IsolatedAsyncioTestCase):
  async def test_each_phone_has_its_own_key_and_can_be_forgotten_alone(self):
    with tempfile.TemporaryDirectory() as directory:
      path = Path(directory) / "pairing.json"
      self.assertEqual(ensure_store(path), [])
      self.assertEqual(path.stat().st_mode & 0o777, 0o600)
      iphone_id, iphone = add_phone("iPhone", path)
      _, android = add_phone("Android phone", path)
      self.assertNotEqual(iphone, android)

      proxy = Proxy()
      gateway = Gateway(load_keys(path), proxy, path)
      iphone_options = {"device": Variant("o", "/org/bluez/hci0/dev_iphone")}
      android_options = {"device": Variant("o", "/org/bluez/hci0/dev_android")}
      iphone_state = await send(gateway, iphone_options, iphone)
      android_state = await send(gateway, android_options, android)
      self.assertEqual(proxy.calls, 2)
      self.assertTrue(all(phone["last_used"] for phone in load_phones(path)))

      remove_phone(iphone_id, path)
      gateway.refresh_key()
      self.assertTrue(iphone_state.closed)
      self.assertFalse(android_state.closed)  # the other phone stays connected

      # The forgotten phone's key cannot change settings, even with a fresh challenge.
      await send(gateway, iphone_options, iphone)
      self.assertEqual(proxy.calls, 2)
      await send(gateway, {"device": Variant("o", "/org/bluez/hci0/dev_android_again")}, android)
      self.assertEqual(proxy.calls, 3)

      forget_all(path)
      with self.assertRaises(DBusError):
        gateway.session(android_options)
      self.assertTrue(android_state.closed)

  async def test_phone_names_itself_and_replaces_its_old_entry(self):
    with tempfile.TemporaryDirectory() as directory:
      path = Path(directory) / "pairing.json"
      old_id, _ = add_phone("Phone", path)
      other_id, _ = add_phone("Phone", path)
      new_id, new = add_phone("Phone", path)
      proxy = Proxy()
      gateway = Gateway(load_keys(path), proxy, path)
      options = {"device": Variant("o", "/org/bluez/hci0/dev_iphone")}
      state = gateway.session(options)
      request = {"id": "t", "session": state.challenge.hex(), "counter": 1, "path": "/api/params", "method": "GET", "body": "",
                 "phone": {"name": "Danny\u2019s iPhone\n", "replaces": old_id}}
      for packet in packets(seal(request, new, "request")):
        gateway.write(packet, options)
      await state.task
      phones = {phone["id"]: phone for phone in load_phones(path)}
      self.assertEqual(set(phones), {other_id, new_id})
      self.assertEqual(phones[new_id]["label"], "Danny\u2019s iPhone")
      self.assertEqual(proxy.calls, 1)
      # A phone can't drop the shared pre-update entry or itself, and bad ids are ignored.
      self.assertFalse(introduce(new_id, replaces=new_id, path=path))
      self.assertFalse(introduce(new_id, replaces="legacy", path=path))
      self.assertFalse(introduce(new_id, replaces="../../x", path=path))

  async def test_single_key_file_from_before_update_still_works(self):
    with tempfile.TemporaryDirectory() as directory:
      path = Path(directory) / "pairing.json"
      key = os.urandom(32)
      path.write_text(json.dumps({"key": key.hex()}))
      os.chmod(path, 0o600)
      self.assertEqual(load_keys(path), {LEGACY_ID: key})
      proxy = Proxy()
      gateway = Gateway(load_keys(path), proxy, path)
      await send(gateway, {"device": Variant("o", "/org/bluez/hci0/dev_old")}, key)
      self.assertEqual(proxy.calls, 1)
      add_phone("iPhone", path)  # rewrites in the new format and keeps the old phones
      self.assertEqual(load_keys(path)[LEGACY_ID], key)
      self.assertEqual(len(load_keys(path)), 2)

  async def test_bad_or_missing_file_revokes_sessions_and_fails_closed(self):
    with tempfile.TemporaryDirectory() as directory:
      path = Path(directory) / "pairing.json"
      add_phone("iPhone", path)
      gateway = Gateway(load_keys(path), None, path)
      options = {"device": Variant("o", "/org/bluez/hci0/dev_test")}
      state = gateway.session(options)
      os.chmod(path, 0o644)
      with self.assertRaises(DBusError):
        gateway.session(options)
      self.assertTrue(state.closed)
      with self.assertRaises(ValueError):
        add_phone("iPhone", path)  # Never silently replace a damaged existing credential.
      path.unlink()
      with self.assertRaises(DBusError):
        gateway.session(options)

  async def test_symlink_is_rejected(self):
    with tempfile.TemporaryDirectory() as directory:
      path = Path(directory) / "pairing.json"
      add_phone("iPhone", path)
      link = Path(directory) / "link.json"
      link.symlink_to(path)
      with self.assertRaises(OSError):
        load_keys(link)

  def test_forgetting_a_bluetooth_device_forgets_its_app_key_only(self):
    with tempfile.TemporaryDirectory() as directory:
      path = Path(directory) / "pairing.json"
      first_id, _ = add_phone("Pixel", path)
      second_id, second = add_phone("iPhone", path)
      self.assertFalse(link_address(first_id, "not an address", path))
      self.assertTrue(link_address(first_id, "11:22:33:44:55:66", path))
      self.assertEqual([phone["id"] for phone in app_only(path)], [second_id])
      self.assertEqual(remove_by_address("aa:bb:cc:dd:ee:ff", path), 0)
      self.assertEqual(remove_by_address("11:22:33:44:55:66", path), 1)
      self.assertEqual(list(load_keys(path).values()), [second])

  def test_address_survives_rewrites_and_is_never_trusted_when_malformed(self):
    with tempfile.TemporaryDirectory() as directory:
      path = Path(directory) / "pairing.json"
      phone_id, _ = add_phone("Pixel", path)
      link_address(phone_id, "11:22:33:44:55:66", path)
      add_phone("Other", path)
      self.assertEqual(load_phones(path)[0]["bt_address"], "11:22:33:44:55:66")
      raw = json.loads(path.read_text())
      raw["phones"][0]["bt_address"] = "garbage"
      path.write_text(json.dumps(raw))
      self.assertNotIn("bt_address", load_phones(path)[0])


if __name__ == "__main__":
  unittest.main()
