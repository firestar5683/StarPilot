"""Honda AOL host qualification and serialized integration tests."""

import time
import unittest
from unittest import mock

from openpilot.cereal import log, messaging
from openpilot.common.prefix import OpenpilotPrefix
from opendbc.car.structs import car
from opendbc.car import gen_empty_fingerprint
from opendbc.car.interfaces import RadarInterfaceBase
from opendbc.car.honda.interface import CarInterface
from opendbc.car.honda.values import CAR, CarControllerParams, HondaFlags
from openpilot.common.params import Params
from openpilot.selfdrive.car.card import Car
from openpilot.selfdrive.selfdrived.selfdrived import SelfdriveD
from openpilot.selfdrive.controls.controlsd import Controls
from openpilot.starpilot.aol.intent import read_settings
from openpilot.starpilot.aol.wire import SafetyState, decode_intent, encode_safety
from openpilot.starpilot.car.honda.aol import CLASSIC_BOSCH_AOL_CARS, qualified_honda


def car_state(*, brake=False):
  return car.CarState(canValid=True, gearShifter=car.CarState.GearShifter.drive,
                      vEgo=20.0, brakePressed=brake)


class HondaFamilyQualificationTests(unittest.TestCase):
  def setUp(self):
    # Some upstream interfaces set this shared table while constructing CP.
    self.addCleanup(setattr, CarControllerParams, 'BOSCH_GAS_LOOKUP_V', list(CarControllerParams.BOSCH_GAS_LOOKUP_V))

  def test_exact_classic_bosch_cp_family_and_rejections(self):
    self.assertEqual(len(CLASSIC_BOSCH_AOL_CARS), 10)
    all_honda = tuple(candidate for candidate in CAR if candidate.config.flags & HondaFlags.BOSCH)
    for candidate in all_honda:
      with self.subTest(candidate=candidate):
        cp = CarInterface.get_params(candidate, gen_empty_fingerprint(), [], True, False, False)
        self.assertEqual(qualified_honda(cp), candidate in CLASSIC_BOSCH_AOL_CARS)
        if candidate in CLASSIC_BOSCH_AOL_CARS:
          self.assertEqual(cp.brand, 'honda')
          self.assertTrue(cp.openpilotLongitudinalControl)
          self.assertFalse(cp.pcmCruise)
          self.assertEqual(len(cp.safetyConfigs), 1)
          self.assertIn(cp.safetyConfigs[0].safetyParam, (2, 3, 131))
          cp.safetyConfigs[0].safetyParam |= 32
          self.assertTrue(qualified_honda(cp))
          cp.safetyConfigs[0].safetyParam |= 4
          self.assertFalse(qualified_honda(cp))

    for candidate in CLASSIC_BOSCH_AOL_CARS:
      with self.subTest(stock=candidate):
        cp = CarInterface.get_params(candidate, gen_empty_fingerprint(), [], False, False, False)
        self.assertFalse(qualified_honda(cp))

    cp = CarInterface.get_params(CAR.HONDA_ACCORD, gen_empty_fingerprint(), [], True, False, False)
    cp.passive = True
    self.assertFalse(qualified_honda(cp))
    cp.passive = False
    cp.dashcamOnly = True
    self.assertFalse(qualified_honda(cp))
    cp.dashcamOnly = False
    cp.brand = 'other'
    self.assertFalse(qualified_honda(cp))
    cp.brand = 'honda'
    cp.notCar = True
    self.assertFalse(qualified_honda(cp))
    cp.notCar = False
    cp.flags |= int(HondaFlags.BOSCH_ALT_RADAR)
    self.assertFalse(qualified_honda(cp))
    cp.flags &= ~int(HondaFlags.BOSCH_ALT_RADAR)
    cp.safetyConfigs[0].safetyModel = car.CarParams.SafetyModel.hondaNidec
    self.assertFalse(qualified_honda(cp))
    cp.safetyConfigs[0].safetyModel = car.CarParams.SafetyModel.hondaBosch
    cp.safetyConfigs = [car.CarParams.SafetyConfig(safetyModel=car.CarParams.SafetyModel.hondaBosch, safetyParam=2),
                        car.CarParams.SafetyConfig(safetyModel=car.CarParams.SafetyModel.noOutput, safetyParam=0)]
    self.assertFalse(qualified_honda(cp))

  def test_card_serializes_opt_in_only_for_actual_eligible_cp(self):
    class FakeHonda:
      CC = object()
      CS = object()

      def __init__(self, candidate, alpha_long):
        self.CP = CarInterface.get_params(candidate, gen_empty_fingerprint(), [], alpha_long, False, False)

      def init(self, _cp, _recv, _send):
        pass

    class FakeRadar(RadarInterfaceBase):
      def update(self, can_packets):
        return None

    for candidate in sorted(CLASSIC_BOSCH_AOL_CARS, key=str):
      for alpha_long in (False, True):
        with self.subTest(candidate=candidate, alpha_long=alpha_long), OpenpilotPrefix(), \
             mock.patch.dict('os.environ', {'AOL_REPLAY_RUNTIME': '1', 'SIMULATION': '1'}):
          messaging.reset_context()
          params = Params()
          params.put_bool('OpenpilotEnabledToggle', True, block=True)
          params.put_bool('AlwaysOnLateral', True, block=True)
          honda = FakeHonda(candidate, alpha_long)
          card = Car(honda, FakeRadar(honda.CP))
          expected = alpha_long or candidate != CAR.HONDA_ACCORD
          self.assertEqual(card.aol_qualified, expected)
          self.assertEqual(bool(card.CP.safetyConfigs[0].safetyParam & 32), alpha_long)
          experience = 32 if expected and not alpha_long else 0
          self.assertEqual(card.CP.alternativeExperience, experience)
          with car.CarParams.from_bytes(params.get('CarParams')) as published:
            self.assertEqual(bool(published.safetyConfigs[0].safetyParam & 32), alpha_long)
            self.assertEqual(published.alternativeExperience, experience)


