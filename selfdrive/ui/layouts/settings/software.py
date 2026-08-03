import dataclasses
import os
import subprocess
import threading
import time
import datetime
from pathlib import Path
from openpilot.common.time_helpers import system_time_valid
from openpilot.common.swaglog import cloudlog
from openpilot.selfdrive.ui.lib.starpilot_version import starpilot_display_description
from openpilot.selfdrive.ui.ui_state import ui_state
from openpilot.system.hardware import HARDWARE
from openpilot.system.ui.lib.application import gui_app
from openpilot.system.ui.lib.multilang import tr, trn
from openpilot.system.ui.widgets import Widget, DialogResult
from openpilot.system.ui.widgets.confirm_dialog import ConfirmDialog
from openpilot.system.ui.widgets.list_view import button_item, text_item, toggle_item, ListItem
from openpilot.system.ui.widgets.option_dialog import MultiOptionDialog
from openpilot.system.ui.widgets.scroller_tici import Scroller

# TODO: remove this. updater fails to respond on startup if time is not correct
UPDATED_TIMEOUT = 10  # seconds to wait for updated to respond

# Mapping updater internal states to translated display strings
STATE_TO_DISPLAY_TEXT = {
  "checking...": tr("checking..."),
  "downloading...": tr("downloading..."),
  "finalizing update...": tr("finalizing update..."),
}

# ── Git environment hardening (prevent prompts, hangs) ─
_GIT_ENV = os.environ.copy() | {
  "GIT_TERMINAL_PROMPT": "0",
  "GIT_ASKPASS": "/bin/false",
  "SSH_ASKPASS": "/bin/false",
  "GCM_INTERACTIVE": "Never",
}

class FastUpdateStage:
  IDLE = "idle"
  PREPARING = "preparing"
  FETCHING = "fetching"
  APPLYING = "applying"
  SUBMODULES = "submodules"
  REBOOTING = "rebooting"
  ERROR = "error"


@dataclasses.dataclass
class _FastUpdateState:
  stage: str = FastUpdateStage.IDLE
  status: str = ""
  error: str = ""


_FAST_UPDATE_GIT_TIMEOUT_S = 15
_FAST_UPDATE_FETCH_TIMEOUT_S = 120
_FAST_UPDATE_RESET_TIMEOUT_S = 120
_FAST_UPDATE_SUBMODULE_TIMEOUT_S = 300
_FAST_UPDATE_REBOOT_NOTICE_S = 6.0

_fast_update_lock = threading.Lock()
_fast_update_state = _FastUpdateState()
_fast_update_state_lock = threading.Lock()


def _set_fast_update_state(**kwargs):
  with _fast_update_state_lock:
    for k, v in kwargs.items():
      setattr(_fast_update_state, k, v)


def _get_fast_update_state() -> _FastUpdateState:
  with _fast_update_state_lock:
    return dataclasses.replace(_fast_update_state)


def time_ago(date: datetime.datetime | None) -> str:
  if not date:
    return tr("never")

  if not system_time_valid():
    return date.strftime("%a %b %d %Y")

  now = datetime.datetime.now(datetime.UTC)
  if date.tzinfo is None:
    date = date.replace(tzinfo=datetime.UTC)

  diff_seconds = int((now - date).total_seconds())
  if diff_seconds < 60:
    return tr("now")
  if diff_seconds < 3600:
    m = diff_seconds // 60
    return trn("{} minute ago", "{} minutes ago", m).format(m)
  if diff_seconds < 86400:
    h = diff_seconds // 3600
    return trn("{} hour ago", "{} hours ago", h).format(h)
  if diff_seconds < 604800:
    d = diff_seconds // 86400
    return trn("{} day ago", "{} days ago", d).format(d)
  return date.strftime("%a %b %d %Y")


