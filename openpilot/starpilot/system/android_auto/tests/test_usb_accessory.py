import os
import subprocess
import tty
from pathlib import Path
from unittest.mock import Mock

import pytest

from openpilot.starpilot.system.android_auto import usb_accessory as usb


def test_parse_uevent_accessory_start_and_state():
  start = usb.parse_uevent(b"change@/devices/virtual/misc/usb_accessory\0ACTION=change\0ACCESSORY=START\0SEQNUM=9\0")
  assert start["ACTION"] == "change" and start["DEVPATH"] == "/devices/virtual/misc/usb_accessory" and start["ACCESSORY"] == "START"
  state = usb.parse_uevent(b"change@/devices/virtual/android_usb/android0\0USB_STATE=CONFIGURED\0")
  assert state["USB_STATE"] == "CONFIGURED"
  assert usb.parse_uevent(b"libudev\0junk") == {}


def fake_configfs(tmp_path):
  """comma's ADB gadget as /usr/comma/set_adb.sh leaves it (NCM then ADB, bound), plus a stale accessory from v1."""
  configfs = tmp_path / "config"
  adb = configfs / "usb_gadget" / "g1"
  for function in ("ncm.0", "ffs.adb", usb.ACCESSORY_FUNCTION):
    (adb / "functions" / function).mkdir(parents=True)
  (adb / usb.CONFIG).mkdir(parents=True)
  for function in ("ncm.0", "ffs.adb"):
    os.symlink(adb / "functions" / function, adb / usb.CONFIG / function)
  for name, value in (("idVendor", "0x04d8"), ("idProduct", "0x1234"), ("UDC", "a600000.dwc3")):
    (adb / name).write_text(value + "\n")
  calls = []

  def run(args, **kwargs):
    assert args[:2] == ["sudo", "-n"]
    command, rest, data = args[2], args[3:], kwargs.get("input") or ""
    calls.append((command, *rest, data.strip()))
    if command == "tee":
      Path(rest[0]).write_text(data)
    elif command == "mkdir":
      os.makedirs(rest[-1], exist_ok=True)
    elif command == "rmdir":
      os.rmdir(rest[0])
    elif command == "ln":
      os.symlink(rest[1], rest[2])
    elif command == "rm":
      os.unlink(rest[1])
    elif command == "mount":
      (Path(rest[-1]) / "usb_gadget").mkdir(parents=True, exist_ok=True)  # configfs with libcomposite
    return subprocess.CompletedProcess(args, 0, "", "")
  return configfs, adb, calls, run


def udc_writes(calls, gadget):
  return [call[-1] for call in calls if call[0] == "tee" and call[1] == str(gadget / "UDC")]


@pytest.mark.parametrize("direct", [False, True])
def test_accessory_gadget_takes_the_controller_and_gives_it_back(tmp_path, monkeypatch, direct):
  configfs, adb, calls, run = fake_configfs(tmp_path)
  device = tmp_path / "usb_accessory"
  device.write_text("")
  monkeypatch.setattr(usb, "ACCESSORY_DEVICE", str(device))
  gadget = usb.AccessoryGadget(lambda *a, **k: None, configfs=configfs, run=run, adb_wanted=lambda: None)
  gadget.prepare(direct=direct)
  ours = configfs / "usb_gadget" / usb.GADGET_NAME
  assert not (adb / "functions" / usb.ACCESSORY_FUNCTION).exists(), "f_accessory allows one instance: the stale one goes"
  assert (adb / "functions" / "ffs.adb").is_dir(), "the ADB gadget itself is left alone"
  assert udc_writes(calls, adb) == [""], "comma's gadget lets go of the controller"
  links = [link.name for link in (ours / usb.CONFIG).iterdir() if link.is_symlink()]
  assert links == [usb.ACCESSORY_FUNCTION], "the accessory alone, so the car finds it at interface 0"
  assert (ours / "UDC").read_text().strip() == "a600000.dwc3" and (ours / "max_speed").read_text().strip() == "high-speed"
  expected = ("0x18d1", "0x2d00") if direct else ("0x04d8", "0x1234")
  assert ((ours / "idVendor").read_text().strip(), (ours / "idProduct").read_text().strip()) == expected
  if not direct:
    gadget.switch_to_accessory()
    assert (ours / "idVendor").read_text().strip() == "0x18d1" and (ours / "idProduct").read_text().strip() == "0x2d00"
    assert udc_writes(calls, ours) == ["a600000.dwc3", "", "a600000.dwc3"]  # unbind before changing identity, then rebind
  gadget.restore()
  assert (ours / "UDC").read_text().strip() == ""
  assert udc_writes(calls, adb) == ["", "a600000.dwc3"], "ADB is rebound afterwards"


