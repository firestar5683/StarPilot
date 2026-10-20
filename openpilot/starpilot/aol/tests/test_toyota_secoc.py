"""Always On Lateral on the SecOC Sienna (TOYOTA_SIENNA_4TH_GEN, safety param 2121)."""
import unittest

from opendbc.car import gen_empty_fingerprint, structs
from opendbc.car.toyota.interface import CarInterface
from opendbc.car.toyota.values import CAR, ToyotaFlags
from openpilot.starpilot.aol.vehicle import policy_for
from openpilot.starpilot.car.toyota.aol import AOL_WORDS, native_accepts_cp, native_profile_supported, qualified
from openpilot.starpilot.longitudinal.toyota_output_policy import production_enabled

TOYOTA = int(structs.CarParams.SafetyModel.toyota)


def sienna(key=True):
  fp = gen_empty_fingerprint()
  fp[0][0x3F6] = 8
  cp = CarInterface.get_params(CAR.TOYOTA_SIENNA_4TH_GEN, fp, [structs.CarParams.CarFw(ecu=structs.CarParams.Ecu.hybrid)],
                               False, False, False)
  cp.secOcKeyAvailable = key
  return cp


class TestSiennaSecocAol(unittest.TestCase):
  def test_factory_params_match_the_logged_car(self):
    cp = sienna()
    self.assertEqual(int(cp.flags), 3099)
    self.assertEqual([(c.safetyModel, c.safetyParam) for c in cp.safetyConfigs],
                     [(structs.CarParams.SafetyModel.toyota, 2121)])
    self.assertTrue(cp.openpilotLongitudinalControl and cp.secOcRequired and cp.pcmCruise)

  def test_admitted_and_marked_like_the_other_toyotas(self):
    cp = sienna()
    self.assertTrue(qualified(cp))
    self.assertFalse(qualified(cp, marked_only=True))
    policy = policy_for(cp)
    self.assertTrue(policy.settings_supported and policy.full_axis_runtime_required)
    self.assertEqual(policy.alternative_experience_addition, 32)
    cp.alternativeExperience |= policy.alternative_experience_addition
    self.assertTrue(qualified(cp, marked_only=True))
    self.assertTrue(native_accepts_cp(cp, TOYOTA, 2121))
    self.assertIn(2121, AOL_WORDS)
    self.assertTrue(native_profile_supported(TOYOTA, 2121))

  def test_secoc_longitudinal_output_stays_on_with_aol(self):
    cp = sienna()
    self.assertTrue(production_enabled(cp))
    cp.alternativeExperience = 32
    self.assertTrue(production_enabled(cp))
    cp.alternativeExperience = 160
    self.assertFalse(production_enabled(cp))

  def test_everything_else_is_refused(self):
    mutations = {
      'no key': lambda cp: setattr(cp, 'secOcKeyAvailable', False),
      'not secoc required': lambda cp: setattr(cp, 'secOcRequired', False),
      'stock long': lambda cp: setattr(cp, 'openpilotLongitudinalControl', False),
      'no pcm cruise': lambda cp: setattr(cp, 'pcmCruise', False),
      'passive': lambda cp: setattr(cp, 'passive', True),
      'dashcam': lambda cp: setattr(cp, 'dashcamOnly', True),
      'angle': lambda cp: setattr(cp, 'steerControlType', structs.CarParams.SteerControlType.angle),
      'word 73': lambda cp: setattr(cp.safetyConfigs[0], 'safetyParam', 73),
      'word 2120': lambda cp: setattr(cp.safetyConfigs[0], 'safetyParam', 2120),
      'no output': lambda cp: setattr(cp.safetyConfigs[0], 'safetyModel', structs.CarParams.SafetyModel.noOutput),
      'no secoc flag': lambda cp: setattr(cp, 'flags', int(cp.flags) & ~int(ToyotaFlags.SECOC)),
      'extra flag': lambda cp: setattr(cp, 'flags', int(cp.flags) | int(ToyotaFlags.AUTO_BRAKE_HOLD)),
      'hold experience': lambda cp: setattr(cp, 'alternativeExperience', 160),
      'other car': lambda cp: setattr(cp, 'carFingerprint', CAR.TOYOTA_RAV4_TSS2),
    }
    for name, mutate in mutations.items():
      with self.subTest(name):
        cp = sienna()
        mutate(cp)
        self.assertFalse(qualified(cp), name)
        self.assertFalse(policy_for(cp).settings_supported, name)
    self.assertFalse(qualified(sienna(key=False)))


