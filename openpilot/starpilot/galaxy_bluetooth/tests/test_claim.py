import hashlib
import hmac
import json
from pathlib import Path
import struct
import sys
import tempfile
import time
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "bridge"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "vendor"))
from Crypto.Cipher import AES
from Crypto.PublicKey import ECC
from dbus_next import DBusError, Variant

import claim
from pairing import ensure_store, load_keys, load_phones
from protocol import Assembler, packets, seal
from server import Gateway


class Proxy:
  calls = 0
  def handle(self, request):
    self.calls += 1
    return {"id": request["id"], "status": 200, "headers": {}, "body": ""}


def phone_request(name="Pixel 8"):
  private = ECC.generate(curve="P-256")
  public = b"\x04" + int(private.pointQ.x).to_bytes(32, "big") + int(private.pointQ.y).to_bytes(32, "big")
  return private, claim.REQUEST_MAGIC + public + name.encode()


def phone_open(private, body, challenge):
  """What an app does with the reply: the same derive/unseal on the phone side."""
  assert body[:4] == claim.REPLY_MAGIC
  server_public, nonce, rest = body[4:69], body[69:81], body[81:]
  key = claim.derive(int(private.d), server_public, challenge)
  cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)
  cipher.update(claim.AAD)
  return json.loads(cipher.decrypt_and_verify(rest[:-16], rest[-16:]))


class ClaimWindowTests(unittest.TestCase):
  def setUp(self):
    self.dir = tempfile.TemporaryDirectory()
    self.path = Path(self.dir.name) / "claim.json"

  def tearDown(self):
    self.dir.cleanup()

  def test_window_opens_expires_and_is_private(self):
    self.assertIsNone(claim.window(self.path))
    claim.arm("AA:BB:CC:DD:EE:FF", "comma", self.path, seconds=60, now=1000)
    self.assertEqual(self.path.stat().st_mode & 0o777, 0o600)
    self.assertIsNotNone(claim.window(self.path, now=1059))
    self.assertIsNone(claim.window(self.path, now=1060))

  def test_finish_closes_the_window_once(self):
    claim.arm("AA:BB:CC:DD:EE:FF", "comma", self.path)
    self.assertTrue(claim.finish("Pixel 8", "0a1b2c3d", self.path))
    self.assertFalse(claim.finish("Other", "ffffffff", self.path))
    self.assertIsNone(claim.window(self.path))
    self.assertEqual(claim.status(self.path), {"claimed": "Pixel 8", "paired": False})

  def test_app_and_music_in_one_window_link_once_in_either_order(self):
    for first in ("app", "music"):
      claim.arm("AA:BB:CC:DD:EE:FF", "comma", self.path, now=time.monotonic())
      steps = {"app": lambda: claim.finish("Pixel 8", "0a1b2c3d", self.path),
               "music": lambda: claim.note_paired("11:22:33:44:55:66", self.path)}
      steps[first]()
      self.assertIsNone(claim.take_link(self.path))
      steps["music" if first == "app" else "app"]()
      self.assertEqual(claim.take_link(self.path), ("0a1b2c3d", "11:22:33:44:55:66"))
      self.assertIsNone(claim.take_link(self.path))

  def test_music_pairing_after_the_window_ends_is_late_but_ignored_when_very_late(self):
    claim.arm("AA:BB:CC:DD:EE:FF", "comma", self.path, seconds=60, now=1000)
    self.assertTrue(claim.note_paired("11:22:33:44:55:66", self.path, now=1100))
    self.assertFalse(claim.note_paired("11:22:33:44:55:66", self.path, now=1200))

  def test_view_counts_down_and_reports_the_claim(self):
    self.assertEqual(claim.view(self.path, now=1000), {"open": False, "left": 0, "claimed": "", "paired": False})
    claim.arm("AA:BB:CC:DD:EE:FF", "comma", self.path, seconds=120, now=1000)
    self.assertEqual(claim.view(self.path, now=1000.5), {"open": True, "left": 120, "claimed": "", "paired": False})
    start = time.monotonic()
    claim.arm("AA:BB:CC:DD:EE:FF", "comma", self.path, seconds=120, now=start)
    claim.finish("Pixel 8", "0a1b2c3d", self.path)
    claim.note_paired("11:22:33:44:55:66", self.path, now=start + 10)
    self.assertEqual(claim.view(self.path, now=start + 60), {"open": True, "left": 60, "claimed": "Pixel 8", "paired": True})
    self.assertEqual(claim.view(self.path, now=start + 130)["open"], False)
    self.assertEqual(claim.view(self.path, now=start + 181), {"open": False, "left": 0, "claimed": "", "paired": False})

  def test_clear_and_missing_file(self):
    claim.arm("AA:BB:CC:DD:EE:FF", "comma", self.path)
    claim.clear(self.path)
    claim.clear(self.path)
    self.assertIsNone(claim.window(self.path))
    self.assertIsNone(claim.window(None))

  def test_requests_must_be_well_formed(self):
    _, good = phone_request()
    self.assertEqual(claim.parse_request(good)[1], "Pixel 8")
    for bad in (b"GCL1", b"XXXX" + good[4:], good[:4] + b"\x02" + good[5:], good[:30]):
      with self.assertRaises(ValueError):
        claim.parse_request(bad)
    with self.assertRaises(ValueError):
      claim.validate(b"\x04" + bytes(64))


