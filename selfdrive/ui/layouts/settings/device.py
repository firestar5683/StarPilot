import hashlib
import os
import math
from pathlib import Path
import secrets
import string

from cereal import messaging, log
import numpy as np
import pyray as rl
import qrcode

from openpilot.common.basedir import BASEDIR
from openpilot.common.swaglog import cloudlog
from openpilot.selfdrive.ui.onroad.driver_camera_dialog import DriverCameraDialog
from openpilot.selfdrive.ui.ui_state import ui_state
from openpilot.selfdrive.ui.layouts.onboarding import TrainingGuide
from openpilot.selfdrive.ui.widgets.pairing_dialog import PairingDialog
from openpilot.system.hardware import HARDWARE, PC, TICI
from openpilot.system.hardware.hw import Paths
from openpilot.system.ui.lib.application import FontWeight, gui_app
from openpilot.system.ui.lib.multilang import multilang, tr, tr_noop
from openpilot.system.ui.widgets import Widget, DialogResult
from openpilot.system.ui.widgets.confirm_dialog import ConfirmDialog, alert_dialog
from openpilot.system.ui.widgets.html_render import HtmlModal
from openpilot.system.ui.widgets.keyboard import Keyboard
from openpilot.system.ui.widgets.list_view import text_item, button_item, dual_button_item
from openpilot.system.ui.widgets.option_dialog import MultiOptionDialog
from openpilot.system.ui.widgets.scroller_tici import Scroller

# Description constants
DESCRIPTIONS = {
  'pair_device': tr_noop("Pair your device with comma connect (connect.comma.ai) and claim your comma prime offer."),
  'pair_galaxy': tr_noop("Pair your device with Galaxy for remote access to The Galaxy."),
  'driver_camera': tr_noop("Preview the driver facing camera to ensure that driver monitoring has good visibility. (vehicle must be off)"),
  'reset_driver_monitoring': tr_noop("Clears the saved driver monitoring wheel-side calibration and any manual right-hand-driving override."),
  'reset_calibration': tr_noop("openpilot requires the device to be mounted within 4° left or right and within 5° up or 9° down."),
  'review_guide': tr_noop("Review the rules, features, and limitations of openpilot"),
}

GALAXY_SLUG_CHARS = string.ascii_letters + string.digits


def get_galaxy_dir() -> Path:
  return Path(Paths.comma_home()) / "starpilot" / "data" / "galaxy" if PC else Path("/data/galaxy")


class GalaxyQRDialog(Widget):
  def __init__(self, url: str):
    super().__init__()
    self._url = url
    self._qr_texture: rl.Texture | None = None
    self._generate_qr_code()

  def _generate_qr_code(self) -> None:
    try:
      qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=10, border=4)
      qr.add_data(self._url)
      qr.make(fit=True)

      pil_img = qr.make_image(fill_color="black", back_color="white").convert("RGBA")
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
    except Exception:
      cloudlog.exception("Galaxy QR generation failed")
      self._qr_texture = None

  def _handle_mouse_release(self, _):
    gui_app.pop_widget()

  def _render_centered_text(self, rect: rl.Rectangle, text: str, y: float, font_size: int, color: rl.Color, font_weight: FontWeight = FontWeight.NORMAL) -> None:
    font = gui_app.font(font_weight)
    size = rl.measure_text_ex(font, text, font_size, 0)
    rl.draw_text_ex(font, text, rl.Vector2(rect.x + (rect.width - size.x) / 2, y), font_size, 0, color)

  def _render(self, rect: rl.Rectangle):
    rl.clear_background(rl.Color(26, 26, 48, 255))

    title_y = rect.y + 100
    self._render_centered_text(rect, tr("Scan to open Galaxy"), title_y, 70, rl.WHITE, FontWeight.BOLD)

    if self._qr_texture is None:
      self._render_centered_text(rect, tr("QR Code Error"), rect.y + rect.height / 2 - 30, 50, rl.RED, FontWeight.BOLD)
      return

    qr_size = min(rect.height * 0.58, rect.width * 0.42)
    qr_x = rect.x + (rect.width - qr_size) / 2
    qr_y = title_y + 120
    source = rl.Rectangle(0, 0, self._qr_texture.width, self._qr_texture.height)
    rl.draw_texture_pro(self._qr_texture, source, rl.Rectangle(qr_x, qr_y, qr_size, qr_size), rl.Vector2(0, 0), 0, rl.WHITE)

    self._render_centered_text(rect, self._url, qr_y + qr_size + 45, 36, rl.Color(180, 150, 230, 255))
    self._render_centered_text(rect, tr("Tap anywhere to dismiss"), rect.y + rect.height - 120, 34, rl.Color(160, 160, 190, 255))

  def __del__(self):
    if self._qr_texture and self._qr_texture.id != 0:
      rl.unload_texture(self._qr_texture)