if __name__ == '__main__':
  unittest.main()




from contextlib import contextmanager
import os
from unittest import mock

import pytest

from opendbc.can import CANPacker
from opendbc.car import Bus
from opendbc.car.secoc import add_mac, build_sync_mac
from opendbc.car.toyota.values import DBC
from openpilot.cereal import messaging
from openpilot.common.params import Params
from openpilot.common.prefix import OpenpilotPrefix
from openpilot.selfdrive.car.card import Car
from openpilot.selfdrive.controls.controlsd import Controls
from openpilot.starpilot.aol.vehicle import native_matches_cp
from openpilot.starpilot.car.toyota.security_key import decode_key
from openpilot.starpilot.lateral.tests.test_lane_runtime import feed

TEST_KEY = '11' * 16


@contextmanager
def actual_card(raw_key=TEST_KEY, *, simulation=True):
  with OpenpilotPrefix(), mock.patch.dict(os.environ, {'SIMULATION': '1' if simulation else '0', 'AOL_REPLAY_RUNTIME': '0',
                                                       'TOYOTA_LONG_OUTPUT_REPLAY_RUNTIME': '0'}):
    params = Params()
    params.put_bool('OpenpilotEnabledToggle', True, block=True)
    params.put_bool('SafeMode', False, block=True)
    params.put_bool('AlwaysOnLateral', True, block=True)
    params.put('LKASButtonControl', 8, block=True)
    if raw_key is not None:
      params.put('SecOCKey', raw_key, block=True)
    cp = sienna(key=False)
    interface = CarInterface(cp)

    with mock.patch('openpilot.selfdrive.car.card.open', side_effect=FileNotFoundError, create=True):
      selected = Car(CI=interface, RI=interface.RadarInterface(cp))
    try:
      yield selected, params
    finally:
      selected.vehicle_startup.close()
      del selected


def parsed_state(interface, *, gear=3, main=True, door=False, belt=True, eps=1, lda=0, now_ns=1_000_000_000, ticks=8):
  interface.update([])
  packer = getattr(interface, '_secoc_fixture_packer', None)
  if packer is None:
    packer = CANPacker(DBC[interface.CP.carFingerprint][Bus.pt])
    interface._secoc_fixture_packer = packer
  tracked = {bus: tuple(parser.vl) for bus, parser in interface.can_parsers.items()}
  values: dict[str, dict[str, float]] = {
    'PCM_CRUISE': {'CRUISE_ACTIVE': 0}, 'PCM_CRUISE_2': {'MAIN_ON': main},
    'GEAR_PACKET_HYBRID': {'GEAR': gear}, 'EPS_STATUS': {'LKA_STATE': eps},
    'BODY_CONTROL_STATE': {'DOOR_OPEN_FL': door, 'SEATBELT_DRIVER_UNLATCHED': not belt},
    'WHEEL_SPEEDS': {f'WHEEL_SPEED_{wheel}': 72 for wheel in ('FR', 'FL', 'RR', 'RL')},
    'LKAS_HUD': {'LDA_ON_MESSAGE': lda},
    'SECOC_SYNCHRONIZATION': {'TRIP_CNT': 1, 'RESET_CNT': 1,
                             'AUTHENTICATOR': build_sync_mac(bytes.fromhex(TEST_KEY), 1, 1)},
  }


  for tick in range(ticks):


    frames_by_id = {}
    for bus, names in tracked.items():
      for name in names:
        if isinstance(name, str):
          frame = packer.make_can_msg(name, 0 if bus == Bus.pt else 2, values.get(name, {}))
          frames_by_id[(frame[0], frame[2])] = frame
    frames = list(frames_by_id.values())
    state = interface.update([(now_ns + tick * 10_000_000, frames)])
  return state, frames


