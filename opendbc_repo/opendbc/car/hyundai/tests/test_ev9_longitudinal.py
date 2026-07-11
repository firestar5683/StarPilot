from types import SimpleNamespace

from opendbc.car.hyundai.ev9_longitudinal import EV9_DTC_CAPTURE_SLOT_FRAMES, EV9_DTC_CAPTURE_TARGETS, \
                                                    EV9LongitudinalProbeMode, EV9LongitudinalTestConfig, EV9LongitudinalTestStage, \
                                                    advance_ev9_longitudinal_support_stage, ev9_communication_control_requests, \
                                                    ev9_dtc_capture_messages, \
                                                    ev9_longitudinal_test_scc_command, \
                                                    filter_ev9_adrv_replay_messages, \
                                                    get_ev9_longitudinal_test_config, parse_ev9_longitudinal_probe_mode, \
                                                    parse_ev9_longitudinal_test_stage


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
  assert parse_ev9_longitudinal_probe_mode(99) == EV9LongitudinalProbeMode.COMMUNICATION_CONTROL


def test_probe_requests_have_matching_restores():
  assert ev9_communication_control_requests(EV9LongitudinalProbeMode.COMMUNICATION_CONTROL) == (
    b"\x28\x01\x01", b"\x28\x00\x01")
  assert ev9_communication_control_requests(EV9LongitudinalProbeMode.TX_DISABLE_ALL_MESSAGE_TYPES) == (
    b"\x28\x01\x03", b"\x28\x00\x03")
  assert ev9_communication_control_requests(EV9LongitudinalProbeMode.RX_TX_DISABLE_NORMAL) == (
    b"\x28\x03\x01", b"\x28\x00\x01")


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

  assert not bounded.persistent_suppression_allowed
  assert persistent.persistent_suppression_allowed
  assert not broad.persistent_suppression_allowed


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
  actuation = EV9LongitudinalTestConfig(True, EV9LongitudinalTestStage.ACTUATION,
                                        EV9LongitudinalProbeMode.TX_DISABLE_ALL_MESSAGE_TYPES)
  broad = EV9LongitudinalTestConfig(True, EV9LongitudinalTestStage.ADRV_1DA,
                                    EV9LongitudinalProbeMode.RX_TX_DISABLE_NORMAL)

  assert advance_ev9_longitudinal_support_stage(stage3, stage5) == stage5
  assert advance_ev9_longitudinal_support_stage(stage5, stage4) == stage5
  assert advance_ev9_longitudinal_support_stage(stage5, scc) == stage5
  assert advance_ev9_longitudinal_support_stage(scc, ccnc) == ccnc
  assert advance_ev9_longitudinal_support_stage(ccnc, status_end) == status_end
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

  active = EV9LongitudinalTestConfig(True, EV9LongitudinalTestStage.ACTUATION)
  assert ev9_longitudinal_test_scc_command(active, True, -1.5, True, True) == (True, -1.5, True, True)


def test_interface_gate_can_be_represented_without_params_backend():
  config = get_ev9_longitudinal_test_config(SimpleNamespace(get_bool=lambda _key: True, get_int=lambda _key: 2))
  assert config.armed
