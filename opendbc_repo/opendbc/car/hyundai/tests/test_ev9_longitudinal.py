from types import SimpleNamespace

from opendbc.car.hyundai.ev9_longitudinal import EV9_DTC_CAPTURE_SLOT_FRAMES, EV9_DTC_CAPTURE_TARGETS, \
                                                    EV9ActuationAbortReason, \
                                                    EV9LongitudinalProbeMode, EV9LongitudinalTestConfig, EV9LongitudinalTestStage, \
                                                    advance_ev9_longitudinal_support_stage, ev9_communication_control_requests, \
                                                    ev9_actuation_abort_reason, \
                                                    ev9_dtc_capture_messages, \
                                                    ev9_longitudinal_test_scc_command, \
                                                    filter_ev9_adrv_replay_messages, \
                                                    get_ev9_longitudinal_test_config, parse_ev9_longitudinal_probe_mode, \
                                                    parse_ev9_longitudinal_test_stage, update_ev9_cruise_main_latch


def test_ev9_cruise_main_latch_toggles_only_on_rising_edges():
  assert update_ev9_cruise_main_latch(False, 0, [0, 1, 1, 0], True)
  assert not update_ev9_cruise_main_latch(True, 0, [1, 0], True)
  assert update_ev9_cruise_main_latch(False, 1, [1, 0], True) is False
  assert update_ev9_cruise_main_latch(False, 0, [0, 0], True) is False


def test_ev9_cruise_main_latch_disabled_preserves_legacy_health_only_behavior():
  assert update_ev9_cruise_main_latch(False, 0, [1, 0], False) is True


class FakeParams:
  def __init__(self, enabled=False, stage=0, probe_mode=0):
    self.enabled = enabled
    self.stage = stage
    self.probe_mode = probe_mode

  def get_bool(self, _key):
    return self.enabled

  def get_int(self, key):
    return self.probe_mode if key.endswith("ProbeMode") else self.stage


def test_stage_parser_fails_closed():
  assert parse_ev9_longitudinal_test_stage(3) == EV9LongitudinalTestStage.RADAR_HEARTBEAT
  assert parse_ev9_longitudinal_test_stage(-1) == EV9LongitudinalTestStage.DISABLED
  assert parse_ev9_longitudinal_test_stage(99) == EV9LongitudinalTestStage.DISABLED
  assert parse_ev9_longitudinal_probe_mode(1) == EV9LongitudinalProbeMode.DIAGNOSTIC_SESSION_ONLY
  assert parse_ev9_longitudinal_probe_mode(2) == EV9LongitudinalProbeMode.TX_DISABLE_ALL_MESSAGE_TYPES
  assert parse_ev9_longitudinal_probe_mode(3) == EV9LongitudinalProbeMode.RX_TX_DISABLE_NORMAL
  assert parse_ev9_longitudinal_probe_mode(4) == EV9LongitudinalProbeMode.RESET_TX_DISABLE_ALL_MESSAGE_TYPES
  assert parse_ev9_longitudinal_probe_mode(5) == EV9LongitudinalProbeMode.FULL_DISABLE_THEN_RX_ENABLE
  assert parse_ev9_longitudinal_probe_mode(99) == EV9LongitudinalProbeMode.COMMUNICATION_CONTROL


def test_probe_requests_have_matching_restores():
  assert ev9_communication_control_requests(EV9LongitudinalProbeMode.COMMUNICATION_CONTROL) == (
    b"\x28\x01\x01", b"\x28\x00\x01")
  assert ev9_communication_control_requests(EV9LongitudinalProbeMode.TX_DISABLE_ALL_MESSAGE_TYPES) == (
    b"\x28\x01\x03", b"\x28\x00\x03")
  assert ev9_communication_control_requests(EV9LongitudinalProbeMode.RX_TX_DISABLE_NORMAL) == (
    b"\x28\x03\x01", b"\x28\x00\x01")
  assert ev9_communication_control_requests(EV9LongitudinalProbeMode.RESET_TX_DISABLE_ALL_MESSAGE_TYPES) == (
    b"\x28\x01\x03", b"\x28\x00\x03")
  assert ev9_communication_control_requests(EV9LongitudinalProbeMode.FULL_DISABLE_THEN_RX_ENABLE) == (
    b"\x28\x01\x03", b"\x28\x00\x03")


