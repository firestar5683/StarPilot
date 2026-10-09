from functools import cached_property

from openpilot.common.params import Params
from openpilot.system.ui.widgets.scroller import NavScroller
from openpilot.selfdrive.ui.mici.widgets.button import BigButton, BigMultiToggle
from openpilot.selfdrive.ui.mici.layouts.settings.toggles import TogglesLayoutMici
from openpilot.selfdrive.ui.mici.layouts.settings.network.network_layout import NetworkLayoutMici
from openpilot.selfdrive.ui.mici.layouts.settings.device import DeviceLayoutMici, PairBigButton
from openpilot.selfdrive.ui.mici.layouts.settings.developer import DeveloperLayoutMici
from openpilot.selfdrive.ui.mici.layouts.settings.driving_model import DrivingModelBigButton
from openpilot.selfdrive.ui.mici.layouts.settings.galaxy import GalaxyBigButton
from openpilot.system.ui.lib.application import gui_app, FontWeight
from openpilot.system.ui.lib.wifi_manager import WifiManager


class SettingsBigButton(BigButton):
  def _get_label_font_size(self):
    return 64


class ForceDriveStateBigButton(BigMultiToggle):
  def __init__(self):
    super().__init__("force drive state", ["offroad", "onroad", "off"])
    self._params = Params()
    self.refresh()

  def _get_label_font_size(self):
    return 40

  def _width_hint(self) -> int:
    return int(self._rect.width - self.LABEL_HORIZONTAL_PADDING * 2 - self._txt_enabled_toggle.width - 20)

  def _handle_mouse_release(self, mouse_pos):
    super()._handle_mouse_release(mouse_pos)
    self._apply_mode(self.value)

  def _apply_mode(self, mode: str):
    if mode == "offroad":
      self._params.put_bool("ForceOffroad", True)
      self._params.put_bool("ForceOnroad", False)
    elif mode == "onroad":
      self._params.put_bool("ForceOffroad", False)
      self._params.put_bool("ForceOnroad", True)
    else:
      self._params.put_bool("ForceOffroad", False)
      self._params.put_bool("ForceOnroad", False)

  def refresh(self):
    if self._params.get_bool("ForceOffroad"):
      self.set_value("offroad")
    elif self._params.get_bool("ForceOnroad"):
      self.set_value("onroad")
    else:
      self.set_value("off")


class SettingsLayout(NavScroller):
  def __init__(self, wifi_manager: WifiManager):
    super().__init__()
    self._params = Params()

    self._toggles_panel = TogglesLayoutMici()
    toggles_btn = SettingsBigButton("toggles", "", gui_app.texture("icons_mici/settings.png", 64, 64))
    toggles_btn.set_click_callback(lambda: gui_app.push_widget(self._toggles_panel))

    self._network_panel = NetworkLayoutMici(wifi_manager)
    network_btn = SettingsBigButton("network", "", gui_app.texture("icons_mici/settings/network/wifi_strength_full.png", 76, 56))
    network_btn.set_click_callback(lambda: gui_app.push_widget(self._network_panel))

    bluetooth_btn = SettingsBigButton("bluetooth", "", gui_app.texture("icons_mici/settings/bluetooth.png", 64, 64))
    bluetooth_btn.set_click_callback(lambda: gui_app.push_widget(self._bluetooth_panel))

    vehicle_btn = SettingsBigButton("vehicle", "", gui_app.texture("icons_mici/settings/vehicle.png", 64, 57))
    vehicle_btn.set_click_callback(lambda: gui_app.push_widget(self._vehicle_panel))

    visuals_btn = SettingsBigButton("visuals", "", gui_app.texture("icons_mici/settings/device/cameras.png", 64, 64))
    visuals_btn.set_click_callback(lambda: gui_app.push_widget(self._visuals_panel))

    device_btn = SettingsBigButton("device", "", gui_app.texture("icons_mici/settings/device_icon.png", 72, 58))
    device_btn.set_click_callback(lambda: gui_app.push_widget(self._device_panel))

    software_btn = SettingsBigButton("software", "", gui_app.texture("icons_mici/settings/device/update.png", 64, 75))
    software_btn.set_click_callback(lambda: gui_app.push_widget(self._software_panel))

    self._developer_panel = DeveloperLayoutMici()
    developer_btn = SettingsBigButton("developer", "", gui_app.texture("icons_mici/settings/developer_icon.png", 64, 60))
    developer_btn.set_click_callback(lambda: gui_app.push_widget(self._developer_panel))

    self._force_drive_state_btn = ForceDriveStateBigButton()
    self._driving_model_btn = DrivingModelBigButton()
    galaxy_btn = GalaxyBigButton()

    self._scroller.add_widgets([
      toggles_btn,
      network_btn,
      bluetooth_btn,
      self._force_drive_state_btn,
      vehicle_btn,
      device_btn,
      software_btn,
      self._driving_model_btn,
      visuals_btn,
      galaxy_btn,
      PairBigButton(),
      #BigDialogButton("manual", "", "icons_mici/settings/manual_icon.png", "Check out the mici user\nmanual at comma.ai/setup"),
      developer_btn,
    ])

    self._font_medium = gui_app.font(FontWeight.MEDIUM)

  @cached_property
  def _bluetooth_panel(self):
    from openpilot.selfdrive.ui.mici.layouts.settings.bluetooth import BluetoothLayoutMici
    return BluetoothLayoutMici()

  @cached_property
  def _vehicle_panel(self):
    from openpilot.selfdrive.ui.mici.layouts.settings.vehicle import VehicleLayoutMici
    return VehicleLayoutMici()

  @cached_property
  def _visuals_panel(self):
    from openpilot.selfdrive.ui.mici.layouts.settings.visuals import VisualsLayoutMici
    return VisualsLayoutMici()

  @cached_property
  def _device_panel(self):
    return DeviceLayoutMici()

  @cached_property
  def _software_panel(self):
    from openpilot.selfdrive.ui.mici.layouts.settings.software import SoftwareLayoutMici
    return SoftwareLayoutMici()

  def show_event(self):
    super().show_event()
    self._force_drive_state_btn.refresh()
    self._driving_model_btn.refresh()
