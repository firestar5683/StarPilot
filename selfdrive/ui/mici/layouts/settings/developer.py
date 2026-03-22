import pyray as rl
from collections.abc import Callable

from openpilot.common.time_helpers import system_time_valid
from openpilot.system.ui.widgets.scroller import Scroller
from openpilot.selfdrive.ui.mici.widgets.button import BigButton, BigToggle, BigParamControl
from openpilot.selfdrive.ui.mici.widgets.dialog import BigDialog, BigInputDialog, BigMultiOptionDialog
from openpilot.selfdrive.ui.mici.layouts.settings.fingerprint_catalog import (
  FingerprintModelOption,
  format_fingerprint_value,
  get_fingerprint_catalog,
  shorten_model_label,
)
from openpilot.system.ui.lib.application import gui_app
from openpilot.system.ui.widgets import NavWidget
from openpilot.selfdrive.ui.layouts.settings.common import restart_needed_callback
from openpilot.selfdrive.ui.ui_state import ui_state
from openpilot.selfdrive.ui.widgets.ssh_key import SshKeyAction


class DeveloperLayoutMici(NavWidget):
  def __init__(self, back_callback: Callable):
    super().__init__()
    self.set_back_callback(back_callback)

    def github_username_callback(username: str):
      if username:
        ssh_keys = SshKeyAction()
        ssh_keys._fetch_ssh_key(username)
        if not ssh_keys._error_message:
          self._ssh_keys_btn.set_value(username)
        else:
          dlg = BigDialog("", ssh_keys._error_message)
          gui_app.set_modal_overlay(dlg)

    def ssh_keys_callback():
      github_username = ui_state.params.get("GithubUsername") or ""
      dlg = BigInputDialog("enter GitHub username", github_username, confirm_callback=github_username_callback)
      if not system_time_valid():
        dlg = BigDialog("Please connect to Wi-Fi to fetch your key", "")
        gui_app.set_modal_overlay(dlg)
        return
      gui_app.set_modal_overlay(dlg)

    txt_ssh = gui_app.texture("icons_mici/settings/developer/ssh.png", 77, 44)
    github_username = ui_state.params.get("GithubUsername") or ""
    self._ssh_keys_btn = BigButton("SSH keys", "Not set" if not github_username else github_username, icon=txt_ssh)
    self._ssh_keys_btn.set_click_callback(ssh_keys_callback)

    # Fingerprint controls
    (
      self._make_options,
      self._models_by_make,
      self._models_by_value,
      self._make_by_model,
    ) = get_fingerprint_catalog()
    self._car_make_btn = BigButton("car make", self._get_display_make())
    self._car_make_btn.set_click_callback(self._open_make_selector)
    self._car_model_btn = BigButton("car model", self._get_display_model())
    self._car_model_btn.set_click_callback(self._open_model_selector)
    self._force_fingerprint_toggle = BigParamControl("disable auto fingerprint", "ForceFingerprint",
                                                     toggle_callback=lambda checked: restart_needed_callback(checked))

    # adb, ssh, ssh keys, debug mode, joystick debug mode, longitudinal maneuver mode, ip address
    # ******** Main Scroller ********
    self._adb_toggle = BigParamControl("enable ADB", "AdbEnabled")
    self._use_prebuilt_toggle = BigParamControl("use prebuilt binaries", "UsePrebuilt")
    self._ssh_toggle = BigParamControl("enable SSH", "SshEnabled")
    self._joystick_toggle = BigToggle("joystick debug mode",
                                      initial_state=ui_state.params.get_bool("JoystickDebugMode"),
                                      toggle_callback=self._on_joystick_debug_mode)
    self._long_maneuver_toggle = BigToggle("longitudinal maneuver mode",
                                           initial_state=ui_state.params.get_bool("LongitudinalManeuverMode"),
                                           toggle_callback=self._on_long_maneuver_mode)
    self._alpha_long_toggle = BigToggle("alpha longitudinal",
                                        initial_state=ui_state.params.get_bool("AlphaLongitudinalEnabled"),
                                        toggle_callback=self._on_alpha_long_enabled)
    self._debug_mode_toggle = BigParamControl("ui debug mode", "ShowDebugInfo",
                                              toggle_callback=lambda checked: (gui_app.set_show_touches(checked),
                                                                               gui_app.set_show_fps(checked)))

    self._scroller = Scroller([
      self._adb_toggle,
      self._use_prebuilt_toggle,
      self._ssh_toggle,
      self._ssh_keys_btn,
      self._car_make_btn,
      self._car_model_btn,
      self._force_fingerprint_toggle,
      self._joystick_toggle,
      self._long_maneuver_toggle,
      self._alpha_long_toggle,
      self._debug_mode_toggle,
    ], snap_items=False, scroll_indicator=True, edge_shadows=True)

    # Toggle lists
    self._refresh_toggles = (
      ("AdbEnabled", self._adb_toggle),
      ("UsePrebuilt", self._use_prebuilt_toggle),
      ("SshEnabled", self._ssh_toggle),
      ("ForceFingerprint", self._force_fingerprint_toggle),
      ("JoystickDebugMode", self._joystick_toggle),
      ("LongitudinalManeuverMode", self._long_maneuver_toggle),
      ("AlphaLongitudinalEnabled", self._alpha_long_toggle),
      ("ShowDebugInfo", self._debug_mode_toggle),
    )
    onroad_blocked_toggles = (self._adb_toggle, self._car_make_btn, self._car_model_btn, self._force_fingerprint_toggle, self._joystick_toggle)
    release_blocked_toggles = (self._joystick_toggle, self._long_maneuver_toggle, self._alpha_long_toggle)
    engaged_blocked_toggles = (self._long_maneuver_toggle, self._alpha_long_toggle)

    # Hide non-release toggles on release builds
    for item in release_blocked_toggles:
      item.set_visible(not ui_state.is_release)

    # Disable toggles that require offroad
    for item in onroad_blocked_toggles:
      item.set_enabled(lambda: ui_state.is_offroad())

    # Disable toggles that require not engaged
    for item in engaged_blocked_toggles:
      item.set_enabled(lambda: not ui_state.engaged)

    # Set initial state
    if ui_state.params.get_bool("ShowDebugInfo"):
      gui_app.set_show_touches(True)
      gui_app.set_show_fps(True)

    ui_state.add_offroad_transition_callback(self._update_toggles)

  def _get_display_make(self) -> str:
    make = ui_state.params.get("CarMake") or ""
    if make:
      return make

    model = ui_state.params.get("CarModel") or ""
    if model:
      return self._make_by_model.get(model, format_fingerprint_value(model.split("_", 1)[0]))
    return "Select"

  def _get_selected_model_option(self) -> FingerprintModelOption | None:
    model = ui_state.params.get("CarModel") or ""
    if not model:
      return None

    model_name = ui_state.params.get("CarModelName") or ""
    make = ui_state.params.get("CarMake") or self._make_by_model.get(model, "")
    if make and model_name:
      for option in self._models_by_make.get(make, ()):
        if option.value == model and option.label == model_name:
          return option

    return self._models_by_value.get(model)

  def _get_display_model(self) -> str:
    selected_option = self._get_selected_model_option()
    if selected_option is not None:
      return selected_option.button_label

    model = ui_state.params.get("CarModel") or ""
    model_name = ui_state.params.get("CarModelName") or ""
    if model:
      model_option = self._models_by_value.get(model)
      if model_option is not None:
        return model_option.button_label

    if model_name:
      return shorten_model_label(self._get_display_make(), model_name)
    if model:
      return format_fingerprint_value(model)
    return "Select"

  def _set_car_make(self, make: str):
    ui_state.params.put("CarMake", make)
    self._car_make_btn.set_value(make)

  def _set_car_model(self, model: str | FingerprintModelOption):
    if isinstance(model, FingerprintModelOption):
      model_option = model
      model_value = model.value
      model_name = model.label
    else:
      model_value = model
      model_option = self._models_by_value.get(model_value)
      model_name = model_option.label if model_option is not None else format_fingerprint_value(model_value)

    make = self._make_by_model.get(model_value)
    if make is not None:
      ui_state.params.put("CarMake", make)
      self._car_make_btn.set_value(make)

    ui_state.params.put("CarModel", model_value)
    ui_state.params.put("CarModelName", model_name)
    self._car_model_btn.set_value(self._get_display_model())
    restart_needed_callback(True)

  def _open_make_selector(self):
    options = list(self._make_options)
    if not options:
      gui_app.set_modal_overlay(BigDialog("No fingerprint list available", ""))
      return

    current_make = self._get_display_make()
    default_make = current_make if current_make in options else options[0]

    def on_selected():
      selected_make = option_dialog.get_selected_option()
      self._set_car_make(selected_make)

      current_model = ui_state.params.get("CarModel") or ""
      available_models = {option.value for option in self._models_by_make.get(selected_make, ())}
      if current_model not in available_models:
        default_model = self._models_by_make[selected_make][0]
        self._set_car_model(default_model)

    option_dialog = BigMultiOptionDialog(options=options, default=default_make, right_btn_callback=on_selected)
    gui_app.set_modal_overlay(option_dialog)

  def _open_model_selector(self):
    make = self._get_display_make()
    model_options = self._models_by_make.get(make, ())
    if not model_options:
      gui_app.set_modal_overlay(BigDialog("Select a car make first", ""))
      return

    current_model = ui_state.params.get("CarModel") or ""
    current_model_name = ui_state.params.get("CarModelName") or ""
    option_labels = [option.option_label for option in model_options]
    selected_by_label = {option.option_label: option for option in model_options}
    default_model = next((option.option_label for option in model_options if option.value == current_model and option.label == current_model_name), None)
    if default_model is None:
      default_model = next((option.option_label for option in model_options if option.value == current_model), option_labels[0])

    def on_selected():
      selected_model = selected_by_label[option_dialog.get_selected_option()]
      self._set_car_model(selected_model)

    option_dialog = BigMultiOptionDialog(options=option_labels, default=default_model, right_btn_callback=on_selected)
    gui_app.set_modal_overlay(option_dialog)

  def show_event(self):
    super().show_event()
    self._scroller.show_event()
    self._update_toggles()

  def _render(self, rect: rl.Rectangle):
    self._scroller.render(rect)

  def _update_toggles(self):
    ui_state.update_params()

    # CP gating
    if ui_state.CP is not None:
      alpha_avail = ui_state.CP.alphaLongitudinalAvailable
      if not alpha_avail or ui_state.is_release:
        self._alpha_long_toggle.set_visible(False)
        ui_state.params.remove("AlphaLongitudinalEnabled")
      else:
        self._alpha_long_toggle.set_visible(True)

      long_man_enabled = ui_state.has_longitudinal_control and ui_state.is_offroad()
      self._long_maneuver_toggle.set_enabled(long_man_enabled)
      if not long_man_enabled:
        self._long_maneuver_toggle.set_checked(False)
        ui_state.params.put_bool("LongitudinalManeuverMode", False)
    else:
      self._long_maneuver_toggle.set_enabled(False)
      self._alpha_long_toggle.set_visible(False)

    # Refresh toggles from params to mirror external changes
    for key, item in self._refresh_toggles:
      item.set_checked(ui_state.params.get_bool(key))

    self._car_make_btn.set_value(self._get_display_make())
    self._car_model_btn.set_value(self._get_display_model())

  def _on_joystick_debug_mode(self, state: bool):
    ui_state.params.put_bool("JoystickDebugMode", state)
    ui_state.params.put_bool("LongitudinalManeuverMode", False)
    self._long_maneuver_toggle.set_checked(False)

  def _on_long_maneuver_mode(self, state: bool):
    ui_state.params.put_bool("LongitudinalManeuverMode", state)
    ui_state.params.put_bool("JoystickDebugMode", False)
    self._joystick_toggle.set_checked(False)
    restart_needed_callback(state)

  def _on_alpha_long_enabled(self, state: bool):
    # TODO: show confirmation dialog before enabling
    ui_state.params.put_bool("AlphaLongitudinalEnabled", state)
    restart_needed_callback(state)
    self._update_toggles()