class SoftwareLayout(Widget):
  def __init__(self):
    super().__init__()

    self._onroad_label = ListItem(lambda: tr("Updates are only downloaded while the car is off."))
    self._version_item = text_item(lambda: tr("Current Version"), starpilot_display_description(ui_state.ui_params.get("UpdaterCurrentDescription")))
    self._auto_updates_toggle = toggle_item(
      lambda: tr("Automatically Install Updates"),
      lambda: tr("Automatically install updates when parked with an active internet connection."),
      initial_state=ui_state.ui_params.get_bool("AutomaticUpdates"),
      callback=self._on_auto_updates_toggle,
    )
    self._download_btn = button_item(
      lambda: tr("Download"), lambda: tr("CHECK"),
      callback=self._on_download_update,
      long_press_callback=self._on_long_press_fast_update,
    )

    # Install button is initially hidden
    self._install_btn = button_item(lambda: tr("Install Update"), lambda: tr("INSTALL"), callback=self._on_install_update)
    self._install_btn.set_visible(False)

    # Track waiting-for-updater transition to avoid brief re-enable while still idle
    self._waiting_for_updater = False
    self._waiting_start_ts: float = 0.0

    # Branch switcher
    self._branch_btn = button_item(lambda: tr("Target Branch"), lambda: tr("SELECT"), callback=self._on_select_branch)
    self._branch_btn.set_visible(not ui_state.ui_params.get_bool("IsTestedBranch"))
    self._branch_btn.action_item.set_value(ui_state.ui_params.get("UpdaterTargetBranch") or "")
    self._branch_dialog: MultiOptionDialog | None = None

    self._scroller = Scroller(
      [
        self._onroad_label,
        self._version_item,
        self._auto_updates_toggle,
        self._download_btn,
        self._install_btn,
        self._branch_btn,
        button_item(lambda: tr("Uninstall"), lambda: tr("UNINSTALL"), callback=self._on_uninstall),
        button_item(lambda: tr("Error Log"), lambda: tr("VIEW"), callback=self._on_error_log),
      ],
      line_separator=True,
      spacing=0,
    )

  def show_event(self):
    self._scroller.show_event()

  def _render(self, rect):
    self._scroller.render(rect)

  def _update_state(self):
    # Show/hide onroad warning
    self._onroad_label.set_visible(ui_state.is_onroad())

    # Update current version and release notes
    current_desc = starpilot_display_description(ui_state.ui_params.get("UpdaterCurrentDescription"))
    current_release_notes = (ui_state.ui_params.get("UpdaterCurrentReleaseNotes") or b"").decode("utf-8", "replace")
    self._version_item.action_item.set_text(current_desc)
    self._version_item.set_description(current_release_notes)
    self._auto_updates_toggle.action_item.set_state(ui_state.ui_params.get_bool("AutomaticUpdates"))

    # Update download button visibility and state
    self._download_btn.set_visible(ui_state.is_offroad())

    # ── Fast update progress (in-memory status from worker thread) ─
    state = _get_fast_update_state()
    if state.stage == FastUpdateStage.REBOOTING:
      self._download_btn.action_item.set_enabled(False)
      self._download_btn.action_item.set_text(tr("REBOOTING"))
      self._download_btn.action_item.set_value(tr("Update applied, rebooting..."))
    elif state.stage == FastUpdateStage.ERROR:
      self._download_btn.action_item.set_enabled(True)
      self._download_btn.action_item.set_text(tr("RETRY"))
      self._download_btn.action_item.set_value(tr("Failed: {}").format(state.error))
    elif state.stage != FastUpdateStage.IDLE:
      self._download_btn.action_item.set_enabled(False)
      self._download_btn.action_item.set_text(tr("FAST UPDATE"))
      self._download_btn.action_item.set_value(state.status or tr("Starting..."))

    # ── Normal updater state (only when fast update NOT active) ───
    if state.stage == FastUpdateStage.IDLE:
      updater_state = ui_state.ui_params.get("UpdaterState") or "idle"
      failed_count = ui_state.ui_params.get("UpdateFailedCount") or 0
      fetch_available = ui_state.ui_params.get_bool("UpdaterFetchAvailable")
      update_available = ui_state.ui_params.get_bool("UpdateAvailable")

      if updater_state != "idle":
        self._waiting_for_updater = False
        self._download_btn.action_item.set_enabled(False)
        display_text = STATE_TO_DISPLAY_TEXT.get(updater_state, updater_state)
        self._download_btn.action_item.set_value(display_text)
      else:
        if failed_count > 0:
          self._download_btn.action_item.set_value(tr("failed to check for update"))
          self._download_btn.action_item.set_text(tr("CHECK"))
        elif fetch_available:
          self._download_btn.action_item.set_value(tr("update available"))
          self._download_btn.action_item.set_text(tr("DOWNLOAD"))
        else:
          last_update = ui_state.ui_params.get("LastUpdateTime")
          if last_update:
            formatted = time_ago(last_update)
            self._download_btn.action_item.set_value(tr("up to date, last checked {}").format(formatted))
          else:
            self._download_btn.action_item.set_value(tr("up to date, last checked never"))
          self._download_btn.action_item.set_text(tr("CHECK"))

        if self._waiting_for_updater and (time.monotonic() - self._waiting_start_ts > UPDATED_TIMEOUT):
          self._waiting_for_updater = False

        self._download_btn.action_item.set_enabled(not self._waiting_for_updater)
    else:
      update_available = False

    # Update target branch button value
    current_branch = ui_state.ui_params.get("UpdaterTargetBranch") or ""
    self._branch_btn.action_item.set_value(current_branch)

    # Update install button
    self._install_btn.set_visible(ui_state.is_offroad() and update_available and state.stage == FastUpdateStage.IDLE)
    if update_available and state.stage == FastUpdateStage.IDLE:
      new_desc = starpilot_display_description(ui_state.ui_params.get("UpdaterNewDescription"))
      new_release_notes = (ui_state.ui_params.get("UpdaterNewReleaseNotes") or b"").decode("utf-8", "replace")
      self._install_btn.action_item.set_text(tr("INSTALL"))
      self._install_btn.action_item.set_value(new_desc)
      self._install_btn.set_description(new_release_notes)
      self._install_btn.action_item.set_enabled(True)
    else:
      self._install_btn.set_visible(False)

  def _on_download_update(self):
    state = _get_fast_update_state()
    if state.stage == FastUpdateStage.ERROR:
      _set_fast_update_state(stage=FastUpdateStage.IDLE, status="", error="")
      return
    if state.stage != FastUpdateStage.IDLE:
      return
    self._download_btn.action_item.set_enabled(False)
    if self._download_btn.action_item.text == tr("CHECK"):
      self._waiting_for_updater = True
      self._waiting_start_ts = time.monotonic()
      os.system("pkill -SIGUSR1 -f system.updated.updated")
    else:
      self._waiting_for_updater = True
      self._waiting_start_ts = time.monotonic()
      ui_state.params_memory.put_bool("ManualUpdateInitiated", True)
      os.system("pkill -SIGHUP -f system.updated.updated")

  def _on_long_press_fast_update(self):
    if _get_fast_update_state().stage != FastUpdateStage.IDLE:
      return
    def on_confirm(result):
      if result == DialogResult.CONFIRM:
        self._execute_fast_update()
    gui_app.push_widget(ConfirmDialog(
      tr("Fast update will replace the current installation without backup and reboot the device. Continue?"),
      tr("Fast Update"), callback=on_confirm,
    ))

  def _execute_fast_update(self):
    if ui_state.is_onroad():
      self._download_btn.action_item.set_value(tr("Cannot update while driving"))
      return
    if not _fast_update_lock.acquire(blocking=False):
      return
    _set_fast_update_state(stage=FastUpdateStage.PREPARING, status=tr("Starting fast update..."), error="")
    self._download_btn.action_item.set_enabled(False)
    self._download_btn.action_item.set_text(tr("FAST UPDATE"))
    self._download_btn.action_item.set_value(tr("Starting fast update..."))
    subprocess.run(["pkill", "-f", "system.updated.updated"], check=False)

    def _run_worker():
      repo_path = str(Path(__file__).resolve().parents[4])
      try:
        result = subprocess.run(
          ["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=repo_path,
          capture_output=True, text=True, timeout=_FAST_UPDATE_GIT_TIMEOUT_S, env=_GIT_ENV)
        if result.returncode != 0:
          raise RuntimeError(result.stderr.strip() or "failed to resolve HEAD branch")
        branch = result.stdout.strip()

        result = subprocess.run(
          ["git", "rev-parse", "HEAD"], cwd=repo_path,
          capture_output=True, text=True, timeout=_FAST_UPDATE_GIT_TIMEOUT_S, env=_GIT_ENV)
        if result.returncode != 0:
          raise RuntimeError(result.stderr.strip() or "failed to resolve HEAD commit")

        _set_fast_update_state(stage=FastUpdateStage.FETCHING, status=tr("Fetching latest commit..."))
        result = subprocess.run(
          ["git", "-c", "gc.auto=0", "-c", "maintenance.auto=false", "fetch",
           "--progress", "--depth=1", "--no-recurse-submodules", "origin", branch],
          cwd=repo_path, capture_output=True, text=True, timeout=_FAST_UPDATE_FETCH_TIMEOUT_S, env=_GIT_ENV)
        if result.returncode != 0:
          raise RuntimeError(result.stderr.strip() or "fetch failed")

        _set_fast_update_state(stage=FastUpdateStage.APPLYING, status=tr("Applying update..."))
        result = subprocess.run(["git", "reset", "--hard", "FETCH_HEAD"],
                                cwd=repo_path, capture_output=True, text=True, timeout=_FAST_UPDATE_RESET_TIMEOUT_S, env=_GIT_ENV)
        if result.returncode != 0:
          raise RuntimeError(result.stderr.strip() or "reset failed")

        gitmodules = Path(repo_path) / ".gitmodules"
        if gitmodules.is_file():
          _set_fast_update_state(stage=FastUpdateStage.SUBMODULES, status=tr("Updating submodules..."))
          result = subprocess.run(
            ["git", "submodule", "update", "--init", "--recursive", "--depth=1", "--progress"],
            cwd=repo_path, capture_output=True, text=True, timeout=_FAST_UPDATE_SUBMODULE_TIMEOUT_S, env=_GIT_ENV)
          if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or "submodule update failed")

        _set_fast_update_state(stage=FastUpdateStage.REBOOTING, status=tr("Update applied, rebooting..."))
        time.sleep(_FAST_UPDATE_REBOOT_NOTICE_S)
        HARDWARE.reboot()

      except Exception as e:
        _set_fast_update_state(stage=FastUpdateStage.ERROR, error=str(e)[:1000], status="")
        cloudlog.exception("Fast update failed")
      finally:
        _fast_update_lock.release()

    threading.Thread(target=_run_worker, daemon=True).start()

  def _on_auto_updates_toggle(self, enabled: bool):
    ui_state.ui_params.put_bool("AutomaticUpdates", enabled)

  def _on_uninstall(self):
    def handle_step1(result):
      if result == DialogResult.CONFIRM:

        def handle_step2(result2):
          if result2 == DialogResult.CONFIRM:

            def handle_step3(result3):
              if result3 == DialogResult.CONFIRM:
                ui_state.ui_params.clear_all()
              ui_state.ui_params.put_bool("DoUninstall", True)

            dialog = ConfirmDialog(tr("This is a complete factory reset and cannot be undone. Are you absolutely sure?"), tr("Reset"), callback=handle_step3)
            gui_app.push_widget(dialog)
          else:
            ui_state.ui_params.put_bool("DoUninstall", True)

        dialog = ConfirmDialog(
          tr("Do you want to perform a full factory reset? All saved assets and settings will be permanently deleted!"), tr("Factory Reset"), tr("Skip"), callback=handle_step2
        )
        gui_app.push_widget(dialog)

    dialog = ConfirmDialog(tr("Are you sure you want to uninstall?"), tr("Uninstall"), callback=handle_step1)
    gui_app.push_widget(dialog)

  def _on_error_log(self):
    try:
      txt = Path("/data/error_logs/error.txt").read_text(encoding='utf-8', errors='replace')
    except Exception:
      txt = tr("No error log found.")
    gui_app.push_widget(ConfirmDialog(txt, tr("OK"), rich=True))

  def _on_install_update(self):
    # Trigger reboot to install update
    self._install_btn.action_item.set_enabled(False)
    ui_state.ui_params.put_bool("DoReboot", True)

  def _on_select_branch(self):
    # Get available branches and order
    current_git_branch = ui_state.ui_params.get("GitBranch") or ""
    branches_str = ui_state.ui_params.get("UpdaterAvailableBranches") or ""
    branches = [b for b in branches_str.split(",") if b]

    for b in [current_git_branch, "devel-staging", "devel", "nightly", "nightly-dev", "master"]:
      if b in branches:
        branches.remove(b)
        branches.insert(0, b)

    current_target = ui_state.ui_params.get("UpdaterTargetBranch") or ""

    def handle_selection(result):
      # Confirmed selection
      if result == DialogResult.CONFIRM and self._branch_dialog is not None and self._branch_dialog.selection:
        selection = self._branch_dialog.selection
        ui_state.ui_params.put("UpdaterTargetBranch", selection)
        self._branch_btn.action_item.set_value(selection)
        os.system("pkill -SIGUSR1 -f system.updated.updated")
      self._branch_dialog = None

    self._branch_dialog = MultiOptionDialog(tr("Select a branch"), branches, current_target, callback=handle_selection)
    gui_app.push_widget(self._branch_dialog)
