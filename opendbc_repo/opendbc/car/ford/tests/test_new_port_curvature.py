"""Current-strategy Edge/Mondeo wiring and current native scalar-curvature proof.

Source-only authored cases; runtime must bind actual DEBUG/RELEASE libraries.
"""
import os
from pathlib import Path
import unittest
from unittest.mock import patch

from openpilot.cereal import messaging
from openpilot.common.params import Params
from openpilot.common.prefix import OpenpilotPrefix
from openpilot.selfdrive.controls.controlsd import Controls
from openpilot.starpilot.tests import test_vehicle_preferences as startup
from openpilot.starpilot.lateral.tests import test_lane_runtime as lane
from opendbc.car import gen_empty_fingerprint, structs
from opendbc.car.ford.new_port_curvature import qualified, create_controller
from opendbc.car.ford.tests.test_three_ports import params as factory
from opendbc.car.ford.values import CAR, FordFlags
from opendbc.safety.tests import test_ford_aol as physical
from opendbc.safety.tests.libsafety import libsafety_py

PROFILES = (CAR.FORD_EDGE_MK2, CAR.FORD_MONDEO_MK5)


class TestNewPortCurvature(unittest.TestCase):
  def test_exact_existing_factory_profiles_and_no_namespace_or_topology_inference(self):
    for identity in PROFILES:
      for alpha, release in ((False, False), (True, False), (False, True), (True, True)):
        cp = factory(identity, alpha, release)
        expected_long = bool(alpha and (identity == CAR.FORD_EDGE_MK2 or not release))
        self.assertTrue(cp.pcmCruise)
        self.assertEqual(cp.openpilotLongitudinalControl, expected_long)
        self.assertEqual(cp.safetyConfigs[-1].safetyParam, (8 if identity == CAR.FORD_EDGE_MK2 else 10) + int(expected_long))
        self.assertTrue(qualified(cp))
        self.assertIsNotNone(create_controller(cp))
        original = cp.to_bytes()
        cp.clear_write_flag()
        create_controller(cp)
        self.assertEqual(cp.to_bytes(), original)
        cp.clear_write_flag()
        for field, value in (("passive", True), ("dashcamOnly", True), ("notCar", True), ("alternativeExperience", 64),
                             ("pcmCruise", False), ("openpilotLongitudinalControl", not expected_long)):
          with structs.CarParams.from_bytes(original) as prior:
            changed = prior.as_builder()
          setattr(changed, field, value)
          self.assertFalse(qualified(changed))
        for word in (0, 2, 12, 18, 32, 66, 128, 130, 65535):
          with structs.CarParams.from_bytes(original) as prior:
            changed = prior.as_builder()
          changed.safetyConfigs[-1].safetyParam = word
          self.assertIsNone(create_controller(changed))
        cp.alternativeExperience = 32
        self.assertTrue(qualified(cp))
        cp.safetyConfigs = [cp.safetyConfigs[-1], cp.safetyConfigs[-1]]
        self.assertFalse(qualified(cp))
    self.assertIsNone(create_controller(factory(CAR.FORD_TRANSIT_MK5)))
    self.assertIsNone(create_controller(factory(CAR.FORD_BRONCO_SPORT_MK1)))

  def test_saved_card_controls_actual_parser_provider_sender_and_native_both_signs(self):
    safety = libsafety_py.libsafety
    for identity in PROFILES:
      for direction in (-1, 1):
        with self.subTest(identity=identity, direction=direction), OpenpilotPrefix(), \
             patch.dict(os.environ, {"REPLAY": "1", "SIMULATION": "1"}), \
             patch("openpilot.selfdrive.controls.controlsd.messaging.PubMaster"):
          saved = Params()
          helper = startup.TestVehicleStartupPreferences()
          helper.setUp()
          helper.params = saved
          native = physical.TestFordAolDriverIntent()
          try:
            for key, value in (("OpenpilotEnabledToggle", True), ("SafeMode", False), ("AlwaysOnLateral", False),
                               ("AlphaLongitudinalEnabled", False), ("IsReleaseBranch", False)):
              saved.put_bool(key, value, block=True)
            observed = gen_empty_fingerprint()
            observed[0][0x5A] = 8
            observed[2].update({0x3D6: 8, 0x186: 8})
            host, constructed, cp = helper.start(identity, key="FordHumanTurnDetection", observed=observed,
              capture=lambda ci: (ci.CP.safetyConfigs[-1].safetyParam, ci.CC.new_port_curvature is not None))
            self.assertEqual(constructed, [(8 if identity == CAR.FORD_EDGE_MK2 else 10, True)])
            self.assertEqual(host.CI.CP.to_dict(), cp.to_dict())
            self.assertTrue(qualified(cp))
            owner = host.CI.CC.new_port_curvature
            inputs = host.CI.CC.manual_turn_inputs
            self.assertIsNotNone(inputs)
            inputs.sm = messaging.SubMaster(["modelV2", "lateralDelay"])
            host.sm = messaging.SubMaster(["carControl"])
            controls = Controls()
            native.setUp()
            native.word, native.tick = cp.safetyConfigs[-1].safetyParam, 0
            safety.set_alternative_experience(0)
            self.assertEqual(safety.set_safety_hooks(structs.CarParams.SafetyModel.ford, native.word), 0)
            safety.init_tests()
            received, sent, active_curvatures = [], [], []

            def rx(name, values, *, native=native, received=received):
              self.assertLessEqual(set(values), set(native.packer.dbc.name_to_msg[name].sigs))
              frame = native.packer.make_can_msg(name, 0, values)
              addr, data, bus = frame
              self.assertTrue(safety.safety_rx_hook(libsafety_py.make_CANPacket(addr, bus, data)))
              received.append(frame)

            host.publish_sendcan = lambda frames, valid=True, sent=sent: sent.extend(frames) if valid else self.fail("Invalid Card trace")
            host.ci_initialized = True
            host.CI.update([])
            saw_human_zero = saw_fault_zero = saw_stale_model = saw_rate_neutral = False
            for tick in range(600):
              received.clear()
              with patch.object(native, "rx", rx):
                native.pump(1, main=0 if tick < 30 else 4, speed=15.)
              now = (1_000_000 + native.tick * 10_000) * 1000
              pressed = 100 <= tick < 430
              fault = 460 <= tick < 480
              extra: list[tuple[str, int, dict[str, float]]] = [("Cluster_Info1_FD1", 0, {"AccEnbl_B_RqDrv": 1}),
                       ("BodyInfo_3_FD1", 0, {}), ("RCMStatusMessage2_FD1", 0, {"FirstRowBuckleDriver": 1}),
                       ("INSTRUMENT_PANEL", 0, {}), ("IPMA_Data", 2, {}), ("ACCDATA", 2, {}),
                       ("ACCDATA_2", 2, {}), ("ACCDATA_3", 2, {}),
                       ("EPAS_INFO", 0, {"SteeringColumnTorque": 2 if pressed else 0, "EPAS_Failure": 2 if fault else 0})]
              if cp.flags & FordFlags.ALT_STEER_ANGLE:
                extra += [("ParkAid_Data", 0, {"ExtSteeringAngleReq2": 60 if pressed else 0, "EPASExtAngleStatReq": 0, "ApaSys_D_Stat": 0}),
                          ("SteeringPinion_Data_Alt", 0, {"StePinRelInit_An_Sns": 60 if pressed else 0})]
              else:
                extra += [("SteeringPinion_Data", 0, {"StePinComp_An_Est": 60 if pressed else 0, "StePinCompAnEst_D_Qf": 3})]
              host_sources = [native.packer.make_can_msg(name, bus, values) for name, bus, values in extra]
              for addr, data, bus in host_sources:
                self.assertTrue(safety.safety_rx_hook(libsafety_py.make_CANPacket(addr, bus, data)))
              received.extend(host_sources)
              state = host.CI.update([(now, list(received))])
              if tick < 40:
                continue
              self.assertTrue(state.canValid)
              self.assertFalse(state.canTimeout)
              self.assertTrue(safety.get_controls_allowed())
              with patch("openpilot.starpilot.controller_extensions.time.monotonic_ns", return_value=now), \
                   patch("openpilot.selfdrive.car.card.time.monotonic", return_value=now / 1e9), \
                   patch.object(inputs.sm, "update", return_value=None):
                feed_events = []
                with patch.object(controls.sm, "update_msgs", side_effect=lambda _, events, collector=feed_events: collector.extend(events)):
                  lane.feed(controls, now, tick, speed=15.)
                car_state = messaging.new_message("carState", valid=True, logMonoTime=now)
                car_state.carState = state

                preview = messaging.new_message("modelV2", valid=True, logMonoTime=now)
                preview.modelV2 = lane.model()
                preview.modelV2.action.desiredCurvature = direction * .0002
                predicted = .012 + (tick - 430) * .0002 if 430 <= tick < 460 else .0012
                preview.modelV2.orientationRate.z = [direction * predicted * 15.] * 33
                delay = messaging.new_message("lateralDelay", valid=True, logMonoTime=now)
                delay.lateralDelay.lateralDelay = .38
                replacements = {"carState": car_state.as_reader(), "modelV2": preview.as_reader(), "lateralDelay": delay.as_reader()}
                controls.sm.update_msgs(now / 1e9, [event for event in feed_events
                                                  if event.which() not in replacements] + list(replacements.values()))
                if tick < 490:
                  inputs.sm.update_msgs(now / 1e9, [preview.as_reader(), delay.as_reader()])
                command, controller_log = controls.state_control()
                self.assertTrue(command.enabled)
                control_events = []
                def capture_control(service, event, collector=control_events):
                  if service == "carControl":
                    collector.append(messaging.log_from_bytes(event.to_bytes()))
                with patch.object(controls.pm, "send", side_effect=capture_control):
                  controls.publish(command, controller_log)
                self.assertEqual(len(control_events), 1)
                self.assertEqual(control_events[0].carControl.to_dict(), command.to_dict())
                self.assertEqual(control_events[0].valid, state.canValid)
                host.sm.update_msgs(now / 1e9, control_events)
                command = host.sm["carControl"]
                host.can_log_mono_time = now
                sent.clear()
                host.controls_update(state, command)
                if tick > 510:
                  self.assertIsNone(owner.model)
                  saw_stale_model = True
              for addr, data, bus in sent:
                if addr not in (0x3CA, 0x3D3, 0x3D6):
                  continue
                self.assertTrue(safety.safety_tx_hook(libsafety_py.make_CANPacket(addr, bus, data)), (identity, tick, hex(addr)))
                if addr == 0x3CA:
                  self.assertEqual(data[4] & 3, 0)  # Existing neutral body, no extension announcement.
                elif addr in (0x3D3, 0x3D6):
                  fd = addr == 0x3D6
                  mode = (data[0] >> 4) & 7 if fd else (data[4] >> 2) & 7
                  curvature = ((data[2] << 3) | (data[3] >> 5)) - 1000 if fd else ((data[0] << 3) | (data[1] >> 5)) - 1000
                  rate = (data[6] << 3) | (data[7] >> 5) if fd else ((data[1] & 31) << 8) | data[2]
                  self.assertEqual(rate, 1024 if fd else 4096)
                  if 430 <= tick < 460 and host.CI.CC.new_port_curvature_demand.curvature_rate != 0:
                    saw_rate_neutral = True
                  if 400 <= tick < 425:
                    self.assertEqual((mode, curvature), (0, 0))
                    saw_human_zero = True
                  if fault:
                    self.assertEqual((mode, curvature), (0, 0))
                    saw_fault_zero = True
                  if 70 <= tick < 100 and mode and curvature:
                    active_curvatures.append(curvature)
                    self.assertAlmostEqual(owner._curvature_lookahead(), .38, places=6)
                    self.assertGreater(direction * host.CI.CC.new_port_curvature_demand.curvature, .0002)
            self.assertTrue(active_curvatures)
            self.assertTrue(all(value * direction < 0 for value in active_curvatures))
            self.assertTrue(saw_human_zero and saw_fault_zero and saw_stale_model and saw_rate_neutral)
            self.assertEqual(Path(saved.get_param_path("FordHumanTurnDetection")).read_bytes(), b"1")
          finally:
            helper.doCleanups()
            safety.set_alternative_experience(0)
            safety.set_safety_hooks(structs.CarParams.SafetyModel.noOutput, 0)