class ClaimGatewayTests(unittest.IsolatedAsyncioTestCase):
  def setUp(self):
    self.dir = tempfile.TemporaryDirectory()
    root = Path(self.dir.name)
    self.keys = root / "pairing.json"
    self.claim = root / "claim.json"
    ensure_store(self.keys)
    self.proxy = Proxy()
    self.gateway = Gateway(load_keys(self.keys), self.proxy, self.keys, self.claim)
    self.options = {"device": Variant("o", "/org/bluez/hci0/dev_01_02_03_04_05_06"), "mtu": Variant("q", 185)}

  def tearDown(self):
    self.dir.cleanup()

  async def send(self, data):
    state = self.gateway.session(self.options, fresh=True)
    for packet in packets(struct.pack(">I", len(data)) + data):
      self.gateway.write(packet, self.options)
    await state.task
    return state

  def read_reply(self, state):
    assembler, result = Assembler(), None
    while state.index < len(state.response):
      result = assembler.add(self.gateway.read(self.options))
    return result

  async def test_no_window_means_no_session_and_no_key(self):
    with self.assertRaises(DBusError):
      self.gateway.session(self.options, fresh=True)
    self.assertEqual(load_phones(self.keys), [])

  async def test_window_hands_one_phone_its_key(self):
    claim.arm("AA:BB:CC:DD:EE:FF", "comma", self.claim)
    private, data = phone_request()
    state = await self.send(data)
    reply = phone_open(private, self.read_reply(state), state.challenge)
    self.assertEqual(reply["adapterAddress"], "AA:BB:CC:DD:EE:FF")
    phones = load_phones(self.keys)
    self.assertEqual([(p["id"], p["key"].hex(), p["label"]) for p in phones], [(reply["id"], reply["key"], "Pixel 8")])
    self.assertEqual(claim.status(self.claim), {"claimed": "Pixel 8", "paired": False})
    # The same connection keeps working with the new key, and the key change does not close it.
    self.gateway.refresh_key()
    self.assertIs(self.gateway.sessions[self.options["device"].value], state)
    # A second phone in the same window is refused.
    _, second = phone_request("Intruder")
    state2 = await self.send(second)
    self.assertFalse(state2.response)
    self.assertEqual(len(load_phones(self.keys)), 1)

  async def test_music_bond_made_first_links_the_claimed_phone(self):
    claim.arm("AA:BB:CC:DD:EE:FF", "comma", self.claim)
    claim.note_paired("11:22:33:44:55:66", self.claim)
    private, data = phone_request()
    state = await self.send(data)
    reply = phone_open(private, self.read_reply(state), state.challenge)
    self.assertEqual(load_phones(self.keys)[0]["bt_address"], "11:22:33:44:55:66")
    self.assertEqual(load_phones(self.keys)[0]["id"], reply["id"])

  async def test_claimed_key_passes_the_normal_handshake(self):
    claim.arm("AA:BB:CC:DD:EE:FF", "comma", self.claim)
    private, data = phone_request()
    state = await self.send(data)
    key = bytes.fromhex(phone_open(private, self.read_reply(state), state.challenge)["key"])
    self.gateway.refresh_key()
    state = self.gateway.session(self.options, fresh=True)
    request = {"id": "a", "session": state.challenge.hex(), "counter": 1, "path": "/_bridge/health", "method": "GET", "body": ""}
    for packet in packets(seal(request, key, "request")):
      self.gateway.write(packet, self.options)
    await state.task
    self.assertTrue(state.response)

  async def test_expired_window_and_bad_points_are_refused(self):
    claim.arm("AA:BB:CC:DD:EE:FF", "comma", self.claim, seconds=60, now=time.monotonic() - 61)
    with self.assertRaises(DBusError):
      self.gateway.session(self.options, fresh=True)
    claim.arm("AA:BB:CC:DD:EE:FF", "comma", self.claim)
    state = await self.send(claim.REQUEST_MAGIC + b"\x04" + bytes(64))
    self.assertFalse(state.response)
    self.assertEqual(load_phones(self.keys), [])
    self.assertIsNotNone(claim.window(self.claim))  # a bad request does not use up the window

  async def test_gateway_without_claim_path_is_unchanged(self):
    plain = Gateway({}, self.proxy, self.keys)
    with self.assertRaises(DBusError):
      plain.session(self.options, fresh=True)

  def test_derive_matches_rfc5869(self):
    a, b = ECC.generate(curve="P-256"), ECC.generate(curve="P-256")
    def pub(k):
      return b"\x04" + int(k.pointQ.x).to_bytes(32, "big") + int(k.pointQ.y).to_bytes(32, "big")
    salt = bytes(range(16))
    self.assertEqual(claim.derive(int(a.d), pub(b), salt), claim.derive(int(b.d), pub(a), salt))
    secret = int((b.pointQ * int(a.d)).x).to_bytes(32, "big")
    prk = hmac.new(salt, secret, hashlib.sha256).digest()
    self.assertEqual(claim.derive(int(a.d), pub(b), salt), hmac.new(prk, b"galaxy-claim-v1\x01", hashlib.sha256).digest())


if __name__ == "__main__":
  unittest.main()
