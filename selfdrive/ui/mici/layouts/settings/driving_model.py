from __future__ import annotations

import re
import threading
import time
from dataclasses import dataclass
from collections.abc import Callable
from pathlib import Path

from openpilot.common.file_chunker import get_chunk_name, get_manifest_path
from openpilot.common.params import Params
from openpilot.starpilot.assets.model_manager import external_gpu_available, model_uses_external_gpu, set_model_profile
from openpilot.selfdrive.ui.mici.widgets.button import BigButton
from openpilot.selfdrive.ui.mici.widgets.dialog import BigDialog, BigDialogBase, BigMultiOptionDialog
from openpilot.selfdrive.ui.ui_state import ui_state
from openpilot.system.hardware import PC
from openpilot.system.hardware.hw import Paths
from openpilot.system.ui.lib.application import gui_app, FontWeight
from openpilot.system.ui.widgets import Widget
from openpilot.system.ui.widgets.label import gui_label
import pyray as rl

CANCEL_DOWNLOAD_PARAM = "CancelModelDownload"
DOWNLOAD_PROGRESS_PARAM = "ModelDownloadProgress"
MODELS_PATH = Path(Paths.comma_home()) / "starpilot" / "data" / "models" if PC else Path("/data/models")
MANIFEST_STALE_SECONDS = 60 * 60
_PROGRESS_HOLD_SECONDS = 2.5
_DOWNLOAD_DIALOG_CLOSE_SECONDS = 1.0
_TERMINAL_PROGRESS_PATTERNS = (
  "downloaded",
  "cancelled",
  "failed",
  "offline",
  "verification failed",
  "server error",
  "download invalid",
)
_SORT_MODE_PARAM = "ModelSortMode"
_SORT_MODE_ALPHABETICAL = "alphabetical"
_SORT_MODE_DATE_NEWEST = "date"
_SORT_MODE_DATE_OLDEST = "date_oldest"
_SORT_MODE_FAVORITES = "favorites"
_SORT_MODES = (
  _SORT_MODE_ALPHABETICAL,
  _SORT_MODE_DATE_NEWEST,
  _SORT_MODE_DATE_OLDEST,
  _SORT_MODE_FAVORITES,
)
_SORT_MODE_LABELS = {
  _SORT_MODE_ALPHABETICAL: "alphabetical",
  _SORT_MODE_DATE_NEWEST: "newest",
  _SORT_MODE_DATE_OLDEST: "oldest",
  _SORT_MODE_FAVORITES: "favorites",
}
_LABEL_TO_SORT_MODE = {label: mode for mode, label in _SORT_MODE_LABELS.items()}


@dataclass
class ModelEntry:
  key: str
  name: str
  series: str
  version: str
  released: str
  community_favorite: bool
  requires_external_gpu: bool = False


def _clean_model_name(name: str) -> str:
  cleaned = re.sub(r"[🗺️👀📡]", "", str(name or "")).replace("(Default)", "")
  return cleaned.strip()


def _split_param(param_value: str | None) -> list[str]:
  return [item.strip() for item in (param_value or "").split(",") if item.strip()]


