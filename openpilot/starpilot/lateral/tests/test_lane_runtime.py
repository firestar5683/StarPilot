"""Saved preferences reach actual Controls only with fresh lateral authority."""

import os
import tempfile
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest import mock

from openpilot.cereal import messaging
from openpilot.common.params import Params
from openpilot.common.prefix import OpenpilotPrefix
from openpilot.selfdrive.controls.controlsd import Controls
from openpilot.starpilot.lateral.lane_centering import ControlMode
from openpilot.starpilot.lateral.lane_runtime import LaneCenteringHost, read_settings, runtime_supported
from openpilot.starpilot.lateral.tests.test_lane_centering import model
from openpilot.starpilot.aol.wire import SafetyState, encode_safety
from opendbc.car import gen_empty_fingerprint
from opendbc.car.car_helpers import interfaces
from opendbc.car.honda.interface import CarInterface as HondaCarInterface
from opendbc.car.honda.values import CAR as HondaCAR
from opendbc.car.hyundai.interface import CarInterface as HyundaiCarInterface
from opendbc.car.hyundai.ioniq6_handoff import build_ioniq6_hda2_long_candidate
from opendbc.car.hyundai.values import CAR as HyundaiCAR
from opendbc.car.structs import car
from opendbc.car.toyota.values import CAR


def ioniq_candidate(*, alternate=False):
  fingerprint = gen_empty_fingerprint()
  fingerprint[2].update({0x110: 32, 0x362: 32} if alternate else {0x50: 16, 0x2A4: 24})
  fingerprint[1].update({0x1CF: 8, 0x35: 32, 0x175: 24, 0xA0: 24, 0xEA: 24,
                         0x1BA: 24, 0x1E5: 16, 0x36A: 16})
  fingerprint[0][0x3A5] = 24
  fingerprint[0][0x100] = 24
  stock = HyundaiCarInterface.get_params(HyundaiCAR.HYUNDAI_IONIQ_6, fingerprint, [], False, False, False)
  return stock, build_ioniq6_hda2_long_candidate(stock, fingerprint)


class Frame:
  def __init__(self, now_ns):
    self.logMonoTime = dict.fromkeys(LaneCenteringHost.REQUIRED, now_ns)
    self.checked = True
    self.state = SimpleNamespace(canValid=True, canTimeout=False)

  def all_checks(self, _services):
    return self.checked

  def __getitem__(self, _service):
    return self.state


def feed(controls, timestamp, tick, *, active=True, enabled=True, fault=False, override=False, signal=False, model_age=0,
         can_valid=True, can_timeout=False, aol_lat_only=False, native_session='lane-aol-session'):
  events = []

  def msg(service, size=None):
    event = messaging.new_message(service, size, valid=True, logMonoTime=timestamp)
    events.append(event)
    return getattr(event, service)

  cs = msg('carState')
  cs.vEgo = cs.vEgoRaw = 20.0
  cs.vCruise = cs.vCruiseCluster = 100.0
  cs.canValid = can_valid
  cs.canTimeout = can_timeout
  cs.steerFaultTemporary = fault
  cs.steeringPressed = override
  cs.leftBlinker = signal
  state = msg('selfdriveState')
  state.active, state.enabled = active, enabled
  state.state = 'enabled' if enabled else 'disabled'
  if tick % 5 == 0:
    lp = msg('vehicleParameters')
    lp.stiffnessFactor, lp.steerRatio = 1.0, controls.CP.steerRatio
  msg('longitudinalPlan').aTarget = 0.5
  msg('lateralDelay').lateralDelay = 0.1
  msg('onroadEvents', 0)
  if tick % 5 == 0:
    event = messaging.new_message('modelV2', valid=True, logMonoTime=timestamp - model_age)
    event.modelV2 = model()
    event.modelV2.action.desiredCurvature = 0.0002
    events.append(event)
  if aol_lat_only:
    axis = msg('aolAxisState')
    axis.qualified = axis.nativeAcknowledged = axis.desiredLateral = axis.lateralActive = True
    axis.desiredLongitudinal = axis.longitudinalActive = False
    axis.sessionId = 'lane-aol-session'
    axis.observedMonoTime = timestamp
    axis.validUntilMonoTime = timestamp + 30_000_000
    msg('aolSafetyWire', 0)
    events[-1].aolSafetyWire = encode_safety(SafetyState(
      1, True, timestamp, timestamp + 200_000_000, int(car.CarParams.SafetyModel.hondaBosch),
      controls.CP.safetyConfigs[-1].safetyParam, True, False, True, False,
      'lane-test-panda', native_session))
  controls.sm.update_msgs(timestamp / 1e9, [event.as_reader() for event in events])