def test_accessory_gadget_without_adb_leaves_nothing_to_rebind(tmp_path, monkeypatch):
  configfs, adb, calls, run = fake_configfs(tmp_path)
  (adb / "UDC").write_text("\n")  # ADB off: nothing holds the controller
  device = tmp_path / "usb_accessory"
  device.write_text("")
  monkeypatch.setattr(usb, "ACCESSORY_DEVICE", str(device))
  gadget = usb.AccessoryGadget(lambda *a, **k: None, configfs=configfs, run=run, adb_wanted=lambda: None)
  gadget.prepare()
  gadget.restore()
  assert udc_writes(calls, adb) == []


def test_accessory_strings_read_through_ioctls():
  sent = {"manufacturer": b"Hyundai\0", "model": b"Android Auto\0junk", "serial": b"HU123\0"}
  names = {request: name for name, request in usb.ACCESSORY_GET_STRING.items()}
  assert usb.ACCESSORY_GET_STRING["manufacturer"] == 0x41004D01  # _IOW('M', 1, char[256])

  def ioctl(fd, request, buffer, mutate):
    value = sent.get(names[request])
    if value is None:
      raise OSError(25, "Inappropriate ioctl for device")
    buffer[:len(value)] = value

  assert usb.read_accessory_strings(3, ioctl) == {"manufacturer": "Hyundai", "model": "Android Auto", "serial": "redacted"}


def test_configfs_mount_is_found(tmp_path):
  mounts = tmp_path / "mounts"
  mounts.write_text("sysfs /sys sysfs rw 0 0\nnone /config configfs rw,relatime 0 0\n")
  assert usb.configfs_mount(str(mounts)) == usb.Path("/config")
  mounts.write_text("sysfs /sys sysfs rw 0 0\n")
  assert usb.configfs_mount(str(mounts)) is None


def test_bridge_copies_both_ways_and_reports_disconnect():
  master, slave = os.openpty()
  tty.setraw(slave)
  bridge = usb.AccessoryBridge(os.ttyname(slave))
  os.close(slave)
  try:
    sock = bridge.socket
    sock.settimeout(5)
    os.write(master, b"\x00\x03\x00\x06\x00\x01\x00\x01\x00\x04")  # the car's version request
    assert sock.recv(64) == b"\x00\x03\x00\x06\x00\x01\x00\x01\x00\x04"
    sock.sendall(b"reply")
    received = b""
    while len(received) < 5:
      received += os.read(master, 64)
    assert received == b"reply"
    os.close(master)  # the car unplugs
    assert bridge.closed.wait(5)
    assert sock.recv(64) == b""
  finally:
    bridge.close()