class DownloadProgressDialog(BigDialogBase):
  def __init__(self, params_memory: Params, is_downloading: Callable[[], bool], cancel_callback: Callable[[], None],
               is_terminal_progress: Callable[[str], bool], on_close: Callable[[], None] | None = None):
    super().__init__()
    self._params_memory = params_memory
    self._is_downloading = is_downloading
    self._cancel_callback = cancel_callback
    self._is_terminal_progress = is_terminal_progress
    self._on_close = on_close

    self._progress = 0.0
    self._status = "Downloading..."
    self._terminal_progress_since = 0.0
    self._downloading = False
    self._dismissed = False

    self._cancel_btn = DownloadActionButton("cancel download")
    self._cancel_btn.set_click_callback(self._cancel_callback)

  def show_event(self):
    super().show_event()
    self._cancel_btn.show_event()

  def hide_event(self):
    super().hide_event()
    self._cancel_btn.hide_event()

  @staticmethod
  def _parse_progress(progress: str) -> float | None:
    match = re.search(r"(\d{1,3})\s*%", progress)
    if match:
      return max(0.0, min(float(match.group(1)) / 100.0, 1.0))
    lowered = progress.lower()
    if "verifying" in lowered:
      return 1.0
    if "downloaded" in lowered:
      return 1.0
    return None

  def _update_state(self):
    super()._update_state()

    progress = self._params_memory.get(DOWNLOAD_PROGRESS_PARAM, encoding="utf-8") or ""
    is_downloading = self._is_downloading()
    self._downloading = is_downloading
    parsed_progress = self._parse_progress(progress)

    if parsed_progress is not None:
      self._progress = parsed_progress

    if progress:
      self._status = progress
    elif is_downloading:
      self._status = "Downloading..."
    else:
      self._status = "Downloaded!"
      self._progress = max(self._progress, 1.0)

    self._cancel_btn.set_enabled(is_downloading)

    terminal = (not is_downloading) and (
      not progress or
      self._is_terminal_progress(progress) or
      (parsed_progress is not None and parsed_progress >= 1.0)
    )
    if terminal:
      if self._terminal_progress_since == 0.0:
        self._terminal_progress_since = time.monotonic()
      elif time.monotonic() - self._terminal_progress_since >= _DOWNLOAD_DIALOG_CLOSE_SECONDS:
        if not self._dismissed:
          self._dismissed = True
          self.dismiss(self._on_close)
    else:
      self._terminal_progress_since = 0.0

  def _render(self, _):
    super()._render(_)

    width = int(self._rect.width)
    height = int(self._rect.height)

    rl.draw_rectangle(0, 0, width, height, rl.Color(0, 0, 0, 170))

    panel_margin_x = 40
    panel_margin_y = 28
    panel_width = int(min(width - panel_margin_x * 2, 980))
    panel_height = int(min(height - panel_margin_y * 2, 300))
    panel_x = int((width - panel_width) / 2)
    panel_y = int((height - panel_height) / 2)
    panel_rect = rl.Rectangle(panel_x, panel_y, panel_width, panel_height)
    rl.draw_rectangle_rounded(panel_rect, 0.08, 24, rl.Color(16, 16, 16, 245))
    rl.draw_rectangle_rounded_lines_ex(panel_rect, 0.08, 24, 2, rl.Color(255, 255, 255, 32))

    cancel_w = int(self._cancel_btn.rect.width)
    cancel_h = int(self._cancel_btn.rect.height)
    cancel_x = int(panel_x + (panel_width - cancel_w) / 2)

    top_padding = 22
    side_padding = 36
    gap = 16
    bar_h = 34
    status_h = 44
    bottom_padding = 24

    bar_y = int(panel_y + top_padding)
    status_y = int(bar_y + bar_h + gap)
    cancel_y = int(status_y + status_h + gap)
    max_cancel_y = int(panel_y + panel_height - cancel_h - bottom_padding)
    if cancel_y > max_cancel_y:
      cancel_y = max_cancel_y

    status_rect = rl.Rectangle(panel_x + side_padding, status_y, panel_width - side_padding * 2, status_h)
    gui_label(
      status_rect,
      self._status,
      32,
      font_weight=FontWeight.MEDIUM,
      alignment=rl.GuiTextAlignment.TEXT_ALIGN_CENTER,
    )

    bar_width = int(min(panel_width - side_padding * 2, 760))
    bar_x = int(panel_x + (panel_width - bar_width) / 2)
    self._cancel_btn.render(rl.Rectangle(cancel_x, cancel_y, cancel_w, cancel_h))

    # Draw the bar last so it cannot get hidden by other dialog graphics.
    bar_rect = rl.Rectangle(bar_x, bar_y, bar_width, bar_h)
    rl.draw_rectangle_rounded(bar_rect, 0.35, 16, rl.Color(34, 34, 34, 255))
    rl.draw_rectangle_rounded_lines_ex(bar_rect, 0.35, 16, 2, rl.Color(255, 255, 255, 95))

    fill_padding = 4
    fill_h = bar_h - fill_padding * 2
    bar_inner_w = max(0, bar_width - fill_padding * 2)
    clamped_progress = min(max(self._progress, 0.0), 1.0)

    if self._downloading and clamped_progress <= 0.001:
      # If backend reports status text but no percentage yet, show animated activity.
      segment_w = max(70.0, bar_inner_w * 0.22)
      max_offset = max(1.0, bar_inner_w - segment_w)
      phase = (time.monotonic() * 1.35) % 1.0
      fill_x = bar_x + fill_padding + (phase * max_offset)
      rl.draw_rectangle_rounded(
        rl.Rectangle(fill_x, bar_y + fill_padding, segment_w, fill_h),
        0.35,
        16,
        rl.Color(70, 91, 234, 255),
      )
    else:
      fill_width = max(0.0, bar_inner_w * clamped_progress)
      if fill_width > 0:
        rl.draw_rectangle_rounded(
          rl.Rectangle(bar_x + fill_padding, bar_y + fill_padding, fill_width, fill_h),
          0.35,
          16,
          rl.Color(70, 91, 234, 255),
        )

    if clamped_progress > 0.0:
      gui_label(
        bar_rect,
        f"{int(clamped_progress * 100)}%",
        24,
        color=rl.Color(255, 255, 255, 210),
        font_weight=FontWeight.BOLD,
        alignment=rl.GuiTextAlignment.TEXT_ALIGN_CENTER,
      )


