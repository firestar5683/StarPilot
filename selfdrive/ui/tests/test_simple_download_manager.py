from types import SimpleNamespace

import pytest

from openpilot.selfdrive.ui.layouts.settings.starpilot import simple_download_manager as downloads
from openpilot.system.ui.widgets import DialogResult


class FakeParams:
  def __init__(self):
    self.values = {}

  def get(self, key, encoding=None):
    return self.values.get(key, "")

  def put(self, key, value):
    self.values[key] = value


@pytest.mark.parametrize("result", [DialogResult.CANCEL, DialogResult.CONFIRM])
def test_asset_deletion_requires_confirmation_and_preserves_other_assets(tmp_path, monkeypatch, result):
  target = tmp_path / "boot_logo_a.png"
  other = tmp_path / "boot_logo_b.png"
  target.write_bytes(b"target")
  other.write_bytes(b"other")
  params = FakeParams()
  manager = downloads.SimpleDownloadManager(
    "Boot Logo", "boot logo", tmp_path, "Asset", "Download", "Downloadable", params, FakeParams(), lambda *_: None,
  )
  manager._active_mode = manager.MODE_DELETE
  manager._refresh_list()
  dialogs = []
  monkeypatch.setattr(downloads, "ConfirmDialog", lambda text, confirm_text, callback: SimpleNamespace(text=text, callback=callback))
  monkeypatch.setattr(downloads.gui_app, "push_widget", dialogs.append)

  manager._on_target("item:0")

  assert len(dialogs) == 1
  assert "Boot Logo A" in dialogs[0].text
  assert target.exists() and other.exists()
  assert not params.values

  dialogs[0].callback(result)

  assert other.read_bytes() == b"other"
  if result == DialogResult.CONFIRM:
    assert not target.exists()
    assert manager._list_items == ["Boot Logo B"]
    assert params.values["Downloadable"] == "boot_logo_a"
  else:
    assert target.read_bytes() == b"target"
    assert manager._list_items == ["Boot Logo A", "Boot Logo B"]
    assert not params.values
