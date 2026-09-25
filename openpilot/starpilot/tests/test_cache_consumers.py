import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from opendbc.car.structs import car
from openpilot.common.params import Params
from openpilot.selfdrive.test.process_replay import process_replay
from openpilot.starpilot.schema_cache import get_cache, put_cache
from openpilot.system.athena import athenad
from openpilot.system.webrtc import helpers as webrtc_helpers
from tools.scripts import set_car_params


class TestCacheConsumers(unittest.TestCase):
  def setUp(self):
    temporary = tempfile.TemporaryDirectory()
    self.addCleanup(temporary.cleanup)
    self.root = Path(temporary.name)
    self.params = Params(str(self.root / "params"))
    self.namespace = Path(self.params.get_param_path())

  def test_athena_not_car_requires_verified_cache(self):
    cp = car.CarParams.new_message(notCar=True)
    with patch.object(athenad, "Params", return_value=self.params):
      self.assertFalse(athenad.getNotCar())
      self.params.put("CarParamsPersistent", cp.to_bytes(), block=True)
      self.assertFalse(athenad.getNotCar())
      put_cache(self.params, "CarParamsPersistent", cp, block=True)
      self.assertTrue(athenad.getNotCar())
      cp.notCar = False
      put_cache(self.params, "CarParamsPersistent", cp, block=True)
      self.assertFalse(athenad.getNotCar())

  def test_stream_joystick_bridge_requires_verified_cache(self):
    cp = car.CarParams.new_message(notCar=True)
    self.params.put_bool("IsOffroad", False, block=True)
    with patch.object(athenad, "Params", return_value=self.params), \
         patch.object(webrtc_helpers, "post_stream_request", side_effect=lambda body: body) as post, \
         patch.object(webrtc_helpers, "wait_for_webrtcd") as wait:
      self.params.put("CarParamsPersistent", cp.to_bytes(), block=True)
      self.assertEqual(athenad.startStream("synthetic-sdp", True).bridge_services_in, [])
      put_cache(self.params, "CarParamsPersistent", cp, block=True)
      self.assertEqual(athenad.startStream("synthetic-sdp", True).bridge_services_in, ["testJoystick"])
      self.assertEqual(post.call_count, 2)
      wait.assert_not_called()

  def test_replay_config_refuses_raw_cache_before_params_or_environment_changes(self):
    before = dict(os.environ)
    container = object.__new__(process_replay.ProcessContainer)
    config = {"OpenpilotEnabledToggle": True, "CarParamsCache": car.CarParams.new_message().to_bytes()}
    with patch.object(process_replay, "Params") as factory, self.assertRaisesRegex(ValueError, "verified cache envelope"):
      container._setup_env(config, {"PROC_NAME": "must-not-change"})
    factory.assert_not_called()
    self.assertEqual(dict(os.environ), before)
    self.assertEqual(list(self.namespace.iterdir()), [])

  def test_replay_accepts_current_synthetic_envelopes(self):
    cp = car.CarParams.new_message(carFingerprint="cache-test-car", fingerprintSource="fw")
    put_cache(self.params, "CarParamsCache", cp, block=True)
    encoded = self.params.get("CarParamsCache")
    config = process_replay.generate_params_config(CP=cp, custom_params={"CarParamsCache": encoded})
    self.params.remove("CarParamsCache")
    container = object.__new__(process_replay.ProcessContainer)
    with patch.object(container, "cfg", SimpleNamespace(proc_name="card", simulation=True), create=True), \
         patch.dict(os.environ), patch.object(process_replay, "Params", return_value=self.params):
      container._setup_env(config, {})
    self.assertEqual(self.params.get("CarParamsCache"), encoded)
    with car.CarParams.from_bytes(get_cache(self.params, "CarParamsCache")) as restored:
      self.assertEqual(restored.carFingerprint, "cache-test-car")

  def test_replay_refuses_implicit_log_cache_and_raw_custom_cache(self):
    cp = car.CarParams.new_message(fingerprintSource="fw")
    with self.assertRaisesRegex(ValueError, "Automatic CarParamsCache"):
      process_replay.generate_params_config(CP=cp)
    with self.assertRaisesRegex(ValueError, "verified cache envelope"):
      process_replay.generate_params_config(custom_params={"CarParamsPrevRoute": cp.to_bytes()})
    self.assertNotIn("CarParamsCache", process_replay.generate_params_config(CP=cp, fingerprint="explicit-current-car"))

  def test_log_cache_helper_refuses_without_reading_log(self):
    class UnqualifiedLog:
      def __iter__(self):
        raise AssertionError("The log must not be read before source provenance is established")

    with self.assertRaisesRegex(ValueError, "source schema provenance"):
      process_replay.get_custom_params_from_lr(UnqualifiedLog())

  def test_route_script_refuses_before_params_access(self):
    with patch.object(set_car_params, "Params") as factory, self.assertRaisesRegex(SystemExit, "source schema provenance"):
      set_car_params.main(["unqualified-route"])
    factory.assert_not_called()

  def test_script_synthetic_defaults_write_typed_caches(self):
    with patch.object(set_car_params, "Params", return_value=self.params):
      set_car_params.main([])
    for key in ("CarParamsCache", "CarParamsPersistent"):
      with car.CarParams.from_bytes(get_cache(self.params, key)) as restored:
        self.assertTrue(restored.openpilotLongitudinalControl)
    with car.CarParams.from_bytes(self.params.get("CarParams")) as live:
      self.assertTrue(live.openpilotLongitudinalControl)


if __name__ == "__main__":
  unittest.main()