class DownloadActionButton(Widget):
  def __init__(self, label: str):
    super().__init__()
    self._label = label
    self.set_rect(rl.Rectangle(0, 0, 380, 86))

  def set_label(self, label: str):
    self._label = label

  def _render(self, _):
    if not self.enabled:
      bg = rl.Color(48, 48, 48, 255)
      border = rl.Color(255, 255, 255, 45)
      label_alpha = 145
    elif self.is_pressed:
      bg = rl.Color(72, 86, 170, 255)
      border = rl.Color(255, 255, 255, 85)
      label_alpha = 235
    else:
      bg = rl.Color(58, 70, 146, 255)
      border = rl.Color(255, 255, 255, 70)
      label_alpha = 225

    rl.draw_rectangle_rounded(self._rect, 0.35, 14, bg)
    rl.draw_rectangle_rounded_lines_ex(self._rect, 0.35, 14, 2, border)

    gui_label(
      self._rect,
      self._label,
      34,
      color=rl.Color(255, 255, 255, label_alpha),
      font_weight=FontWeight.MEDIUM,
      alignment=rl.GuiTextAlignment.TEXT_ALIGN_CENTER,
    )


class DrivingModelBigButton(BigButton):
  def __init__(self):
    super().__init__("driving model", "", gui_app.texture("icons_mici/settings/device/lkas.png", 72, 56))
    self._params = Params()
    self._params_memory = Params(memory=True)
    self._model_manager = None

    self._worker_thread: threading.Thread | None = None
    self._active_job = ""
    self._manifest_last_refresh_mono = 0.0
    self._terminal_progress_since = 0.0
    self._sub_label.set_font_size(32)
    self._sub_label._scroll = True
    self._sub_label._elide = False
    self._sub_label._wrap_text = False

    self.set_click_callback(self._open_manager_menu)
    self.refresh()

  def _get_model_manager(self):
    if self._model_manager is None:
      from openpilot.starpilot.assets.model_manager import ModelManager

      self._model_manager = ModelManager(self._params, self._params_memory)
    return self._model_manager

  def show_event(self):
    super().show_event()
    self._sub_label.reset_scroll()
    self.refresh()
    # Always fetch manifest once when this settings pane opens.
    self._maybe_refresh_manifest(force=(self._manifest_last_refresh_mono == 0.0))

  def refresh(self):
    self._update_button_value()

  def set_value(self, value: str):
    super().set_value(value)
    self._sub_label.reset_scroll()

  def _get_label_font_size(self):
    return 42

  def _width_hint(self) -> int:
    icon_width = self._txt_icon.width + 16 if self._txt_icon else 0
    return int(self._rect.width - self.LABEL_HORIZONTAL_PADDING * 2 - icon_width)

  def _show_option_dialog(self, title: str, options: list[str], current: str | None, on_selected: Callable[[str], None],
                          back_callback: Callable[[], None] | None = None):
    dialog_holder: dict[str, BigMultiOptionDialog] = {}

    def on_confirm():
      on_selected(dialog_holder["dialog"].get_selected_option())

    default_option = current if current in options else None
    dialog = BigMultiOptionDialog(options=options, default=default_option, right_btn_callback=on_confirm)
    if back_callback is not None:
      dialog.set_back_callback(back_callback)
    dialog_holder["dialog"] = dialog
    gui_app.push_widget(dialog)

  def _update_state(self):
    super()._update_state()
    self._process_terminal_progress()
    self._update_button_value()

  def _open_manager_menu(self):
    options = [
      "set sort mode",
      "switch model",
      "download model",
      "download all missing",
      "refresh manifest",
    ]

    if not options:
      return

    def on_selected(value: str):
      if value == "set sort mode":
        self._open_sort_mode_dialog()
      elif value == "switch model":
        self._open_switch_dialog()
      elif value == "download model":
        self._open_download_dialog()
      elif value == "download all missing":
        self._download_all_missing()
      elif value == "refresh manifest":
        self._maybe_refresh_manifest(force=True)

    self._show_option_dialog("driving model", options, None, on_selected)

  def _open_switch_dialog(self):
    self._maybe_refresh_manifest(force=False)
    entries = self._load_model_entries()
    if not entries:
      message = "Refreshing model list..." if self._active_job == "refresh" else "Refresh manifest and try again."
      self._show_message("Model list unavailable", message, return_to_manager=True)
      return

    installed = [entry for entry in entries if self._is_model_installed(entry.key, entry.version)]
    if not installed:
      self._show_message("No downloaded models", "Download a model first.", return_to_manager=True)
      return

    current_key = self._get_current_model_key()
    self._show_model_dialog("Select Driving Model", installed, current_key, self._switch_model,
                            back_callback=self._open_manager_menu)

  def _open_download_dialog(self):
    if ui_state.started:
      self._show_message("Downloads blocked while driving", "Try again offroad.", return_to_manager=True)
      return

    self._maybe_refresh_manifest(force=False)
    entries = self._load_model_entries()
    if not entries:
      message = "Refreshing model list..." if self._active_job == "refresh" else "Refresh manifest and try again."
      self._show_message("Model list unavailable", message, return_to_manager=True)
      return

    missing = [entry for entry in entries if not self._is_model_installed(entry.key, entry.version)]
    if not missing:
      self._show_message("All models downloaded", "No additional models are available.", return_to_manager=True)
      return

    self._show_model_dialog("Download Driving Model", missing, "", self._start_model_download,
                            back_callback=self._open_manager_menu)

  def _download_all_missing(self):
    if ui_state.started:
      self._show_message("Downloads blocked while driving", "Try again offroad.", return_to_manager=True)
      return

    self._maybe_refresh_manifest(force=False)
    entries = self._load_model_entries()
    if not entries:
      self._show_message("Model list unavailable", "Refresh manifest and try again.", return_to_manager=True)
      return

    missing_exists = any(not self._is_model_installed(entry.key, entry.version) for entry in entries)
    if not missing_exists:
      self._show_message("All models downloaded", "No additional models are available.", return_to_manager=True)
      return

    if not self._start_worker("download_all", self._run_download_all):
      self._show_message("Model manager busy", "Please wait for the current task.", return_to_manager=True)
      return

    self._show_download_progress_dialog()

  def _cancel_download(self):
    if not self._is_download_job_running():
      return
    self._params_memory.put_bool(CANCEL_DOWNLOAD_PARAM, True)

  def _open_sort_mode_dialog(self):
    options = [_SORT_MODE_LABELS[mode] for mode in _SORT_MODES]
    current_mode = self._get_sort_mode()

    def on_selected(selected_label: str):
      selected_mode = _LABEL_TO_SORT_MODE.get(selected_label, _SORT_MODE_ALPHABETICAL)
      self._params.put(_SORT_MODE_PARAM, selected_mode)
      self._open_manager_menu()

    self._show_option_dialog("sort mode", options, _SORT_MODE_LABELS[current_mode], on_selected,
                             back_callback=self._open_manager_menu)

  def _get_sort_mode(self) -> str:
    mode = (self._params.get(_SORT_MODE_PARAM, encoding="utf-8") or "").strip()
    return mode if mode in _SORT_MODES else _SORT_MODE_ALPHABETICAL

  def _show_model_dialog(self, title: str, entries: list[ModelEntry], current_key: str,
                         on_selected: Callable[[str], None], back_callback: Callable[[], None] | None = None):
    options, option_to_key, key_to_option = self._build_model_options(entries)
    if not options:
      self._show_message("No models available", "Refresh manifest and try again.", return_to_manager=True)
      return

    default_option = key_to_option.get(current_key, options[0])

    def on_dialog_selected(selected_option: str):
      model_key = option_to_key.get(selected_option)
      if model_key:
        on_selected(model_key)

    self._show_option_dialog(title, options, default_option, on_dialog_selected, back_callback=back_callback)

  def _build_model_options(self, entries: list[ModelEntry]) -> tuple[list[str], dict[str, str], dict[str, str]]:
    # Ensure display names are unique before applying status text (date/favorite).
    display_names: dict[str, str] = {}
    for entry in entries:
      name = entry.name
      if name in display_names and display_names[name] != entry.key:
        name = f"{entry.name} [{entry.series}]"
      if name in display_names and display_names[name] != entry.key:
        name = f"{entry.name} [{entry.key}]"
      display_names[name] = entry.key

    key_to_display = {key: name for name, key in display_names.items()}
    sorted_entries = self._sort_entries(entries)

    options: list[str] = []
    option_to_key: dict[str, str] = {}
    key_to_option: dict[str, str] = {}

    for entry in sorted_entries:
      display_name = key_to_display.get(entry.key, entry.name)
      favorite_prefix = "♥ " if entry.community_favorite else ""
      option = f"{favorite_prefix}{display_name}"
      if option in option_to_key:
        option = f"{option} [{entry.key}]"

      options.append(option)
      option_to_key[option] = entry.key
      key_to_option[entry.key] = option

    return options, option_to_key, key_to_option

  def _sort_entries(self, entries: list[ModelEntry]) -> list[ModelEntry]:
    sort_mode = self._get_sort_mode()
    entry_list = sorted(entries, key=lambda entry: (entry.series.lower(), entry.name.lower()))

    def normalized_release(entry: ModelEntry) -> str:
      return entry.released if entry.released else "0000-00-00"

    if sort_mode == _SORT_MODE_DATE_NEWEST:
      return sorted(entry_list, key=normalized_release, reverse=True)
    if sort_mode == _SORT_MODE_DATE_OLDEST:
      return sorted(entry_list, key=normalized_release)
    if sort_mode == _SORT_MODE_FAVORITES:
      return sorted(entry_list, key=lambda entry: (
        0 if entry.community_favorite else 1,
        entry.series.lower(),
        entry.name.lower(),
      ))
    return entry_list

  def _start_model_download(self, model_key: str):
    entry = next((item for item in self._load_model_entries() if item.key == model_key), None)
    if entry is not None and entry.requires_external_gpu and not external_gpu_available():
      self._show_message("GPU required", "This model requires a detected external GPU.", return_to_manager=True)
      return
    if not self._start_worker("download", self._run_download_one, model_key):
      self._show_message("Model manager busy", "Please wait for the current task.", return_to_manager=True)
      return

    self._show_download_progress_dialog()

  def _run_download_one(self, model_key: str):
    self._params_memory.put_bool(CANCEL_DOWNLOAD_PARAM, False)
    self._get_model_manager().download_model(model_key)

    entries = {entry.key: entry for entry in self._load_model_entries()}
    entry = entries.get(model_key)
    model_version = entry.version if entry else ""
    if not self._is_model_installed(model_key, model_version):
      self._params_memory.put(DOWNLOAD_PROGRESS_PARAM, "Verification failed...")

  def _run_download_all(self):
    self._params_memory.put_bool(CANCEL_DOWNLOAD_PARAM, False)
    self._get_model_manager().download_all_models()

  def _run_manifest_refresh(self):
    self._get_model_manager().update_models()

  def _switch_model(self, model_key: str):
    entries = {entry.key: entry for entry in self._load_model_entries()}
    entry = entries.get(model_key)

    if entry is None:
      self._show_message("Model unavailable", "Refresh manifest and try again.", return_to_manager=True)
      return

    if entry.requires_external_gpu and not external_gpu_available():
      self._show_message("GPU required", "This model requires a detected external GPU.", return_to_manager=True)
      return

    if not self._is_model_installed(entry.key, entry.version):
      self._show_message("Model not downloaded", "Download this model first.", return_to_manager=True)
      return

    self._params.put("Model", entry.key)
    self._params.put("DrivingModel", entry.key)
    self._params.put("DrivingModelName", entry.name)

    version = entry.version.strip()
    if version:
      self._params.put("ModelVersion", version)
      self._params.put("DrivingModelVersion", version)
    set_model_profile(
      self._params,
      "big" if entry.requires_external_gpu else "small",
      entry.key,
      entry.name,
      version,
    )

    if ui_state.started:
      self._params.put_bool("OnroadCycleRequested", True)
      self._show_message("Model switched", "Drive-cycle requested for immediate apply.", return_to_manager=True)

    self.refresh()

  def _start_worker(self, job: str, target, *args) -> bool:
    if self._worker_thread is not None and self._worker_thread.is_alive():
      return False

    self._active_job = job

    def run_job():
      try:
        target(*args)
      finally:
        if job == "refresh":
          self._manifest_last_refresh_mono = time.monotonic()
        self._active_job = ""

    self._worker_thread = threading.Thread(target=run_job, daemon=True)
    self._worker_thread.start()
    return True

  def _maybe_refresh_manifest(self, force: bool):
    if ui_state.started:
      return

    now = time.monotonic()
    has_entries = bool(self._load_model_entries())
    stale = (now - self._manifest_last_refresh_mono) > MANIFEST_STALE_SECONDS

    if force or not has_entries or stale:
      self._start_worker("refresh", self._run_manifest_refresh)

  def _is_download_job_running(self) -> bool:
    return self._active_job in {"download", "download_all"}

  def _process_terminal_progress(self):
    if self._is_download_job_running():
      self._terminal_progress_since = 0.0
      return

    progress = self._params_memory.get(DOWNLOAD_PROGRESS_PARAM, encoding="utf-8") or ""
    if not progress:
      self._terminal_progress_since = 0.0
      return

    if not self._is_terminal_progress(progress):
      return

    if self._terminal_progress_since == 0.0:
      self._terminal_progress_since = time.monotonic()
      return

    if time.monotonic() - self._terminal_progress_since >= _PROGRESS_HOLD_SECONDS:
      self._params_memory.remove(CANCEL_DOWNLOAD_PARAM)
      self._params_memory.remove(DOWNLOAD_PROGRESS_PARAM)
      self._terminal_progress_since = 0.0

  def _update_button_value(self):
    if self._active_job == "refresh":
      value = "refreshing"
    elif self._is_download_job_running():
      value = self._params_memory.get(DOWNLOAD_PROGRESS_PARAM, encoding="utf-8") or "downloading..."
    else:
      progress = self._params_memory.get(DOWNLOAD_PROGRESS_PARAM, encoding="utf-8") or ""
      if progress and self._is_terminal_progress(progress):
        value = progress
      else:
        value = self._get_current_model_name()

    if value != self.get_value():
      self.set_value(value)

  def _load_model_entries(self) -> list[ModelEntry]:
    available_models = _split_param(self._params.get("AvailableModels", encoding="utf-8"))
    model_names = _split_param(self._params.get("AvailableModelNames", encoding="utf-8"))
    model_series = [item.strip() for item in (self._params.get("AvailableModelSeries", encoding="utf-8") or "").split(",")]
    model_versions = [item.strip() for item in (self._params.get("ModelVersions", encoding="utf-8") or "").split(",")]
    released_dates = [item.strip() for item in (self._params.get("ModelReleasedDates", encoding="utf-8") or "").split(",")]
    community_favs = set(_split_param(self._params.get("CommunityFavorites", encoding="utf-8")))

    size = min(len(available_models), len(model_names))
    entries: list[ModelEntry] = []

    for i in range(size):
      key = available_models[i].strip()
      name = _clean_model_name(model_names[i])
      if not key or not name:
        continue

      series = model_series[i].strip() if i < len(model_series) and model_series[i].strip() else "Custom Series"
      version = model_versions[i].strip() if i < len(model_versions) else ""
      released = released_dates[i].strip() if i < len(released_dates) else ""

      entries.append(ModelEntry(
        key=key,
        name=name,
        series=series,
        version=version,
        released=released,
        community_favorite=(key in community_favs),
        requires_external_gpu=model_uses_external_gpu(key),
      ))

    return entries

  def _get_current_model_key(self) -> str:
    model_key = self._params.get("Model", encoding="utf-8") or self._params.get("DrivingModel", encoding="utf-8") or ""
    if model_key:
      return model_key

    default_key = self._params.get_default_value("Model") or self._params.get_default_value("DrivingModel")
    if isinstance(default_key, bytes):
      return default_key.decode("utf-8", errors="ignore").strip()
    return str(default_key or "").strip()

  def _get_current_model_name(self) -> str:
    current_name = _clean_model_name(self._params.get("DrivingModelName", encoding="utf-8") or "")
    if current_name:
      return current_name

    current_key = self._get_current_model_key()
    for entry in self._load_model_entries():
      if entry.key == current_key:
        return entry.name

    return "default"

  def _is_model_installed(self, key: str, version: str) -> bool:
    if not key:
      return False

    if self._is_builtin_default_model(key):
      return True

    required_files = self._required_files_for_version(key, version)
    if not required_files:
      return False

    return all(self._artifact_installed(filename) for filename in required_files)

  @staticmethod
  def _artifact_installed(filename: str) -> bool:
    if (MODELS_PATH / filename).is_file():
      return True

    manifest = get_manifest_path(filename)
    if not (MODELS_PATH / manifest).is_file():
      return False

    try:
      num_chunks = int((MODELS_PATH / manifest).read_text().strip())
    except Exception:
      return False

    return all((MODELS_PATH / get_chunk_name(filename, idx, num_chunks)).is_file() for idx in range(num_chunks))

  def _is_builtin_default_model(self, key: str) -> bool:
    default_key = self._params.get_default_value("DrivingModel") or self._params.get_default_value("Model")
    if isinstance(default_key, bytes):
      default_key = default_key.decode("utf-8", errors="ignore")
    default_key = str(default_key or "").strip()
    if not default_key:
      default_key = "rdf43"

    # Keep the built-in model selectable even when the manifest omits it.
    if key == default_key:
      return True
    if default_key == "rdf43" and key == "rdf":
      return True
    if default_key.endswith("2") and key == default_key[:-1]:
      return True
    if not default_key.endswith("2") and key == f"{default_key}2":
      return True
    return False

  def _required_files_for_version(self, key: str, version: str) -> list[str]:
    del version
    return [f"{key}_driving_tinygrad.pkl"]

  @staticmethod
  def _is_terminal_progress(progress: str) -> bool:
    lower = progress.lower()
    return any(pattern in lower for pattern in _TERMINAL_PROGRESS_PATTERNS)

  def _show_download_progress_dialog(self):
    dialog = DownloadProgressDialog(
      params_memory=self._params_memory,
      is_downloading=self._is_download_job_running,
      cancel_callback=self._cancel_download,
      is_terminal_progress=self._is_terminal_progress,
      on_close=self._open_manager_menu,
    )
    gui_app.push_widget(dialog)

  def _show_message(self, title: str, description: str, return_to_manager: bool = False):
    dialog = BigDialog(title, description)
    if return_to_manager:
      dialog.set_back_callback(self._open_manager_menu)
    gui_app.push_widget(dialog)
