"""Actual saved owner/factory/Card/Controls/parser/sender/native qualification.

These tests must run with the runner-selected DEBUG and RELEASE safety library.
No authority, measurement, desired-history or angle-ready test setters are used.
"""
import os
import ctypes
import hashlib
import shutil
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch
from contextlib import ExitStack
from types import SimpleNamespace

from openpilot.cereal import messaging
from openpilot.common.params import Params, ParamKeyType
from openpilot.common.prefix import OpenpilotPrefix
from openpilot.selfdrive.controls.controlsd import Controls
from openpilot.starpilot.tests import test_vehicle_preferences as startup
from openpilot.starpilot.lateral.tests import test_lane_runtime as lane
from openpilot.starpilot.vehicle_preferences import VehicleStartupPreferences
from opendbc.car import gen_empty_fingerprint, structs
from opendbc.car.ford.values import CAR, FordFlags, DBC
from opendbc.bluepilot_lateral.tests import reference
from openpilot.starpilot.controller_extensions import configure_controller
from opendbc.bluepilot_lateral.hosts.starpilot import CLASSIC, CANFD, qualified, select
from opendbc.safety.tests import test_ford_aol as physical
from opendbc.safety.tests.libsafety import libsafety_py


class TestFordAngleStartup(unittest.TestCase):
  def setUp(self):
    self.helper = startup.TestVehicleStartupPreferences()
    self.helper.setUp()
    self.addCleanup(self.helper.doCleanups)
    self.params = self.helper.params
    self.helper.raw("SafeMode", b"0")
    self.helper.raw("AlwaysOnLateral", b"0")
    self.params.put_bool("AlphaLongitudinalEnabled", False, block=True)
    self.params.put_bool("IsReleaseBranch", False, block=True)

  def start(self, identity, requested=True, *, auxiliary=False, **kwargs):
    observed = gen_empty_fingerprint()
    offset = 4 if auxiliary else 0
    observed[offset][0x5A] = 8
    observed[offset + 2].update({0x3D6: 8, 0x186: 8})
    return self.helper.start(identity, key="FordLateralMode", requested=requested, observed=observed,
                             capture=lambda ci: (int(ci.CP.safetyConfigs[-1].safetyParam), ci.CC.bp_lat is not None), **kwargs)

  def test_actual_factory_card_saved_choice_before_controller_all_eleven(self):
    for identity in sorted(CLASSIC | CANFD):
      for requested in (False, True):
        with self.subTest(identity=identity, selected=requested):
          host, constructed, published = self.start(identity, requested)
          baseline = 18 if identity == CAR.FORD_MUSTANG_MACH_E_MK1 else 66 if identity in CANFD else 32
          word = 130 if identity in CANFD else 128
          self.assertEqual(constructed, [(word if requested else baseline, requested)])
          self.assertEqual(published.safetyConfigs[-1].safetyParam, constructed[0][0])
          self.assertEqual(qualified(published), requested)
          self.assertEqual(host.CI.CP.to_dict(), published.to_dict())
          if requested:
            self.assertIsNotNone(host.CI.CC.bp_lat.host.inputs)
            self.assertAlmostEqual(published.steerActuatorDelay, .22, places=6)
          self.assertEqual(self.params.get("FordLateralMode"), int(requested))
          self.assertEqual(Path(self.params.get_param_path("FordLateralMode")).read_bytes(), b"1" if requested else b"0")

  def test_absent_corrupt_dependencies_and_typed_value_fail_closed(self):
    self.assertEqual(self.params.get_type("FordLateralMode"), ParamKeyType.INT)
    self.assertEqual(self.params.get_default_value("FordLateralMode"), 0)
    for raw in (None, b"0", b"", b"1\n", b"true", b"2", b"1" * 20, b"1"):
      self.helper.raw("FordLateralMode", raw)
      selected = VehicleStartupPreferences.read(self.params, enabled=True)
      self.assertEqual(selected.ford_lateral_mode, int(raw == b"1"))
      self.assertEqual(Path(self.params.get_param_path("FordLateralMode")).read_bytes() if raw is not None else None, raw)
    from opendbc.car.ford.tests.test_three_ports import params
    for raw in (1, b"1", "1", True, 1.0, None, "01"):
      cp = params(CAR.FORD_BRONCO_SPORT_MK1)
      self.assertEqual(select(cp, raw), type(raw) is int or type(raw) in (bytes, str) and raw in (b"1", "1"))
    for key in ("SafeMode", "AlwaysOnLateral"):
      for raw in (b"1", b"", b"false", b"0\n"):
        self.helper.raw(key, raw)
        self.assertEqual(VehicleStartupPreferences.read(self.params, enabled=True).ford_lateral_mode, 0)
      self.helper.raw(key, b"0")
    self.assertEqual(VehicleStartupPreferences.read(self.params, enabled=False).ford_lateral_mode, 0)

  def test_saved_selection_excluded_profiles_and_final_longitudinal_owner(self):
    for identity in (CAR.FORD_EDGE_MK2, CAR.FORD_MONDEO_MK5, CAR.FORD_TRANSIT_MK5):
      host, constructed, published = self.start(identity)
      self.assertFalse(qualified(published))
      self.assertFalse(constructed[0][1])
      self.assertIsNone(host.CI.CC.bp_lat)
      self.assertEqual(self.params.get("FordLateralMode"), 1)
    for identity in (CAR.FORD_BRONCO_SPORT_MK1, CAR.FORD_MUSTANG_MACH_E_MK1):
      for release in (False, True):
        self.params.put_bool("AlphaLongitudinalEnabled", True, block=True)
        self.params.put_bool("IsReleaseBranch", release, block=True)
        host, constructed, published = self.start(identity)
        word = (130 if identity in CANFD else 128) + int(published.openpilotLongitudinalControl)
        self.assertEqual(constructed, [(word, True)])
        self.assertEqual(published.safetyConfigs[-1].safetyParam, word)
        self.assertEqual(published.openpilotLongitudinalControl, not release)
        self.assertTrue(published.pcmCruise)
        self.assertEqual(published.alternativeExperience, 0)
        self.assertTrue(qualified(published))
        self.assertIsNotNone(host.CI.CC.bp_lat)
        self.assertEqual(self.params.get("FordLateralMode"), 1)

  def test_actual_factory_alpha_long_angle_admission_and_exact_config_denials(self):
    from opendbc.car.ford.interface import CarInterface
    for identity in (CAR.FORD_BRONCO_SPORT_MK1, CAR.FORD_MUSTANG_MACH_E_MK1):
      for alpha in (False, True):
        for release in (False, True):
          with self.subTest(identity=identity, alpha=alpha, release=release):
            observed = gen_empty_fingerprint()
            observed[0][0x5A] = 8
            observed[2].update({0x3D6: 8, 0x186: 8})
            cp = CarInterface.get_params(identity, observed, [], alpha, release, False)
            long = alpha and (identity not in CANFD or not release)
            self.assertEqual(cp.openpilotLongitudinalControl, long)
            self.assertTrue(cp.pcmCruise)
            self.assertEqual(cp.alternativeExperience, 0)
            self.assertEqual(cp.flags, int(FordFlags.CANFD) if identity in CANFD else 0)
            self.assertEqual(cp.safetyConfigs[-1].safetyParam, (18 if identity in CANFD else 32) + int(long))
            self.assertTrue(select(cp, 1))
            self.assertEqual(cp.safetyConfigs[-1].safetyParam, (130 if identity in CANFD else 128) + int(long))
            self.assertTrue(qualified(cp))
            for field, value in (("pcmCruise", False), ("alternativeExperience", 32), ("passive", True),
                                 ("dashcamOnly", True), ("notCar", True), ("brand", "hyundai"),
                                 ("flags", 128), ("steerControlType", structs.CarParams.SteerControlType.torque)):
              invalid = cp.as_reader().as_builder()
              setattr(invalid, field, value)
              self.assertFalse(qualified(invalid), field)
            for field, value in (("safetyModel", structs.CarParams.SafetyModel.noOutput),
                                 ("safetyParam", cp.safetyConfigs[-1].safetyParam ^ 1)):
              invalid = cp.as_reader().as_builder()
              setattr(invalid.safetyConfigs[-1], field, value)
              self.assertFalse(qualified(invalid), field)



