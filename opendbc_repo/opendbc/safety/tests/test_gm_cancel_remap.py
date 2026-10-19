"""Known Dom bit64 is admitted only for exact supported pedal-long Bolt words."""
import pytest
import unittest
from opendbc.safety.tests.libsafety import libsafety_py
from opendbc.car.gm.tests.test_bolt_cc import native


@pytest.fixture(autouse=True)
def restore_native_configuration():
  safety = libsafety_py.libsafety
  safety.set_alternative_experience(0)
  try:
    yield
  finally:
    safety.set_alternative_experience(0)
    assert safety.set_safety_hooks(19, 0) == 0


@pytest.mark.parametrize('word', [0, 5, 16, 0xE710, 0xE711, 0xE712, 0xE713, 0xC140, 0xE800])
@pytest.mark.parametrize('experience', [64, 96])
def test_remap_bit_on_unqualified_profile_has_no_native_output(word, experience):
  safety = libsafety_py.libsafety
  safety.init_tests()
  safety.set_alternative_experience(experience)
  assert safety.set_safety_hooks(4, word) == 0
  safety.set_aol_test_heartbeat(True)
  safety.aol_set_host_request(3)
  safety.set_controls_allowed(True)
  assert safety.aol_get_permission_mask() == 0
  assert not native('tx', (0x180, bytes(4), 0), 1_000_000)
  assert not native('tx', (0x200, bytes(6), 0), 1_000_000)


@pytest.mark.parametrize('experience', [65, 66, 97, 98, 127, 255])
@pytest.mark.parametrize('word', [0xBD, 0x9D, 0x19D, 0x1CD, 0xE700, 0xE701, 0xE702, 0xE703])
def test_known_profile_does_not_allow_unknown_bits_with_remap(word, experience):
  safety = libsafety_py.libsafety
  safety.init_tests()
  safety.set_alternative_experience(experience)
  assert safety.set_safety_hooks(4, word) == 0
  safety.set_aol_test_heartbeat(True)
  safety.aol_set_host_request(3)
  safety.set_controls_allowed(True)
  assert safety.aol_get_permission_mask() == 0
  assert not native('tx', (0x180, bytes(4), 0), 1_000_000)
  assert not native('tx', (0x200, bytes(6), 0), 1_000_000)


@pytest.mark.parametrize('word', [0x9D, 0x1CD, 0xE701, 0xE703])
@pytest.mark.parametrize('experience', [64, 96])
@pytest.mark.parametrize('condition', ['on', 'absent', 'off', 'stale'])
def test_remap_requires_fresh_physical_main_for_all_active_outputs(word, experience, condition):
  from opendbc.can import CANPacker
  from opendbc.car import Bus
  from opendbc.car.gm.gmcan import create_pedal_command, create_steering_control, create_bolt_regen_paddle, create_bolt_regen_gear
  from opendbc.car.gm.values import CAR, DBC
  from opendbc.car.gm.tests.test_cc_gateway_stock import pt_frames
  from opendbc.car.gm.tests.test_bolt_pedal import TestBoltPedalMessages
  safety = libsafety_py.libsafety
  gen2 = word in (0x1CD, 0xE703)
  packer = CANPacker(DBC[CAR.CHEVROLET_BOLT_CC_2018_2021][Bus.pt])
  safety.init_tests()
  safety.set_alternative_experience(experience)
  assert safety.set_safety_hooks(4, word) == 0
  safety.reset_recorded_can()
  now = 1_000_000

  def feed(stamp, main, counter):
    safety.set_timer(stamp)
    packets = pt_frames(packer, main=main is not False, cruise=False, counter=counter % 4, acc_cruise=0)
    packets = [packet for packet in packets if packet[0] not in (0x1F5, 0xC9)]
    if main is not None:
      packets.append(packer.make_can_msg('ECMEngineStatus', 0, {'CruiseMainOn': int(main)}))
    packets.extend([packer.make_can_msg('ECMPRDNL2', 0, {'PRNDL2': 6}),
                    packer.make_can_msg('EBCMRegenPaddle', 0, {'RegenPaddle': 0}),
                    TestBoltPedalMessages.sensor(packer, 0., counter % 16),
                    (0x3D1, bytes(8), 0)])
    for packet in packets:
      assert native('rx', packet, stamp)
    safety.set_aol_test_heartbeat(True)
    if experience == 96:
      safety.aol_set_host_request(3)
  feed(now, None if condition == 'absent' else True, 0)
  feed(now + 10_000, None if condition == 'absent' else True, 1)
  safety.set_controls_allowed(True)  # Established full engagement before the Main transition.
  if condition == 'off':
    feed(now + 20_000, False, 2)
    assert not safety.get_controls_allowed()
  elif condition == 'stale':
    # Refresh every other physical source so only the original Main receipt expires.
    feed(now + 310_001, None, 2)
  now += 310_001 if condition == 'stale' else 20_000
  safety.set_timer(now)
  safety.set_torque_driver(0, 0)
  safety.set_desired_torque_last(1)
  safety.set_rt_torque_last(1)
  expected = condition == 'on'
  assert bool(native('tx', create_steering_control(packer, 0, 1, 0, True), now)) is expected
  assert bool(native('tx', create_pedal_command(packer, .2, 1), now)) is expected
  assert native('tx', create_steering_control(packer, 0, 0, 1, False), now)
  assert native('tx', create_pedal_command(packer, 0., 2), now)
  # Host paddle feeds are never sent directly. Stock RX invokes the checked scheduler.
  safety.reset_recorded_can()
  assert not native('tx', create_bolt_regen_paddle(packer, True), now)
  assert not native('tx', create_bolt_regen_gear(packer, True, gen2), now)
  native('rx', packer.make_can_msg('EBCMRegenPaddle', 0, {'RegenPaddle': 0}), now)
  native('rx', packer.make_can_msg('ECMPRDNL2', 0, {'PRNDL2': 6}), now)
  assert bool(safety.get_recorded_can_count()) is expected
  if experience == 96 and not expected:
    assert safety.aol_get_permission_mask() == 0