def test_dtc_capture_is_one_shot_read_only_and_excludes_adas():
  assert 0x730 not in EV9_DTC_CAPTURE_TARGETS
  for index, addr in enumerate(EV9_DTC_CAPTURE_TARGETS):
    start = index * EV9_DTC_CAPTURE_SLOT_FRAMES
    request, complete = ev9_dtc_capture_messages(start, 1)
    assert not complete
    assert request == [(addr, b"\x03\x19\x02\xFF\x00\x00\x00\x00", 1)]

    flow_control, complete = ev9_dtc_capture_messages(start + 2, 1)
    assert not complete
    assert flow_control == [(addr, b"\x30\x00\x00\x00\x00\x00\x00\x00", 1)]

  messages, complete = ev9_dtc_capture_messages(len(EV9_DTC_CAPTURE_TARGETS) * EV9_DTC_CAPTURE_SLOT_FRAMES, 1)
  assert messages == []
  assert complete


def test_config_requires_explicit_enable_and_tx_disable_stage():
  assert not get_ev9_longitudinal_test_config(FakeParams(False, 10)).armed
  assert not get_ev9_longitudinal_test_config(FakeParams(True, 1)).armed
  assert get_ev9_longitudinal_test_config(FakeParams(True, 2)).armed


def test_persistent_suppression_requires_validated_request_and_heartbeat_stage():
  bounded = EV9LongitudinalTestConfig(True, EV9LongitudinalTestStage.TX_DISABLE,
                                      EV9LongitudinalProbeMode.TX_DISABLE_ALL_MESSAGE_TYPES)
  persistent = EV9LongitudinalTestConfig(True, EV9LongitudinalTestStage.RADAR_HEARTBEAT,
                                         EV9LongitudinalProbeMode.TX_DISABLE_ALL_MESSAGE_TYPES)
  broad = EV9LongitudinalTestConfig(True, EV9LongitudinalTestStage.RADAR_HEARTBEAT,
                                    EV9LongitudinalProbeMode.RX_TX_DISABLE_NORMAL)
  reset_persistent = EV9LongitudinalTestConfig(True, EV9LongitudinalTestStage.RADAR_HEARTBEAT,
                                               EV9LongitudinalProbeMode.RESET_TX_DISABLE_ALL_MESSAGE_TYPES)
  transitioned = EV9LongitudinalTestConfig(True, EV9LongitudinalTestStage.RADAR_HEARTBEAT,
                                           EV9LongitudinalProbeMode.FULL_DISABLE_THEN_RX_ENABLE)

  assert not bounded.persistent_suppression_allowed
  assert persistent.persistent_suppression_allowed
  assert not broad.persistent_suppression_allowed
  assert reset_persistent.persistent_suppression_allowed
  assert transitioned.persistent_suppression_allowed


def test_live_support_stage_changes_are_monotonic_and_do_not_cross_safety_boundaries():
  stage3 = EV9LongitudinalTestConfig(True, EV9LongitudinalTestStage.RADAR_HEARTBEAT,
                                     EV9LongitudinalProbeMode.TX_DISABLE_ALL_MESSAGE_TYPES)
  stage5 = EV9LongitudinalTestConfig(True, EV9LongitudinalTestStage.ADRV_1DA,
                                     EV9LongitudinalProbeMode.TX_DISABLE_ALL_MESSAGE_TYPES)
  stage4 = EV9LongitudinalTestConfig(True, EV9LongitudinalTestStage.ADRV_160,
                                     EV9LongitudinalProbeMode.TX_DISABLE_ALL_MESSAGE_TYPES)
  scc = EV9LongitudinalTestConfig(True, EV9LongitudinalTestStage.SCC_INACTIVE,
                                  EV9LongitudinalProbeMode.TX_DISABLE_ALL_MESSAGE_TYPES)
  ccnc = EV9LongitudinalTestConfig(True, EV9LongitudinalTestStage.CCNC_STATUS,
                                   EV9LongitudinalProbeMode.TX_DISABLE_ALL_MESSAGE_TYPES)
  status_end = EV9LongitudinalTestConfig(True, EV9LongitudinalTestStage.STEERING_KEEPALIVE,
                                         EV9LongitudinalProbeMode.TX_DISABLE_ALL_MESSAGE_TYPES)
  preflight = EV9LongitudinalTestConfig(True, EV9LongitudinalTestStage.ACTUATION_PREFLIGHT,
                                        EV9LongitudinalProbeMode.TX_DISABLE_ALL_MESSAGE_TYPES)
  actuation = EV9LongitudinalTestConfig(True, EV9LongitudinalTestStage.ACTUATION,
                                        EV9LongitudinalProbeMode.TX_DISABLE_ALL_MESSAGE_TYPES)
  broad = EV9LongitudinalTestConfig(True, EV9LongitudinalTestStage.ADRV_1DA,
                                    EV9LongitudinalProbeMode.RX_TX_DISABLE_NORMAL)

  assert advance_ev9_longitudinal_support_stage(stage3, stage5) == stage5
  assert advance_ev9_longitudinal_support_stage(stage5, stage4) == stage5
  assert advance_ev9_longitudinal_support_stage(stage5, scc) == stage5
  assert advance_ev9_longitudinal_support_stage(scc, ccnc) == ccnc
  assert advance_ev9_longitudinal_support_stage(ccnc, status_end) == status_end
  assert advance_ev9_longitudinal_support_stage(status_end, preflight) == status_end
  assert advance_ev9_longitudinal_support_stage(status_end, actuation) == status_end
  assert advance_ev9_longitudinal_support_stage(stage5, broad) == stage5


