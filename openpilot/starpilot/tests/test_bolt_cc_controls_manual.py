import os
import tempfile
import unittest
from unittest.mock import patch

from openpilot.cereal import messaging
from openpilot.common.params import Params
from openpilot.common.prefix import OpenpilotPrefix
from openpilot.selfdrive.controls.controlsd import Controls
from openpilot.selfdrive.selfdrived.selfdrived import SelfdriveD
from openpilot.selfdrive.selfdrived.events import EventName
from opendbc.car import structs
from opendbc.car.gm.bolt_cc import button_bytes
from opendbc.car.gm.tests.test_bolt_cc import feed, fixture, native, setup
from opendbc.car.gm.values import CAR, BOLT_CC_WORDS
from opendbc.safety.tests.libsafety import libsafety_py


class TestBoltCcControlsManual(unittest.TestCase):
  def test_reported_manual_disables_and_requires_fresh_set_release(self):
    for identity, words in BOLT_CC_WORDS.items():
      for removed in (False, True):
        with self.subTest(identity=identity, removed=removed), tempfile.TemporaryDirectory() as params_root, \
             patch.dict(os.environ, {'PARAMS_ROOT': params_root, 'SIMULATION': '1', 'REPLAY': '1'}), OpenpilotPrefix():
          params = Params()
          for key in ('OpenpilotEnabledToggle',):
            params.put_bool(key, True, block=True)
          for key in ('AlwaysOnLateral', 'SafeMode', 'AdvancedLateralTune'):
            params.put_bool(key, False, block=True)
          cp, ci, packer = fixture(identity, removed=removed)
          cp.fingerprintSource = structs.CarParams.FingerprintSource.can
          cp.carFw = []
          params.put('CarParams', cp.to_bytes(), block=True)
          controls = Controls()
          self.assertEqual(controls.CP.to_dict(), cp.to_dict())
          self.assertEqual(controls.CP.safetyConfigs[0].safetyParam, words[int(removed)])
          _, template = feed(ci, packer, 900_000_000, active=False, camera=not removed)
          setup(cp)
          with patch("openpilot.selfdrive.selfdrived.selfdrived.REPLAY", False):
            sd = SelfdriveD(CP=cp)
          previous_control = structs.CarControl()
          active_frames = 0
          for tick in range(520):
            now = 1_000_000_000 + tick * 10_000_000
            manual = tick < 60 or 340 <= tick < 360
            gas = False
            button = 3 if 40 <= tick < 42 or 90 <= tick < 92 or 390 <= tick < 392 else 1
            replacement = [
              packer.make_can_msg('ECMPRDNL2', 0, {'PRNDL2': 6, 'ManualMode': int(manual)}),
              packer.make_can_msg('ECMCruiseControl', 0, {'CruiseActive': int(tick >= 92), 'CruiseSetSpeed': 54}),
              packer.make_can_msg('AcceleratorPedal2', 0, {'AcceleratorPedal2': 30 if gas else 0}),
              (0x1E1, button_bytes(button, tick % 4), 0),
            ]
            if identity == CAR.CHEVROLET_BOLT_ACC_2022_2023_PEDAL and not removed:
              replacement.append(packer.make_can_msg('ASCMActiveCruiseControlStatus', 2, {'ACCCmdActive': int(tick >= 92)}))
            replaced = {frame[0] for frame in replacement}
            frames = [frame for frame in template if frame[0] not in replaced] + replacement
            for frame in sorted(frames, key=lambda frame: frame[0] == 0x3D1):
              if frame[0] in (0x184, 0x3D1, 0x1E1, 0xC9, 0x1C4, 0x1F5, 0x34A, 0x370):
                self.assertTrue(native('rx', frame, now // 1000))
            libsafety_py.libsafety.safety_tick()
            cs = ci.update([(now, frames)])
            self.assertTrue(cs.canValid)
            self.assertEqual(cs.gearShifter, structs.CarState.GearShifter.manumatic if manual else structs.CarState.GearShifter.low)
            cs.vCruise = cs.vCruiseCluster = 100.
            messages = []

            def message(service, size=None, now=now, messages=messages):
              msg = messaging.new_message(service, size, valid=True, logMonoTime=now)
              messages.append(msg)
              return getattr(msg, service)

            state = message('carState')
            state.from_dict(cs.to_dict())
            parameters = message('vehicleParameters')
            parameters.stiffnessFactor, parameters.steerRatio = 1., cp.steerRatio
            message('longitudinalPlan').aTarget = 1.
            message('modelV2').action.desiredCurvature = .00001
            message('lateralDelay').lateralDelay = .1
            message('carOutput')
            peers = []
            for service in sd.sm.data:
              if service in ('alertDebug', 'lateralManeuverPlan', 'laneChangeAssistWire'):
                continue
              size = 1 if service == 'pandaStates' else 0 if service == 'laneChangeAssistWire' else None
              peer = messaging.new_message(service, size,
                                           valid=True, logMonoTime=now)
              payload = getattr(peer, service)
              if service == 'pandaStates':
                payload[0].safetyModel = cp.safetyConfigs[0].safetyModel
                payload[0].safetyParam = cp.safetyConfigs[0].safetyParam
                payload[0].alternativeExperience = cp.alternativeExperience
                payload[0].controlsAllowed = bool(libsafety_py.libsafety.get_controls_allowed())
                payload[0].safetyRxChecksInvalid = not bool(libsafety_py.libsafety.safety_config_valid())
              elif service == 'extrinsicsCalibration':
                payload.calStatus = 'calibrated'
                payload.rpyCalib = [0., 0., 0.]
              elif service == 'vehicleParameters':
                payload.stiffnessFactor, payload.steerRatio, payload.valid = 1., cp.steerRatio, True
              elif service == 'deviceMotion':
                payload.inputsOK = payload.posenetOK = True
                payload.velocityDevice.x = cs.vEgo
              elif service == 'controlsState':
                payload.lateralControlState.init('torqueState')
              elif service == 'carControl':
                payload.from_dict(previous_control.to_dict())
              elif service == 'deviceState':
                payload.freeSpacePercent = 50.
              peers.append(peer.as_reader())
            car_state_event = messages[0].as_reader()
            with patch('openpilot.selfdrive.selfdrived.selfdrived.REPLAY', False), \
                 patch('openpilot.selfdrive.selfdrived.selfdrived.messaging.recv_one', return_value=car_state_event), \
                 patch.object(sd.sm, 'update', side_effect=lambda timeout, now=now, peers=peers, sd=sd:
                              sd.sm.update_msgs(now / 1e9, peers)):
              sd.step()
            self.assertEqual(sd.mismatch_counter, int(tick == 340), tick)
            self.assertNotIn(EventName.controlsMismatch, sd.events.names)
            host = message('selfdriveState')
            host.enabled, host.active, host.state = sd.enabled, sd.active, sd.state_machine.state
            event_message = messaging.new_message('onroadEvents', len(sd.events.to_msg()), valid=True, logMonoTime=now)
            event_message.onroadEvents = sd.events.to_msg()
            messages.append(event_message)
            controls.sm.update_msgs(now / 1e9, [msg.as_reader() for msg in messages])
            cc, lateral_log = controls.state_control()
            self.assertEqual(cc.enabled, sd.enabled)
            controls.publish(cc, lateral_log)
            self.assertEqual(cc.cruiseControl.cancel, cs.cruiseState.enabled and (not cc.enabled or not cp.pcmCruise))
            _, commands = ci.apply(cc.as_reader(), now + 1_000_000)
            for frame in commands:
              self.assertTrue(native('tx', frame, (now + 1_000_000) // 1000), (tick, hex(frame[0])))
              if manual and frame[0] == 0x180:
                self.assertEqual(((frame[1][0] & 7) << 8) | frame[1][1], 0)
            if 95 <= tick < 340 or tick >= 395:
              self.assertTrue(cc.enabled and cc.latActive, tick)
              self.assertTrue(libsafety_py.libsafety.get_controls_allowed(), tick)
              active_frames += 1
            if manual or 360 <= tick < 390:
              self.assertFalse(cc.enabled or cc.latActive or cc.longActive, tick)
            if manual:
              self.assertFalse(libsafety_py.libsafety.get_controls_allowed(), tick)
              self.assertEqual(cc.actuators.torque, 0.)
            previous_control = cc
          self.assertGreater(active_frames, 200)