def test_supervisor_wired_session_end_to_end(tmp_path, monkeypatch):
  import socket
  import threading
  import time
  from pathlib import Path
  from openpilot.starpilot.system.android_auto import hw_encoder, identity as identity_store, supervisor as supervisor_module
  from openpilot.starpilot.system.android_auto.tests.fake_head_unit import FakeHeadUnit, make_identity

  identity = make_identity(tmp_path / "ident")
  data = tmp_path / "android_auto"
  (data / "identity").mkdir(parents=True)
  for src, name in ((identity["phone_cert"], "phone-cert.pem"), (identity["phone_key"], "phone-key.pem"), (identity["root"], "root-cert.pem")):
    (data / "identity" / name).write_bytes(Path(src).read_bytes())
  (data / "identity" / "phone-key.pem").chmod(0o600)
  monkeypatch.setattr(identity_store, "IDENTITY_DIR", data / "identity")
  monkeypatch.setattr(identity_store, "CONFIG_PATH", data / "config.json")
  monkeypatch.setattr(identity_store, "LOG_DIR", data / "logs")
  monkeypatch.setattr(hw_encoder, "LIBRARY", tmp_path / "missing.so")
  hu = FakeHeadUnit(identity)
  calls = []

  class FakeGadget:
    def __init__(self, log):
      pass

    def prepare(self, direct=False):
      calls.append("prepare")

    def switch_to_accessory(self):
      calls.append("switch")

    def connection_state(self):
      return ""

    def detach(self):
      calls.append("detach")

    def restore(self):
      calls.append("restore")

  class FakeListener:
    events = [{"DEVPATH": "/devices/virtual/android_usb/android0", "USB_STATE": "CONFIGURED"},
              {"DEVPATH": "/devices/virtual/misc/usb_accessory", "ACCESSORY": "START"},
              {"DEVPATH": "/devices/virtual/android_usb/android0", "USB_STATE": "CONFIGURED"}]

    def next(self, timeout):
      return self.events.pop(0) if self.events else None

    def close(self):
      pass

  class FakeBridge:  # the "cable": a TCP connection to the fake head unit
    def __init__(self, log=None):
      self.socket = socket.create_connection(("127.0.0.1", hu.port))
      self.closed = threading.Event()

    def close(self):
      self.closed.set()
      self.socket.close()
      calls.append("close_bridge")

  monkeypatch.setattr(usb, "AccessoryGadget", FakeGadget)
  monkeypatch.setattr(usb, "UeventListener", FakeListener)
  monkeypatch.setattr(usb, "AccessoryBridge", FakeBridge)
  sup = supervisor_module.Supervisor(synthetic=True)
  sup.set_connection("wired")
  try:
    sup.start()  # no car chosen: wired needs none
    deadline = time.monotonic() + 20
    while len(hu.frames) < 3:
      assert time.monotonic() < deadline, sup.status()
      time.sleep(0.05)
    status = sup.status()
    assert status["connection"] == "wired" and status["state"] == "streaming"
    try:
      sup.set_connection("wireless")
      raise AssertionError("connection changed while running")
    except RuntimeError:
      pass
  finally:
    sup.stop()
    hu.close()
  assert calls[:2] == ["prepare", "switch"] and "restore" in calls
  assert calls[-3:] == ["detach", "close_bridge", "restore"]
  assert identity_store.load_config()["connection"] == "wired"


class ScriptedListener:
  """USB uevents on a timeline: (seconds after the first call, event)."""

  def __init__(self, script):
    self.script, self.started = list(script), None

  def next(self, timeout):
    import time
    now = time.monotonic()
    self.started = self.started or now
    if self.script and now - self.started >= self.script[0][0]:
      return self.script.pop(0)[1]
    time.sleep(0.01)
    return None


CONNECTED = {"DEVPATH": "/devices/virtual/android_usb/android1", "USB_STATE": "CONNECTED"}
CONFIGURED = {"DEVPATH": "/devices/virtual/android_usb/android1", "USB_STATE": "CONFIGURED"}
DISCONNECTED = {"DEVPATH": "/devices/virtual/android_usb/android1", "USB_STATE": "DISCONNECTED"}
START = {"DEVPATH": "/devices/virtual/misc/usb_accessory", "ACCESSORY": "START"}


def test_no_accessory_start_falls_back_to_direct(tmp_path, monkeypatch):
  from openpilot.starpilot.system.android_auto import identity as identity_store, supervisor as supervisor_module
  monkeypatch.setattr(identity_store, "CONFIG_PATH", tmp_path / "config.json")
  monkeypatch.setattr(identity_store, "LOG_DIR", tmp_path / "logs")
  monkeypatch.setattr(supervisor_module, "USB_HANDSHAKE_WAIT", 0.3)
  sup = supervisor_module.Supervisor(synthetic=True)

  assert sup._await_accessory_start(ScriptedListener([(0, CONFIGURED), (0.1, START)]), fallback=True) is False
  assert sup._await_accessory_start(ScriptedListener([(0, CONFIGURED)]), fallback=True) is True
  # Connected, descriptors read, but never configured: an unfamiliar device to this head unit.
  assert sup._await_accessory_start(ScriptedListener([(0, CONNECTED)]), fallback=True) is True
  assert any(record["event"] == "usb_no_accessory_start" for record in sup.log.recent)
  # Unplugged meanwhile: the wait starts over when the car configures the comma again.
  import time
  started = time.monotonic()
  assert sup._await_accessory_start(ScriptedListener([(0, CONFIGURED), (0.2, DISCONNECTED), (0.4, CONFIGURED)]), fallback=True)
  assert time.monotonic() - started >= 0.65
  assert sup._await_usb_configured(ScriptedListener([(0.05, CONFIGURED)]), 1.0)
  assert not sup._await_usb_configured(ScriptedListener([]), 0.2)


