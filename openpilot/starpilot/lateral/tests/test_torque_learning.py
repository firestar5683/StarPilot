"""Controller-specific learning is enforced by its producer and both consumers."""

import os
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest import mock

from opendbc.car.car_helpers import interfaces
from opendbc.car.hyundai.values import CAR as HYUNDAI
from opendbc.car.toyota.values import CAR as TOYOTA
from openpilot.cereal import messaging
from openpilot.common.params import Params
from openpilot.common.prefix import OpenpilotPrefix
from openpilot.selfdrive.controls.controlsd import Controls
from openpilot.selfdrive.locationd import torqued
from openpilot.starpilot.lateral.controller_selection import (
  DOCUMENT_KEY, LEARNING_OFF_KEY, ControllerMode, learning_allowed, replace_mode,
)
from openpilot.starpilot.lateral.tests.test_lane_runtime import feed
from openpilot.starpilot.lateral.tests.test_torque_runtime import LearnedFrame
from openpilot.starpilot.lateral.torque_runtime import TorqueHost, read_settings
from openpilot.starpilot.lateral.torque_tuning import TorqueSource


VEHICLES = (HYUNDAI.HYUNDAI_IONIQ_6, HYUNDAI.GENESIS_G70_2020, TOYOTA.TOYOTA_COROLLA_TSS2)
ENV = {'REPLAY': '1', 'TORQUE_REPLAY_RUNTIME': '0', 'AOL_REPLAY_RUNTIME': '0', 'LANE_CENTERING_REPLAY_RUNTIME': '0'}


def cp_for(vehicle):
  return interfaces[vehicle].get_non_essential_params(vehicle)


def select(params, cp, mode):
  Path(params.get_param_path(DOCUMENT_KEY)).write_bytes(replace_mode(None, cp, mode))


def learned_event(cp, now):
  event = messaging.new_message('lateralTorqueParameters', valid=True, logMonoTime=now)
  state = event.lateralTorqueParameters
  state.useParams = state.valid = True
  state.version = torqued.VERSION
  state.latAccelFactorFiltered = cp.lateralTuning.torque.latAccelFactor * 1.1
  state.latAccelOffsetFiltered = 0.03
  state.frictionCoefficientFiltered = cp.lateralTuning.torque.friction * 1.1
  return event.as_reader()


