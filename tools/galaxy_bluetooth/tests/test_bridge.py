import asyncio
import base64
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import struct
import sys
import threading
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "bridge"))
from dbus_next import Variant
from protocol import Assembler, MAX_BODY, MAX_FRAME, open_message, packets, seal
from proxy import GalaxyProxy, PARAMS_SNAPSHOT_LIMIT, validate_target
from server import Application, Characteristic, GattService, Gateway, SERVICE_PATH

KEY = bytes(range(32))


class ProtocolTests(unittest.TestCase):
    def test_roundtrip_all_att_sizes_and_binary_body(self):
        value = {"body": base64.b64encode(bytes(range(256)) * 32).decode(), "unicode": "Galaxy ✨", "status": 200}
        frame = seal(value, KEY, "response")
        for size in (20, 64, 180):
            assembler = Assembler()
            decoded = None
            for packet in packets(frame, size):
                self.assertLessEqual(len(packet), size)
                decoded = assembler.add(packet)
            self.assertEqual(open_message(decoded, KEY, "response"), value)

    def test_ciphertext_tamper_wrong_key_and_direction(self):
        message = seal({"id": "test"}, KEY, "request")[4:]
        for data, key, direction in [(message[:-1] + bytes([message[-1] ^ 1]), KEY, "request"),
                                     (message, bytes(32), "request"), (message, KEY, "response")]:
            with self.assertRaises(ValueError):
                open_message(data, key, direction)

    def test_compression_and_bounded_frames(self):
        frame = seal({"data": "parameter" * 20000}, KEY, "response")
        self.assertLess(len(frame), 1000)
        with self.assertRaises(ValueError):
            Assembler().add(b"\x01" + struct.pack(">I", 0) + struct.pack(">I", MAX_FRAME + 1))
        with self.assertRaises(ValueError):
            Assembler().add(b"\x01" + struct.pack(">I", 1) + b"bad")

    def test_reject_trailing_frame_bytes(self):
        frame = seal({"id": "a"}, KEY, "request")
        with self.assertRaises(ValueError):
            Assembler().add(b"\x01" + bytes(4) + frame + b"extra")


class Fixture(BaseHTTPRequestHandler):
    seen = []
    def log_message(self, *args):
        pass

    def respond(self, status, body, content_type="application/json", extra=None):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        for key, value in (extra or {}).items():
            self.send_header(key, value)
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        Fixture.seen.append(("GET", self.path, dict(self.headers)))
        if self.path == "/api/redirect":
            self.respond(302, b"", extra={"Location": "http://example.com/"})
        elif self.path == "/api/large":
            self.respond(200, b"x" * (MAX_BODY + 1))
        elif self.path == "/api/video":
            self.respond(200, b"video", "video/mp4")
        elif self.path == "/api/routes":
            self.respond(200, b'data: {"progress":100,"routes":[]}\n\n', "text/event-stream")
        elif self.path == "/api/continuous":
            self.respond(200, b'data: waiting\n\n', "text/event-stream")
        elif self.path == "/api/binary":
            self.respond(200, bytes(range(256)), "image/jpeg")
        elif self.path == "/api/params/all":
            self.respond(200, json.dumps({"Metric": True, "LanguageSetting": "en",
                                         "LongitudinalPersonalityProfiles": {"custom": [1, 2, 3]},
                                         "LiveTorqueParameters": "learning history" * 110000}).encode())
        elif self.path == "/api/params/all?remaining-large":
            self.respond(200, json.dumps({"Metric": True, "OtherValue": "x" * MAX_BODY}).encode())
        elif self.path == "/api/params/all?upstream-large":
            self.respond(200, b"x" * (PARAMS_SNAPSHOT_LIMIT + 1))
        elif self.path == "/api/params/all?invalid":
            self.respond(200, b"[1, 2, 3]")
        else:
            self.respond(200, b'{"online":true}')

    def do_PUT(self):
        body = self.rfile.read(int(self.headers.get("Content-Length", "0")))
        Fixture.seen.append(("PUT", self.path, body))
        self.respond(200, body)


class ProxyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), Fixture)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.proxy = GalaxyProxy(cls.server.server_port)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def request(self, path, method="GET", body=b"", headers=None):
        return self.proxy.handle({"id": "request", "path": path, "method": method,
                                  "body": base64.b64encode(body).decode(), "headers": headers or {}})

    def test_forwards_read_and_setting_change(self):
        self.assertEqual(self.request("/api/device/status")["status"], 200)
        body = b'{"key":"Metric","value":true}'
        result = self.request("/api/params", "PUT", body, {"Content-Type": "application/json"})
        self.assertEqual(base64.b64decode(result["body"]), body)
        self.assertEqual(Fixture.seen[-1], ("PUT", "/api/params", body))

    def test_large_learning_history_does_not_block_toggles(self):
        result = self.request("/api/params/all")
        self.assertEqual(result["status"], 200)
        data = base64.b64decode(result["body"])
        self.assertLess(len(data), MAX_BODY)
        self.assertEqual(json.loads(data), {"Metric": True, "LanguageSetting": "en",
                                           "LongitudinalPersonalityProfiles": {"custom": [1, 2, 3]}})
        assembler = Assembler()
        for packet in packets(seal(result, KEY, "response")):
            message = assembler.add(packet)
        self.assertEqual(open_message(message, KEY, "response"), result)

    def test_parameter_snapshot_is_still_bounded_and_requires_an_object(self):
        self.assertEqual(self.request("/api/params/all?remaining-large")["status"], 413)
        self.assertEqual(self.request("/api/params/all?upstream-large")["status"], 413)
        self.assertEqual(self.request("/api/params/all?invalid")["status"], 502)

    def test_preserves_query_binary_sse_and_filters_headers(self):
        result = self.request("/api/params?key=Metric", headers={"Cookie": "a=b", "Host": "bad", "Authorization": "bad"})
        self.assertEqual(result["status"], 200)
        headers = Fixture.seen[-1][2]
        self.assertEqual(headers["Cookie"], "a=b")
        self.assertNotIn("Authorization", headers)
        self.assertNotEqual(headers["Host"], "bad")
        self.assertEqual(base64.b64decode(self.request("/api/binary")["body"]), bytes(range(256)))
        stream = self.request("/api/routes")
        self.assertEqual(stream["headers"]["content-type"], "text/event-stream")
        self.assertIn(b"progress", base64.b64decode(stream["body"]))

    def test_rejects_external_urls_and_path_traversal(self):
        for target in ("http://evil/api/x", "//evil/api/x", "/api/../etc", "/api/%2e%2e/etc",
                       "/api/%252e%252e/etc", "/api/a%0d%0aHost:evil", "/api/a\\b", "/etc/passwd"):
            self.assertEqual(self.request(target)["status"], 400, target)

    def test_size_media_and_redirect_limits(self):
        self.assertEqual(self.request("/api/large")["status"], 413)
        self.assertEqual(self.request("/api/video")["status"], 501)
        self.assertEqual(self.request("/api/redirect")["status"], 502)
        self.assertEqual(self.request("/api/continuous")["status"], 501)
        self.assertEqual(self.request("/api/screen_recordings/download/foo")["status"], 501)


class CountingProxy:
    def __init__(self):
        self.calls = 0
    def handle(self, request):
        self.calls += 1
        return {"id": request["id"], "status": 200, "headers": {}, "body": ""}


class GatewayTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.proxy = CountingProxy()
        self.gateway = Gateway(KEY, self.proxy)
        self.options = {"device": Variant("o", "/org/bluez/hci0/dev_01_02_03_04_05_06"), "mtu": Variant("q", 185)}
        self.state = self.gateway.session(self.options, fresh=True)

    async def submit(self, counter=1, session=None, key=KEY):
        request = {"id": "unique", "session": session or self.state.challenge.hex(), "counter": counter,
                   "path": "/api/params", "method": "PUT", "body": ""}
        for packet in packets(seal(request, key, "request")):
            self.gateway.write(packet, self.options)
        task = self.state.task
        await task

    def drain(self):
        assembler = Assembler()
        decoded = None
        while self.state.response:
            packet = self.gateway.read(self.options)
            self.assertEqual(self.gateway.read(self.options), packet)  # Read is repeatable until ACK.
            decoded = assembler.add(packet)
            self.gateway.write(b"\x02" + packet[1:5], self.options)
        return open_message(decoded, KEY, "response") if decoded else None

    async def test_actual_gatt_request_ack_and_replay(self):
        await self.submit()
        reply = self.drain()
        self.assertEqual(reply["counter"], 1)
        self.assertEqual(self.proxy.calls, 1)
        await self.submit()  # Same session + counter cannot mutate twice.
        self.assertFalse(self.state.response)
        self.assertEqual(self.proxy.calls, 1)
        await self.submit(counter=2)
        self.drain()
        self.assertEqual(self.proxy.calls, 2)

    async def test_wrong_key_and_old_session_never_reach_galaxy(self):
        await self.submit(key=bytes(32))
        await self.submit(session="00" * 16)
        self.assertEqual(self.proxy.calls, 0)
        self.assertFalse(self.state.response)

    async def test_dbus_exports_and_mtu_minimum(self):
        characteristic = Characteristic("uuid", ["read"], self.gateway, "tx")
        service = GattService()
        application = Application({SERVICE_PATH: service})
        self.assertIn(SERVICE_PATH, application.GetManagedObjects.__wrapped__(application))
        self.assertEqual(characteristic.props()["Flags"].value, ["read"])
        self.options["mtu"] = Variant("q", 23)
        await self.submit()
        self.assertTrue(all(len(p) <= 20 for p in self.state.response))
        self.drain()


if __name__ == "__main__":
    unittest.main()