def test_adrv_replay_is_cumulative_and_drops_uncaptured_0x51():
  messages = [
    (0x51, b"", 0),
    (0x160, b"", 1),
    (0x1DA, b"", 1),
    (0x1EA, b"", 1),
    (0x200, b"", 1),
    (0x345, b"", 1),
  ]
  assert filter_ev9_adrv_replay_messages(EV9LongitudinalTestStage.TX_DISABLE, messages) == []
  assert [m[0] for m in filter_ev9_adrv_replay_messages(EV9LongitudinalTestStage.ADRV_1EA, messages)] == [
    0x160, 0x1DA, 0x1EA,
  ]
  assert [m[0] for m in filter_ev9_adrv_replay_messages(EV9LongitudinalTestStage.ACTUATION, messages)] == [
    0x160, 0x1DA, 0x1EA, 0x200, 0x345,
  ]


def test_scc_is_non_actuating_until_final_stage():
  inactive = EV9LongitudinalTestConfig(True, EV9LongitudinalTestStage.SCC_INACTIVE)
  assert ev9_longitudinal_test_scc_command(inactive, True, -1.5, True, True) == (False, 0.0, False, False)

  preflight = EV9LongitudinalTestConfig(True, EV9LongitudinalTestStage.ACTUATION_PREFLIGHT)
  assert preflight.actuation_test_armed
  assert not preflight.actuation_allowed
  assert ev9_longitudinal_test_scc_command(preflight, True, 0.3, False, False) == (False, 0.0, False, False)

  active = EV9LongitudinalTestConfig(True, EV9LongitudinalTestStage.ACTUATION)
  assert ev9_longitudinal_test_scc_command(active, True, -1.5, True, True) == (True, -0.5, True, True)
  assert ev9_longitudinal_test_scc_command(active, True, 1.5, False, False) == (True, 0.3, False, False)
  assert ev9_longitudinal_test_scc_command(active, True, 0.1, False, False, False) == (False, 0.0, False, False)


def test_actuation_abort_gate_is_inactive_until_control_requested_and_then_fails_closed():
  active = EV9LongitudinalTestConfig(True, EV9LongitudinalTestStage.ACTUATION)
  args = dict(config=active, control_requested=False, was_active=False, drive_gear=False, brake_pressed=True,
              gas_pressed=True, can_valid=False, radar_valid=False, panda_faulted=True, v_ego=20.0)
  assert ev9_actuation_abort_reason(**args) == EV9ActuationAbortReason.NONE

  healthy = dict(config=active, control_requested=True, was_active=False, drive_gear=True, brake_pressed=False,
                 gas_pressed=False, can_valid=True, radar_valid=True, panda_faulted=False, v_ego=1.0)
  assert ev9_actuation_abort_reason(**healthy) == EV9ActuationAbortReason.NONE
  for field, reason in (
    ("drive_gear", EV9ActuationAbortReason.NOT_DRIVE),
    ("brake_pressed", EV9ActuationAbortReason.BRAKE_PRESSED),
    ("gas_pressed", EV9ActuationAbortReason.GAS_PRESSED),
    ("can_valid", EV9ActuationAbortReason.CAN_INVALID),
    ("radar_valid", EV9ActuationAbortReason.RADAR_INVALID),
    ("panda_faulted", EV9ActuationAbortReason.PANDA_FAULT),
  ):
    values = healthy | {field: not healthy[field]}
    assert ev9_actuation_abort_reason(**values) == reason
  assert ev9_actuation_abort_reason(**(healthy | {"v_ego": 5.01})) == EV9ActuationAbortReason.SPEED_LIMIT

  preflight = EV9LongitudinalTestConfig(True, EV9LongitudinalTestStage.ACTUATION_PREFLIGHT)
  assert ev9_actuation_abort_reason(**(healthy | {"config": preflight, "radar_valid": False})) == \
    EV9ActuationAbortReason.RADAR_INVALID


def test_interface_gate_can_be_represented_without_params_backend():
  config = get_ev9_longitudinal_test_config(SimpleNamespace(get_bool=lambda _key: True, get_int=lambda _key: 2))
  assert config.armed