def test_gadget_detach_settles_for_switch_restore_and_crash_recovery(tmp_path, monkeypatch):
  configfs, adb, calls, run = fake_configfs(tmp_path)
  device = tmp_path / "usb_accessory"
  device.write_text("")
  monkeypatch.setattr(usb, "ACCESSORY_DEVICE", str(device))
  monkeypatch.setattr(usb.time, "sleep", lambda seconds: calls.append(("sleep", seconds)))
  gadget = usb.AccessoryGadget(lambda *a, **k: None, configfs=configfs, run=run, adb_wanted=lambda: None)
  gadget.prepare()
  root = gadget.root
  assert root is not None
  gadget.switch_to_accessory()
  # Simulate a crashed daemon: a fresh owner must detach before editing configfs.
  recovered = usb.AccessoryGadget(lambda *a, **k: None, configfs=configfs, run=run, adb_wanted=lambda: None)
  before = len(calls)
  recovered.prepare()
  assert calls[before:before + 2] == [("tee", str(root / "UDC"), ""), ("sleep", usb.UDC_SETTLE_SECONDS)]  # ty: ignore[unsupported-operator]
  gadget.restore()
  after = len(calls)
  gadget.restore()
  assert len(calls) == after, "restoring twice must not rebind an already-bound ADB gadget"
  assert udc_writes(calls, adb) == ["", usb.UDC_NAME]
  detaches = [i for i, call in enumerate(calls) if call[0] == "tee" and call[1].endswith("/UDC") and call[-1] == ""]
  assert len(detaches) == 4
  for i in detaches:
    assert calls[i + 1] == ("sleep", usb.UDC_SETTLE_SECONDS)


def test_stale_accessory_detection_follows_symlink_target(tmp_path):
  configfs, adb, calls, run = fake_configfs(tmp_path)
  (adb / usb.CONFIG / "alternate-name").symlink_to("../../functions/" + usb.ACCESSORY_FUNCTION)
  gadget = usb.AccessoryGadget(lambda *a, **k: None, configfs=configfs, run=run, adb_wanted=lambda: None)
  gadget._remove_stale_accessories(configfs / "usb_gadget")
  assert (adb / "functions" / usb.ACCESSORY_FUNCTION).exists()
  assert not any(call[0] == "rmdir" for call in calls)


def _session(tmp_path, monkeypatch, adb_wanted, *, adb_bound=True):
  configfs, adb, calls, run = fake_configfs(tmp_path)
  if not adb_bound:
    (adb / "UDC").write_text("\n")
  device = tmp_path / "usb_accessory"
  device.write_text("")
  monkeypatch.setattr(usb, "ACCESSORY_DEVICE", str(device))
  monkeypatch.setattr(usb.time, "sleep", lambda seconds: None)
  gadget = usb.AccessoryGadget(lambda *a, **k: None, configfs=configfs, run=run, adb_wanted=adb_wanted)
  return configfs, adb, calls, run, gadget


def test_adb_turned_off_mid_session_stays_off(tmp_path, monkeypatch):
  _, adb, calls, _, gadget = _session(tmp_path, monkeypatch, lambda: False)
  gadget.prepare()
  gadget.restore()
  assert udc_writes(calls, adb) == [""], "ADB was on at the start, but the setting is off now"


def test_adb_turned_on_mid_session_comes_up_afterwards(tmp_path, monkeypatch):
  _, adb, calls, _, gadget = _session(tmp_path, monkeypatch, lambda: True, adb_bound=False)
  gadget.prepare()
  assert gadget.released is None, "ADB was off: nothing to release"
  gadget.restore()
  assert udc_writes(calls, adb) == [usb.UDC_NAME], "set_adb.sh could not bind while we held the port; we bind it for it"


def test_restore_leaves_a_controller_someone_else_took(tmp_path, monkeypatch):
  configfs, adb, calls, _, gadget = _session(tmp_path, monkeypatch, lambda: True)
  gadget.prepare()
  other = configfs / "usb_gadget" / "other"
  other.mkdir()
  (other / "UDC").write_text(usb.UDC_NAME + "\n")
  gadget.detach = lambda: (gadget.root / "UDC").write_text("\n")
  gadget.restore()
  assert udc_writes(calls, adb) == [""]


