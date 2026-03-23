import os
import threading
import json
import hashlib
import secrets
import string
import pyray as rl
from enum import IntEnum
from collections.abc import Callable
from pathlib import Path

from openpilot.common.basedir import BASEDIR
from openpilot.common.params import Params
from openpilot.common.swaglog import cloudlog
from openpilot.common.time_helpers import system_time_valid
from openpilot.system.ui.widgets.scroller import Scroller
from openpilot.system.ui.lib.scroll_panel2 import GuiScrollPanel2
from openpilot.selfdrive.ui.mici.widgets.button import BigButton, BigCircleButton, BigParamControl
from openpilot.selfdrive.ui.mici.widgets.dialog import BigMultiOptionDialog, BigDialog, BigConfirmationDialogV2, BigInputDialog
from openpilot.selfdrive.ui.mici.widgets.pairing_dialog import PairingDialog
from openpilot.selfdrive.ui.mici.onroad.driver_camera_dialog import DriverCameraDialog
from openpilot.selfdrive.ui.mici.layouts.onboarding import TrainingGuide
from openpilot.system.ui.lib.application import gui_app, FontWeight, MousePos
from openpilot.system.ui.lib.multilang import tr
from openpilot.system.ui.widgets import Widget, NavWidget
from openpilot.selfdrive.ui.ui_state import ui_state
from openpilot.system.ui.widgets.label import MiciLabel
from openpilot.system.ui.widgets.html_render import HtmlModal, HtmlRenderer
from openpilot.system.athena.registration import UNREGISTERED_DONGLE_ID
from openpilot.system.hardware import PC
from openpilot.system.hardware.hw import Paths

import qrcode
import numpy as np


class MiciFccModal(NavWidget):
  BACK_TOUCH_AREA_PERCENTAGE = 0.1

  def __init__(self, file_path: str | None = None, text: str | None = None):
    super().__init__()
    self.set_back_callback(lambda: gui_app.set_modal_overlay(None))
    self._content = HtmlRenderer(file_path=file_path, text=text)
    self._scroll_panel = GuiScrollPanel2(horizontal=False)
    self._fcc_logo = gui_app.texture("icons_mici/settings/device/fcc_logo.png", 76, 64)

  def _render(self, rect: rl.Rectangle):
    content_height = self._content.get_total_height(int(rect.width))
    content_height += self._fcc_logo.height + 20

    scroll_content_rect = rl.Rectangle(rect.x, rect.y, rect.width, content_height)
    scroll_offset = round(self._scroll_panel.update(rect, scroll_content_rect.height))

    fcc_pos = rl.Vector2(rect.x + 20, rect.y + 20 + scroll_offset)

    scroll_content_rect.y += scroll_offset + self._fcc_logo.height + 20
    self._content.render(scroll_content_rect)

    rl.draw_texture_ex(self._fcc_logo, fcc_pos, 0.0, 1.0, rl.WHITE)

    return -1


def _engaged_confirmation_callback(callback: Callable, action_text: str):
  if not ui_state.engaged:
    def confirm_callback():
      # Check engaged again in case it changed while the dialog was open
      if not ui_state.engaged:
        callback()

    red = False
    if action_text == "power off":
      icon = "icons_mici/settings/device/power.png"
      red = True
    elif action_text == "reboot":
      icon = "icons_mici/settings/device/reboot.png"
    elif action_text == "reset":
      icon = "icons_mici/settings/device/lkas.png"
    elif action_text == "reset driver monitoring":
      icon = "icons_mici/settings/device/cameras.png"
    elif action_text == "uninstall":
      icon = "icons_mici/settings/device/uninstall.png"
    else:
      # TODO: check
      icon = "icons_mici/settings/comma_icon.png"

    dlg: BigConfirmationDialogV2 | BigDialog = BigConfirmationDialogV2(f"slide to\n{action_text.lower()}", icon, red=red,
                                                                       exit_on_confirm=action_text in {"reset", "reset driver monitoring"},
                                                                       confirm_callback=confirm_callback)
    gui_app.set_modal_overlay(dlg)
  else:
    dlg = BigDialog(f"Disengage to {action_text}", "")
    gui_app.set_modal_overlay(dlg)