class TestFordAngleJoined(unittest.TestCase):
  def test_saved_card_controls_parser_and_actual_native_trace_both_signs(self):
    safety = libsafety_py.libsafety
    native_debug = safety.set_safety_hooks(structs.CarParams.SafetyModel.allOutput, 0) == 0
    safety.set_safety_hooks(structs.CarParams.SafetyModel.noOutput, 0)
    sources = ("BrakeSysFeatures", "EngVehicleSpThrottle2", "Yaw_Data_FD1", "EngBrakeData",
               "EngVehicleSpThrottle", "DesiredTorqBrk", "Steering_Data_FD1")
    faults = [("crc", source) for source in (sources[0], sources[2])] + \
             [("quality", source) for source in sources[:3]] + \
             [("counter", source) for source in (sources[0], sources[2])] + \
             [("freshness", source) for source in sources] + \
             [(name, None) for name in ("gas", "brake", "cruise", "relay", "buttons", "panda_stale",
                                       "panda_model", "panda_param", "panda_ae", "panda_topology",
                                       "panda_heartbeat", "panda_fault_status", "panda_controls")]
    for identity in (CAR.FORD_BRONCO_SPORT_MK1, CAR.FORD_EXPLORER_MK6,
                     CAR.FORD_MUSTANG_MACH_E_MK1, CAR.FORD_F_150_MK14):
      scenarios = [("angle", None), ("default0", None)]
      if identity in (CAR.FORD_BRONCO_SPORT_MK1, CAR.FORD_MUSTANG_MACH_E_MK1):
        scenarios += [("aux", None)] + faults + [("alpha", None), ("alpha_cruise", None), ("alpha_buttons", None)]
      for scenario, source in scenarios:
        alpha_requested = scenario.startswith("alpha")
        kind = "angle" if scenario == "alpha" else scenario.removeprefix("alpha_")
        for direction in (-1, 1):
          with self.subTest(identity=identity, direction=direction, kind=scenario, source=source), OpenpilotPrefix(), \
               patch.dict(os.environ, {"REPLAY": "1", "SIMULATION": "1"}), \
               patch("openpilot.selfdrive.controls.controlsd.messaging.PubMaster"):
            params = Params()
            helper = TestFordAngleStartup()
            helper.setUp()
            auxiliary = None
            auxiliary_directory = None
            try:
              helper.params = helper.helper.params = params
              for key, value in (("SafeMode", False), ("AlwaysOnLateral", False), ("AlphaLongitudinalEnabled", alpha_requested),
                                 ("IsReleaseBranch", alpha_requested and not native_debug), ("OpenpilotEnabledToggle", True)):
                params.put_bool(key, value, block=True)
              selected = kind != "default0"
              host, _, cp = helper.start(identity, selected, auxiliary=kind == "aux")
              offset = 4 if kind == "aux" else 0
              self.assertEqual(qualified(cp), selected)
              alpha_active = alpha_requested and native_debug
              self.assertEqual(cp.openpilotLongitudinalControl, alpha_active)
              self.assertTrue(cp.pcmCruise)
              if alpha_requested:
                self.assertEqual(cp.safetyConfigs[-1].safetyParam, (130 if identity in CANFD else 128) + int(alpha_active))
                self.assertTrue(params.get_bool("AlphaLongitudinalEnabled"))
              controls = Controls()
              native = physical.TestFordAolDriverIntent()
              native.setUp()
              native.word = 66 if cp.flags & FordFlags.CANFD else 32
              native.tick = 0
              self.assertEqual(safety.set_safety_hooks(structs.CarParams.SafetyModel.ford, cp.safetyConfigs[-1].safetyParam), 0)
              safety.init_tests()
              safety.set_alternative_experience(0)
              auxiliary = None
              auxiliary_handle = None
              if kind == "aux":
                self.assertEqual(len(cp.safetyConfigs), 2)
                self.assertEqual(cp.safetyConfigs[0].safetyModel, structs.CarParams.SafetyModel.noOutput)
                self.assertEqual(cp.safetyConfigs[0].safetyParam, 0)
                self.assertEqual(host.CI.CC.CAN.main, 4)
                self.assertEqual(host.CI.CC.CAN.camera, 6)
                # Copy the actual library selected by the public test runner,
                # so the noOutput Panda has independent native static storage.
                main_file = Path(libsafety_py.libpath)
                auxiliary_directory = tempfile.TemporaryDirectory()
                aux_file = Path(auxiliary_directory.name) / "libsafety-auxiliary.so"
                shutil.copyfile(main_file, aux_file)
                self.assertNotEqual(main_file.resolve(), aux_file.resolve())
                self.assertEqual(hashlib.sha256(main_file.read_bytes()).digest(), hashlib.sha256(aux_file.read_bytes()).digest())
                auxiliary = libsafety_py.ffi.dlopen(str(aux_file))
                auxiliary_handle = ctypes.CDLL(str(aux_file))
                self.assertEqual(auxiliary.set_safety_hooks(int(cp.safetyConfigs[0].safetyModel.raw), cp.safetyConfigs[0].safetyParam), 0)
                auxiliary.init_tests()
                auxiliary.set_alternative_experience(0)
                self.assertFalse(auxiliary.get_controls_allowed())
                self.assertEqual(safety.get_current_safety_param(), cp.safetyConfigs[-1].safetyParam)
              baseline = None
              if not selected:
                baseline = reference.curvature_controller()(DBC[identity], cp)
                configure_controller(SimpleNamespace(CP=cp, CC=baseline), params)
              providers = []
              received, sent, validity = [], [], []
              observed_allowed = False
              observed_relay = False
              observed_health = False
              path_seen, resumed, withdraw_seen = [], False, False
              paired_cancel, paired_resume = False, False
              alpha_button_cancelled = alpha_button_acc_off = False
              alpha_cancel_event_seen = alpha_cancel_requested = alpha_physical_rearmed = False
              tx_rejected, invalid_rx = 0, 0
              counter_rx: list[tuple[int, int, bool]] = []
              long_positive = long_recovered = long_withdrawn = False

              def bind(host, selected, baseline, providers, sent, validity):
                providers.clear()
                providers.append(host.CI.CC.bp_lat.host.inputs if selected else host.CI.CC.manual_turn_inputs)
                if baseline is not None:
                  providers.append(baseline.manual_turn_inputs)
                for owner in providers:
                  self.assertIsNotNone(owner)
                  services = ["modelV2", "lateralDelay"] + (["pandaStates"] if owner.track_assist_permission else [])
                  owner.sm = messaging.SubMaster(services)
                host.sm = messaging.SubMaster(["carControl"])
                host.publish_sendcan = lambda frames, valid=True: (sent.extend(frames), validity.append(valid))
                host.ci_initialized = True
                host.CI.update([])

              bind(host, selected, baseline, providers, sent, validity)
              for tick in range(340):
                failing = 120 <= tick < 180
                recovery = 180 <= tick < 220
                received.clear()

                def rx(name, values, *, failing=failing, kind=kind, source=source, tick=tick,
                       received=received, offset=offset, native=native, counter_rx=counter_rx):
                  nonlocal invalid_rx
                  if failing and kind == "freshness" and name == source:
                    return
                  values = dict(values)
                  if failing and name == source:
                    if kind == "quality":
                      signal = {sources[0]: "VehVActlBrk_D_Qf", sources[1]: "VehVActlEng_D_Qf", sources[2]: "VehYawWActl_D_Qf"}[name]
                      values[signal] = 0
                    elif kind == "counter":
                      values["VehVActlBrk_No_Cnt" if name == sources[0] else "VehRollYaw_No_Cnt"] = 0
                  if kind == "counter" and name == source and tick >= 180:
                    # The recovered sender continues from its last transmitted fault counter, zero.
                    brake_counter = name == sources[0]
                    signal = "VehVActlBrk_No_Cnt" if brake_counter else "VehRollYaw_No_Cnt"
                    values[signal] = ((native.tick - 180) // (2 if brake_counter else 1)) % (16 if brake_counter else 256)
                  if failing and kind == "gas" and name == "EngVehicleSpThrottle":
                    values["ApedPos_Pc_ActlArb"] = 50
                  if failing and kind == "brake" and name == "EngBrakeData":
                    values["BpedDrvAppl_D_Actl"] = 2
                  if kind == "buttons" and name == "Steering_Data_FD1":
                    values["CcAslButtnCnclResPress"] = int(119 <= tick < 140 or 159 <= tick < 180)
                  frame = native.packer.make_can_msg(name, 0, values)
                  if failing and kind == "crc" and name == source:
                    addr, data, bus = frame
                    data = bytearray(data)
                    data[3 if name == sources[0] else 4] ^= 1
                    frame = (addr, bytes(data), bus)
                  accepted = safety.safety_rx_hook(libsafety_py.make_CANPacket(frame[0], frame[2], frame[1]))
                  if kind == "counter" and name == source and tick >= 120:
                    counter = (frame[1][2] >> 2) & 0xF if name == sources[0] else frame[1][5]
                    counter_rx.append((tick, counter, bool(accepted)))
                  if not accepted:
                    invalid_rx += 1
                  if not (failing and kind in ("crc", "quality", "counter") and name == source):
                    self.assertTrue(accepted, (kind, source, tick, name))
                  received.append((frame[0], frame[1], frame[2] + offset))
                  # Same bytes/order: Panda-local0 maps to its actual host bus4 in the auxiliary factory topology.

                main = 0 if tick < 30 or recovery and kind not in ("angle", "default0", "aux", "buttons", "panda_stale") else 4
                if failing and kind == "cruise":
                  main = 3
                if kind == "buttons":
                  main = 3 if 129 <= tick < 169 else main
                if kind == "relay" and tick == 180:
                  # A relay fault is latched. Only a new actual factory/native session can recover.
                  host, _, replacement = helper.start(identity)
                  self.assertEqual(replacement.to_dict(), cp.to_dict())
                  self.assertEqual(safety.set_safety_hooks(structs.CarParams.SafetyModel.ford, cp.safetyConfigs[-1].safetyParam), 0)
                  safety.init_tests()
                  safety.set_alternative_experience(0)
                  bind(host, selected, baseline, providers, sent, validity)
                with patch.object(native, "rx", rx):
                  native.pump(1, main=main, speed=15.)
                now = (1_000_000 + native.tick * 10_000) * 1000
                if kind == "relay" and tick == 120:
                  frame = native.packer.make_can_msg("LateralMotionControl2" if cp.flags & FordFlags.CANFD else "LateralMotionControl", 0, {})
                  safety.safety_rx_hook(libsafety_py.make_CANPacket(frame[0], frame[2], frame[1]))
                  received.append(frame)
                  self.assertTrue(safety.get_relay_malfunction())
                safety.safety_tick()
                extra: tuple[tuple[str, int, dict[str, float]], ...] = (("SteeringPinion_Data", 0, {"StePinCompAnEst_D_Qf": 3, "StePinComp_An_Est": 0.0}),
                         ("Cluster_Info1_FD1", 0, {"AccEnbl_B_RqDrv": 1}),
                         ("BodyInfo_3_FD1", 0, {}), ("RCMStatusMessage2_FD1", 0, {"FirstRowBuckleDriver": 1}),
                         ("INSTRUMENT_PANEL", 0, {}), ("IPMA_Data", 2, {}),
                         ("ACCDATA", 2, {}), ("ACCDATA_2", 2, {}), ("ACCDATA_3", 2, {}))
                received.extend(native.packer.make_can_msg(name, bus + offset, values) for name, bus, values in extra)
                state = host.CI.update([(now, list(received))])
                self.assertEqual(state.steeringAngleDeg, 0.0)
                if alpha_active and kind == "buttons":
                  # This component feed consumes the actual parsed Cancel event; the full SD loop is qualified separately.
                  if any(event.type == structs.CarState.ButtonEvent.Type.cancel and event.pressed for event in state.buttonEvents):
                    alpha_button_cancelled = alpha_cancel_event_seen = True
                  if alpha_button_cancelled and not state.cruiseState.enabled:
                    alpha_button_acc_off = True
                  elif alpha_button_acc_off and state.cruiseState.enabled:
                    alpha_button_cancelled = alpha_button_acc_off = False
                    alpha_physical_rearmed = True
                if tick < 40:
                  continue
                if kind in ("angle", "default0", "aux"):
                  self.assertTrue(state.canValid and not state.canTimeout)
                  self.assertTrue(safety.get_controls_allowed())
                with ExitStack() as stack:
                  stack.enter_context(patch("openpilot.starpilot.controller_extensions.time.monotonic_ns", return_value=now))
                  stack.enter_context(patch("openpilot.starpilot.controller_extensions.time.clock_gettime_ns", return_value=now))
                  stack.enter_context(patch("openpilot.selfdrive.car.card.time.monotonic", return_value=now / 1e9))
                  for owner in providers:
                    stack.enter_context(patch.object(owner.sm, "update", return_value=None))
                  events = []
                  if tick % 10 == 0 and not (failing and kind == "panda_stale"):
                    pandas = messaging.new_message("pandaStates", len(cp.safetyConfigs) + int(failing and kind == "panda_topology"),
                                                   valid=True, logMonoTime=now)
                    for i, _config in enumerate(cp.safetyConfigs):
                      p = pandas.pandaStates[i]
                      owner = safety if i == len(cp.safetyConfigs) - 1 else auxiliary
                      self.assertIsNotNone(owner)
                      p.safetyModel, p.safetyParam = owner.get_current_safety_mode(), owner.get_current_safety_param()
                      p.alternativeExperience = cp.alternativeExperience
                      p.controlsAllowed = owner.get_controls_allowed()
                      if owner is safety:
                        p.safetyRxChecksInvalid = not safety.safety_config_valid()
                      else:
                        assert auxiliary_handle is not None
                        p.safetyRxChecksInvalid = ctypes.c_bool.in_dll(auxiliary_handle, "safety_rx_checks_invalid").value
                      p.faultStatus = "faultPerm" if owner.get_relay_malfunction() else "none"
                      p.faults = ["relayMalfunction"] if owner.get_relay_malfunction() else []
                    if failing:
                      p = pandas.pandaStates[len(cp.safetyConfigs) - 1]
                      if kind == "panda_model":
                        p.safetyModel = structs.CarParams.SafetyModel.noOutput
                      elif kind == "panda_param":
                        p.safetyParam = 130 if p.safetyParam == 128 else 128
                      elif kind == "panda_ae":
                        p.alternativeExperience = 32
                      elif kind == "panda_heartbeat":
                        p.heartbeatLost = True
                      elif kind == "panda_fault_status":
                        p.faultStatus = "faultTemp"
                      elif kind == "panda_controls":
                        p.controlsAllowed = False
                    observed_allowed = bool(pandas.pandaStates[len(cp.safetyConfigs) - 1].controlsAllowed)
                    observed_relay = safety.get_relay_malfunction()
                    observed_health = safety.safety_config_valid()
                    events.append(pandas.as_reader())
                  # feed already publishes these services. Replace its synthetic
                  # state/model/delay before one update, preserving one sample per tick.
                  feed_events = []
                  component_enabled = observed_allowed and not observed_relay and not alpha_button_cancelled
                  with patch.object(controls.sm, "update_msgs", side_effect=lambda _time, events, collector=feed_events: collector.extend(events)):
                    lane.feed(controls, now, tick, speed=15., active=component_enabled, enabled=component_enabled)
                  car_state = messaging.new_message("carState", valid=True, logMonoTime=now)
                  car_state.carState = state
                  preview = messaging.new_message("modelV2", valid=True, logMonoTime=now)
                  preview.modelV2 = lane.model()
                  preview.modelV2.action.desiredCurvature = direction * .0008
                  preview.modelV2.orientationRate.z = [direction * .0008 * 15.] * 33
                  delay = messaging.new_message("lateralDelay", valid=True, logMonoTime=now)
                  delay.lateralDelay.lateralDelay = .1
                  controls.sm.update_msgs(now / 1e9, [
                    *[event for event in feed_events if event.which() not in ("carState", "modelV2", "lateralDelay")],
                    car_state.as_reader(), preview.as_reader(), delay.as_reader()])
                  for owner in providers:
                    owner.sm.update_msgs(now / 1e9, [preview.as_reader(), delay.as_reader(), *events] if owner.track_assist_permission else
                                         [preview.as_reader(), delay.as_reader()])
                  command, controller_log = controls.state_control()
                  if kind in ("angle", "default0", "aux"):
                    self.assertTrue(command.enabled and command.latActive)
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
                  if alpha_active and kind == "buttons":
                    alpha_cancel_requested |= bool(command.cruiseControl.cancel)
                  host.can_log_mono_time = now
                  sent.clear()
                  validity.clear()
                  host.controls_update(state, command)
                  if baseline is not None:
                    _, expected = baseline.update(command, host.CI.CS, now)
                    self.assertEqual(sent, expected, (identity, direction, tick, "default0 current bytes"))
                button_frames = [(bus, data) for addr, data, bus in sent if addr == 0x83]
                if kind == "buttons" and button_frames:
                  self.assertEqual([bus for bus, _ in button_frames], [host.CI.CC.CAN.camera, host.CI.CC.CAN.main])
                  paired_cancel |= any(data[1] & 1 for _, data in button_frames)
                  paired_resume |= any(data[3] & 2 for _, data in button_frames)
                for addr, data, bus in sent:
                  if addr == 0x186:
                    self.assertTrue(alpha_active)
                    self.assertEqual(bus, offset)
                    accepted_long = bool(safety.safety_tx_hook(libsafety_py.make_CANPacket(addr, bus - offset, data)))
                    gas = ((data[6] & 3) << 8) | data[7]
                    accel = ((data[0] & 31) << 8) | data[1]
                    gas_pred = ((data[2] & 3) << 8) | data[3]
                    if accepted_long and gas > 500:
                      self.assertTrue(command.longActive and safety.get_controls_allowed() and
                                      safety.safety_config_valid() and not safety.get_relay_malfunction())
                      self.assertGreater(command.actuators.accel, 0)
                      self.assertGreater(accel * .0039 - 20., 0)
                      self.assertLessEqual(gas, 700)
                      self.assertTrue(4231 <= accel <= 5641)
                      self.assertEqual(gas_pred, 0)
                      self.assertAlmostEqual(gas * .01 - 5., host.CI.CC.gas, delta=.01)
                      self.assertAlmostEqual(accel * .0039 - 20., host.CI.CC.accel, delta=.0039)
                      long_positive = True
                      long_recovered |= tick >= 240
                    if 140 <= tick < (160 if kind == "buttons" else 180) and kind in ("cruise", "buttons"):
                      self.assertFalse(accepted_long and gas > 0)
                      long_withdrawn = True
                    if not accepted_long:
                      self.assertTrue(120 <= tick < 230 and
                                      (not safety.get_controls_allowed() or not safety.safety_config_valid() or
                                       safety.get_relay_malfunction()))
                    continue
                  if addr not in (0x83, 0x3CA, 0x3D3, 0x3D6):
                    continue
                  packet = libsafety_py.make_CANPacket(addr, bus - offset, data)
                  if auxiliary is not None:
                    # The other actual configured Panda has no steering/longitudinal TX authority.
                    self.assertFalse(auxiliary.safety_tx_hook(packet))
                    self.assertFalse(auxiliary.get_controls_allowed())
                  accepted = bool(safety.safety_tx_hook(packet))
                  if addr == 0x83:
                    # Native retains its physical-context rules; a held redundant cancel after ACC-off is denied.
                    expected = not safety.get_relay_malfunction() and not (data[1] & 1 and not safety.get_cruise_engaged_prev())
                    self.assertEqual(accepted, expected)
                    continue
                  fd = addr == 0x3D6
                  mode = (data[0] >> 4) & 7 if fd else ((data[4] >> 2) & 7 if addr == 0x3D3 else data[0] >> 5)
                  if selected and addr in (0x3D3, 0x3D6):
                    bad_ack = failing and kind.startswith("panda_") and kind != "panda_stale"
                    if not observed_allowed or observed_relay or not observed_health or bad_ack or kind == "panda_stale" and 151 <= tick < 180:
                      self.assertEqual(mode, 0)
                      withdraw_seen |= kind not in ("angle", "default0", "aux")
                    if mode:
                      path = (((data[3] & 31) << 6) | (data[4] >> 2)) - 1000 if fd else ((data[3] << 3) | (data[4] >> 5)) - 1000
                      if path:
                        path_seen.append(path)
                        resumed |= tick >= 240
                  if not accepted:
                    tx_rejected += 1
                    # During actual faults native blocks immediately; the10Hz public acknowledgment can lag <=one period.
                    self.assertNotIn(kind, ("angle", "default0", "aux", "panda_stale", "buttons"))
                    self.assertTrue(120 <= tick < 230 and (not safety.get_controls_allowed() or not safety.safety_config_valid() or
                                                         safety.get_relay_malfunction()))
                  elif selected and addr in (0x3D3, 0x3D6) and mode:
                    self.assertTrue(safety.get_controls_allowed() and safety.safety_config_valid() and not safety.get_relay_malfunction())
                if tick >= 260:
                  self.assertTrue(safety.get_controls_allowed() and safety.safety_config_valid() and not safety.get_relay_malfunction())
              if alpha_active:
                self.assertTrue(long_positive and long_recovered, "Actual Controls/sender/native Alpha Long never accepted positive acceleration/recovery")
                if kind in ("cruise", "buttons"):
                  self.assertTrue(long_withdrawn, "Physical ACC withdrawal did not block native active longitudinal output")
              if selected:
                self.assertTrue(path_seen, "Production sender never produced an active signed angle")
                self.assertTrue(all(value * direction < 0 for value in path_seen),
                                (identity, scenario, source, direction, min(path_seen), max(path_seen), tuple(path_seen[:8])))
                self.assertTrue(resumed, "Actual factory/physical cruise rearm did not resume accepted angle")
              if kind not in ("angle", "default0", "aux"):
                self.assertTrue(withdraw_seen, "Fault did not withdraw production angle")
              if kind == "counter":
                cadence = 2 if source == sources[0] else 1
                modulus = 16 if source == sources[0] else 256
                fault_ticks = range(120 + cadence - 1, 180, cadence)
                recovery_ticks = range(180 + cadence - 1, 340, cadence)
                # Five consecutive wrong counters reject RX; every recovered sequential sample is accepted.
                self.assertEqual(counter_rx,
                                 [(tick, 0, i < 4) for i, tick in enumerate(fault_ticks)] +
                                 [(tick, (i + 1) % modulus, True) for i, tick in enumerate(recovery_ticks)],
                                 (identity, direction, source))
              if kind in ("crc", "quality", "counter"):
                self.assertGreater(invalid_rx, 0)
              if kind == "buttons":
                button_context = (identity, scenario, direction, cp.safetyConfigs[-1].safetyParam,
                                  alpha_cancel_event_seen, alpha_cancel_requested, alpha_physical_rearmed,
                                  paired_cancel, paired_resume)
                if alpha_active:
                  self.assertTrue(alpha_cancel_event_seen and alpha_cancel_requested and alpha_physical_rearmed and paired_cancel, button_context)
                  self.assertFalse(paired_resume, button_context)
                else:
                  self.assertTrue(paired_cancel and paired_resume, button_context)
              self.assertEqual(Path(params.get_param_path("FordLateralMode")).read_bytes(), b"1" if selected else b"0")
            finally:
              helper.doCleanups()
              safety.set_alternative_experience(0)
              safety.set_safety_hooks(structs.CarParams.SafetyModel.noOutput, 0)
              if auxiliary is not None:
                auxiliary.set_alternative_experience(0)
                auxiliary.set_safety_hooks(structs.CarParams.SafetyModel.noOutput, 0)
              if auxiliary_directory is not None:
                auxiliary_directory.cleanup()
