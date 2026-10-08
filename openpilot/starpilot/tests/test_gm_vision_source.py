"""Camera sign selection remains separate from vehicle speed authority."""
from pathlib import Path
import unittest
from unittest.mock import Mock, patch

from openpilot.cereal import messaging
from openpilot.common.params import Params
from openpilot.common.prefix import OpenpilotPrefix
from openpilot.starpilot.feature_runtime import enabled, slc_runtime_settings, vision_control_enabled
from openpilot.starpilot.speed_limits.runtime import Action, Runtime
from openpilot.starpilot.speed_limits.tests.test_runtime_replay import ReplaySM
from openpilot.starpilot.speed_limits.vision.observation import MODEL_ID
from openpilot.starpilot.speed_limits.vision_gate import diagnostic_choice_enabled
from openpilot.starpilot.tests.test_gm_feature_runtime import LONG_CASES, STOCK_CASES, configured
from openpilot.starpilot.longitudinal.tests.test_cruise_ceiling import messages
from openpilot.starpilot.ui.feature_settings_owner import FeatureSettingsOwner
from openpilot.starpilot.ui.feature_settings_state import row_change
from opendbc.car.gm.tests.test_ascm_intercept import params as ordinary_params
from opendbc.car.gm.values import CAR, ORDINARY_ASCM_CAR, ORDINARY_SDGM_CAR


