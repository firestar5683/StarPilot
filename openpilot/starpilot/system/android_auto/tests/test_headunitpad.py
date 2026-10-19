import json
import socket
import time
from pathlib import Path

import pytest

from openpilot.starpilot.system.android_auto import hw_encoder, identity as identity_store, supervisor as supervisor_module
from openpilot.starpilot.system.android_auto.session import FRAGMENT_SIZE, ProjectionSession
from openpilot.starpilot.system.android_auto.tests.fake_head_unit import FakeHeadUnit, make_identity


@pytest.fixture(scope="module")
def identity(tmp_path_factory):
  return make_identity(tmp_path_factory.mktemp("identity"))


@pytest.fixture
def store(tmp_path, monkeypatch, identity):
  data = tmp_path / "android_auto"
  (data / "identity").mkdir(parents=True)
  for src, name in ((identity["phone_cert"], "phone-cert.pem"), (identity["phone_key"], "phone-key.pem"), (identity["root"], "root-cert.pem")):
    (data / "identity" / name).write_bytes(Path(src).read_bytes())
  (data / "identity" / "phone-key.pem").chmod(0o600)
  monkeypatch.setattr(identity_store, "IDENTITY_DIR", data / "identity")
  monkeypatch.setattr(identity_store, "CONFIG_PATH", data / "config.json")
  monkeypatch.setattr(identity_store, "LOG_DIR", data / "logs")
  monkeypatch.setattr(hw_encoder, "LIBRARY", tmp_path / "missing.so")
  return data


def free_port() -> int:
  with socket.socket() as probe:
    probe.bind(("127.0.0.1", 0))
    return probe.getsockname()[1]


def pump_until(session, predicate, timeout=5.0):
  deadline = time.monotonic() + timeout
  while not predicate():
    assert time.monotonic() < deadline, "condition not reached"
    session.pump(0.05)


def keyframe(size: int) -> bytes:
  return b"\x00\x00\x00\x01\x67\x42" + b"\x00\x00\x00\x01\x68\xce" + b"\x00\x00\x00\x01\x65" + bytes(size)


def test_config_keeps_headunitpad_and_rejects_a_bad_port(store):
  (store / "config.json").write_text(json.dumps({"connection": "headunitpad", "headunitpad_port": 80}))
  config = identity_store.load_config()
  assert config["connection"] == "headunitpad" and config["headunitpad_port"] == 5277


def test_fragment_acks_credit_whole_frames(identity):
  hu = FakeHeadUnit(identity, ack_fragments=True)
  sock = socket.create_connection(("127.0.0.1", hu.port), timeout=5)
  session = ProjectionSession(sock, str(identity["phone_cert"]), str(identity["phone_key"]), None, None)
  session.fragment_acks = True
  session.authenticate()
  session.start("StarPilot", "comma.ai")
  pump_until(session, lambda: session.focused)
  session.send_frame(keyframe(3 * FRAGMENT_SIZE), 1, keyframe=True)  # codec config + four fragments: five ACKs
  pump_until(session, lambda: session.acked == 1)
  assert session.video_confirmed and not session.pending and session.fragment_credit == 0
  for i in range(2, 6):
    pump_until(session, session.can_send)
    session.send_frame(b"\x00\x00\x00\x01\x41" + bytes(FRAGMENT_SIZE if i % 2 else 10), i, keyframe=False)
  pump_until(session, lambda: session.acked == 5)
  assert not session.frame_fragments and session.fragment_credit == 0
  session.shutdown()
  session.peer.close()
  hu.thread.join(5)
  assert hu.error is None, hu.error
  assert len(hu.frames) == 5


def test_per_frame_acks_unchanged_for_cars(identity):
  hu = FakeHeadUnit(identity)
  sock = socket.create_connection(("127.0.0.1", hu.port), timeout=5)
  session = ProjectionSession(sock, str(identity["phone_cert"]), str(identity["phone_key"]), None, None)
  session.authenticate()
  session.start("StarPilot", "comma.ai")
  pump_until(session, lambda: session.focused)
  session.send_frame(keyframe(3 * FRAGMENT_SIZE), 1, keyframe=True)
  pump_until(session, lambda: session.acked == 1)
  assert not session.frame_fragments
  session.shutdown()
  session.peer.close()
  hu.thread.join(5)
  assert hu.error is None, hu.error


@pytest.mark.parametrize("connection", ["headunitpad", "openheadunit"])
def test_supervisor_headunitpad_session_end_to_end(store, identity, connection):
  port = free_port()
  sup = supervisor_module.Supervisor(synthetic=True)
  sup.set_connection(connection)
  sup.config["headunitpad_port"] = port
  hu = FakeHeadUnit(identity, connect_to=("127.0.0.1", port), ack_fragments=connection == "headunitpad")
  try:
    sup.start()  # no car chosen: HeadunitPad needs none
    deadline = time.monotonic() + 20
    while len(hu.frames) < 3:
      assert time.monotonic() < deadline, sup.status()
      time.sleep(0.05)
    status = sup.status()
    assert status["connection"] == connection and status["state"] == "streaming", status
  finally:
    sup.stop()
    hu.close()
  assert hu.error is None, hu.error
  assert identity_store.load_config()["connection"] == connection


def test_stop_while_waiting_for_the_ipad_closes_the_port(store):
  port = free_port()
  sup = supervisor_module.Supervisor(synthetic=True)
  sup.set_connection("headunitpad")
  sup.config["headunitpad_port"] = port
  sup.start()
  deadline = time.monotonic() + 5
  while sup.status()["state"] != "waiting_for_ipad":
    assert time.monotonic() < deadline, sup.status()
    time.sleep(0.05)
  sup.stop()
  assert not sup.status()["running"]
  with pytest.raises(OSError):
    socket.create_connection(("127.0.0.1", port), timeout=1).close()


def test_port_in_use_reports_a_clear_error(store):
  port = free_port()
  sup = supervisor_module.Supervisor(synthetic=True)
  sup.set_connection("headunitpad")
  sup.config["headunitpad_port"] = port
  with socket.socket() as busy:
    busy.bind(("", port))
    with pytest.raises(RuntimeError, match=f"port {port}"):
      sup._attempt_headunitpad()
