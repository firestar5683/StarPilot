"""Import actual upstream planner/MPC; mock only native solver and process IPC."""
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import numpy as np
from openpilot.cereal import log
from openpilot.starpilot.longitudinal.upstream import mpc, planner, plannerd


class Solver:
  def __init__(self, *_):
    self.costs = {}
  def reset(self):
    self.costs.clear()
  def cost_set(self, stage, key, value):
    self.costs[stage, key] = np.copy(value)
  def set(self, *_):
    pass


class TestUpstreamPlanner(unittest.TestCase):
  def test_actual_upstream_mpc_has_stock_weights_and_distinct_owner(self):
    with patch.object(mpc, 'AcadosOcpSolverCython', Solver):
      stock = mpc.LongitudinalMpc()
      self.assertEqual(stock.__class__.__module__, 'openpilot.starpilot.longitudinal.upstream.mpc')
      np.testing.assert_equal(np.diag(stock.solver.costs[0, 'W']), [3., 0., 0., 0., 200., 5.])
      stock.set_weights(personality=log.LongitudinalPersonality.aggressive)
      np.testing.assert_equal(np.diag(stock.solver.costs[0, 'W']), [3., 0., 0., 0., 100., 2.5])
      stock.set_weights(prev_accel_constraint=False)
      self.assertEqual(stock.solver.costs[0, 'W'][4, 4], 0)
      self.assertEqual(mpc.get_T_FOLLOW(log.LongitudinalPersonality.relaxed), 1.75)
      self.assertEqual(mpc.get_T_FOLLOW(log.LongitudinalPersonality.standard), 1.45)
      self.assertEqual(mpc.get_T_FOLLOW(log.LongitudinalPersonality.aggressive), 1.25)
      with self.assertRaises(TypeError):
        stock.set_weights(acceleration_jerk=0.25)
      with self.assertRaises(TypeError):
        stock.update(None, follow_seconds=3.)

  def test_actual_stock_planner_uses_isolated_mpc_and_preserves_cp(self):
    cp = SimpleNamespace(openpilotLongitudinalControl=True, pcmCruise=False)
    before = vars(cp).copy()
    with patch.object(mpc, 'AcadosOcpSolverCython', Solver):
      stock = planner.LongitudinalPlanner(cp)
    self.assertIs(stock.CP, cp)
    self.assertIs(type(stock.mpc), mpc.LongitudinalMpc)
    self.assertEqual(vars(cp), before)
    self.assertFalse(hasattr(stock, 'profile_tuning'))

  def test_upstream_process_constructs_only_native_publishers_and_planner(self):
    calls = []
    cp = SimpleNamespace(brand='honda', openpilotLongitudinalControl=True)
    class SM:
      def update(self):
        raise InterruptedError('bounded end of mocked loop')
    def submaster(services, **kwargs):
      calls.append(('subscribe', services, kwargs))
      return SM()
    fake_params = SimpleNamespace(get=lambda key, **kwargs: b'CP')
    with patch.object(plannerd, 'config_realtime_process'), patch.object(plannerd, 'Params', return_value=fake_params), \
         patch.object(plannerd.messaging, 'log_from_bytes', return_value=cp), \
         patch.object(plannerd, 'LongitudinalPlanner', side_effect=lambda cp: calls.append(('planner', cp))), \
         patch.object(plannerd, 'LaneDepartureWarning', return_value=object()), \
         patch.object(plannerd.messaging, 'PubMaster', side_effect=lambda services: calls.append(('publish', services))), \
         patch.object(plannerd.messaging, 'SubMaster', side_effect=submaster):
      with self.assertRaises(InterruptedError):
        plannerd.main()
    self.assertEqual([item for item in calls if item[0] == 'publish'], [('publish', ['longitudinalPlan', 'driverAssistance'])])
    subscribed = next(item[1] for item in calls if item[0] == 'subscribe')
    self.assertEqual(subscribed, ['carControl', 'carState', 'controlsState', 'vehicleParameters', 'radarState', 'modelV2', 'selfdriveState'])
    self.assertFalse(any('starpilot' in value.lower() or value.startswith('slc') for value in subscribed))
    root = Path(__file__).parents[1] / 'upstream'
    self.assertEqual(Path(plannerd.__file__).resolve(), (root / 'plannerd.py').resolve())


if __name__ == '__main__':
  unittest.main()
