import base64
import hashlib
import json
import secrets
import socket
import string
from pathlib import Path
from urllib.parse import quote

import numpy as np
import pyray as rl
import qrcode

from openpilot.common.swaglog import cloudlog
from openpilot.selfdrive.ui.mici.widgets.button import BigButton
from openpilot.selfdrive.ui.mici.widgets.dialog import BigDialog, BigConfirmationDialog, BigInputDialog, BigMultiOptionDialog
from openpilot.system.hardware import PC
from openpilot.system.hardware.hw import Paths
from openpilot.system.ui.lib.application import FontWeight, gui_app
from openpilot.system.ui.widgets.label import UnifiedLabel
from openpilot.system.ui.widgets.nav_widget import NavWidget


GALAXY_COOKIE_NAME = "galaxy_session"
GALAXY_PUBLIC_BASE_URL = "https://galaxy.firestar.link"


def _build_galaxy_session_value(slug: str, token: str) -> str:
  if not slug or not token:
    return ""
  return quote(f"{slug}:{token}", safe="")


def _local_base_url() -> str:
  try:
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
      sock.connect(("8.8.8.8", 80))
      address = sock.getsockname()[0]
      if address and not address.startswith("127."):
        return f"http://{address}:8082"
  except Exception:
    pass
  return ""


def _galaxy_pairing_payload_value(slug: str, token: str) -> str:
  session_token = _build_galaxy_session_value(slug, token)
  if not slug or not session_token:
    return ""

  payload = {
    "format": "galaxy-vehicle-v1",
    "baseURL": GALAXY_PUBLIC_BASE_URL,
    "portalURL": f"{GALAXY_PUBLIC_BASE_URL}/{slug}",
    "cookieName": GALAXY_COOKIE_NAME,
    "sessionToken": session_token,
    "appKey": session_token,
    "token": session_token,
    "telemetryPath": "/api/galaxy/session",
  }
  local_base_url = _local_base_url()
  if local_base_url:
    payload["localBaseURL"] = local_base_url
    payload["lanURL"] = local_base_url
    payload["localURL"] = local_base_url

  encoded = base64.urlsafe_b64encode(json.dumps(payload, separators=(",", ":")).encode("utf-8")).decode("ascii").rstrip("=")
  return f"galaxy-vehicle-v1:{encoded}"


class GalaxyQRDialog(NavWidget):
  def __init__(self, url: str):
    super().__init__()
    self._url = url
    self._qr_texture: rl.Texture | None = None
    self._title = UnifiedLabel("pair with galaxy", font_size=48, font_weight=FontWeight.BOLD, line_height=0.8)
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
    if self._qr_texture is None:
      rl.draw_text_ex(gui_app.font(FontWeight.BOLD), "QR Code Error", rl.Vector2(rect.x + 20, rect.y + rect.height / 2 - 15), 30, 0.0, rl.RED)
      return

    scale = rect.height / self._qr_texture.height
    pos = rl.Vector2(round(rect.x + 8), round(rect.y))
    rl.draw_texture_ex(self._qr_texture, pos, 0.0, scale, rl.WHITE)

    label_x = rect.x + 8 + rect.height + 24
    self._title.set_max_width(int(rect.width - label_x))
    self._title.set_position(label_x, rect.y + 16)
    self._title.render()

  def __del__(self):
    if self._qr_texture and self._qr_texture.id != 0:
      rl.unload_texture(self._qr_texture)


class GalaxyBigButton(BigButton):
  _SLUG_CHARS = string.ascii_letters + string.digits

  def __init__(self):
    super().__init__("galaxy", "", gui_app.texture("icons_mici/settings/galaxy.png", 64, 64))
    self._galaxy_dir = Path(Paths.comma_home()) / "starpilot" / "data" / "galaxy" if PC else Path("/data/galaxy")
    self._auth_path = self._galaxy_dir / "glxyauth"
    self._session_path = self._galaxy_dir / "glxysession"
    self._slug_path = self._galaxy_dir / "glxyslug"

  def _get_label_font_size(self):
    return 64

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

  def _get_session_token(self) -> str:
    try:
      return self._session_path.read_text(encoding="utf-8").strip()
    except Exception:
      return ""

  def _show_qr(self):
    slug = self._get_slug()
    token = self._get_session_token()
    pairing_value = _galaxy_pairing_payload_value(slug, token)
    if not pairing_value:
      gui_app.push_widget(BigDialog("", "Galaxy is not paired yet."))
      return
    gui_app.push_widget(GalaxyQRDialog(pairing_value))

  def _pair_with_password(self, password: str):
    clean_password = str(password or "").strip()
    if len(clean_password) < 6:
      gui_app.push_widget(BigDialog("", "Password must be at least 6 characters."))
      return

    try:
      self._galaxy_dir.mkdir(parents=True, exist_ok=True)
      self._auth_path.write_text(hashlib.sha256(clean_password.encode("utf-8")).hexdigest(), encoding="utf-8")
      self._session_path.write_text(secrets.token_hex(32), encoding="utf-8")
      slug = "".join(secrets.choice(self._SLUG_CHARS) for _ in range(16))
      self._slug_path.write_text(slug, encoding="utf-8")
    except Exception as e:
      cloudlog.warning(f"Galaxy pairing write failed: {e}")
      gui_app.push_widget(BigDialog("", "Failed to pair with Galaxy."))
      return

    self._show_qr()

  def _unpair(self):
    for path in (self._auth_path, self._session_path, self._slug_path):
      try:
        path.unlink(missing_ok=True)
      except TypeError:
        if path.exists():
          path.unlink()
      except Exception as e:
        cloudlog.warning(f"Galaxy unpair cleanup failed for {path}: {e}")

  def _handle_mouse_release(self, mouse_pos):
    super()._handle_mouse_release(mouse_pos)

    if self._is_paired():
      dialog_holder: dict[str, BigMultiOptionDialog] = {}

      def on_confirm():
        selection = dialog_holder["dialog"].get_selected_option()
        if selection == "show qr":
          self._show_qr()
        elif selection == "unpair":
          gui_app.push_widget(
            BigConfirmationDialog(
              "slide to\nunpair galaxy",
              gui_app.texture("icons_mici/settings/device/uninstall.png", 64, 64),
              self._unpair,
              red=True,
            )
          )

      dialog = BigMultiOptionDialog(options=["show qr", "unpair"], default="show qr", right_btn_callback=on_confirm)
      dialog_holder["dialog"] = dialog
      gui_app.push_widget(dialog)
      return

    gui_app.push_widget(BigInputDialog("set galaxy password...", default_text="", minimum_length=6, confirm_callback=self._pair_with_password))

  def _update_state(self):
    self.set_value("paired" if self._is_paired() else "pair")
