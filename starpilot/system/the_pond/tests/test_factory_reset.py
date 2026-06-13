import subprocess

import pytest

from openpilot.starpilot.system.the_pond import factory_reset


def test_remove_path_retries_directory_not_empty(monkeypatch):
  results = iter(
    [
      subprocess.CompletedProcess([], 1, stderr="rm: cannot remove '/data/params': Directory not empty"),
      subprocess.CompletedProcess([], 0),
    ]
  )
  calls = []
  sleeps = []

  def fake_run(*args, **kwargs):
    calls.append((args, kwargs))
    return next(results)

  monkeypatch.setattr(factory_reset.subprocess, "run", fake_run)
  monkeypatch.setattr(factory_reset.time, "sleep", sleeps.append)

  factory_reset.remove_path("/data/params")

  assert len(calls) == 2
  assert calls[0][0][0] == ["sudo", "rm", "-rf", "--", "/data/params"]
  assert sleeps == [factory_reset._DELETE_RETRY_DELAY_S]


def test_remove_path_does_not_retry_non_transient_error(monkeypatch):
  calls = []

  def fake_run(*args, **kwargs):
    calls.append((args, kwargs))
    return subprocess.CompletedProcess([], 1, stderr="rm: cannot remove '/data/params': Permission denied")

  monkeypatch.setattr(factory_reset.subprocess, "run", fake_run)

  with pytest.raises(RuntimeError, match="Permission denied"):
    factory_reset.remove_path("/data/params")

  assert len(calls) == 1
