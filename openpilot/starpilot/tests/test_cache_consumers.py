import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from opendbc.car.structs import car
from openpilot.cereal import messaging
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

  def test_current_factory_recomputes_controls_from_cached_firmware_identity(self):
    from opendbc.car import car_helpers
    from opendbc.car.structs import car
    from opendbc.car.toyota.values import CAR

    cached = car.CarParams.new_message(carFingerprint=str(CAR.TOYOTA_PRIUS), mass=-123.0,
                                      wheelbase=-456.0, steerActuatorDelay=99.0)
    cached.lateralTuning.init('pid')
    cached.lateralTuning.pid.kpBP = [0.0]
    cached.lateralTuning.pid.kpV = [123.0]
    # Fingerprinting supplies identity only. The production get_car factory
    # must rebuild dynamics/control fields rather than return the cached CP.
    identity = (CAR.TOYOTA_PRIUS, {0: {}, 1: {}, 2: {}}, '00000000000000000', [], car.CarParams.FingerprintSource.fw, True)
    with patch.object(car_helpers, 'fingerprint', return_value=identity) as fingerprint:
      interface = car_helpers.get_car(lambda wait_for_one=False: [], lambda messages: None, lambda enabled: None,
                                      alpha_long_allowed=False, is_release=True, cached_params=cached)
    self.assertIs(fingerprint.call_args.args[3], cached)
    self.assertGreater(interface.CP.mass, 0)
    self.assertGreater(interface.CP.wheelbase, 0)
    self.assertLess(interface.CP.steerActuatorDelay, 1)
    self.assertNotEqual(interface.CP.lateralTuning.to_dict(), cached.lateralTuning.to_dict())

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

  def test_locationd_replay_ignores_vehicle_cache_without_fingerprinting(self):
    event = messaging.new_message("carParams")
    event.carParams = car.CarParams.new_message(fingerprintSource="fw", openpilotLongitudinalControl=True, notCar=True)
    config = next(cfg for cfg in process_replay.CONFIGS if cfg.proc_name == "locationd")
    container = Mock()
    container.start.side_effect = RuntimeError("captured replay startup")
    with patch.object(process_replay, "ProcessContainer", return_value=container), \
         self.assertRaisesRegex(RuntimeError, "captured replay startup"):
      process_replay._replay_multi_process([config], [event.as_reader()], None, None, None, None, True)
    params, environment = container.start.call_args.args[:2]
    self.assertNotIn("CarParamsCache", params)
    self.assertNotIn("AlphaLongitudinalEnabled", params)
    self.assertNotIn("JoystickDebugMode", params)
    self.assertEqual(environment["FINGERPRINT"], "")
    container.stop.assert_called_once_with()

  def test_vehicle_replay_still_requires_qualified_firmware_cache(self):
    event = messaging.new_message("carParams")
    event.carParams = car.CarParams.new_message(fingerprintSource="fw")
    location = next(cfg for cfg in process_replay.CONFIGS if cfg.proc_name == "locationd")
    for name in ("card", "controlsd", "selfdrived", "radard", "plannerd"):
      vehicle = next(cfg for cfg in process_replay.CONFIGS if cfg.proc_name == name)
      with self.subTest(process=name), patch.object(process_replay, "ProcessContainer") as factory, \
           self.assertRaisesRegex(ValueError, "Automatic CarParamsCache"):
        process_replay._replay_multi_process([location, vehicle], [event.as_reader()], None, None, None, None, True)
      factory.assert_not_called()

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