def test_recover_after_a_crash_follows_the_adb_setting(tmp_path, monkeypatch):
  configfs, adb, calls, run, gadget = _session(tmp_path, monkeypatch, lambda: True)
  gadget.prepare()  # then the daemon dies: nothing restores
  ours = configfs / "usb_gadget" / usb.GADGET_NAME
  assert (ours / "UDC").read_text().strip() == usb.UDC_NAME

  for wanted, expected in ((False, []), (True, [usb.UDC_NAME])):
    (ours / "UDC").write_text(usb.UDC_NAME + "\n")
    (adb / "UDC").write_text("\n")
    calls.clear()
    fresh = usb.AccessoryGadget(lambda *a, **k: None, configfs=configfs, run=run, adb_wanted=lambda wanted=wanted: wanted)
    assert fresh.recover()
    assert (ours / "UDC").read_text().strip() == ""
    assert udc_writes(calls, adb) == expected, f"ADB setting {wanted}"

  calls.clear()
  assert not usb.AccessoryGadget(lambda *a, **k: None, configfs=configfs, run=run, adb_wanted=lambda: True).recover()
  assert calls == [], "no leftover gadget: recovery touches nothing"


def test_recover_never_mounts_configfs(tmp_path, monkeypatch):
  monkeypatch.setattr(usb, "configfs_mount", lambda: None)
  calls = []
  gadget = usb.AccessoryGadget(lambda *a, **k: None, run=Mock(side_effect=lambda args, **k: calls.append(args)), adb_wanted=lambda: True)
  assert not gadget.recover()
  assert calls == []


def test_prepare_without_adb_mounts_configfs_itself(tmp_path, monkeypatch):
  """ADB never turned on since boot: nothing has mounted configfs yet."""
  _, _, calls, run = fake_configfs(tmp_path)
  primary, fallback = tmp_path / "missing-root" / "config", tmp_path / "sys_kernel_config"
  fallback.mkdir()
  monkeypatch.setattr(usb, "configfs_mount", lambda: None)
  monkeypatch.setattr(usb, "CONFIGFS_MOUNT", primary)
  monkeypatch.setattr(usb, "CONFIGFS_FALLBACK_MOUNT", fallback)
  monkeypatch.setattr(usb.time, "sleep", lambda seconds: None)
  device = tmp_path / "usb_accessory"
  device.write_text("")
  monkeypatch.setattr(usb, "ACCESSORY_DEVICE", str(device))

  def read_only_root(args, **kwargs):
    if args[2] == "mkdir" and args[-1] == str(primary):
      return subprocess.CompletedProcess(args, 1, "", "mkdir: cannot create directory: Read-only file system")
    return run(args, **kwargs)

  events = []
  gadget = usb.AccessoryGadget(lambda name, **k: events.append(name), run=read_only_root, adb_wanted=lambda: None)
  gadget.prepare()
  assert ("mount", "-t", "configfs", "none", str(fallback), "") in calls
  assert gadget.root == fallback / "usb_gadget" / usb.GADGET_NAME
  assert gadget.root is not None
  assert (gadget.root / "UDC").read_text().strip() == usb.UDC_NAME
  assert "usb_configfs_mounted" in events
  gadget.restore()
  assert gadget.root is None


def test_prepare_explains_missing_kernel_support(tmp_path, monkeypatch):
  configfs = tmp_path / "config"
  configfs.mkdir()  # configfs mounted, but no usb_gadget directory: no libcomposite
  gadget = usb.AccessoryGadget(lambda *a, **k: None, configfs=configfs, run=Mock(return_value=None), adb_wanted=lambda: None)
  with pytest.raises(RuntimeError, match="no USB gadget support"):
    gadget.prepare()

  _, _, _, run = fake_configfs(tmp_path / "second")

  def no_accessory(args, **kwargs):
    if args[2] == "mkdir" and args[-1].endswith(usb.ACCESSORY_FUNCTION):
      return subprocess.CompletedProcess(args, 1, "", "mkdir: No such file or directory")
    return run(args, **kwargs)

  gadget = usb.AccessoryGadget(lambda *a, **k: None, configfs=tmp_path / "second" / "config", run=no_accessory, adb_wanted=lambda: None)
  with pytest.raises(RuntimeError, match="does not support USB accessory mode"):
    gadget.prepare()


