from types import SimpleNamespace

from openpilot.system.hardware.chestnut import status as chestnut_status
from openpilot.system.hardware.chestnut.status import ChestnutStatus
from openpilot.system.hardware.usb import CHESTNUT_USB_PRODUCT


DEVICE = {
  "vendorId": 0x3801,
  "productId": 0x0001,
  "product": CHESTNUT_USB_PRODUCT,
  "speedMbps": 5000,
}
STATE = SimpleNamespace(
  supplyVoltage=12000,
  supplyFault=False,
  pcieLtssm=0x78,
  tempC=50.0,
  memoryTempC=60.0,
)


class Alerts:
  def __init__(self):
    self.values = {}

  def set(self, name, enabled, extra=None):
    self.values[name] = (enabled, extra)

  @property
  def active(self):
    return {name for name, (enabled, _) in self.values.items() if enabled}


def update(status, alerts=None, *, offroad=True, expected=True, devices=None, firmware_failed=False,
           loading=False, active=False, compiled=True, state=STATE):
  alerts = alerts or Alerts()
  status.update(
    offroad,
    expected,
    [DEVICE] if devices is None else devices,
    firmware_failed,
    loading,
    active,
    compiled,
    state,
    alerts.set,
  )
  return alerts


def test_missing_chestnut_only_alerts_when_expected(monkeypatch):
  status = ChestnutStatus()
  monkeypatch.setattr(chestnut_status.time, "monotonic", lambda: status.started + 11.0)
  assert not update(status, expected=False, devices=[]).active
  alerts = update(status, expected=True, devices=[])
  assert alerts.active == {"Offroad_ChestnutNotDetected"}


def test_slow_usb_and_uncompiled_alerts():
  status = ChestnutStatus()
  alerts = update(status, devices=[DEVICE | {"speedMbps": 480}])
  assert alerts.active == {"Offroad_ChestnutUsbSlow"}
  assert alerts.values["Offroad_ChestnutUsbSlow"][1] == "480 Mbps"

  alerts = update(status, compiled=False)
  assert alerts.active == {"Offroad_ChestnutUncompiled"}


def test_firmware_failure_alert():
  alerts = update(ChestnutStatus(), firmware_failed=True)
  assert alerts.active == {"Offroad_ChestnutUpdateFailed"}


def test_overheat_hysteresis():
  status = ChestnutStatus()
  hot = SimpleNamespace(**(vars(STATE) | {"tempC": 101.0}))
  alerts = update(status, state=hot)
  assert alerts.active == {"Offroad_ChestnutOverheated"}
  assert alerts.values["Offroad_ChestnutOverheated"][1] == "101 °C"

  warm = SimpleNamespace(**(vars(STATE) | {"tempC": 97.0}))
  assert "Offroad_ChestnutOverheated" in update(status, state=warm).active
  assert "Offroad_ChestnutOverheated" not in update(status).active


def test_pcie_failure_after_model_load():
  status, alerts = ChestnutStatus(), Alerts()
  update(status, alerts, offroad=False, loading=True)
  update(status, alerts, offroad=False, loading=False, active=False)
  link_down = SimpleNamespace(**(vars(STATE) | {"pcieLtssm": 0x00}))
  update(status, alerts, offroad=False, state=link_down)
  assert "Offroad_ChestnutPcieUnavailable" not in alerts.active
  update(status, alerts, offroad=False, state=link_down)
  assert alerts.active == {"Offroad_ChestnutPcieUnavailable"}
  assert "PCIe link is not up" in alerts.values["Offroad_ChestnutPcieUnavailable"][1]


def test_power_loss_reports_cause_and_recovery():
  status, alerts = ChestnutStatus(), Alerts()
  update(status, alerts, offroad=False, loading=True)
  update(status, alerts, offroad=False, loading=False, active=True)
  low = SimpleNamespace(**(vars(STATE) | {"supplyVoltage": 3000, "supplyFault": True, "pcieLtssm": 0x00}))
  update(status, alerts, offroad=False, state=low)
  assert alerts.active == {"Offroad_ChestnutPcieUnavailable"}
  assert "power lost" in alerts.values["Offroad_ChestnutPcieUnavailable"][1]

  update(status, alerts, offroad=False, state=STATE)
  assert "power restored" in alerts.values["Offroad_ChestnutPcieUnavailable"][1]


def test_onroad_usb_disconnect_is_latched():
  status, alerts = ChestnutStatus(), Alerts()
  update(status, alerts, offroad=False)
  update(status, alerts, offroad=False, devices=[], state=None)
  assert alerts.active == {"Offroad_ChestnutNotDetected"}
  update(status, alerts, offroad=False)
  assert "Offroad_ChestnutNotDetected" in alerts.active