class DeviceLayout(Widget):
  def __init__(self):
    super().__init__()

    self._params = ui_state.ui_params
    self._select_language_dialog: MultiOptionDialog | None = None
    self._driver_camera: DriverCameraDialog | None = None
    self._pair_device_dialog: PairingDialog | None = None
    self._galaxy_keyboard = Keyboard(min_text_size=6, password_mode=True, show_password_toggle=True)
    self._galaxy_manage_dialog: MultiOptionDialog | None = None
    self._fcc_dialog: HtmlModal | None = None
    self._training_guide: TrainingGuide | None = None

    self._galaxy_dir = get_galaxy_dir()
    self._galaxy_auth_path = self._galaxy_dir / "glxyauth"
    self._galaxy_session_path = self._galaxy_dir / "glxysession"
    self._galaxy_slug_path = self._galaxy_dir / "glxyslug"

    items = self._initialize_items()
    self._scroller = Scroller(items, line_separator=True, spacing=0)

    ui_state.add_offroad_transition_callback(self._offroad_transition)

  def _initialize_items(self):
    self._pair_device_btn = button_item(lambda: tr("Pair Device"), lambda: tr("PAIR"), lambda: tr(DESCRIPTIONS['pair_device']), callback=self._pair_device)
    self._pair_device_btn.set_visible(lambda: not ui_state.prime_state.is_paired())
    self._pair_galaxy_btn = button_item(lambda: tr("Pair with Galaxy"), self._galaxy_button_text,
                                        lambda: tr(DESCRIPTIONS['pair_galaxy']), callback=self._pair_galaxy)

    self._reset_calib_btn = button_item(lambda: tr("Reset Calibration"), lambda: tr("RESET"), lambda: tr(DESCRIPTIONS['reset_calibration']),
                                        callback=self._reset_calibration_prompt)
    self._reset_calib_btn.set_description_opened_callback(self._update_calib_description)

    self._power_off_btn = dual_button_item(lambda: tr("Reboot"), lambda: tr("Power Off"),
                                           left_callback=self._reboot_prompt, right_callback=self._power_off_prompt)

    items = [
      text_item(lambda: tr("Dongle ID"), self._params.get("DongleId") or (lambda: tr("N/A"))),
      text_item(lambda: tr("Serial"), self._params.get("HardwareSerial") or (lambda: tr("N/A"))),
      self._pair_device_btn,
      self._pair_galaxy_btn,
      button_item(lambda: tr("Driver Camera"), lambda: tr("PREVIEW"), lambda: tr(DESCRIPTIONS['driver_camera']),
                  callback=self._show_driver_camera, enabled=ui_state.is_offroad),
      button_item(lambda: tr("Reset Driver Monitoring"), lambda: tr("RESET"), lambda: tr(DESCRIPTIONS['reset_driver_monitoring']),
                  callback=self._reset_driver_monitoring_prompt, enabled=ui_state.is_offroad),
      self._reset_calib_btn,
      button_item(lambda: tr("Review Training Guide"), lambda: tr("REVIEW"), lambda: tr(DESCRIPTIONS['review_guide']),
                  self._on_review_training_guide, enabled=ui_state.is_offroad),
      regulatory_btn := button_item(lambda: tr("Regulatory"), lambda: tr("VIEW"), callback=self._on_regulatory, enabled=ui_state.is_offroad),
      button_item(lambda: tr("Change Language"), lambda: tr("CHANGE"), callback=self._show_language_dialog),
      self._power_off_btn,
    ]
    regulatory_btn.set_visible(TICI)
    return items

  def _offroad_transition(self):
    self._power_off_btn.action_item.right_button.set_visible(ui_state.is_offroad())

  def show_event(self):
    self._scroller.show_event()

  def _render(self, rect):
    self._scroller.render(rect)

  def _show_language_dialog(self):
    def handle_language_selection(result: int):
      if result == 1 and self._select_language_dialog:
        selected_language = multilang.languages[self._select_language_dialog.selection]
        multilang.change_language(selected_language)
        self._update_calib_description()
      self._select_language_dialog = None

    self._select_language_dialog = MultiOptionDialog(tr("Select a language"), multilang.languages, multilang.codes[multilang.language],
                                                      option_font_weight=FontWeight.UNIFONT, callback=handle_language_selection)
    gui_app.push_widget(self._select_language_dialog)

  def _show_driver_camera(self):
    if not self._driver_camera:
      self._driver_camera = DriverCameraDialog()

    gui_app.push_widget(self._driver_camera)

  def _reset_calibration_prompt(self):
    if ui_state.engaged:
      gui_app.push_widget(alert_dialog(tr("Disengage to Reset Calibration")))
      return

    def reset_calibration(result: int):
      # Check engaged again in case it changed while the dialog was open
      if ui_state.engaged or result != DialogResult.CONFIRM:
        return

      self._params.remove("CalibrationParams")
      self._params.remove("LiveTorqueParameters")
      self._params.remove("LiveParameters")
      self._params.remove("LiveParametersV2")
      self._params.remove("LiveDelay")
      self._params.put_bool("OnroadCycleRequested", True)
      self._update_calib_description()

    dialog = ConfirmDialog(tr("Are you sure you want to reset calibration?"), tr("Reset"), callback=reset_calibration)
    gui_app.push_widget(dialog)

  def _reset_driver_monitoring_prompt(self):
    if ui_state.engaged:
      gui_app.push_widget(alert_dialog(tr("Disengage to Reset Driver Monitoring")))
      return

    def reset_driver_monitoring(result: int):
      if ui_state.engaged or result != DialogResult.CONFIRM:
        return

      self._params.remove("IsRhdDetected")
      self._params.remove("IsRHD")
      self._params.remove("IsRHDOverride")
      self._params.put_bool("OnroadCycleRequested", True)

    dialog = ConfirmDialog(tr("Are you sure you want to reset driver monitoring calibration?"), tr("Reset"), callback=reset_driver_monitoring)
    gui_app.push_widget(dialog)

  def _update_calib_description(self):
    desc = tr(DESCRIPTIONS['reset_calibration'])

    calib_bytes = self._params.get("CalibrationParams")
    if calib_bytes:
      try:
        calib = messaging.log_from_bytes(calib_bytes, log.Event).liveCalibration

        if calib.calStatus != log.LiveCalibrationData.Status.uncalibrated:
          pitch = math.degrees(calib.rpyCalib[1])
          yaw = math.degrees(calib.rpyCalib[2])
          desc += tr(" Your device is pointed {:.1f}° {} and {:.1f}° {}.").format(abs(pitch), tr("down") if pitch > 0 else tr("up"),
                                                                                  abs(yaw), tr("left") if yaw > 0 else tr("right"))
      except Exception:
        cloudlog.exception("invalid CalibrationParams")

    lag_perc = 0
    lag_bytes = self._params.get("LiveDelay")
    if lag_bytes:
      try:
        lag_perc = messaging.log_from_bytes(lag_bytes, log.Event).liveDelay.calPerc
      except Exception:
        cloudlog.exception("invalid LiveDelay")
    if lag_perc < 100:
      desc += tr("<br><br>Steering lag calibration is {}% complete.").format(lag_perc)
    else:
      desc += tr("<br><br>Steering lag calibration is complete.")

    torque_bytes = self._params.get("LiveTorqueParameters")
    if torque_bytes:
      try:
        torque = messaging.log_from_bytes(torque_bytes, log.Event).liveTorqueParameters
        # don't add for non-torque cars
        if torque.useParams:
          torque_perc = torque.calPerc
          if torque_perc < 100:
            desc += tr(" Steering torque response calibration is {}% complete.").format(torque_perc)
          else:
            desc += tr(" Steering torque response calibration is complete.")
      except Exception:
        cloudlog.exception("invalid LiveTorqueParameters")

    desc += "<br><br>"
    desc += tr("openpilot is continuously calibrating, resetting is rarely required. " +
               "Resetting calibration will restart openpilot if the car is powered on.")

    self._reset_calib_btn.set_description(desc)

  def _reboot_prompt(self):
    dialog = ConfirmDialog(tr("Are you sure you want to reboot?"), tr("Reboot"), callback=self._perform_reboot)
    gui_app.push_widget(dialog)

  def _perform_reboot(self, result: DialogResult):
    if result == DialogResult.CONFIRM:
      self._params.put_bool("DoUserReboot", True)
      try:
        HARDWARE.reboot()
      except Exception:
        cloudlog.exception("Direct user-requested reboot failed; manager fallback requested")

  def _power_off_prompt(self):
    if ui_state.engaged:
      gui_app.push_widget(alert_dialog(tr("Disengage to Power Off")))
      return

    dialog = ConfirmDialog(tr("Are you sure you want to power off?"), tr("Power Off"), callback=self._perform_power_off)
    gui_app.push_widget(dialog)

  def _perform_power_off(self, result: int):
    if not ui_state.engaged and result == DialogResult.CONFIRM:
      self._params.put_bool_nonblocking("DoShutdown", True)

  def _pair_device(self):
    if not self._pair_device_dialog:
      self._pair_device_dialog = PairingDialog()
    gui_app.push_widget(self._pair_device_dialog)

  def _is_galaxy_paired(self) -> bool:
    try:
      return len(self._galaxy_auth_path.read_text(encoding="utf-8").strip()) == 64
    except Exception:
      return False

  def _galaxy_button_text(self) -> str:
    return tr("MANAGE") if self._is_galaxy_paired() else tr("PAIR")

  def _get_galaxy_slug(self) -> str:
    try:
      return self._galaxy_slug_path.read_text(encoding="utf-8").strip()
    except Exception:
      return ""

  def _show_galaxy_qr(self):
    slug = self._get_galaxy_slug()
    if not slug:
      gui_app.push_widget(alert_dialog(tr("Galaxy is not paired yet.")))
      return
    gui_app.push_widget(GalaxyQRDialog(f"https://galaxy.firestar.link/{slug}"))

  def _pair_galaxy(self):
    if self._is_galaxy_paired():
      show_qr = tr("Show QR")
      unpair = tr("Unpair")

      def on_select(result: int):
        if result != DialogResult.CONFIRM or not self._galaxy_manage_dialog:
          return

        if self._galaxy_manage_dialog.selection == show_qr:
          self._show_galaxy_qr()
        elif self._galaxy_manage_dialog.selection == unpair:
          gui_app.push_widget(ConfirmDialog(tr("Are you sure you want to unpair from Galaxy?"), tr("Unpair"), callback=self._unpair_galaxy))

      self._galaxy_manage_dialog = MultiOptionDialog(tr("Galaxy"), [show_qr, unpair], show_qr, callback=on_select)
      gui_app.push_widget(self._galaxy_manage_dialog)
      return

    self._galaxy_keyboard.clear()
    self._galaxy_keyboard.set_title(tr("Set Galaxy Password"), tr("Set a password to secure your Galaxy access. Min 6 characters."))
    self._galaxy_keyboard.set_callback(self._pair_galaxy_from_keyboard)
    gui_app.push_widget(self._galaxy_keyboard)

  def _pair_galaxy_from_keyboard(self, result: int):
    if result != DialogResult.CONFIRM:
      return

    password = self._galaxy_keyboard.text.strip()
    self._galaxy_keyboard.clear()
    if len(password) < 6:
      gui_app.push_widget(alert_dialog(tr("Password must be at least 6 characters.")))
      return

    try:
      self._galaxy_dir.mkdir(parents=True, exist_ok=True)
      self._galaxy_auth_path.write_text(hashlib.sha256(password.encode("utf-8")).hexdigest(), encoding="utf-8")
      self._galaxy_session_path.write_text(secrets.token_hex(32), encoding="utf-8")
      slug = "".join(secrets.choice(GALAXY_SLUG_CHARS) for _ in range(16))
      self._galaxy_slug_path.write_text(slug, encoding="utf-8")
    except Exception:
      cloudlog.exception("Galaxy pairing write failed")
      gui_app.push_widget(alert_dialog(tr("Failed to pair with Galaxy.")))
      return

    self._show_galaxy_qr()

  def _unpair_galaxy(self, result: int):
    if result != DialogResult.CONFIRM:
      return

    for path in (self._galaxy_auth_path, self._galaxy_session_path, self._galaxy_slug_path):
      try:
        path.unlink(missing_ok=True)
      except TypeError:
        if path.exists():
          path.unlink()
      except Exception:
        cloudlog.exception(f"Galaxy unpair cleanup failed for {path}")

  def _on_regulatory(self):
    if not self._fcc_dialog:
      self._fcc_dialog = HtmlModal(os.path.join(BASEDIR, "selfdrive/assets/offroad/fcc.html"))
    gui_app.push_widget(self._fcc_dialog)

  def _on_review_training_guide(self):
    if not self._training_guide:
      def completed_callback():
        gui_app.pop_widget()

      self._training_guide = TrainingGuide(completed_callback=completed_callback)
    gui_app.push_widget(self._training_guide)
