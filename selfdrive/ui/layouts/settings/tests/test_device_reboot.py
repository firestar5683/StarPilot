from openpilot.selfdrive.ui.layouts.settings import device
from openpilot.system.ui.widgets import DialogResult


class FakeParams:
  def __init__(self):
    self.writes = []

  def put_bool(self, key, value):
    self.writes.append((key, value))

  def put_bool_nonblocking(self, *_args, **_kwargs):
    raise AssertionError("reboot command must be written synchronously")


def _device_layout():
  layout = device.DeviceLayout.__new__(device.DeviceLayout)
  layout._params = FakeParams()
  return layout


class FakeHardware:
  def __init__(self, error=None):
    self.error = error
    self.reboot_calls = 0

  def reboot(self):
    self.reboot_calls += 1
    if self.error is not None:
      raise self.error


def test_confirmed_user_reboot_is_written_synchronously(monkeypatch):
  layout = _device_layout()
  hardware = FakeHardware()
  monkeypatch.setattr(device, "HARDWARE", hardware)

  layout._perform_reboot(DialogResult.CONFIRM)

  assert layout._params.writes == [("DoUserReboot", True)]
  assert hardware.reboot_calls == 1


def test_confirmed_user_reboot_is_allowed_onroad(monkeypatch):
  layout = _device_layout()
  hardware = FakeHardware()

  monkeypatch.setattr(device, "HARDWARE", hardware)
  monkeypatch.setattr(device.ui_state, "started", True)
  monkeypatch.setattr(device.ui_state, "ignition", True)
  layout._perform_reboot(DialogResult.CONFIRM)

  assert layout._params.writes == [("DoUserReboot", True)]
  assert hardware.reboot_calls == 1


def test_cancelled_user_reboot_is_ignored(monkeypatch):
  layout = _device_layout()
  hardware = FakeHardware()
  monkeypatch.setattr(device, "HARDWARE", hardware)

  layout._perform_reboot(DialogResult.CANCEL)

  assert layout._params.writes == []
  assert hardware.reboot_calls == 0


def test_failed_direct_reboot_keeps_manager_fallback(monkeypatch):
  layout = _device_layout()
  hardware = FakeHardware(RuntimeError("reboot failed"))
  monkeypatch.setattr(device, "HARDWARE", hardware)
  monkeypatch.setattr(device.cloudlog, "exception", lambda *_args, **_kwargs: None)

  layout._perform_reboot(DialogResult.CONFIRM)

  assert layout._params.writes == [("DoUserReboot", True)]
  assert hardware.reboot_calls == 1
