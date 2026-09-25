"""Native Corolla torque source selection, saved choices, and controller gates."""

import math
import os
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest import mock

from openpilot.cereal import messaging
from openpilot.common.params import ParamKeyFlag, Params
from openpilot.common.prefix import OpenpilotPrefix
from openpilot.selfdrive.controls.controlsd import Controls
from openpilot.selfdrive.locationd.torqued import TorqueEstimator
from openpilot.starpilot.lateral.tests.test_lane_runtime import feed
from openpilot.starpilot.lateral.controller_selection import DOCUMENT_KEY as CONTROLLER_KEY, ControllerMode, replace_mode
from openpilot.starpilot.lateral.torque_runtime import TorqueHost, development_enabled, read_settings
from openpilot.starpilot.lateral.torque_tuning import TorqueSource
from opendbc.car.car_helpers import interfaces
from opendbc.car.toyota.values import CAR


def corolla():
  return interfaces[CAR.TOYOTA_COROLLA_TSS2].get_non_essential_params(CAR.TOYOTA_COROLLA_TSS2)


class LearnedFrame:
  def __init__(self, now_ns, *, factor=2.0, offset=0.1, friction=0.1, version=1, valid=True):
    self.logMonoTime = {'lateralTorqueParameters': now_ns}
    self.checked = True
    self.state = SimpleNamespace(useParams=True, valid=valid, version=version, latAccelFactorFiltered=factor,
                                 latAccelOffsetFiltered=offset, frictionCoefficientFiltered=friction)

  def all_checks(self, _names):
    return self.checked

  def __getitem__(self, _name):
    return self.state


