from __future__ import annotations
import os
import shutil
import threading
import subprocess
from datetime import datetime
from pathlib import Path

from openpilot.system.ui.lib.application import gui_app
from openpilot.system.ui.lib.multilang import tr, tr_noop
from openpilot.system.ui.widgets import DialogResult
from openpilot.system.ui.widgets.confirm_dialog import ConfirmDialog, alert_dialog
from openpilot.system.ui.widgets.selection_dialog import SelectionDialog
from openpilot.system.ui.widgets.input_dialog import InputDialog
from openpilot.selfdrive.ui.layouts.settings.starpilot.panel import StarPilotPanel


class StarPilotDataLayout(StarPilotPanel):
  def __init__(self):
    super().__init__()
    self.CATEGORIES = [
      {"title": tr_noop("Manage Backups"), "panel": "backups", "icon": "toggle_icons/icon_system.png", "color": "#FA6800"},
      {"title": tr_noop("Toggle Backups"), "panel": "toggle_backups", "icon": "toggle_icons/icon_system.png", "color": "#FA6800"},
      {"title": tr_noop("Manage Storage"), "panel": "storage", "icon": "toggle_icons/icon_system.png", "color": "#FA6800"},
      {
        "title": tr_noop("Delete Driving Data"),
        "type": "hub",
        "on_click": self._on_delete_driving_data,
        "icon": "toggle_icons/icon_system.png",
        "color": "#FA6800",
      },
      {
        "title": tr_noop("Delete Error Logs"),
        "type": "hub",
        "on_click": self._on_delete_error_logs,
        "icon": "toggle_icons/icon_system.png",
        "color": "#FA6800",
      },
    ]

    self._sub_panels = {
      "backups": StarPilotBackupsLayout(),
      "toggle_backups": StarPilotToggleBackupsLayout(),
      "storage": StarPilotStorageLayout(),
    }

    for name, panel in self._sub_panels.items():
      if hasattr(panel, 'set_navigate_callback'):
        panel.set_navigate_callback(self._navigate_to)
      if hasattr(panel, 'set_back_callback'):
        panel.set_back_callback(self._go_back)

    self._rebuild_grid()

  def _on_delete_driving_data(self):
    def _do_delete(res):
      if res == DialogResult.CONFIRM:

        def _task():
          drive_paths = ["/data/media/0/realdata/", "/data/media/0/realdata_HD/", "/data/media/0/realdata_konik/"]
          for path in drive_paths:
            p = Path(path)
            if p.exists():
              for entry in p.iterdir():
                if entry.is_dir():
                  shutil.rmtree(entry, ignore_errors=True)

        threading.Thread(target=_task, daemon=True).start()
        gui_app.set_modal_overlay(alert_dialog(tr("Driving data deletion started.")))

    gui_app.set_modal_overlay(ConfirmDialog(tr("Delete all driving data and footage?"), tr("Delete"), on_close=_do_delete))

  def _on_delete_error_logs(self):
    def _do_delete(res):
      if res == DialogResult.CONFIRM:
        shutil.rmtree("/data/error_logs", ignore_errors=True)
        os.makedirs("/data/error_logs", exist_ok=True)
        gui_app.set_modal_overlay(alert_dialog(tr("Error logs deleted.")))

    gui_app.set_modal_overlay(ConfirmDialog(tr("Delete all error logs?"), tr("Delete"), on_close=_do_delete))


class StarPilotBackupsLayout(StarPilotPanel):
  def __init__(self):
    super().__init__()
    self.CATEGORIES = [
      {"title": tr_noop("Create Backup"), "type": "hub", "on_click": self._on_create_backup, "color": "#FA6800"},
      {"title": tr_noop("Restore Backup"), "type": "hub", "on_click": self._on_restore_backup, "color": "#FA6800"},
      {"title": tr_noop("Delete Backup"), "type": "hub", "on_click": self._on_delete_backup, "color": "#FA6800"},
    ]
    self._rebuild_grid()

  def _get_backups(self):
    b_dir = Path("/data/backups")
    if not b_dir.exists():
      return []
    return [f.name for f in b_dir.glob("*.tar.zst") if "in_progress" not in f.name]

  def _on_create_backup(self):
    def on_name(res, name):
      if res == DialogResult.CONFIRM:
        safe_name = name.replace(" ", "_") if name else f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        backup_path = f"/data/backups/{safe_name}.tar.zst"
        if Path(backup_path).exists():
          gui_app.set_modal_overlay(alert_dialog(tr("A backup with this name already exists.")))
          return
        gui_app.set_modal_overlay(alert_dialog(tr("Backup creation started.")))

        def _task():
          os.makedirs("/data/backups", exist_ok=True)
          subprocess.run(["tar", "--use-compress-program=zstd", "-cf", backup_path, "/data/openpilot"])

        threading.Thread(target=_task, daemon=True).start()

    gui_app.set_modal_overlay(InputDialog(tr("Name your backup"), "", on_close=on_name))

  def _on_restore_backup(self):
    backups = self._get_backups()
    if not backups:
      gui_app.set_modal_overlay(alert_dialog(tr("No backups found.")))
      return

    def _on_select(res, val):
      if res == DialogResult.CONFIRM:
        gui_app.set_modal_overlay(alert_dialog(tr("Restoring... device will reboot.")))

        def _task():
          subprocess.run(["rm", "-rf", "/data/openpilot/*"])
          subprocess.run(["tar", "--use-compress-program=zstd", "-xf", f"/data/backups/{val}", "-C", "/"])
          os.system("reboot")

        threading.Thread(target=_task, daemon=True).start()

    gui_app.set_modal_overlay(SelectionDialog(tr("Select Backup"), backups, on_close=_on_select))

  def _on_delete_backup(self):
    backups = self._get_backups()
    if not backups:
      gui_app.set_modal_overlay(alert_dialog(tr("No backups found.")))
      return

    def _on_select(res, val):
      if res == DialogResult.CONFIRM:
        os.remove(f"/data/backups/{val}")
        self._rebuild_grid()

    gui_app.set_modal_overlay(SelectionDialog(tr("Delete Backup"), backups, on_close=_on_select))


