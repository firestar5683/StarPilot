import os
from types import SimpleNamespace

os.environ.setdefault("SP_HEADLESS_TEST", "1")

from openpilot.starpilot.system.bluetooth.protocol import BluetoothDevice, BluetoothStatus
import openpilot.selfdrive.ui.layouts.settings.settings as settings_module
from openpilot.selfdrive.ui.layouts.settings.settings import PanelType, SettingsLayout
from openpilot.system.ui.widgets import DialogResult
from openpilot.system.ui.widgets.bluetooth import (BluetoothManagerUI, PANEL_BACKGROUND, ROW_BORDER,
                                                   device_action_allowed, device_status_text)


ADDRESS = "00:11:22:33:44:55"


class FakeBluetoothManager:
  def __init__(self, status: BluetoothStatus):
    self.status = status
    self.calls = []

  def operation_for(self, _address: str) -> str:
    return ""

  def pair(self, address: str):
    self.calls.append(("pair", address))

  def connect(self, address: str):
    self.calls.append(("connect", address))

  def disconnect(self, address: str):
    self.calls.append(("disconnect", address))

  def set_scanning(self, enabled: bool):
    self.calls.append(("scan", enabled))

  def respond(self, prompt_id: str, accepted: bool, value: str = ""):
    self.calls.append(("respond", prompt_id, accepted, value))


def make_ui(manager: FakeBluetoothManager) -> BluetoothManagerUI:
  ui = object.__new__(BluetoothManagerUI)
  ui._manager = manager
  ui._scan_pending = False
  return ui


def make_device(**overrides) -> BluetoothDevice:
  return BluetoothDevice(ADDRESS, "Speaker", **overrides)


def test_bluetooth_is_a_standalone_settings_panel():
  assert PanelType.BLUETOOTH.value == PanelType.NETWORK.value + 1
  assert PanelType.TOGGLES.value == PanelType.BLUETOOTH.value + 1


def test_bluetooth_uses_the_network_panel_black_surface():
  def rgba(color):
    return tuple(color) if isinstance(color, tuple) else (color.r, color.g, color.b, color.a)

  assert rgba(PANEL_BACKGROUND) == (0, 0, 0, 255)
  assert rgba(ROW_BORDER) == (200, 200, 200, 255)


def test_settings_constructs_a_dedicated_bluetooth_panel(monkeypatch):
  class PanelStub:
    def __init__(self, *_args):
      pass

    def set_depth_callback(self, _callback):
      pass

    def set_settings_layout(self, _layout):
      pass

  class ManagerStub:
    def __init__(self):
      self.active = None

    def set_active(self, active):
      self.active = active

  captured = {}

  class BluetoothPanelStub(PanelStub):
    def __init__(self, manager):
      captured["manager"] = manager

  for name in ("StarPilotLayout", "DeviceLayout", "TogglesLayout", "SoftwareLayout", "DeveloperLayout", "NetworkUI"):
    monkeypatch.setattr(settings_module, name, PanelStub)
  monkeypatch.setattr(settings_module, "WifiManager", ManagerStub)
  monkeypatch.setattr(settings_module, "BluetoothManager", ManagerStub)
  monkeypatch.setattr(settings_module, "BluetoothManagerUI", BluetoothPanelStub)
  monkeypatch.setattr(settings_module.gui_app, "font", lambda *_args: object())
  monkeypatch.setattr(settings_module.gui_app, "texture", lambda *_args: object())

  layout = SettingsLayout()

  assert PanelType.BLUETOOTH in layout._panels
  assert isinstance(captured["manager"], ManagerStub)
  assert captured["manager"].active is False


def test_device_status_prioritizes_operations_then_connection_and_capabilities():
  device = make_device(paired=True, connected=True, audio=True, controller=True)
  serial_device = make_device(serial=True)

  assert device_status_text(device, "connecting", ADDRESS) == "Connecting..."
  assert device_status_text(device, "", ADDRESS) == "Connected / audio output / controller"
  assert device_status_text(serial_device, "", "") == "Tap to pair / serial"


def test_device_action_policy_matches_the_daemon_onroad_rules():
  unpaired = make_device()
  paired = make_device(paired=True)

  assert device_action_allowed(unpaired, "", offroad=True)
  assert not device_action_allowed(unpaired, "", offroad=False)
  assert device_action_allowed(paired, "", offroad=False)
  assert not device_action_allowed(paired, "pairing", offroad=True)


def test_primary_device_action_is_pair_then_connect_then_manage():
  unpaired = make_device()
  paired = make_device(paired=True)
  connected = make_device(paired=True, connected=True)
  manager = FakeBluetoothManager(BluetoothStatus(offroad=True, devices=(unpaired,)))
  ui = make_ui(manager)

  ui._select_device(ADDRESS)
  assert manager.calls == [("pair", ADDRESS)]

  manager.status = BluetoothStatus(offroad=True, devices=(paired,))
  ui._select_device(ADDRESS)
  assert manager.calls[-1] == ("connect", ADDRESS)

  managed = []
  ui._show_device_actions = lambda device: managed.append(device.address)
  manager.status = BluetoothStatus(offroad=True, devices=(connected,))
  ui._select_device(ADDRESS)
  assert managed == [ADDRESS]


def test_scan_is_only_requested_when_the_existing_daemon_policy_allows_it():
  manager = FakeBluetoothManager(BluetoothStatus(enabled=True, offroad=True))
  ui = make_ui(manager)

  ui._scan()
  assert manager.calls == [("scan", True)]

  ui._scan()
  assert manager.calls == [("scan", True)]

  manager.status = BluetoothStatus(enabled=True, offroad=False)
  ui._scan()
  assert manager.calls == [("scan", True)]


def test_pairing_dialog_callbacks_send_explicit_acceptance_or_rejection():
  manager = FakeBluetoothManager(BluetoothStatus())
  ui = make_ui(manager)
  ui._on_pairing_confirmation("confirm", DialogResult.CANCEL)
  ui._on_pairing_confirmation("confirm", DialogResult.CONFIRM)

  ui._keyboard = SimpleNamespace(text="123456", clear=lambda: None)
  ui._on_pairing_value("pin", DialogResult.CANCEL)
  ui._on_pairing_value("pin", DialogResult.CONFIRM)

  assert manager.calls == [
    ("respond", "confirm", False, ""),
    ("respond", "confirm", True, ""),
    ("respond", "pin", False, ""),
    ("respond", "pin", True, "123456"),
  ]
