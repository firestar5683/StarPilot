import random
import numpy as np

from openpilot.common.test import OpenpilotTestCase
from openpilot.cereal import messaging
from opendbc.car.structs import car
from openpilot.selfdrive.locationd.paramsd import retrieve_initial_vehicle_params
from openpilot.selfdrive.locationd.models.car_kf import CarKalman
from openpilot.common.params import Params
from openpilot.starpilot.schema_cache import put_cache


def get_random_vehicle_parameters(CP):
  msg = messaging.new_message("vehicleParameters")
  msg.vehicleParameters.steerRatio = (random.random() + 0.5) * CP.steerRatio
  msg.vehicleParameters.stiffnessFactor = random.random()
  msg.vehicleParameters.angleOffsetAverageDeg = random.random()
  msg.vehicleParameters.debugFilterState.std = [random.random() for _ in range(CarKalman.P_initial.shape[0])]
  return msg


class TestParamsd(OpenpilotTestCase):
  def test_unqualified_saved_params_are_not_loaded(self):
    params = Params()
    CP = car.CarParams.new_message(carFingerprint="cache-test-car", steerRatio=15.0)
    msg = get_random_vehicle_parameters(CP)
    raw = msg.to_bytes()
    params.put("LiveParametersV2", raw, block=True)
    put_cache(params, "CarParamsPrevRoute", CP, block=True)

    self.assertEqual(retrieve_initial_vehicle_params(params, CP, replay=True, debug=True), (CP.steerRatio, 1.0, 0.0, None))
    self.assertEqual(params.get("LiveParametersV2"), raw)

  def test_read_saved_params(self):
    params = Params()

    CP = car.CarParams.new_message(carFingerprint="cache-test-car", steerRatio=15.0)

    msg = get_random_vehicle_parameters(CP)
    put_cache(params, "LiveParametersV2", msg, block=True)
    put_cache(params, "CarParamsPrevRoute", CP, block=True)

    sr, sf, offset, p_init = retrieve_initial_vehicle_params(params, CP, replay=True, debug=True)
    np.testing.assert_allclose(sr, msg.vehicleParameters.steerRatio)
    np.testing.assert_allclose(sf, msg.vehicleParameters.stiffnessFactor)
    np.testing.assert_allclose(offset, msg.vehicleParameters.angleOffsetAverageDeg)
    np.testing.assert_equal(p_init.shape, CarKalman.P_initial.shape)
    np.testing.assert_allclose(np.diagonal(p_init), msg.vehicleParameters.debugFilterState.std)