class StarPilotToggleBackupsLayout(StarPilotPanel):
  def __init__(self):
    super().__init__()
    self.CATEGORIES = [
      {"title": tr_noop("Create Toggle Backup"), "type": "hub", "on_click": self._on_create, "color": "#FA6800"},
      {"title": tr_noop("Restore Toggle Backup"), "type": "hub", "on_click": self._on_restore, "color": "#FA6800"},
      {"title": tr_noop("Delete Toggle Backup"), "type": "hub", "on_click": self._on_delete, "color": "#FA6800"},
    ]
    self._rebuild_grid()

  def _get_backups(self):
    b_dir = Path("/data/toggle_backups")
    if not b_dir.exists():
      return []
    return [d.name for d in b_dir.iterdir() if d.is_dir() and "in_progress" not in d.name]

  def _on_create(self):
    def on_name(res, name):
      if res == DialogResult.CONFIRM:
        safe_name = name.replace(" ", "_") if name else f"toggle_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        backup_path = Path(f"/data/toggle_backups/{safe_name}")
        if backup_path.exists():
          gui_app.set_modal_overlay(alert_dialog(tr("A toggle backup with this name already exists.")))
          return
        os.makedirs(backup_path, exist_ok=True)
        shutil.copytree("/data/params/d", str(backup_path), dirs_exist_ok=True)
        gui_app.set_modal_overlay(alert_dialog(tr("Toggle backup created.")))
        self._rebuild_grid()

    gui_app.set_modal_overlay(InputDialog(tr("Name your toggle backup"), "", on_close=on_name))

  def _on_restore(self):
    backups = self._get_backups()
    if not backups:
      gui_app.set_modal_overlay(alert_dialog(tr("No toggle backups found.")))
      return

    def _on_select(res, val):
      if res == DialogResult.CONFIRM:

        def on_confirm(r2):
          if r2 == DialogResult.CONFIRM:
            src = Path(f"/data/toggle_backups/{val}")
            shutil.copytree(str(src), "/data/params/d", dirs_exist_ok=True)
            gui_app.set_modal_overlay(alert_dialog(tr("Toggles restored.")))
            self._rebuild_grid()

        gui_app.set_modal_overlay(ConfirmDialog(tr("This will overwrite your current toggles."), tr("Restore"), on_close=on_confirm))

    gui_app.set_modal_overlay(SelectionDialog(tr("Select Toggle Backup"), backups, on_close=_on_select))

  def _on_delete(self):
    backups = self._get_backups()
    if not backups:
      gui_app.set_modal_overlay(alert_dialog(tr("No toggle backups found.")))
      return

    def _on_select(res, val):
      if res == DialogResult.CONFIRM:
        shutil.rmtree(f"/data/toggle_backups/{val}", ignore_errors=True)
        self._rebuild_grid()

    gui_app.set_modal_overlay(SelectionDialog(tr("Delete Toggle Backup"), backups, on_close=_on_select))


class StarPilotStorageLayout(StarPilotPanel):
  def __init__(self):
    super().__init__()
    self.CATEGORIES = [
      {"title": tr_noop("Driving Data"), "type": "value", "get_value": self._get_storage, "on_click": lambda: None, "color": "#FA6800"},
    ]
    self._rebuild_grid()

  def _get_storage(self):
    paths = ["/data/media/0/osm/offline", "/data/media/0/realdata", "/data/backups"]
    total = 0
    for p in paths:
      pp = Path(p)
      if pp.exists():
        total += sum(f.stat().st_size for f in pp.rglob('*') if f.is_file())
    mb = total / (1024 * 1024)
    if mb > 1024:
      return f"{(mb / 1024):.2f} GB"
    return f"{mb:.2f} MB"