class HondaHostTests(unittest.TestCase):
  def test_real_car_params_selfdrive_controls_chain_fails_closed(self):
    class FakeHonda:
      CC = object()
      CS = object()

      def __init__(self):
        self.CP = CarInterface.get_params(CAR.HONDA_CIVIC_BOSCH, gen_empty_fingerprint(), [], True, False, False)

      def update(self, _can):
        state = car_state()
        state.cruiseState.available = True
        return state

      def init(self, _cp, _recv, _send):
        pass

      def apply(self, _control, _now_ns):
        return car.CarControl.Actuators(), []

    class FakeRadar(RadarInterfaceBase):
      def update(self, can_packets):
        return None

    with OpenpilotPrefix(), mock.patch.dict('os.environ', {'AOL_REPLAY_RUNTIME': '1', 'SIMULATION': '1'}):
      messaging.reset_context()
      params = Params()
      params.put_bool('OpenpilotEnabledToggle', True, block=True)
      params.put_bool('AlwaysOnLateral', True, block=True)
      honda = FakeHonda()
      card = Car(honda, FakeRadar(honda.CP))
      self.assertEqual(card.CP.safetyConfigs[-1].safetyParam & 0x20, 0x20)
      with car.CarParams.from_bytes(params.get('CarParams')) as published:
        self.assertEqual(published.safetyConfigs[-1].safetyParam & 0x20, 0x20)
      selfdrive = SelfdriveD()  # reads the actual card-published CarParams
      controls = Controls()    # reads the same serialized CarParams
      self.assertTrue(selfdrive.aol_replay and controls.aol_replay)
      can = messaging.PubMaster(['can'])
      intent = messaging.SubMaster(['aolIntentWire'])
      can.send('can', messaging.new_message('can', 1))
      card.step()
      intent.update(100)
      self.assertTrue(intent.seen['aolIntentWire'])
      self.assertTrue(decode_intent(intent['aolIntentWire']).allowedLatch)
      selfdrive.step()
      controls.sm.update(100)
      cc, _ = controls.state_control()
      self.assertFalse(cc.latActive or cc.longActive)  # no native capability/ack
      self.assertEqual(selfdrive.aol_axis_decision.mode, 'off')

      source = messaging.PubMaster(['aolSafetyWire', 'modelV2', 'extrinsicsCalibration', 'driverMonitoringState'])
      time.sleep(0.05)  # allow native IPC subscriptions to connect before the first publication
      model = messaging.new_message('modelV2')
      model.valid = True
      calibration = messaging.new_message('extrinsicsCalibration')
      calibration.valid = True
      calibration.extrinsicsCalibration.calStatus = log.ExtrinsicsCalibration.Status.calibrated
      dm = messaging.new_message('driverMonitoringState')
      dm.valid = True
      def publish_native(*, requested_long=False):
        native = messaging.new_message('aolSafetyWire', 0)
        native.valid = True
        observed = time.monotonic_ns()
        native.aolSafetyWire = encode_safety(SafetyState(
          1, True, observed, observed + 200_000_000, int(car.CarParams.SafetyModel.hondaBosch),
          card.CP.safetyConfigs[-1].safetyParam, True, requested_long, True, requested_long,
          'test-panda', selfdrive.aol_session_id))
        source.send('aolSafetyWire', native)

      for _ in range(3):
        source.send('modelV2', model)
        model.clear_write_flag()
        source.send('extrinsicsCalibration', calibration)
        calibration.clear_write_flag()
        source.send('driverMonitoringState', dm)
        dm.clear_write_flag()
        publish_native()
        selfdrive.sm.update(100)
        controls.sm.update(0)
      selfdrive.initialized = True
      with mock.patch.object(selfdrive, 'update_events', side_effect=lambda _cs: selfdrive.events.clear()):
        can.send('can', messaging.new_message('can', 1))
        card.step()
        selfdrive.step()
      self.assertEqual(selfdrive.aol_axis_decision.mode, 'lateralOnly')
      controls.sm.update(0)
      cc, _ = controls.state_control()
      self.assertTrue(cc.latActive)
      self.assertFalse(cc.longActive)
      # The native long request may still reflect a previous combined mode;
      # this must not interrupt unchanged lateral permission.
      publish_native(requested_long=True)
      controls.sm.update(0)
      cc, _ = controls.state_control()
      self.assertTrue(cc.latActive)
      self.assertFalse(cc.longActive)
      # On the reverse transition, an old lateral-only acknowledgment keeps
      # lateral active while the newly requested longitudinal axis waits.
      publish_native()
      axis_msg = messaging.new_message('aolAxisState')
      axis_msg.valid = True
      axis = axis_msg.aolAxisState
      axis.sessionId = selfdrive.aol_session_id
      axis.qualified = True
      axis.desiredLateral = True
      axis.desiredLongitudinal = True
      axis.lateralActive = True
      axis.longitudinalActive = False
      axis.nativeAcknowledged = True
      axis.observedMonoTime = time.monotonic_ns()
      axis.validUntilMonoTime = axis.observedMonoTime + 30_000_000
      selfdrive.pm.send('aolAxisState', axis_msg)
      controls.sm.update(0)
      cc, _ = controls.state_control()
      self.assertTrue(cc.latActive)
      self.assertFalse(cc.longActive)

      dm.driverMonitoringState.lockout = True
      source.send('driverMonitoringState', dm)
      with mock.patch.object(selfdrive, 'update_events', side_effect=lambda _cs: selfdrive.events.clear()):
        can.send('can', messaging.new_message('can', 1))
        card.step()
        selfdrive.step()
      self.assertEqual(selfdrive.aol_axis_decision.mode, 'off')
      controls.sm.update(100)
      cc, _ = controls.state_control()
      self.assertFalse(cc.latActive or cc.longActive)

      # Saved AOL off retains the negotiated protocol while ending extra lateral autonomy.
      params.put_bool('AlwaysOnLateral', False, block=True)
      assert card.aol_card_intent is not None
      card.aol_card_intent.settings = read_settings(params)
      selfdrive.aol_settings = read_settings(params)
      can.send('can', messaging.new_message('can', 1))
      card.step()
      selfdrive.step()
      controls.sm.update(100)
      cc, _ = controls.state_control()
      self.assertFalse(cc.latActive or cc.longActive)
      self.assertTrue(card.aol_qualified)