@pytest.mark.parametrize('key', (None, '', 'not-a-key', '11' * 15, TEST_KEY))
def test_actual_card_decodes_key_before_aol_admission_and_publishes_exact_profile(key):
  with actual_card(key) as (selected, saved):
    admitted = decode_key(key) is not None
    assert selected.CP.secOcKeyAvailable == admitted
    assert selected.aol_qualified == admitted
    assert selected.CP.alternativeExperience == (32 if admitted else 0)
    assert selected.CP.safetyConfigs[0].safetyParam == 2121
    assert selected.CP.secOcRequired and selected.CP.openpilotLongitudinalControl
    assert policy_for(selected.CP).auxiliary_lkas_supported
    assert saved.get('LKASButtonControl') == 8
    if admitted:
      assert selected.aol_card_intent.settings.lkas_action == selected.aol_card_intent.settings.main_action == 0
      assert selected.CI.CS.secoc_key == selected.CI.CC.secoc_key == bytes.fromhex(TEST_KEY)
      assert native_matches_cp(selected.CP, TOYOTA, 2121)
      assert production_enabled(selected.CP)
    else:
      assert selected.aol_card_intent is None
      assert not production_enabled(selected.CP)
    with structs.CarParams.from_bytes(saved.get('CarParams')) as published:
      assert published.to_dict() == selected.CP.to_dict()
    controls = Controls()
    assert controls.CP.to_dict() == selected.CP.to_dict()
    if admitted:
      assert controls.aol_replay
      from openpilot.selfdrive.selfdrived.selfdrived import SelfdriveD
      from openpilot.selfdrive.controls.lib.longcontrol import LongControl
      from openpilot.starpilot.longitudinal.tests.extension_helpers import extension_state
      with mock.patch('openpilot.selfdrive.selfdrived.selfdrived.REPLAY', False):
        selfdrived = SelfdriveD(CP=selected.CP)
      assert selfdrived.aol_replay and selfdrived.axis_transport_required
      assert extension_state(LongControl(selected.CP), 'toyota_output') is not None
      del selfdrived
    del controls


@pytest.mark.parametrize('gear,expected', ((0, 'park'), (1, 'reverse'), (2, 'neutral'), (3, 'drive'), (4, 'brake')))
def test_actual_secoc_factory_parser_uses_hybrid_gear_without_legacy_gear(gear, expected):
  cp = sienna()
  interface = CarInterface(cp)
  state, frames = parsed_state(interface, gear=gear)
  assert state.canValid and not state.canTimeout
  assert str(state.gearShifter) == expected
  pt_addresses = {address for address, _, bus in frames if bus == 0}
  assert 0x127 in pt_addresses
  assert sum(address == 0x127 and bus == 0 for address, _, bus in frames) == 1
  assert 0x3BC not in pt_addresses

  packer = CANPacker(DBC[cp.carFingerprint][Bus.pt])
  raw = next(payload for address, payload, bus in frames if address == 0x127 and bus == 0)
  assert raw[5] >> 4 == gear
  legacy = packer.make_can_msg('GEAR_PACKET', 0, {'GEAR': 0})
  after_legacy = interface.update([(1_080_000_000, [legacy])])
  assert str(after_legacy.gearShifter) == expected


@pytest.mark.parametrize('vehicle', (CAR.TOYOTA_RAV4_PRIME, CAR.TOYOTA_YARIS, CAR.TOYOTA_RAV4_TSS2_2023))
def test_other_secoc_and_angle_factories_never_join_sienna_aol(vehicle):
  cp = CarInterface.get_params(vehicle, gen_empty_fingerprint(), [], False, False, False)
  cp.secOcKeyAvailable = True
  cp.alternativeExperience = 32
  assert not qualified(cp)
  assert not policy_for(cp).intent_supported
  assert not native_matches_cp(cp, TOYOTA, cp.safetyConfigs[0].safetyParam)
  assert policy_for(cp).auxiliary_lkas_supported