class DeviceInfoLayoutMici(Widget):
  def __init__(self):
    super().__init__()

    self.set_rect(rl.Rectangle(0, 0, 360, 180))

    params = Params()
    header_color = rl.Color(255, 255, 255, int(255 * 0.9))
    subheader_color = rl.Color(255, 255, 255, int(255 * 0.9 * 0.65))
    max_width = int(self._rect.width - 20)
    self._dongle_id_label = MiciLabel("device ID", 48, width=max_width, color=header_color, font_weight=FontWeight.DISPLAY)
    self._dongle_id_text_label = MiciLabel(params.get("DongleId") or 'N/A', 32, width=max_width, color=subheader_color, font_weight=FontWeight.ROMAN)

    self._serial_number_label = MiciLabel("serial", 48, color=header_color, font_weight=FontWeight.DISPLAY)
    self._serial_number_text_label = MiciLabel(params.get("HardwareSerial") or 'N/A', 32, width=max_width, color=subheader_color, font_weight=FontWeight.ROMAN)

  def _render(self, _):
    self._dongle_id_label.set_position(self._rect.x + 20, self._rect.y - 10)
    self._dongle_id_label.render()

    self._dongle_id_text_label.set_position(self._rect.x + 20, self._rect.y + 68 - 25)
    self._dongle_id_text_label.render()

    self._serial_number_label.set_position(self._rect.x + 20, self._rect.y + 114 - 30)
    self._serial_number_label.render()

    self._serial_number_text_label.set_position(self._rect.x + 20, self._rect.y + 161 - 25)
    self._serial_number_text_label.render()


class UpdaterState(IntEnum):
  IDLE = 0
  WAITING_FOR_UPDATER = 1
  UPDATER_RESPONDING = 2


class PairBigButton(BigButton):
  def __init__(self):
    super().__init__("pair", "connect.comma.ai", "icons_mici/settings/comma_icon.png")

  def _update_state(self):
    if ui_state.prime_state.is_paired():
      self.set_text("paired")
      if ui_state.prime_state.is_prime():
        self.set_value("subscribed")
      else:
        self.set_value("upgrade to prime")
    else:
      self.set_text("pair")
      self.set_value("connect.comma.ai")

  def _handle_mouse_release(self, mouse_pos: MousePos):
    super()._handle_mouse_release(mouse_pos)

    # TODO: show ad dialog when clicked if not prime
    if ui_state.prime_state.is_paired():
      return
    dlg: BigDialog | PairingDialog
    if not system_time_valid():
      dlg = BigDialog(tr("Please connect to Wi-Fi to complete initial pairing"), "")
    elif UNREGISTERED_DONGLE_ID == (ui_state.params.get("DongleId") or UNREGISTERED_DONGLE_ID):
      dlg = BigDialog(tr("Device must be registered with the comma.ai backend to pair"), "")
    else:
      dlg = PairingDialog()
    gui_app.set_modal_overlay(dlg)