class TorqueRuntimeTests(unittest.TestCase):
  def test_saved_partial_precedence_and_corrupt_raw_bytes(self):
    with OpenpilotPrefix():
      params, cp = Params(), corolla()
      host = TorqueHost(params, cp)
      base = host.vehicle
      self.assertFalse(read_settings(params, base).advanced)
      params.put_bool('AdvancedLateralTune', True, block=True)
      params.put('SteerLatAccel', base.lat_accel_factor * 1.2, block=True)
      params.put('SteerFriction', min(1.0, base.friction * 1.2), block=True)
      settings = read_settings(params, base)
      self.assertTrue(settings.valid)
      host.settings = settings
      learned = LearnedFrame(1_000_000_000, factor=base.lat_accel_factor * 1.1,
                             offset=0.1, friction=base.friction * 1.1)
      selected = host._select(learned, 1_000_000_000)
      self.assertEqual(selected.source, TorqueSource.USER)
      self.assertEqual(selected.lat_accel_factor, settings.user_factor)
      self.assertEqual(selected.lat_accel_offset, base.lat_accel_offset)
      self.assertEqual(selected.friction, settings.user_friction)
      Path(params.get_param_path('SteerLatAccel')).write_bytes(b'nan')
      self.assertFalse(read_settings(params, base).valid)
      self.assertTrue(params.get_bool('AdvancedLateralTune'))
      host.settings = read_settings(params, base)
      self.assertEqual(host._select(learned, 1_000_000_000), base)
      self.assertEqual(host.sample(learned, now_ns=1_000_000_000, lat_active=True), base)

  def test_frozen_auto_synced_stock_and_individual_overrides(self):
    with OpenpilotPrefix():
      params, cp = Params(), corolla()
      host = TorqueHost(params, cp)
      base = host.vehicle
      now = 1_000_000_000
      learned = LearnedFrame(now, factor=base.lat_accel_factor * 1.1,
                             offset=0.1, friction=base.friction * 1.1)
      params.put_bool('AdvancedLateralTune', True, block=True)
      params.put('SteerLatAccel', base.lat_accel_factor, block=True)
      params.put('SteerFriction', base.friction, block=True)
      host.settings = read_settings(params, base)
      self.assertIsNone(host.settings.user_factor)
      self.assertIsNone(host.settings.user_friction)
      self.assertEqual(host._select(learned, now).source, TorqueSource.LEARNED)

      params.put('SteerLatAccel', base.lat_accel_factor * 1.2, block=True)
      host.settings = read_settings(params, base)
      factor_only = host._select(learned, now)
      self.assertEqual(factor_only.source, TorqueSource.USER)
      self.assertAlmostEqual(factor_only.lat_accel_factor, base.lat_accel_factor * 1.2)
      self.assertEqual(factor_only.lat_accel_offset, base.lat_accel_offset)
      self.assertAlmostEqual(factor_only.friction, base.friction * 1.1)

      params.put('SteerLatAccel', base.lat_accel_factor, block=True)
      params.put('SteerFriction', base.friction * 1.2, block=True)
      host.settings = read_settings(params, base)
      friction_only = host._select(learned, now)
      self.assertEqual(friction_only.source, TorqueSource.USER)
      self.assertAlmostEqual(friction_only.lat_accel_factor, base.lat_accel_factor * 1.1)
      self.assertAlmostEqual(friction_only.lat_accel_offset, 0.1)
      self.assertAlmostEqual(friction_only.friction, base.friction * 1.2)

      # A frozen stock-sync file distinguishes an old stock save from a user edit
      # after a later CarParams retune changes the current stock value.
      old_stock = base.lat_accel_factor * 0.9
      params.put('SteerLatAccel', old_stock, block=True)
      params.put('SteerLatAccelStock', old_stock, block=True)
      params.clear_all(ParamKeyFlag.CLEAR_ON_MANAGER_START)
      self.assertAlmostEqual(params.get('SteerLatAccelStock'), old_stock)
      host.settings = read_settings(params, base)
      self.assertIsNone(host.settings.user_factor)
      self.assertAlmostEqual(host._select(learned, now).lat_accel_factor, learned.state.latAccelFactorFiltered)

      # Old untouched stock may be outside today's safe custom range: it is a
      # stock-tracking marker, not a custom override to reject or apply.
      older_stock = base.lat_accel_factor * 2.0
      params.put('SteerLatAccel', older_stock, block=True)
      params.put('SteerLatAccelStock', older_stock, block=True)
      host.settings = read_settings(params, base)
      self.assertTrue(host.settings.valid)
      self.assertIsNone(host.settings.user_factor)
      self.assertAlmostEqual(host._select(learned, now).lat_accel_factor, learned.state.latAccelFactorFiltered)
      params.put('SteerFriction', base.friction, block=True)
      params.put_bool('ForceAutoTuneOff', True, block=True)
      host.settings = read_settings(params, base)
      self.assertEqual(host._select(learned, now), base)

  def test_malformed_saved_bool_and_numeric_settings_fail_closed(self):
    with OpenpilotPrefix():
      params, cp = Params(), corolla()
      host = TorqueHost(params, cp)
      params.put_bool('AdvancedLateralTune', True, block=True)
      for key, bad in (('AdvancedLateralTune', b'yes'), ('ForceAutoTuneOff', b'2'),
                       ('SteerLatAccel', b'nan'), ('SteerFriction', b'inf'),
                       ('SteerLatAccelStock', b'bad'), ('SteerFrictionStock', b'bad')):
        with self.subTest(key=key):
          path = Path(params.get_param_path(key))
          original = path.read_bytes() if path.exists() else None
          path.write_bytes(bad)
          self.assertFalse(read_settings(params, host.vehicle).valid)
          if original is None:
            path.unlink()
          else:
            path.write_bytes(original)

  def test_learned_source_freshness_version_and_override(self):
    with OpenpilotPrefix():
      params, cp = Params(), corolla()
      host = TorqueHost(params, cp)
      base = host.vehicle
      frame = LearnedFrame(1_000_000_000, factor=base.lat_accel_factor * 1.1,
                           offset=0.1, friction=base.friction * 1.1)
      self.assertEqual(host._select(frame, 1_000_000_000).source, TorqueSource.LEARNED)
      frame.state.version = 99
      self.assertEqual(host._select(frame, 1_000_000_000), base)
      frame.state.version = 1
      frame.logMonoTime['lateralTorqueParameters'] = 1
      self.assertEqual(host._select(frame, 1_000_000_000), base)
      frame.logMonoTime['lateralTorqueParameters'] = 1_000_000_000
      frame.checked = False
      self.assertEqual(host._select(frame, 1_000_000_000), base)
      params.put_bool('AdvancedLateralTune', True, block=True)
      params.put_bool('ForceAutoTuneOff', True, block=True)
      host.settings = read_settings(params, base)
      frame.checked = True
      self.assertEqual(host._select(frame, 1_000_000_000), base)

  def test_exact_car_development_policy(self):
    cp = corolla()
    with mock.patch.dict(os.environ, {'TORQUE_REPLAY_RUNTIME': '1'}):
      self.assertTrue(development_enabled(cp))
      cp.carFingerprint = 'TOYOTA_RAV4_TSS2_2023'
      self.assertFalse(development_enabled(cp))
    with mock.patch.dict(os.environ, {'TORQUE_REPLAY_RUNTIME': '0'}):
      self.assertFalse(development_enabled(corolla()))

  def test_opt_in_learner_skips_old_cache_without_deleting_it(self):
    cp = corolla()
    with OpenpilotPrefix(), mock.patch('openpilot.selfdrive.locationd.torqued.get_cache', return_value=None) as get_cache:
      with mock.patch.dict(os.environ, {'TORQUE_REPLAY_RUNTIME': '1'}):
        fresh = TorqueEstimator(cp.as_reader())
      self.assertEqual(get_cache.call_count, 0)
      self.assertEqual(fresh.filtered_params['latAccelFactor'].x, cp.lateralTuning.torque.latAccelFactor)
      cp.carFingerprint = 'TOYOTA_RAV4_TSS2_2023'
      with mock.patch.dict(os.environ, {'TORQUE_REPLAY_RUNTIME': '1'}):
        TorqueEstimator(cp.as_reader())
      self.assertEqual(get_cache.call_count, 2)

  def test_native_controls_default_equivalence_and_selected_torque(self):
    with OpenpilotPrefix(), mock.patch.dict(os.environ, {'REPLAY': '1', 'AOL_REPLAY_RUNTIME': '0',
                                                         'LANE_CENTERING_REPLAY_RUNTIME': '0'}), \
         mock.patch('openpilot.selfdrive.controls.controlsd.messaging.PubMaster'):
      params, cp = Params(), corolla()
      params.put('CarParams', cp.to_bytes(), block=True)
      with mock.patch.dict(os.environ, {'TORQUE_REPLAY_RUNTIME': '0'}):
        baseline = Controls()
      with mock.patch.dict(os.environ, {'TORQUE_REPLAY_RUNTIME': '1'}):
        selected = Controls()
      self.assertIsNone(baseline.torque_host)
      self.assertIsNotNone(selected.torque_host)
      for tick in range(110):
        now = 1_000_000_000 + tick * 10_000_000
        for controls in (baseline, selected):
          feed(controls, now, tick)
        a, _ = baseline.state_control()
        b, _ = selected.state_control()
        self.assertEqual(a.to_dict(), b.to_dict())
      params.put_bool('AdvancedLateralTune', True, block=True)
      native_factor = selected.torque_host.vehicle.lat_accel_factor
      params.put('SteerLatAccel', native_factor * 1.3, block=True)
      torque_differences = []
      for tick in range(110, 230):
        now = 1_000_000_000 + tick * 10_000_000
        for controls in (baseline, selected):
          feed(controls, now, tick)
        reference, _ = baseline.state_control()
        command, _ = selected.state_control()
        torque_differences.append(abs(command.actuators.torque - reference.actuators.torque))
      self.assertTrue(command.latActive)
      self.assertGreater(selected.torque_host.applied.lat_accel_factor, native_factor)
      self.assertLessEqual(selected.torque_host.applied.lat_accel_factor, native_factor * 1.3)
      self.assertGreater(selected.LaC.pid.pos_limit, baseline.LaC.pid.pos_limit)
      self.assertGreater(max(torque_differences), 1e-6)
      feed(selected, now + 10_000_000, 230, active=False, enabled=False)
      off, _ = selected.state_control()
      self.assertFalse(off.latActive)
      self.assertEqual(off.actuators.torque, 0.0)
      self.assertEqual(selected.torque_host.applied, selected.torque_host.vehicle)
      self.assertEqual(selected.LaC.pid.i, 0.0)
      feed(selected, now + 20_000_000, 231, can_valid=False)
      invalid, _ = selected.state_control()
      self.assertFalse(invalid.latActive)
      self.assertEqual(invalid.actuators.torque, 0.0)
      feed(selected, now + 30_000_000, 232)
      resumed, _ = selected.state_control()
      self.assertTrue(resumed.latActive)
      self.assertLess(abs(resumed.actuators.torque), selected.LaC.steer_max)
      feed(selected, now + 40_000_000, 233, can_timeout=True)
      timeout, _ = selected.state_control()
      self.assertFalse(timeout.latActive)
      self.assertEqual(timeout.actuators.torque, 0.0)
      feed(selected, now + 50_000_000, 234, override=True)
      prior_integral = selected.LaC.pid.i
      override, _ = selected.state_control()
      self.assertTrue(override.latActive)
      self.assertTrue(math.isfinite(override.actuators.torque))
      self.assertEqual(selected.LaC.pid.i, prior_integral)

  def test_actual_controls_learned_to_user_to_stale_source(self):
    with OpenpilotPrefix(), mock.patch.dict(os.environ, {'REPLAY': '1', 'TORQUE_REPLAY_RUNTIME': '1',
                                                         'AOL_REPLAY_RUNTIME': '0', 'LANE_CENTERING_REPLAY_RUNTIME': '0'}), \
         mock.patch('openpilot.selfdrive.controls.controlsd.messaging.PubMaster'):
      params, cp = Params(), corolla()
      Path(params.get_param_path(CONTROLLER_KEY)).write_bytes(replace_mode(None, cp, ControllerMode.STANDARD))
      params.put('CarParams', cp.to_bytes(), block=True)
      controls = Controls()
      base = controls.torque_host.vehicle
      target = base.lat_accel_factor * 1.1
      for tick in range(120):
        now = 1_000_000_000 + tick * 10_000_000
        feed(controls, now, tick)
        if tick % 25 == 0:
          event = messaging.new_message('lateralTorqueParameters', valid=True, logMonoTime=now)
          state = event.lateralTorqueParameters
          state.useParams = state.valid = True
          state.version = 1
          state.latAccelFactorFiltered = target
          state.latAccelOffsetFiltered = 0.1
          state.frictionCoefficientFiltered = base.friction
          controls.sm.update_msgs(now / 1e9, [event.as_reader()])
        controls.state_control()
      self.assertEqual(controls.torque_host.selected.source, TorqueSource.LEARNED)
      self.assertGreater(controls.torque_host.applied.lat_accel_factor, base.lat_accel_factor)
      params.put_bool('AdvancedLateralTune', True, block=True)
      params.put('SteerLatAccel', base.lat_accel_factor * 1.2, block=True)
      for tick in range(120, 230):
        now = 1_000_000_000 + tick * 10_000_000
        feed(controls, now, tick)
        controls.state_control()
      self.assertEqual(controls.torque_host.selected.source, TorqueSource.USER)
      self.assertEqual(controls.torque_host.selected.lat_accel_offset, base.lat_accel_offset)
      self.assertGreater(controls.torque_host.applied.lat_accel_factor, target)
      params.put_bool('AdvancedLateralTune', False, block=True)
      for tick in range(230, 340):
        now = 1_000_000_000 + tick * 10_000_000
        feed(controls, now, tick)
        controls.state_control()
      self.assertEqual(controls.torque_host.selected, base)
      self.assertAlmostEqual(controls.torque_host.applied.lat_accel_factor, base.lat_accel_factor)


if __name__ == '__main__':
  unittest.main()
