"""Local FLM input admission uses disposable recordings and never remote routes."""

import hashlib
import os
from unittest.mock import patch

import pytest

from openpilot.starpilot.flm.local_logs import LocalLogUnavailable, read_closed_rlog


SEGMENT = "1234abcd--0123456789--0"


def recording(tmp_path, name="rlog.zst"):
  root = tmp_path.resolve()
  folder = root / SEGMENT
  folder.mkdir()
  path = folder / name
  path.write_bytes(b"immutable compressed fixture")
  return root, path


def test_receipt_binds_exact_bytes_and_requires_full_log(tmp_path):
  root, path = recording(tmp_path)
  result = read_closed_rlog(root, SEGMENT, permitted=lambda: True)
  assert result.compressed == path.read_bytes()
  assert result.sha256 == hashlib.sha256(result.compressed).hexdigest()
  assert result.codec == "zst" and result.size == len(result.compressed)
  path.rename(path.with_name("qlog.zst"))
  with pytest.raises(LocalLogUnavailable, match="full rlog"):
    read_closed_rlog(root, SEGMENT, permitted=lambda: True)


@pytest.mark.parametrize("name", ("rlog.lock", "writer.lock"))
def test_open_segment_is_not_analyzed(tmp_path, name):
  root, path = recording(tmp_path)
  path.with_name(name).touch()
  with pytest.raises(LocalLogUnavailable, match="open"):
    read_closed_rlog(root, SEGMENT, permitted=lambda: True)


def test_symlink_fifo_ambiguous_and_outside_selection_refused(tmp_path):
  root, path = recording(tmp_path)
  for selection in ("../" + SEGMENT, "/" + SEGMENT, SEGMENT + "/rlog.zst", "https://example.com/log"):
    with pytest.raises(LocalLogUnavailable):
      read_closed_rlog(root, selection, permitted=lambda: True)
  path.with_name("rlog.bz2").write_bytes(b"ambiguous")
  with pytest.raises(LocalLogUnavailable):
    read_closed_rlog(root, SEGMENT, permitted=lambda: True)
  path.with_name("rlog.bz2").unlink()
  path.unlink()
  external = root / "external"
  external.write_bytes(b"not a selected recording")
  path.symlink_to(external)
  with pytest.raises(LocalLogUnavailable):
    read_closed_rlog(root, SEGMENT, permitted=lambda: True)
  path.unlink()
  os.mkfifo(path)
  with pytest.raises(LocalLogUnavailable):
    read_closed_rlog(root, SEGMENT, permitted=lambda: True)


@pytest.mark.parametrize("change", ("replace", "mutate", "lock", "segment", "cancel"))
def test_changes_during_read_never_return_a_receipt(tmp_path, change):
  root, path = recording(tmp_path)
  allowed = [True]
  native_read = os.read
  changed = False
  def interrupted(fd, size):
    nonlocal changed
    result = native_read(fd, size)
    if result and not changed:
      changed = True
      if change == "replace":
        other = path.with_name("replacement")
        other.write_bytes(result)
        other.replace(path)
      elif change == "mutate":
        path.write_bytes(b"X" * len(result))
      elif change == "lock":
        path.with_name("rlog.lock").touch()
      elif change == "segment":
        path.parent.rename(root / (SEGMENT + "-moved"))
        path.parent.mkdir()
      else:
        allowed[0] = False
    return result
  with patch("openpilot.starpilot.flm.local_logs.os.read", side_effect=interrupted), pytest.raises(LocalLogUnavailable):
    read_closed_rlog(root, SEGMENT, permitted=lambda: allowed[0])


def test_size_limit_and_cancel_before_any_open(tmp_path):
  root, path = recording(tmp_path)
  with patch("openpilot.starpilot.flm.local_logs.MAX_COMPRESSED_BYTES", len(path.read_bytes()) - 1), \
       pytest.raises(LocalLogUnavailable, match="oversized"):
    read_closed_rlog(root, SEGMENT, permitted=lambda: True)
  with patch("openpilot.starpilot.flm.local_logs.os.open") as opened, pytest.raises(LocalLogUnavailable):
    read_closed_rlog(root, SEGMENT, permitted=lambda: False)
  opened.assert_not_called()
