import os
from types import SimpleNamespace
from unittest.mock import Mock, patch

from jetlink.openpilot import Openpilot, conformance
from openpilot.starpilot.models import jetlink_adapter as adapter


def test_public_interface_and_params_directory(monkeypatch, tmp_path):
  op = adapter.adapter()
  op.log = Mock()
  assert conformance(op, Openpilot) == []
  monkeypatch.setenv("PARAMS_ROOT", str(tmp_path))
  monkeypatch.setenv("OPENPILOT_PREFIX", "jetlink-test")
  assert op.params_dir() == tmp_path / "jetlink-test"
  assert adapter.owner_config().params_dir == op.params_dir()
  assert op.keys.link == "JetlinkMode"
  assert op.keys.big_model != "ModelSelected"


def test_small_history_and_current_delay_forwarding():
  small = SimpleNamespace(prev_desire=object(), npy={"desire": object()}, input_queues={"history": object()},
                          chestnut=False, behavior_version="v16")
  face = adapter.SmallModelFace(small)
  assert face.prev_desire is small.prev_desire
  assert face.numpy_inputs is small.npy
  assert face.input_queues is small.input_queues
  joined = SimpleNamespace(chestnut=False, lat_delay=0., frame_drop_ratio=0.)
  model = adapter.JetlinkModel(joined, small)
  model.observe_frame(.23, .004)
  assert joined.lat_delay == .23
  assert joined.frame_drop_ratio == .004


def test_chestnut_and_recovery_never_prepare_link():
  small = object()
  with patch.object(adapter, "get_jetlink") as get:
    assert adapter.attach(small, 1344, 760, chestnut=True) is small
    assert adapter.attach(small, 1344, 760, recovery=True) is small
    get.assert_not_called()


def test_link_failure_preserves_small():
  small = object()
  link = Mock()
  link.prepare.side_effect = RuntimeError("link unavailable")
  op = Mock()
  with patch.object(adapter, "get_jetlink", return_value=link), patch.object(adapter, "adapter", return_value=op), \
       patch.object(adapter, "supported_device", return_value=True):
    assert adapter.attach(small, 1344, 760) is small
    op.log.exception.assert_called_once()


def test_runtime_requires_fresh_same_boot_and_process():
  record = {"version": 1, "boot_id": "boot", "session": "a" * 32, "pid": os.getpid(), "process_start_ticks": 12,
            "artifact_sha256": "b" * 64, "mono_ns": 2_000_000_000, "remote_output_mono_ns": 1_999_000_000, "state": "running"}
  assert adapter.runtime_snapshot(record, 3_000_000_000, "boot", 12)["active"]
  for changes in ({"boot_id": "other"}, {"process_start_ticks": 13}, {"session": "bad"},
                  {"mono_ns": 3_000_000_001}, {"remote_output_mono_ns": 0}, {"state": "ready"}):
    assert not adapter.runtime_snapshot(record | changes, 3_000_000_000, "boot", 12)["active"]
  assert not adapter.runtime_snapshot(record, 3_500_000_001, "boot", 12)["active"]


def test_handover_action_contract_tracks_actual_driver():
  from openpilot.selfdrive.modeld import modeld
  from openpilot.starpilot.models import runner

  small = SimpleNamespace(behavior_version="v9")
  joined = SimpleNamespace(chestnut=False)
  model = adapter.JetlinkModel(joined, small)
  outputs, previous = object(), object()
  with patch.object(runner, "action_from_outputs", return_value="catalog") as catalog, \
       patch.object(modeld, "get_action_from_model", return_value="remote") as remote:
    assert model.action(outputs, previous, .4, .7, 12.) == "catalog"
    assert catalog.call_args.args[:6] == (outputs, "v9", previous, .4, .7, 12.)
    joined.chestnut = True
    assert model.action(outputs, previous, .4, .7, 12.) == "remote"
    remote.assert_called_once_with(outputs, previous, .4, .7, 12.)
    joined.chestnut = False
    assert model.action(outputs, previous, .4, .7, 12.) == "catalog"
    assert catalog.call_count == 2


def test_remote_parser_rejects_nonfinite_and_missing_outputs():
  import numpy as np
  import pytest

  parser = adapter.remote_parser()
  with pytest.raises(ValueError, match="non-finite"):
    parser.parse_outputs({"action": np.array([[np.nan, 0.]])})
  with pytest.raises(ValueError, match="Missing output"):
    parser.parse_outputs({})


def test_vendor_attach_failure_returns_unwrapped_small():
  small = object()
  link = Mock()
  link.prepare.return_value = True
  link.attach.side_effect = lambda face, w, h: face
  with patch.object(adapter, "get_jetlink", return_value=link), patch.object(adapter, "supported_device", return_value=True):
    assert adapter.attach(small, 1344, 760) is small


def test_runtime_persistence_runs_off_frame_thread():
  import threading

  entered, release = threading.Event(), threading.Event()
  writes = []
  def write(key, record, *, block=False):
    writes.append((threading.get_ident(), key, record, block))
    entered.set()
    release.wait(1.)

  joined = SimpleNamespace(chestnut=False, big_model_state="joining", handovers=0, close=Mock())
  op = Mock()
  op.put.side_effect = write
  with patch.object(adapter, "adapter", return_value=op):
    model = adapter.JetlinkModel(joined, object())
    try:
      model.publish_runtime()
      assert entered.wait(1.)
      assert writes[0][0] != threading.get_ident()
      assert writes[0][1] == "JetlinkRuntime"
      assert writes[0][3] is True
      model.close()
    finally:
      release.set()
      model._runtime_thread.join(1.)
    assert not model._runtime_thread.is_alive()
    assert writes[-1][2]["state"] == "unavailable"


def test_unsupported_device_never_prepares_link():
  small = object()
  assert adapter.supported_device("tizi")
  assert adapter.supported_device("mici")
  for device in ("tici", "pc", "unknown", "neo"):
    assert not adapter.supported_device(device)
    with patch.object(adapter, "supported_device", return_value=False), patch.object(adapter, "get_jetlink") as get:
      assert adapter.attach(small, 1928, 1208) is small
      get.assert_not_called()