def test_component_controls_authenticated_controller_and_native_secoc_aol():



  from opendbc.safety.tests.libsafety import libsafety_py
  safety = libsafety_py.libsafety
  with actual_card() as (selected, _):
    controls = Controls()
    physical, frames = parsed_state(selected.CI)
    assert physical.canValid and not physical.canTimeout
    assert physical.gearShifter == structs.CarState.GearShifter.drive
    assert physical.cruiseState.available and not physical.cruiseState.enabled
    selected.aol_card_intent.update(physical.as_reader())
    assert selected.aol_card_intent.allowed_latch
    for tick in range(20):
      now = 2_000_000_000 + tick * 10_000_000
      incoming = []
      with mock.patch.object(controls.sm, 'update_msgs', side_effect=lambda _time, messages, packets=incoming: packets.extend(messages)):
        feed(controls, now, tick, active=False, enabled=False, independent=True)
      event = messaging.new_message('carState', valid=True, logMonoTime=now)
      event.carState = physical


      controls.sm.update_msgs(now / 1e9, [sample for sample in incoming if sample.which() != 'carState'] + [event.as_reader()])
      with mock.patch('openpilot.selfdrive.controls.controlsd.time.monotonic_ns', return_value=now):
        command, _ = controls.state_control()
    assert command.latActive and not command.longActive
    safety.init_tests()
    safety.set_alternative_experience(32)
    safety.set_safety_hooks(structs.CarParams.SafetyModel.toyota, 2121)
    safety.set_timer(1_000_000)
    safety.set_aol_test_heartbeat(True)
    for address, payload, bus in frames:
      assert safety.safety_rx_hook(libsafety_py.make_CANPacket(address, bus, payload))
    safety.aol_set_host_request(1)
    assert safety.aol_get_permission_mask() == 1
    _, sends = selected.CI.apply(command.as_reader(), 2_200_000_000)
    steer = next(frame for frame in sends if frame[0] == 0x2E4)
    torque = int.from_bytes(steer[1][1:3], 'big', signed=True)
    assert len(steer[1]) == 8 and 0 < abs(torque) <= 15 and steer[1][0] & 1
    assert steer == add_mac(bytes.fromhex(TEST_KEY), 1, 1, 0, (steer[0], steer[1][:4], steer[2]))
    assert safety.safety_tx_hook(libsafety_py.make_CANPacket(steer[0], steer[2], steer[1]))

    packer = CANPacker(DBC[selected.CP.carFingerprint][Bus.pt])
    address, payload, bus = packer.make_can_msg('GEAR_PACKET_HYBRID', 0, {'GEAR': 0})
    assert safety.safety_rx_hook(libsafety_py.make_CANPacket(address, bus, payload))
    assert safety.aol_get_permission_mask() == 0
    assert not safety.safety_tx_hook(libsafety_py.make_CANPacket(steer[0], steer[2], steer[1]))
    safety.set_alternative_experience(0)
    safety.set_safety_hooks(structs.CarParams.SafetyModel.noOutput, 0)
    del controls


def test_secoc_fixture_advances_real_counter_and_duplicate_counter_invalidates_can():
  interface = CarInterface(sienna())
  state, first = parsed_state(interface)
  assert state.canValid and not state.canTimeout
  first_count = next(payload[3] & 0xF for address, payload, bus in first if address == 0x24D and bus == 0)
  state, second = parsed_state(interface, now_ns=1_080_000_000, ticks=1)
  assert state.canValid and not state.canTimeout
  second_count = next(payload[3] & 0xF for address, payload, bus in second if address == 0x24D and bus == 0)
  assert second_count == (first_count + 1) % 16


  for tick in range(8):
    state = interface.update([(1_090_000_000 + tick * 10_000_000, second)])
  assert not state.canValid and not state.canTimeout
