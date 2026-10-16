from types import SimpleNamespace
from unittest.mock import patch

import numpy as np

from jetlink.openpilot import Openpilot, conformance
from jetlink.openpilot.hooks import Hooks, Off
from openpilot.starpilot.models import jetlink_adapter as adapter


def test_interface_keys():
  # the params directory is Stock's, held against openpilot's Params in test_jetlink_lifecycle
  op = adapter.adapter()
  assert conformance(op, Openpilot) == []
  assert adapter.owner_config().adapter == adapter.__name__
  assert op.keys.link == "JetlinkMode"
  # nothing writes a big-model slot or catalog: jetlink's default model, so a fresh Jetson is provisioned
  assert op.keys.big_model is None and op.keys.catalog is None


def test_guard_answers_link_off_without_a_usable_jetlink():
  adapter.hooks.cache_clear()
  try:
    with patch.object(adapter, "supported_device", return_value=False):
      assert isinstance(adapter.hooks(), Off)
    adapter.hooks.cache_clear()
    with patch.object(adapter, "supported_device", return_value=True), patch.object(adapter, "API", 2):
      assert isinstance(adapter.hooks(), Off)
    adapter.hooks.cache_clear()
    with patch.object(adapter, "supported_device", return_value=True):
      assert isinstance(adapter.hooks(), Hooks)
    adapter.hooks.cache_clear()
    with patch.dict("sys.modules", {"jetlink.openpilot.hooks": None}):
      hooks = adapter.hooks()
    assert not hooks.prepare(False) and not hooks.should_run(False, None, None) and hooks.status() is None
    assert hooks.shutdown_step(True) and not hooks.shutdown_step(False)
  finally:
    adapter.hooks.cache_clear()


def test_one_action_call_for_every_small_model():
  from openpilot.selfdrive.modeld import modeld
  from openpilot.starpilot.models import runner

  small = runner.CatalogModelState.__new__(runner.CatalogModelState)
  small.behavior_version = "v9"
  outputs, previous = object(), object()
  with patch.object(runner, "action_from_outputs", return_value="catalog") as catalog:
    assert small.get_action_from_model(outputs, previous, .4, .7, 12.) == "catalog"
  catalog.assert_called_once_with(outputs, "v9", previous, .4, .7, 12., modeld.LAT_SMOOTH_SECONDS, modeld.LONG_SMOOTH_SECONDS)
  assert modeld.ModelState.get_action_from_model is modeld.get_action_from_model


def test_small_reset_only_for_the_catalog_runner():
  assert adapter.adapter().small_reset(SimpleNamespace(input_queues={}, npy={}, prev_desire=np.zeros(8))) is None


def test_unsupported_device():
  assert adapter.supported_device("tizi")
  assert adapter.supported_device("mici")
  for device in ("tici", "pc", "unknown", "neo"):
    assert not adapter.supported_device(device)