class TestTorqueLearning(unittest.TestCase):
  def test_exact_policy_defaults_and_saved_off_without_manual_adjustments(self):
    with OpenpilotPrefix():
      params = Params()
      for vehicle in VEHICLES:
        with self.subTest(vehicle=vehicle):
          cp = cp_for(vehicle)
          params.remove(DOCUMENT_KEY)
          params.remove(LEARNING_OFF_KEY)
          self.assertFalse(learning_allowed(params, cp))
          select(params, cp, ControllerMode.STANDARD)
          self.assertTrue(learning_allowed(params, cp))
          for saved in (b'1', b'invalid', b''):
            Path(params.get_param_path(LEARNING_OFF_KEY)).write_bytes(saved)
            self.assertFalse(learning_allowed(params, cp))
          params.put_bool(LEARNING_OFF_KEY, False, block=True)
          self.assertTrue(learning_allowed(params, cp))
      params.put_bool(LEARNING_OFF_KEY, True, block=True)
      for vehicle in (HYUNDAI.KIA_EV6, HYUNDAI.HYUNDAI_SONATA, TOYOTA.TOYOTA_RAV4_TSS2):
        self.assertTrue(learning_allowed(params, cp_for(vehicle)))

  def test_learner_does_not_restore_collect_estimate_or_overwrite_disabled_cache(self):
    for vehicle in VEHICLES:
      with self.subTest(vehicle=vehicle), OpenpilotPrefix(), mock.patch.dict(os.environ, ENV):
        params, cp = Params(), cp_for(vehicle)
        params.put('CarParams', cp.to_bytes(), block=True)
        cache = Path(params.get_param_path('LiveTorqueParameters'))
        cache.write_bytes(b'preserved previous learning')
        with mock.patch.object(torqued, 'get_cache') as restore:
          estimator = torqued.TorqueEstimator(cp, allow_learning=learning_allowed(params, cp))
          restore.assert_not_called()
        self.assertFalse(estimator.learning_allowed)
        estimator.handle_log(1, 'carControl', SimpleNamespace(latActive=True))
        estimator.handle_log(1, 'carOutput', SimpleNamespace(actuatorsOutput=SimpleNamespace(torque=0.2)))
        self.assertFalse(estimator.raw_points)
        with mock.patch.object(estimator, 'estimate_params', side_effect=AssertionError('Learning is disabled')):
          msg = estimator.get_msg(with_points=True).lateralTorqueParameters
        self.assertFalse(msg.useParams)
        self.assertFalse(msg.valid)
        self.assertEqual(msg.totalBucketPoints, 0)
        self.assertEqual(msg.latAccelFactorFiltered, cp.lateralTuning.torque.latAccelFactor)
        sm = mock.Mock(frame=240, updated={})
        sm.update.side_effect = [None, StopIteration]
        sm.all_checks.return_value = True
        with mock.patch.object(torqued, 'prewarm_cache_contracts'), mock.patch.object(torqued, 'config_realtime_process'), \
             mock.patch.object(torqued.messaging, 'SubMaster', return_value=sm), mock.patch.object(torqued.messaging, 'PubMaster'), \
             mock.patch.object(torqued, 'put_cache') as persist, self.assertRaises(StopIteration):
          torqued.main()
        persist.assert_not_called()
        self.assertEqual(cache.read_bytes(), b'preserved previous learning')

  def test_standard_and_untuned_learner_keep_upstream_collection_and_cache(self):
    with OpenpilotPrefix(), mock.patch.dict(os.environ, ENV):
      params = Params()
      for vehicle in (*VEHICLES, HYUNDAI.KIA_EV6):
        cp = cp_for(vehicle)
        if vehicle in VEHICLES:
          select(params, cp, ControllerMode.STANDARD)
        with self.subTest(vehicle=vehicle), mock.patch.object(torqued, 'get_cache', return_value=None) as restore:
          estimator = torqued.TorqueEstimator(cp)
          self.assertEqual(restore.call_count, 2)
        self.assertTrue(estimator.learning_allowed)
        self.assertTrue(estimator.use_params)
        estimator.handle_log(1, 'carControl', SimpleNamespace(latActive=True))
        self.assertEqual(list(estimator.raw_points['lat_active']), [True])
      select(params, cp_for(VEHICLES[0]), ControllerMode.STANDARD)
      params.put_bool(LEARNING_OFF_KEY, True, block=True)
      cp = cp_for(VEHICLES[0])
      estimator = torqued.TorqueEstimator(cp, allow_learning=learning_allowed(params, cp))
      self.assertFalse(estimator.learning_allowed)

  def test_offline_fitting_is_not_disabled_by_saved_controller_or_learning_preference(self):
    with OpenpilotPrefix(), mock.patch.dict(os.environ, ENV):
      params, cp = Params(), cp_for(HYUNDAI.HYUNDAI_IONIQ_6)
      select(params, cp, ControllerMode.STARPILOT)
      params.put_bool(LEARNING_OFF_KEY, True, block=True)
      self.assertFalse(learning_allowed(params, cp))
      with mock.patch.object(torqued, 'get_cache', return_value=None):
        estimator = torqued.TorqueEstimator(cp, decimated=True, track_all_points=True)
      estimator.handle_log(1, 'carControl', SimpleNamespace(latActive=True))
      self.assertEqual(list(estimator.raw_points['lat_active']), [True])
      self.assertTrue(estimator.use_params)
      with mock.patch.object(estimator.filtered_points, 'is_calculable', return_value=True), \
           mock.patch.object(estimator.filtered_points, 'is_valid', return_value=True), \
           mock.patch.object(estimator, 'estimate_params', return_value=(3.1, 0.01, 0.10)) as fit:
        message = estimator.get_msg().lateralTorqueParameters
      fit.assert_called_once()
      self.assertTrue(message.valid)

  def test_direct_controller_consumer_rejects_learned_messages_and_latches_policy(self):
    now = 1_000_000_000

    def feed_learning(controls):
      # Real SubMaster frequency checks need a measured interval. Host development
      # defaults to SIMULATION=1, which otherwise hides an unqualified fixture.
      self.assertFalse(controls.sm.simulation)
      for tick in range(2):
        stamp = now + tick * 250_000_000  # lateralTorqueParameters publishes at 4 Hz.
        feed(controls, stamp, 0)
        controls.sm.update_msgs(stamp / 1e9, [learned_event(cp, stamp)])
        self.assertEqual(controls.sm.all_checks(['lateralTorqueParameters']), tick == 1)

    for vehicle in (*VEHICLES, HYUNDAI.KIA_EV6):
      with self.subTest(vehicle=vehicle), OpenpilotPrefix(), mock.patch.dict(os.environ, {**ENV, 'SIMULATION': '0'}), \
           mock.patch('openpilot.selfdrive.controls.controlsd.messaging.PubMaster'):
        params, cp = Params(), cp_for(vehicle)
        params.put('CarParams', cp.to_bytes(), block=True)
        controls = Controls()
        self.assertIsNone(controls.torque_host)
        feed_learning(controls)
        with mock.patch.object(controls.LaC, 'update_torque_parameters') as update:
          controls.state_control()
          self.assertEqual(update.call_count, 0 if vehicle in VEHICLES else 1)
          if vehicle in VEHICLES:
            select(params, cp, ControllerMode.STANDARD)
            controls.state_control()
            update.assert_not_called()
            self.assertEqual(controls.LaC.controller_mode, ControllerMode.STARPILOT)
            next_drive = Controls()
            self.assertTrue(next_drive.torque_learning_allowed)
            self.assertEqual(next_drive.LaC.controller_mode, ControllerMode.STANDARD)
            feed_learning(next_drive)
            with mock.patch.object(next_drive.LaC, 'update_torque_parameters') as standard_update:
              next_drive.state_control()
              standard_update.assert_called_once()
              invalid = learned_event(cp, now + 500_000_000).as_builder()
              invalid.valid = False
              next_drive.sm.update_msgs((now + 500_000_000) / 1e9, [invalid.as_reader()])
              self.assertFalse(next_drive.sm.all_checks(['lateralTorqueParameters']))
              next_drive.state_control()
              standard_update.assert_called_once()
              invalid.valid = True
              next_drive.sm.update_msgs((now + 750_000_000) / 1e9, [invalid.as_reader()])
              self.assertTrue(next_drive.sm.all_checks(['lateralTorqueParameters']))
              next_drive.sm.update_msgs((now + 4_000_000_000) / 1e9, [])
              self.assertFalse(next_drive.sm.all_checks(['lateralTorqueParameters']))
              next_drive.state_control()
              standard_update.assert_called_once()
            params.put_bool(LEARNING_OFF_KEY, True, block=True)
            disabled = Controls()
            self.assertFalse(disabled.torque_learning_allowed)
            feed_learning(disabled)
            with mock.patch.object(disabled.LaC, 'update_torque_parameters') as disabled_update:
              disabled.state_control()
              disabled_update.assert_not_called()

  def test_manual_factor_and_friction_do_not_inherit_learning_with_starpilot(self):
    with OpenpilotPrefix():
      params, cp = Params(), cp_for(HYUNDAI.HYUNDAI_IONIQ_6)
      params.put_bool('AdvancedLateralTune', True, block=True)
      params.put('SteerLatAccel', cp.lateralTuning.torque.latAccelFactor * 1.1, block=True)
      host = TorqueHost(params, cp, allow_learning=learning_allowed(params, cp))
      base = host.vehicle
      now = 1_000_000_000
      learned = LearnedFrame(now, factor=base.lat_accel_factor * 1.2, offset=0.03, friction=base.friction * 1.1)
      host.sample(learned, now_ns=now, lat_active=True)
      self.assertEqual(host.selected.source, TorqueSource.USER)
      self.assertAlmostEqual(host.selected.lat_accel_factor, base.lat_accel_factor * 1.1)
      self.assertEqual(host.selected.lat_accel_offset, base.lat_accel_offset)
      self.assertEqual(host.selected.friction, base.friction)
      params.remove('SteerLatAccel')
      params.put('SteerFriction', base.friction * 1.2, block=True)
      host.settings = read_settings(params, base)
      self.assertEqual(host._select(learned, now).lat_accel_factor, base.lat_accel_factor)
      self.assertAlmostEqual(host._select(learned, now).friction, base.friction * 1.2)
      select(params, cp, ControllerMode.STANDARD)
      self.assertFalse(host.allow_learning)
      self.assertEqual(host._select(learned, now).lat_accel_factor, base.lat_accel_factor)
      params.put_bool('AdvancedLateralTune', False, block=True)
      params.put_bool(LEARNING_OFF_KEY, True, block=True)
      host.settings = read_settings(params, base)
      self.assertTrue(host.settings.valid)
      self.assertAlmostEqual(host.settings.user_friction, base.friction * 1.2)
      self.assertEqual(host._select(learned, now).source, TorqueSource.USER)
      self.assertFalse(TorqueHost(params, cp, allow_learning=learning_allowed(params, cp)).allow_learning)

  def test_running_manual_host_latches_both_learning_directions_and_keeps_manual_edits(self):
    with OpenpilotPrefix(), mock.patch.dict(os.environ, ENV), \
         mock.patch('openpilot.selfdrive.controls.controlsd.messaging.PubMaster'):
      params, cp = Params(), cp_for(HYUNDAI.HYUNDAI_IONIQ_6)
      params.put('CarParams', cp.to_bytes(), block=True)
      params.put_bool('AdvancedLateralTune', True, block=True)
      select(params, cp, ControllerMode.STANDARD)
      controls = Controls()
      host, base = controls.torque_host, controls.torque_host.vehicle
      now = 1_000_000_000
      learned = LearnedFrame(now, factor=base.lat_accel_factor * 1.2, offset=0.03, friction=base.friction * 1.1)
      host.sample(learned, now_ns=now, lat_active=True)
      self.assertEqual(host.selected.source, TorqueSource.LEARNED)
      select(params, cp, ControllerMode.STARPILOT)
      params.put_bool(LEARNING_OFF_KEY, True, block=True)
      for tick in range(1, 102):
        stamp = now + tick * 10_000_000
        learned.logMonoTime['lateralTorqueParameters'] = stamp
        host.sample(learned, now_ns=stamp, lat_active=True)
      self.assertEqual(controls.LaC.controller_mode, ControllerMode.STANDARD)
      self.assertEqual(host.selected.source, TorqueSource.LEARNED)
      params.put('SteerLatAccel', base.lat_accel_factor * 1.1, block=True)
      host.last_refresh_ns = None
      host.sample(learned, now_ns=stamp + 10_000_000, lat_active=True)
      self.assertEqual(host.selected.source, TorqueSource.USER)
      self.assertAlmostEqual(host.selected.lat_accel_factor, base.lat_accel_factor * 1.1)
      self.assertEqual(host.selected.friction, learned.state.frictionCoefficientFiltered)

      next_drive = Controls()
      disabled = next_drive.torque_host
      self.assertFalse(disabled.allow_learning)
      select(params, cp, ControllerMode.STANDARD)
      params.put_bool(LEARNING_OFF_KEY, False, block=True)
      disabled.sample(learned, now_ns=stamp + 20_000_000, lat_active=True)
      self.assertEqual(next_drive.LaC.controller_mode, ControllerMode.STARPILOT)
      self.assertEqual(disabled.selected.source, TorqueSource.USER)
      self.assertEqual(disabled.selected.friction, base.friction)

  def test_unrelated_manual_host_preserves_master_off_behavior(self):
    with OpenpilotPrefix():
      params, cp = Params(), cp_for(TOYOTA.TOYOTA_RAV4_TSS2)
      host = TorqueHost(params, cp)
      now = 1_000_000_000
      learned = LearnedFrame(now, factor=host.vehicle.lat_accel_factor * 1.1,
                             offset=host.vehicle.lat_accel_offset, friction=host.vehicle.friction * 1.1)
      for raw, valid, force_off, source in (
        (b'0', True, False, TorqueSource.LEARNED),
        (b'1', True, True, TorqueSource.VEHICLE),
        (b'invalid', False, False, TorqueSource.VEHICLE),
      ):
        with self.subTest(raw=raw):
          Path(params.get_param_path(LEARNING_OFF_KEY)).write_bytes(raw)
          settings = read_settings(params, host.vehicle)
          self.assertEqual(settings.valid, valid)
          self.assertIsNone(settings.user_factor)
          self.assertIsNone(settings.user_friction)
          self.assertEqual(settings.force_auto_off, force_off)
          self.assertIsNone(host.allow_learning)
          host.settings = settings
          self.assertEqual(host._select(learned, now).source, source)



if __name__ == '__main__':
  unittest.main()