@pytest.mark.parametrize('word', [0x9D, 0x1CD, 0xE701, 0xE703])
@pytest.mark.parametrize('experience', [64, 96])
@pytest.mark.parametrize('condition', ['off', 'stale'])
def test_previously_accepted_applied_paddle_feed_cannot_outlive_main(word, experience, condition):
  from opendbc.can import CANPacker
  from opendbc.car import Bus
  from opendbc.car.gm.gmcan import create_bolt_regen_paddle, create_bolt_regen_gear
  from opendbc.car.gm.values import CAR, DBC
  from opendbc.car.gm.tests.test_cc_gateway_stock import pt_frames
  from opendbc.car.gm.tests.test_bolt_pedal import TestBoltPedalMessages
  safety = libsafety_py.libsafety
  gen2 = word in (0x1CD, 0xE703)
  packer = CANPacker(DBC[CAR.CHEVROLET_BOLT_CC_2018_2021][Bus.pt])
  safety.init_tests()
  safety.set_alternative_experience(experience)
  assert safety.set_safety_hooks(4, word) == 0

  def feed(stamp, main, counter):
    packets = pt_frames(packer, cruise=False, counter=counter % 4, acc_cruise=0)
    packets = [packet for packet in packets if packet[0] not in (0xC9, 0x1F5)]
    packets.extend([packer.make_can_msg('ECMPRDNL2', 0, {'PRNDL2': 6}),
                    packer.make_can_msg('EBCMRegenPaddle', 0, {'RegenPaddle': 0}),
                    TestBoltPedalMessages.sensor(packer, 0., counter % 16), (0x3D1, bytes(8), 0)])
    if main is not None:
      packets.append(packer.make_can_msg('ECMEngineStatus', 0, {'CruiseMainOn': int(main)}))
    for packet in packets:
      assert native('rx', packet, stamp)
    safety.set_aol_test_heartbeat(True)
    if experience == 96:
      safety.aol_set_host_request(3)
  feed(1_000_000, True, 0)
  # Main remains fresh at 280ms; the host feed lease remains fresh when Main later expires.
  feed(1_280_000, None, 1)
  safety.set_controls_allowed(True)
  assert safety.aol_get_permission_mask() == (3 if experience == 96 else 0)
  assert not native('tx', create_bolt_regen_paddle(packer, True), 1_280_000)
  assert not native('tx', create_bolt_regen_gear(packer, True, gen2), 1_280_000)
  # Prove the same feed actually emits while Main is fresh before testing withdrawal.
  safety.reset_recorded_can()
  native('rx', packer.make_can_msg('EBCMRegenPaddle', 0, {'RegenPaddle': 0}), 1_280_001)
  native('rx', packer.make_can_msg('ECMPRDNL2', 0, {'PRNDL2': 6}), 1_280_001)
  assert safety.get_recorded_can_count() == 2
  withdrawn = 1_290_000 if condition == 'off' else 1_310_001
  feed(withdrawn, False if condition == 'off' else None, 2)
  safety.reset_recorded_can()
  native('rx', packer.make_can_msg('EBCMRegenPaddle', 0, {'RegenPaddle': 0}), withdrawn + 1)
  native('rx', packer.make_can_msg('ECMPRDNL2', 0, {'PRNDL2': 6}), withdrawn + 1)
  assert safety.get_recorded_can_count() == 0
  # A new inactive feed can still release the synthetic paddle while Main is absent.
  assert not native('tx', create_bolt_regen_paddle(packer, False), withdrawn + 2)
  assert not native('tx', create_bolt_regen_gear(packer, False, gen2), withdrawn + 2)
  native('rx', packer.make_can_msg('EBCMRegenPaddle', 0, {'RegenPaddle': 0}), withdrawn + 3)
  native('rx', packer.make_can_msg('ECMPRDNL2', 0, {'PRNDL2': 6}), withdrawn + 3)
  assert safety.get_recorded_can_count() == 2


class TestGmCancelRemapCoverage(unittest.TestCase):
  """Unittest coverage uses the same real Main/output contract as pytest."""

  def test_physical_main_gates_active_outputs_and_allows_neutral_release(self):
    safety = libsafety_py.libsafety
    try:
      for word in (0x9D, 0x1CD, 0xE701, 0xE703):
        for experience in (64, 96):
          for condition in ('on', 'absent', 'off', 'stale'):
            with self.subTest(word=word, experience=experience, condition=condition):
              test_remap_requires_fresh_physical_main_for_all_active_outputs(word, experience, condition)
    finally:
      safety.set_alternative_experience(0)
      self.assertEqual(safety.set_safety_hooks(19, 0), 0)

  def test_previously_accepted_paddle_feed_withdraws_but_neutral_release_remains(self):
    safety = libsafety_py.libsafety
    try:
      for word in (0x9D, 0x1CD, 0xE701, 0xE703):
        for experience in (64, 96):
          for condition in ('off', 'stale'):
            with self.subTest(word=word, experience=experience, condition=condition):
              test_previously_accepted_applied_paddle_feed_cannot_outlive_main(word, experience, condition)
    finally:
      safety.set_alternative_experience(0)
      self.assertEqual(safety.set_safety_hooks(19, 0), 0)