class LaneRuntimeTests(unittest.TestCase):
  def test_strength_saved_values_and_live_refresh_keep_existing_admission(self):
    with tempfile.TemporaryDirectory() as temporary:
      root = Path(temporary)
      params = SimpleNamespace(get_param_path=lambda key: str(root / key))
      (root / 'LaneCentering').write_bytes(b'1')
      self.assertEqual(read_settings(params).strength, 1.0)
      host = LaneCenteringHost(params)
      now = 10_000_000_000
      first = host.sample(Frame(now), now_ns=now, lateral_active=True, longitudinal_active=False)
      self.assertEqual(first.settings.strength, 1.0)
      (root / 'LaneCenteringStrength').write_bytes(b'1.5')
      now += host.REFRESH_NS
      updated = host.sample(Frame(now), now_ns=now, lateral_active=True, longitudinal_active=False)
      self.assertEqual(updated.settings.strength, 1.5)
      self.assertTrue(updated.time_discontinuity)
      for invalid in (b'nan', b'0.49', b'1.51', b'true'):
        (root / 'LaneCenteringStrength').write_bytes(invalid)
        self.assertFalse(read_settings(params).enabled)
        now += host.REFRESH_NS
        self.assertIsNone(host.sample(Frame(now), now_ns=now, lateral_active=True, longitudinal_active=False))


  def test_normal_reader_admission_keeps_exact_vehicle_and_saved_preference_gates(self):
    with OpenpilotPrefix(), mock.patch.dict(os.environ, {'LANE_CENTERING_REPLAY_RUNTIME': '0'}):
      params = Params()
      for alternate in (False, True):
        with self.subTest(alternate=alternate):
          stock, tagged = ioniq_candidate(alternate=alternate)
          self.assertFalse(runtime_supported(stock))
          self.assertTrue(runtime_supported(tagged))
          self.assertFalse(read_settings(params).enabled)
          params.put_bool('LaneCentering', True, block=True)
          self.assertTrue(read_settings(params).enabled)
          self.assertFalse(runtime_supported(interfaces[CAR.TOYOTA_COROLLA_TSS2].get_non_essential_params(CAR.TOYOTA_COROLLA_TSS2)))
          tagged.safetyConfigs[0].safetyParam = 0
          self.assertFalse(runtime_supported(tagged))
          params.put_bool('LaneCentering', False, block=True)
      _, tagged = ioniq_candidate()
      params.put_bool('LaneCentering', True, block=True)
      Path(params.get_param_path('LaneCenterOffset')).write_bytes(b'nan')
      self.assertFalse(read_settings(params).enabled)
      with mock.patch.dict(os.environ, {'LANE_CENTERING_REPLAY_RUNTIME': '1'}):
        self.assertTrue(runtime_supported(tagged))

  def test_actual_tagged_ioniq_saved_host_uses_fresh_lateral_authority(self):
    with OpenpilotPrefix(), mock.patch.dict(os.environ, {'LANE_CENTERING_REPLAY_RUNTIME': '0', 'REPLAY': '1',
                                                         'AOL_REPLAY_RUNTIME': '0'}), \
         mock.patch('openpilot.selfdrive.controls.controlsd.messaging.PubMaster'):
      params = Params()
      stock, tagged = ioniq_candidate()
      params.put('LaneCenteringE2EAuthority', 0.0, block=True)
      params.put('CarParams', tagged.to_bytes(), block=True)
      disabled = Controls()
      self.assertIsNotNone(disabled.lane_centering_host)
      frame = Frame(1_000_000_000)
      self.assertIsNone(disabled.lane_centering_host.sample(frame, now_ns=1_000_000_000,
                                                         lateral_active=True, longitudinal_active=False))
      params.put_bool('LaneCentering', True, block=True)
      controls = disabled
      self.assertIsNotNone(controls.lane_centering_host)
      for tick in range(35):
        now = 2_000_000_000 + tick * 10_000_000
        feed(controls, now, tick)
        command, _ = controls.state_control()
        self.assertTrue(command.latActive)
      self.assertIsNotNone(controls.last_lane_centering_result)
      self.assertGreater(controls.last_lane_centering_result.correction, 0.0)
      feed(controls, now + 10_000_000, 35, model_age=200_000_000)
      controls.state_control()
      self.assertIsNone(controls.last_lane_centering_result)
      params.put_bool('LaneCentering', False, block=True)
      feed(controls, 3_000_000_000, 36)
      controls.state_control()
      self.assertIsNone(controls.last_lane_centering_result)
      self.assertEqual(controls.lane_centering_applied, 0.0)
      params.put('CarParams', stock.to_bytes(), block=True)
      self.assertIsNone(Controls().lane_centering_host)

  def test_tagged_ioniq_four_axes_and_stale_reset(self):
    with OpenpilotPrefix(), mock.patch.dict(os.environ, {'LANE_CENTERING_REPLAY_RUNTIME': '0', 'REPLAY': '1',
                                                         'AOL_REPLAY_RUNTIME': '0'}), \
         mock.patch('openpilot.selfdrive.controls.controlsd.messaging.PubMaster'):
      params = Params()
      _, tagged = ioniq_candidate()
      params.put('CarParams', tagged.to_bytes(), block=True)
      params.put_bool('LaneCentering', True, block=True)
      params.put('LaneCenteringE2EAuthority', 0.0, block=True)
      controls = Controls()
      self.assertIsNotNone(controls.lane_centering_host)
      # Inject already-qualified independent-axis results at the consumer seam;
      # AOL's native/session checks are covered by its own wire tests.
      controls.aol_replay = True
      tick = 0
      for lat, lon in ((True, True), (True, False), (False, True), (False, False)):
        with self.subTest(lat=lat, lon=lon), \
             mock.patch('openpilot.selfdrive.controls.controlsd.current_axis', return_value=SimpleNamespace(
               sessionId='test-session', nativeAcknowledged=True, lateralActive=lat, desiredLateral=lat,
               longitudinalActive=lon, desiredLongitudinal=lon)), \
             mock.patch('openpilot.selfdrive.controls.controlsd.current_native', return_value=SimpleNamespace(
               requestedLateral=lat, lateralAllowed=lat, requestedLongitudinal=lon, longitudinalAllowed=lon)):
          for _ in range(10):
            now = 1_000_000_000 + tick * 10_000_000
            feed(controls, now, tick, active=lat, enabled=lon)
            command, _ = controls.state_control()
            tick += 1
          self.assertEqual((command.latActive, command.longActive), (lat, lon))
          self.assertIsNotNone(controls.last_lane_centering_result)
          self.assertEqual(controls.last_lane_centering_result.correction > 0.0, lat)
      with mock.patch('openpilot.selfdrive.controls.controlsd.current_axis', return_value=SimpleNamespace(
             sessionId='test-session', nativeAcknowledged=True, lateralActive=True, desiredLateral=True,
             longitudinalActive=False, desiredLongitudinal=False)), \
           mock.patch('openpilot.selfdrive.controls.controlsd.current_native', return_value=SimpleNamespace(
             requestedLateral=True, lateralAllowed=True, requestedLongitudinal=False, longitudinalAllowed=False)):
        now = 1_000_000_000 + tick * 10_000_000
        feed(controls, now, tick, active=False, enabled=False, model_age=200_000_000)
        command, _ = controls.state_control()
        self.assertTrue(command.latActive)
        self.assertFalse(command.longActive)
        self.assertIsNone(controls.last_lane_centering_result)
        for recovery_tick in range(tick + 1, tick + 6):
          now = 1_000_000_000 + recovery_tick * 10_000_000
          feed(controls, now, recovery_tick, active=False, enabled=False)
          controls.state_control()
        self.assertGreater(controls.last_lane_centering_result.correction, 0.0)

  def test_saved_settings_bounds_and_corruption(self):
    with OpenpilotPrefix():
      params = Params()
      self.assertFalse(read_settings(params).enabled)
      self.assertTrue(read_settings(params).pause_on_signal)
      params.put_bool('LaneCentering', True, block=True)
      params.put('LaneCenterOffset', -0.2, block=True)
      params.put('LaneCenteringE2EAuthority', 0.5, block=True)
      settings = read_settings(params)
      self.assertEqual((settings.enabled, settings.offset_m, settings.e2e_authority), (True, -0.2, 0.5))
      for key, values in (('LaneCenterOffset', (b'bad', b'nan', b'inf', b'0.31')),
                          ('LaneCenteringE2EAuthority', (b'', b'1.01', b'-0.1')),
                          ('LaneCenteringPauseOnSignal', (b'false', b'2'))):
        path = Path(params.get_param_path(key))
        original = path.read_bytes() if path.exists() else None
        for value in values:
          with self.subTest(key=key, value=value):
            path.write_bytes(value)
            self.assertFalse(read_settings(params).enabled)
            self.assertTrue(params.get_bool('LaneCentering'))
        if original is None:
          path.unlink()
        else:
          path.write_bytes(original)

  def test_authority_is_derived_from_actual_axes(self):
    with OpenpilotPrefix():
      params = Params()
      params.put_bool('LaneCentering', True, block=True)
      host = LaneCenteringHost(params)
      for tick, (lat, lon, mode) in enumerate(((False, False, ControlMode.OFF), (False, True, ControlMode.LONGITUDINAL_ONLY),
                                             (True, False, ControlMode.LATERAL_ONLY), (True, True, ControlMode.COMBINED))):
        now = 1_000_000_000 + tick * 10_000_000
        request = host.sample(Frame(now), now_ns=now, lateral_active=lat, longitudinal_active=lon)
        self.assertIsNotNone(request)
        self.assertEqual(request.mode, mode)

  def test_stale_future_invalid_input_and_clock_gap(self):
    with OpenpilotPrefix():
      params = Params()
      params.put_bool('LaneCentering', True, block=True)
      host = LaneCenteringHost(params)
      now = 1_000_000_000
      def sample(frame, at=now):
        return host.sample(frame, now_ns=at, lateral_active=True, longitudinal_active=True)
      self.assertIsNotNone(sample(Frame(now)))
      for service in host.REQUIRED:
        for age in (200_000_000, -1):
          frame = Frame(now)
          frame.logMonoTime[service] = now - age
          self.assertIsNone(sample(frame))
      frame = Frame(now)
      frame.checked = False
      self.assertIsNone(sample(frame))
      frame.checked, frame.state.canValid = True, False
      self.assertIsNone(sample(frame))
      frame.state.canValid, frame.state.canTimeout = True, True
      self.assertIsNone(sample(frame))
      frame.state.canTimeout = False
      frame.logMonoTime['modelV2'] = 0
      self.assertIsNone(sample(frame))
      self.assertIsNone(sample(Frame(0), 0))
      gap = sample(Frame(now + 100_000_000), now + 100_000_000)
      self.assertTrue(gap.time_discontinuity)
      self.assertFalse(sample(Frame(now + 110_000_000), now + 110_000_000).time_discontinuity)
      self.assertTrue(sample(Frame(now), now).time_discontinuity)

  def test_live_settings_refresh_and_corrupt_setting_disables(self):
    with OpenpilotPrefix():
      params = Params()
      params.put_bool('LaneCentering', True, block=True)
      host = LaneCenteringHost(params)
      for now in (1_000_000_000, 1_010_000_000):
        self.assertIsNotNone(host.sample(Frame(now), now_ns=now, lateral_active=True, longitudinal_active=False))
      Path(params.get_param_path('LaneCenterOffset')).write_bytes(b'bad')
      now = 2_000_000_000
      self.assertIsNone(host.sample(Frame(now), now_ns=now, lateral_active=True, longitudinal_active=False))
      self.assertTrue(params.get_bool('LaneCentering'))

  def test_actual_controls_saved_settings_and_permission_gates(self):
    scenarios = ('normal', 'disabled_setting', 'off', 'long_only', 'fault', 'override', 'signal', 'stale', 'invalid_can', 'can_timeout')
    with OpenpilotPrefix(), mock.patch.dict(os.environ, {'AOL_REPLAY_RUNTIME': '0', 'REPLAY': '1'}), \
         mock.patch('openpilot.selfdrive.controls.controlsd.messaging.PubMaster'):
      params = Params()
      cp = interfaces[CAR.TOYOTA_COROLLA_TSS2].get_non_essential_params(CAR.TOYOTA_COROLLA_TSS2)
      params.put('CarParams', cp.to_bytes(), block=True)
      for scenario in scenarios:
        with self.subTest(scenario=scenario):
          params.put_bool('LaneCentering', scenario != 'disabled_setting', block=True)
          params.put('LaneCenteringE2EAuthority', 0.0, block=True)
          with mock.patch.dict(os.environ, {'LANE_CENTERING_REPLAY_RUNTIME': '0'}):
            baseline = Controls()
          with mock.patch.dict(os.environ, {'LANE_CENTERING_REPLAY_RUNTIME': '1'}):
            candidate = Controls()
          self.assertIsNone(baseline.lane_centering_host)
          previous = 0.0
          for tick in range(120):
            now = 1_000_000_000 + tick * 10_000_000
            phase = scenario if tick >= 80 else 'normal'
            options = {'active': phase not in ('off', 'long_only'), 'enabled': phase != 'off',
                       'fault': phase == 'fault', 'override': phase == 'override', 'signal': phase == 'signal',
                       'model_age': 200_000_000 if phase == 'stale' else tick % 5 * 10_000_000,
                       'can_valid': phase != 'invalid_can', 'can_timeout': phase == 'can_timeout'}
            for controls in (baseline, candidate):
              feed(controls, now, tick, **options)
            reference, _ = baseline.state_control()
            command, _ = candidate.state_control()
            result = candidate.last_lane_centering_result
            self.assertEqual(command.latActive, reference.latActive)
            self.assertEqual(command.longActive, reference.longActive)
            self.assertEqual(command.actuators.accel, reference.actuators.accel)
            if scenario == 'disabled_setting':
              self.assertEqual(command.to_dict(), reference.to_dict())
            elif phase in ('off', 'long_only', 'fault', 'override'):
              self.assertEqual(result.correction, 0.0)
            elif phase in ('stale', 'invalid_can', 'can_timeout'):
              self.assertIsNone(result)
            elif phase == 'signal':
              self.assertLess(result.correction, previous)
            elif tick >= 20:
              self.assertGreater(result.correction, previous)
            previous = result.correction if result is not None else 0.0

  def test_actual_aol_lateral_only_controls_without_longitudinal(self):
    with OpenpilotPrefix(), mock.patch.dict(os.environ, {'AOL_REPLAY_RUNTIME': '1', 'LANE_CENTERING_REPLAY_RUNTIME': '1',
                                                         'REPLAY': '1'}), \
         mock.patch('openpilot.selfdrive.controls.controlsd.messaging.PubMaster'):
      params = Params()
      params.put_bool('LaneCentering', True, block=True)
      cp = HondaCarInterface.get_params(HondaCAR.HONDA_CIVIC_BOSCH, gen_empty_fingerprint(), [], True, False, False)
      cp.safetyConfigs[-1].safetyParam |= 0x20  # Card's qualified AOL bit in serialized CarParams.
      params.put('CarParams', cp.to_bytes(), block=True)
      controls = Controls()
      self.assertTrue(controls.aol_replay)
      self.assertIsNotNone(controls.lane_centering_host)
      for tick in range(40):
        now = 1_000_000_000 + tick * 10_000_000
        feed(controls, now, tick, active=False, enabled=False, aol_lat_only=True)
        command, _ = controls.state_control()
        self.assertFalse(command.enabled)
        self.assertTrue(command.latActive)
        self.assertFalse(command.longActive)
        self.assertEqual(command.actuators.accel, 0.0)
      assert controls.last_lane_centering_result is not None
      self.assertGreater(controls.last_lane_centering_result.correction, 0.0)
      previous = controls.last_lane_centering_result.correction
      now += 10_000_000
      feed(controls, now, 40, active=False, enabled=False, aol_lat_only=True, native_session='old-drive')
      command, _ = controls.state_control()
      self.assertFalse(command.latActive or command.longActive)
      self.assertEqual(controls.last_lane_centering_result.correction, 0.0)
      now += 10_000_000
      feed(controls, now, 41, active=False, enabled=False, aol_lat_only=True)
      command, _ = controls.state_control()
      self.assertTrue(command.latActive)
      self.assertFalse(command.longActive)
      self.assertLess(controls.last_lane_centering_result.correction, previous)
      for tick in range(42, 48):
        now += 10_000_000
        feed(controls, now, tick, active=False, enabled=False)
        command, _ = controls.state_control()
      self.assertFalse(command.latActive or command.longActive)
      self.assertEqual(controls.last_lane_centering_result.correction, 0.0)

  def test_stock_acc_lateral_stays_separate_from_aol(self):
    with OpenpilotPrefix(), mock.patch.dict(os.environ, {'AOL_REPLAY_RUNTIME': '0', 'LANE_CENTERING_REPLAY_RUNTIME': '1',
                                                         'REPLAY': '1'}), \
         mock.patch('openpilot.selfdrive.controls.controlsd.messaging.PubMaster'):
      params = Params()
      params.put_bool('LaneCentering', True, block=True)
      cp = interfaces[CAR.TOYOTA_COROLLA_TSS2].get_non_essential_params(CAR.TOYOTA_COROLLA_TSS2)
      cp.openpilotLongitudinalControl = False
      cp.pcmCruise = True
      params.put('CarParams', cp.to_bytes(), block=True)
      controls = Controls()
      self.assertFalse(controls.aol_replay)
      for tick in range(40):
        now = 1_000_000_000 + tick * 10_000_000
        feed(controls, now, tick)
        command, _ = controls.state_control()
        self.assertTrue(command.latActive)
        self.assertFalse(command.longActive)
      assert controls.last_lane_centering_result is not None
      self.assertGreater(controls.last_lane_centering_result.correction, 0.0)