class TestGmVisionSource(unittest.TestCase):
  @staticmethod
  def requests(params, control):
    params.put_bool('SpeedLimitController', control, block=True)
    params.put_bool('ShowSpeedLimits', True, block=True)
    params.put('SLCPriority1', 'Vision', block=True)
    params.put('SLCPriority2', 'Dashboard', block=True)

  @staticmethod
  def bus():
    data, _ = messages()
    data['carState'].vCruise = data['carState'].vCruiseCluster = 100.0
    data['carState'].vEgoCluster = data['carState'].vEgo
    data['carState'].canValid = True
    data['carState'].canTimeout = False
    data['carControl'].longActive = True
    data['slcDashboardObservation'] = messaging.new_message('slcDashboardObservation').slcDashboardObservation
    msg = messaging.new_message('slcVisionObservation')
    evidence = msg.slcVisionObservation.init('vision')
    evidence.status = 'valid'
    evidence.producerSessionId = 'camera-a'
    evidence.modelId = MODEL_ID
    evidence.stream = 'road'
    evidence.speedMps = 55 * .44704
    evidence.confidence = .9
    evidence.supportCount = 2
    evidence.episode = 1
    evidence.frameId = 20
    evidence.observedMonoTime = 1_980_000_000
    evidence.validUntilMonoTime = 2_200_000_000
    evidence.cameraFrameEofBootTime = 5_950_000_000
    data['slcVisionObservation'] = msg.slcVisionObservation
    return ReplaySM(data, 2_000_000_000)

  def test_finalized_gm_source_startup_and_control_are_separate(self):
    with OpenpilotPrefix():
      params = Params()
      self.requests(params, True)
      cases = [(configured(params, identity, **kwargs), True) for identity, kwargs in LONG_CASES]
      cases += [(configured(params, identity, **kwargs), False) for identity, kwargs in STOCK_CASES]
      for identity in ORDINARY_ASCM_CAR | ORDINARY_SDGM_CAR:
        cases.extend((ordinary_params(identity, sascm=True, alpha=alpha), alpha) for alpha in (False, True))
      for cp, control in cases:
        with self.subTest(identity=cp.carFingerprint, word=cp.safetyConfigs[0].safetyParam):
          self.assertTrue(enabled(params, cp, 'vision', {}))
          self.assertTrue(diagnostic_choice_enabled({}, cp))
          self.assertEqual(vision_control_enabled(params, cp), control)
          for field in ('passive', 'dashcamOnly', 'notCar'):
            bad = cp.as_reader().as_builder()
            setattr(bad, field, True)
            self.assertFalse(enabled(params, bad, 'vision', {}))
            self.assertFalse(vision_control_enabled(params, bad))
      self.requests(params, False)
      self.assertTrue(enabled(params, cases[0][0], 'vision', {}))
      self.assertFalse(vision_control_enabled(params, cases[0][0]))
      params.put_bool('ShowSpeedLimits', False, block=True)
      self.assertFalse(enabled(params, cases[0][0], 'vision', {}))
      Path(params.get_param_path('SLCPriority1')).write_bytes(b'invalid')
      self.assertFalse(vision_control_enabled(params, cases[0][0]))

  def test_visible_camera_sign_cannot_control_stock_or_display_only_sessions(self):
    with OpenpilotPrefix():
      params = Params()
      for disable, control in ((True, True), (False, False)):
        self.requests(params, control)
        cp = configured(params, CAR.CHEVROLET_VOLT_CC, disable=disable)
        sm = self.bus()
        runtime = Runtime(slc_runtime_settings(params, cp, {}), vision_enabled=True,
                          vision_control_qualified=vision_control_enabled(params, cp),
                          vision_display_qualified=enabled(params, cp, 'vision', {}))
        output = runtime.step(sm, cp, now_ns=2_000_000_000, now_boot_ns=6_000_000_000)
        state = output.message.slcState
        self.assertEqual(state.source, 'vision')
        self.assertAlmostEqual(state.speedLimit, 55 * .44704, places=4)
        self.assertTrue(state.displayOnly)
        self.assertFalse(state.hasPending)
        self.assertFalse(state.hasCeiling)
        self.assertIsNone(output.result.ceiling)
        self.assertIsNone(output.command)
        self.assertEqual(state.sourceProducerSessionId, 'camera-a')
        sm.advance(2_300_000_000)
        stale = runtime.step(sm, cp, now_ns=2_300_000_000, now_boot_ns=6_300_000_000)
        self.assertNotEqual(stale.message.slcState.observationKind, 'valid')
        self.assertFalse(stale.message.slcState.hasCeiling)

  def test_gm_control_requires_current_sign_confirmation_and_axis_authority(self):
    with OpenpilotPrefix():
      params = Params()
      self.requests(params, True)
      cp = configured(params, CAR.CHEVROLET_VOLT_CC)
      sm = self.bus()
      runtime = Runtime(slc_runtime_settings(params, cp, {}), session_id='drive', vision_enabled=True,
                        vision_control_qualified=vision_control_enabled(params, cp))
      first = runtime.step(sm, cp, now_ns=2_000_000_000, now_boot_ns=6_000_000_000)
      self.assertTrue(first.message.slcState.hasPending)
      self.assertFalse(first.message.slcState.hasCeiling)
      sm.advance(2_020_000_000)
      accepted = runtime.step(sm, cp, now_ns=2_020_000_000, now_boot_ns=6_020_000_000,
                              request=Action('drive', 1, first.message.slcState.decisionId,
                                             first.message.slcState.presentationId, 'accept'))
      self.assertTrue(accepted.message.slcState.hasCeiling)
      sm.data['carControl'].longActive = False
      sm.advance(2_040_000_000)
      inactive = runtime.step(sm, cp, now_ns=2_040_000_000, now_boot_ns=6_040_000_000)
      self.assertFalse(inactive.message.slcState.hasCeiling)
      self.assertIsNone(inactive.command)

  def test_actual_planner_and_manager_start_display_producer(self):
    from openpilot.selfdrive.controls import plannerd
    from openpilot.system.manager.process_config import vision_slc_development
    class EndLoop(Exception):
      pass
    with OpenpilotPrefix():
      params = Params()
      self.requests(params, False)
      cp = configured(params, CAR.CHEVROLET_VOLT_CC, disable=True)
      params.put('CarParams', cp.to_bytes(), block=True)
      with patch.dict('os.environ', {}, clear=True):
        self.assertTrue(vision_slc_development(True, params, cp))
        self.assertFalse(vision_slc_development(False, params, cp))
        sm = Mock()
        sm.update.side_effect = EndLoop
        with (patch.object(plannerd, 'Params', return_value=params),
              patch.object(plannerd, 'config_realtime_process'),
              patch.object(plannerd, 'SlcRuntime', wraps=plannerd.SlcRuntime) as runtime,
              patch.object(plannerd.messaging, 'sub_sock'),
              patch.object(plannerd.messaging, 'SubMaster', return_value=sm),
              patch.object(plannerd.messaging, 'PubMaster')):
          with self.assertRaises(EndLoop):
            plannerd.main()
          self.assertTrue(runtime.call_args.kwargs['vision_enabled'])
          self.assertTrue(runtime.call_args.kwargs['vision_display_qualified'])
          self.assertFalse(runtime.call_args.kwargs['vision_control_qualified'])

  def test_stock_ui_can_select_display_source_with_stale_request_guard(self):
    with OpenpilotPrefix():
      params = Params()
      params.put('SLCPriority1', 'Dashboard', block=True)
      cp = configured(params, CAR.CHEVROLET_VOLT_CC, disable=True)
      owner = FeatureSettingsOwner(params, authority=lambda group: group == 'preferences',
                                   vehicle_fingerprint=lambda: cp.carFingerprint, vehicle_params=lambda: cp,
                                   vision_development=lambda: diagnostic_choice_enabled({}, cp))
      state = owner.snapshot('slc', parked=True, system_long=False, lateral_context=True, metric=False)
      row = next(row for row in state.rows if row.key == 'SLCPriority1')
      self.assertTrue(row.available)
      self.assertIn('factory cruise', row.reason)
      request = row_change(row)
      assert request is not None
      self.assertTrue(owner.apply(request))
      self.assertEqual(params.get('SLCPriority1'), 'Vision')
      self.assertFalse(owner.apply(request))