class GalaxyQRDialog(NavWidget):
  def __init__(self, url: str):
    super().__init__()
    self._url = url
    self._qr_texture: rl.Texture | None = None

    self.set_back_callback(lambda: gui_app.set_modal_overlay(None))

    self._title = MiciLabel("pair with galaxy", 48, font_weight=FontWeight.BOLD,
                            color=rl.Color(255, 255, 255, int(255 * 0.9)), line_height=40, wrap_text=True)
    self._generate_qr_code()

  def _generate_qr_code(self) -> None:
    try:
      qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=10, border=0)
      qr.add_data(self._url)
      qr.make(fit=True)

      pil_img = qr.make_image(fill_color="white", back_color="black").convert("RGBA")
      img_array = np.array(pil_img, dtype=np.uint8)

      if self._qr_texture and self._qr_texture.id != 0:
        rl.unload_texture(self._qr_texture)

      rl_image = rl.Image()
      rl_image.data = rl.ffi.cast("void *", img_array.ctypes.data)
      rl_image.width = pil_img.width
      rl_image.height = pil_img.height
      rl_image.mipmaps = 1
      rl_image.format = rl.PixelFormat.PIXELFORMAT_UNCOMPRESSED_R8G8B8A8
      self._qr_texture = rl.load_texture_from_image(rl_image)
    except Exception as e:
      cloudlog.warning(f"Galaxy QR generation failed: {e}")
      self._qr_texture = None

  def _render(self, rect: rl.Rectangle):
    if self._qr_texture is not None:
      scale = rect.height / self._qr_texture.height
      pos = rl.Vector2(rect.x + 8, rect.y)
      rl.draw_texture_ex(self._qr_texture, pos, 0.0, scale, rl.WHITE)
    else:
      rl.draw_text_ex(
        gui_app.font(FontWeight.BOLD),
        "QR Code Error",
        rl.Vector2(rect.x + 20, rect.y + rect.height // 2 - 15),
        30,
        0.0,
        rl.RED,
      )

    label_x = rect.x + 8 + rect.height + 24
    self._title.set_width(int(rect.width - label_x))
    self._title.set_position(label_x, rect.y + 28)
    self._title.render()

    return -1

  def __del__(self):
    if self._qr_texture and self._qr_texture.id != 0:
      rl.unload_texture(self._qr_texture)


class GalaxyBigButton(BigButton):
  _SLUG_CHARS = string.ascii_letters + string.digits

  def __init__(self):
    super().__init__("galaxy", "", gui_app.starpilot_texture("../system/the_pond/assets/images/main_logo.png", 64, 64))
    self._galaxy_dir = Path(Paths.comma_home()) / "frogpilot" / "data" / "galaxy" if PC else Path("/data/galaxy")
    self._auth_path = self._galaxy_dir / "glxyauth"
    self._session_path = self._galaxy_dir / "glxysession"
    self._slug_path = self._galaxy_dir / "glxyslug"

  def _is_paired(self) -> bool:
    try:
      return len(self._auth_path.read_text(encoding="utf-8").strip()) == 64
    except Exception:
      return False

  def _get_slug(self) -> str:
    try:
      return self._slug_path.read_text(encoding="utf-8").strip()
    except Exception:
      return ""

  def _show_qr(self):
    slug = self._get_slug()
    if not slug:
      gui_app.set_modal_overlay(BigDialog("Galaxy is not paired yet.", ""))
      return
    gui_app.set_modal_overlay(GalaxyQRDialog(f"https://galaxy.firestar.link/{slug}"))

  def _pair_with_pin(self, pin: str):
    clean_pin = str(pin or "").strip()
    if len(clean_pin) < 6:
      gui_app.set_modal_overlay(BigDialog("PIN must be at least 6 characters.", ""))
      return

    try:
      self._galaxy_dir.mkdir(parents=True, exist_ok=True)
      self._auth_path.write_text(hashlib.sha256(clean_pin.encode("utf-8")).hexdigest(), encoding="utf-8")
      self._session_path.write_text(secrets.token_hex(32), encoding="utf-8")
      slug = "".join(secrets.choice(self._SLUG_CHARS) for _ in range(16))
      self._slug_path.write_text(slug, encoding="utf-8")
    except Exception as e:
      cloudlog.warning(f"Galaxy pairing write failed: {e}")
      gui_app.set_modal_overlay(BigDialog("Failed to pair with Galaxy.", ""))
      return

    self._show_qr()

  def _unpair(self):
    for path in (self._auth_path, self._session_path, self._slug_path):
      try:
        path.unlink(missing_ok=True)
      except TypeError:
        # Python < 3.8 fallback
        if path.exists():
          path.unlink()
      except Exception as e:
        cloudlog.warning(f"Galaxy unpair cleanup failed for {path}: {e}")

  def _handle_mouse_release(self, mouse_pos: MousePos):
    super()._handle_mouse_release(mouse_pos)

    if self._is_paired():
      show_qr_option = "show qr"
      unpair_option = "unpair"

      def on_option_selected():
        selected = option_dialog.get_selected_option()
        if selected == show_qr_option:
          self._show_qr()
        elif selected == unpair_option:
          confirm = BigConfirmationDialogV2(
            "slide to\nunpair galaxy",
            "icons_mici/settings/device/uninstall.png",
            red=True,
            confirm_callback=self._unpair,
          )
          gui_app.set_modal_overlay(confirm)

      option_dialog = BigMultiOptionDialog(
        options=[show_qr_option, unpair_option],
        default=show_qr_option,
        right_btn_callback=on_option_selected,
      )
      gui_app.set_modal_overlay(option_dialog)
      return

    pin_dialog = BigInputDialog(
      hint="enter galaxy pin...",
      default_text="",
      minimum_length=6,
      confirm_callback=self._pair_with_pin,
    )
    gui_app.set_modal_overlay(pin_dialog)

  def _update_state(self):
    self.set_value("paired" if self._is_paired() else "pair")


UPDATER_TIMEOUT = 10.0  # seconds to wait for updater to respond


class UpdateOpenpilotBigButton(BigButton):
  def __init__(self):
    self._txt_update_icon = gui_app.texture("icons_mici/settings/device/update.png", 64, 64)
    self._txt_reboot_icon = gui_app.texture("icons_mici/settings/device/reboot.png", 64, 64)
    self._txt_up_to_date_icon = gui_app.texture("icons_mici/settings/device/up_to_date.png", 64, 64)
    super().__init__("update openpilot", "", self._txt_update_icon)

    self._waiting_for_updater_t: float | None = None
    self._hide_value_t: float | None = None
    self._state: UpdaterState = UpdaterState.IDLE

    ui_state.add_offroad_transition_callback(self.offroad_transition)

  def offroad_transition(self):
    if ui_state.is_offroad():
      self.set_enabled(True)

  def _handle_mouse_release(self, mouse_pos: MousePos):
    if not system_time_valid():
      dlg = BigDialog(tr("Please connect to Wi-Fi to update"), "")
      gui_app.set_modal_overlay(dlg)
      return

    self.set_enabled(False)
    self._state = UpdaterState.WAITING_FOR_UPDATER
    self.set_icon(self._txt_update_icon)

    def run():
      if self.get_value() == "download update":
        os.system("pkill -SIGHUP -f system.updated.updated")
      elif self.get_value() == "update now":
        ui_state.params.put_bool("DoReboot", True)
      else:
        os.system("pkill -SIGUSR1 -f system.updated.updated")

    threading.Thread(target=run, daemon=True).start()

  def set_value(self, value: str):
    super().set_value(value)
    if value:
      self.set_text("")
    else:
      self.set_text("update openpilot")

  def _update_state(self):
    if ui_state.started:
      self.set_enabled(False)
      return

    updater_state = ui_state.params.get("UpdaterState") or ""
    failed_count = ui_state.params.get("UpdateFailedCount")
    failed = False if failed_count is None else int(failed_count) > 0

    if ui_state.params.get_bool("UpdateAvailable"):
      self.set_rotate_icon(False)
      self.set_enabled(True)
      if self.get_value() != "update now":
        self.set_value("update now")
        self.set_icon(self._txt_reboot_icon)

    elif self._state == UpdaterState.WAITING_FOR_UPDATER:
      self.set_rotate_icon(True)
      if updater_state != "idle":
        self._state = UpdaterState.UPDATER_RESPONDING

      # Recover from updater not responding (time invalid shortly after boot)
      if self._waiting_for_updater_t is None:
        self._waiting_for_updater_t = rl.get_time()

      if self._waiting_for_updater_t is not None and rl.get_time() - self._waiting_for_updater_t > UPDATER_TIMEOUT:
        self.set_rotate_icon(False)
        self.set_value("updater failed to respond")
        self._state = UpdaterState.IDLE
        self._hide_value_t = rl.get_time()

    elif self._state == UpdaterState.UPDATER_RESPONDING:
      if updater_state == "idle":
        self.set_rotate_icon(False)
        self._state = UpdaterState.IDLE
        self._hide_value_t = rl.get_time()
      else:
        if self.get_value() != updater_state:
          self.set_value(updater_state)

    elif self._state == UpdaterState.IDLE:
      self.set_rotate_icon(False)
      if failed:
        if self.get_value() != "failed to update":
          self.set_value("failed to update")

      elif ui_state.params.get_bool("UpdaterFetchAvailable"):
        self.set_enabled(True)
        if self.get_value() != "download update":
          self.set_value("download update")

      elif self._hide_value_t is not None:
        self.set_enabled(True)
        if self.get_value() == "checking...":
          self.set_value("up to date")
          self.set_icon(self._txt_up_to_date_icon)

        # Hide previous text after short amount of time (up to date or failed)
        if rl.get_time() - self._hide_value_t > 3.0:
          self._hide_value_t = None
          self.set_value("")
          self.set_icon(self._txt_update_icon)
      else:
        if self.get_value() != "":
          self.set_value("")

    if self._state != UpdaterState.WAITING_FOR_UPDATER:
      self._waiting_for_updater_t = None


class DeviceLayoutMici(NavWidget):
  def __init__(self, back_callback: Callable):
    super().__init__()

    self._fcc_dialog: HtmlModal | None = None
    self._driver_camera: DriverCameraDialog | None = None
    self._training_guide: TrainingGuide | None = None

    def power_off_callback():
      ui_state.params.put_bool("DoShutdown", True)

    def reboot_callback():
      ui_state.params.put_bool("DoReboot", True)

    def reset_calibration_callback():
      params = ui_state.params
      params.remove("CalibrationParams")
      params.remove("LiveTorqueParameters")
      params.remove("LiveParameters")
      params.remove("LiveParametersV2")
      params.remove("LiveDelay")
      params.put_bool("OnroadCycleRequested", True)

    def reset_driver_monitoring_callback():
      params = ui_state.params
      params.remove("IsRhdDetected")
      params.put_bool("OnroadCycleRequested", True)

    def uninstall_openpilot_callback():
      ui_state.params.put_bool("DoUninstall", True)

    reset_driver_monitoring_btn = BigButton("reset driver monitoring calibration", "", "icons_mici/settings/device/cameras.png")
    reset_driver_monitoring_btn.set_click_callback(lambda: _engaged_confirmation_callback(reset_driver_monitoring_callback, "reset driver monitoring"))

    reset_calibration_btn = BigButton("reset calibration", "", "icons_mici/settings/device/lkas.png")
    reset_calibration_btn.set_click_callback(lambda: _engaged_confirmation_callback(reset_calibration_callback, "reset"))

    uninstall_openpilot_btn = BigButton("uninstall openpilot", "", "icons_mici/settings/device/uninstall.png")
    uninstall_openpilot_btn.set_click_callback(lambda: _engaged_confirmation_callback(uninstall_openpilot_callback, "uninstall"))

    reboot_btn = BigCircleButton("icons_mici/settings/device/reboot.png", red=False)
    reboot_btn.set_click_callback(lambda: _engaged_confirmation_callback(reboot_callback, "reboot"))

    self._power_off_btn = BigCircleButton("icons_mici/settings/device/power.png", red=True)
    self._power_off_btn.set_click_callback(lambda: _engaged_confirmation_callback(power_off_callback, "power off"))

    self._load_languages()

    def language_callback():
      def selected_language_callback():
        selected_language = dlg.get_selected_option()
        ui_state.params.put("LanguageSetting", self._languages[selected_language])

      current_language_name = ui_state.params.get("LanguageSetting")
      current_language = next(name for name, lang in self._languages.items() if lang == current_language_name)

      dlg = BigMultiOptionDialog(list(self._languages), default=current_language, right_btn_callback=selected_language_callback)
      gui_app.set_modal_overlay(dlg)

    # lang_button = BigButton("change language", "", "icons_mici/settings/device/language.png")
    # lang_button.set_click_callback(language_callback)

    regulatory_btn = BigButton("regulatory info", "", "icons_mici/settings/device/info.png")
    regulatory_btn.set_click_callback(self._on_regulatory)

    driver_cam_btn = BigButton("driver camera preview", "", "icons_mici/settings/device/cameras.png")
    driver_cam_btn.set_click_callback(self._show_driver_camera)
    driver_cam_btn.set_enabled(lambda: ui_state.is_offroad())

    review_training_guide_btn = BigButton("review training guide", "", "icons_mici/settings/device/info.png")
    review_training_guide_btn.set_click_callback(self._on_review_training_guide)
    review_training_guide_btn.set_enabled(lambda: ui_state.is_offroad())

    self._scroller = Scroller([
      DeviceInfoLayoutMici(),
      UpdateOpenpilotBigButton(),
      BigParamControl("automatically update starpilot", "AutomaticUpdates"),
      PairBigButton(),
      review_training_guide_btn,
      driver_cam_btn,
      reset_driver_monitoring_btn,
      # lang_button,
      reset_calibration_btn,
      uninstall_openpilot_btn,
      regulatory_btn,
      reboot_btn,
      self._power_off_btn,
    ], snap_items=False, scroll_indicator=True, edge_shadows=True)

    # Set up back navigation
    self.set_back_callback(back_callback)

    # Hide power off button when onroad
    ui_state.add_offroad_transition_callback(self._offroad_transition)

  def _on_regulatory(self):
    if not self._fcc_dialog:
      self._fcc_dialog = MiciFccModal(os.path.join(BASEDIR, "selfdrive/assets/offroad/mici_fcc.html"))
    gui_app.set_modal_overlay(self._fcc_dialog, callback=setattr(self, '_fcc_dialog', None))

  def _offroad_transition(self):
    self._power_off_btn.set_visible(ui_state.is_offroad())

  def _show_driver_camera(self):
    if not self._driver_camera:
      self._driver_camera = DriverCameraDialog()
    gui_app.set_modal_overlay(self._driver_camera, callback=lambda result: setattr(self, '_driver_camera', None))

  def _on_review_training_guide(self):
    if not self._training_guide:
      def completed_callback():
        gui_app.set_modal_overlay(None)

      self._training_guide = TrainingGuide(completed_callback=completed_callback)
    gui_app.set_modal_overlay(self._training_guide, callback=lambda result: setattr(self, '_training_guide', None))

  def _load_languages(self):
    with open(os.path.join(BASEDIR, "selfdrive/ui/translations/languages.json")) as f:
      self._languages = json.load(f)

  def show_event(self):
    super().show_event()
    self._scroller.show_event()

  def _render(self, rect: rl.Rectangle):
    self._scroller.render(rect)