def test_usb_cleanup_error_never_hides_why_the_session_ended():
  from openpilot.starpilot.system.android_auto import supervisor as supervisor_module
  sup = supervisor_module.Supervisor.__new__(supervisor_module.Supervisor)
  events, steps = [], []
  sup.log = Mock(side_effect=lambda name, **values: events.append((name, values)))

  class Part:
    def __init__(self, name, fails=False):
      self.name, self.fails = name, fails

    def run(self):
      steps.append(self.name)
      if self.fails:
        raise RuntimeError("USB I/O did not stop after detach")

  gadget = type("Gadget", (), {})()
  gadget.detach, gadget.restore = Part("detach").run, Part("restore").run
  bridge = type("Bridge", (), {"close": Part("bridge", fails=True).run})()
  listener = type("Listener", (), {"close": Part("listener").run})()

  sup._release_usb(gadget, bridge, listener, failed=True)  # e.g. the car asked to stop: that reason must survive
  assert steps == ["detach", "bridge", "listener", "restore"], "every step runs even after one fails"
  assert ("usb_cleanup_failed", {"step": "bridge", "error": "USB I/O did not stop after detach"}) in events

  steps.clear()
  with pytest.raises(RuntimeError, match="did not stop"):
    sup._release_usb(gadget, bridge, listener, failed=False)  # a clean end still reports the stuck USB I/O
  assert steps == ["detach", "bridge", "listener", "restore"]


def test_usb_attempt_keeps_a_car_requested_stop(monkeypatch):
  from openpilot.starpilot.system.android_auto import identity as identity_store, supervisor as supervisor_module
  from openpilot.starpilot.system.android_auto.session import PeerRequestedStop
  sup = supervisor_module.Supervisor.__new__(supervisor_module.Supervisor)
  sup.log = Mock(return_value=None)
  sup.config = {"usb_mode": "direct"}
  sup._stage = Mock(return_value=None)
  sup._await_usb_configured = Mock(return_value=True)
  monkeypatch.setattr(identity_store, "load_identity", lambda: None)

  class Gadget:
    def __init__(self, log): pass
    def prepare(self, direct=False): pass
    def connection_state(self): return "CONFIGURED"
    def detach(self): pass
    def restore(self): pass

  class Bridge:
    socket = None
    def __init__(self, log=None): pass
    def close(self): raise RuntimeError("USB I/O did not stop after detach")

  monkeypatch.setattr(usb, "AccessoryGadget", Gadget)
  monkeypatch.setattr(usb, "UeventListener", lambda: type("L", (), {"close": lambda self: None})())
  monkeypatch.setattr(usb, "AccessoryBridge", Bridge)

  def project(*args, **kwargs):
    raise PeerRequestedStop("Head unit ended projection (reason 1)")
  sup._project = Mock(side_effect=project)
  with pytest.raises(PeerRequestedStop):
    sup._attempt_usb()


def test_prepare_reuses_a_pre_rename_gadget_that_still_holds_the_accessory(tmp_path, monkeypatch):
  configfs, adb, calls, run = fake_configfs(tmp_path)
  legacy = configfs / "usb_gadget" / usb.LEGACY_GADGET_NAMES[0]
  (legacy / "functions" / usb.ACCESSORY_FUNCTION).mkdir(parents=True)
  (legacy / usb.CONFIG).mkdir(parents=True)
  os.symlink(legacy / "functions" / usb.ACCESSORY_FUNCTION, legacy / usb.CONFIG / usb.ACCESSORY_FUNCTION)
  (adb / "UDC").write_text("\n")
  (legacy / "UDC").write_text("a600000.dwc3\n")
  device = tmp_path / "usb_accessory"
  device.write_text("")
  monkeypatch.setattr(usb, "ACCESSORY_DEVICE", str(device))
  gadget = usb.AccessoryGadget(lambda *a, **k: None, configfs=configfs, run=run, adb_wanted=lambda: None)
  gadget.prepare()
  assert gadget.root == legacy and not (configfs / "usb_gadget" / usb.GADGET_NAME).exists()
  assert [path.name for path in (configfs / "usb_gadget").glob("*/functions/accessory.*")] == [usb.ACCESSORY_FUNCTION]
  assert gadget.recover() is True


def test_usb_device_echo_log_preserves_session_log(tmp_path, capsys):
  import json
  from typing import cast
  from openpilot.starpilot.system.android_auto.supervisor import EventLog
  from openpilot.tools.android_auto.usb_device import EchoLog

  original = EventLog(tmp_path)
  proxy = EchoLog(original)
  log = cast(EventLog, proxy)
  assert log is proxy
  assert log.recent is original.recent
  assert log.open == original.open
  assert log.close == original.close
  log.open()
  try:
    log("session_test", count=3)
  finally:
    log.close()
  assert json.loads(capsys.readouterr().out) == {"event": "session_test", "count": 3}
  assert original.recent[-1]["event"] == "session_test"
  assert original.recent[-1]["count"] == 3
  records = [json.loads(line) for path in tmp_path.glob("session-*.jsonl") for line in path.read_text().splitlines()]
  assert records == list(original.recent)
