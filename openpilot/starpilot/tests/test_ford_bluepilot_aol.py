"""Real Ford factory/Card/SelfdriveD/Controls/native combined-owner lifecycle."""
import pytest
from opendbc.car.ford.values import CAR
from openpilot.starpilot.tests.ford_lifecycle_helpers import ford_joined as ford_joined, run_actual_producer

@pytest.fixture(autouse=True)
def combined_angle(monkeypatch, topology):
  monkeypatch.ford_angle = True
  monkeypatch.ford_topology = topology

@pytest.mark.parametrize('identity', [(CAR.FORD_MUSTANG_MACH_E_MK1,18), (CAR.FORD_ESCAPE_MK4,32), (CAR.FORD_F_150_MK14,66)])
@pytest.mark.parametrize('alpha', [False,True])
@pytest.mark.parametrize('hands_free', [False,True])
@pytest.mark.parametrize('topology', ['automatic','manual-multi'])
def test_angle_aol_brake_reverse_fault_and_hands_free(ford_joined,monkeypatch):
  assert ford_joined.host.CI.CC.bp_lat is not None
  run_actual_producer(ford_joined,monkeypatch,scenario='configuration-parity')


@pytest.mark.parametrize('identity', [(CAR.FORD_MUSTANG_MACH_E_MK1,18)])
@pytest.mark.parametrize('alpha', [False,True])
@pytest.mark.parametrize('hands_free', [True])
@pytest.mark.parametrize('topology', ['automatic'])
def test_mache_nonzero_angle_after_brake_with_hands_free(ford_joined,monkeypatch):
  monkeypatch.ford_nonzero = True
  run_actual_producer(ford_joined,monkeypatch,scenario='configuration-parity')


@pytest.mark.parametrize('identity', [(CAR.FORD_MUSTANG_MACH_E_MK1, 18)])
@pytest.mark.parametrize('alpha', [False, True])
@pytest.mark.parametrize('hands_free', [True])
@pytest.mark.parametrize('topology', ['automatic', 'manual-multi'])
def test_tight_turn_speed_window_stays_inside_native_caps(ford_joined, monkeypatch):
  # Route19's first blocked frames exceed Panda's cap by using the latest
  # speed instead of its six-sample minimum. Exercise real parser/native windows.
  monkeypatch.ford_nonzero = True
  monkeypatch.ford_speed_window = True
  monkeypatch.ford_test_curvature = .03
  run_actual_producer(ford_joined, monkeypatch, scenario='configuration-parity')


@pytest.mark.parametrize('identity', [(CAR.FORD_MUSTANG_MACH_E_MK1, 18)])
@pytest.mark.parametrize('alpha', [False, True])
@pytest.mark.parametrize('hands_free', [True])
@pytest.mark.parametrize('topology', ['automatic'])
def test_real_rejected_packet_resynchronizes_without_permission_bypass(ford_joined, monkeypatch):
  from types import SimpleNamespace
  from opendbc.car import structs
  from opendbc.safety.tests.libsafety import libsafety_py

  joined = ford_joined
  native, safety = joined.native, joined.safety
  native.arm()
  adapter = joined.host.CI.CC.bp_lat
  inputs = adapter.host.inputs
  blocked = 0
  monkeypatch.setattr(inputs, 'update', lambda: None)
  monkeypatch.setattr(inputs, 'lateral_snapshot', lambda speed, *, angle=False: None)
  # Isolate the adapter recovery while preserving actual physical native authority.
  # The full caller matrix above retains real wire/inventory/freshness qualification.
  monkeypatch.setattr(inputs, 'native_permission', lambda cp, max_age_ns: bool(safety.aol_get_permission_mask() & 1))
  CC = structs.CarControl(enabled=True, latActive=True)
  CC.actuators.curvature = .0001
  state = structs.CarState(canValid=True, vEgoRaw=15., gearShifter=structs.CarState.GearShifter.drive)
  state.cruiseState.available = True
  CS = SimpleNamespace(out=state, lat_ctl_lim_stat=0)
  rejected = recovered = False
  neutral_after_rejection = False
  for frame in range(180):
    native.pump(1, mask=1, speed=15.)
    now = (1_000_000 + native.tick * 10_000) * 1000
    from openpilot.cereal import messaging
    panda = messaging.new_message('pandaStates', 1, valid=True, logMonoTime=now)
    panda.pandaStates[0].safetyTxBlocked = blocked
    inputs.sm.update_msgs(now / 1e9, [panda.as_reader()])
    packets = []
    if frame % 5 == 0:
      packets += adapter.step_lateral(CC, CS, native.packer, joined.host.CI.CC.CAN, frame, now)
    if frame % 3 == 0:
      packets += adapter.step_lka(native.packer, joined.host.CI.CC.CAN, now)
    for address, original, bus in packets:
      data = bytearray(original)
      active = address == 0x3D6 and (data[0] >> 4) & 7 == 1
      if active and frame >= 80 and not rejected:
        data[1] ^= 1  # One actual bad checksum; native must reject it.
        assert not safety.safety_tx_hook(libsafety_py.make_CANPacket(address, bus, data))
        blocked += 1
        # Feed the real rejected CAN return, not just the aggregate counter.
        adapter.observe_can([(now, [(address, bytes(data), bus | 0xC0)])], bus)
        rejected = True
        continue
      accepted = safety.safety_tx_hook(libsafety_py.make_CANPacket(address, bus, data))
      assert accepted, (frame, hex(address), data.hex())
      if address == 0x3CA:
        adapter.observe_can([(now + 1, [(address, bytes(data), bus | 0x80)])], bus)
      if rejected and address == 0x3D6:
        neutral_after_rejection |= not active
        recovered |= active and neutral_after_rejection
  assert rejected and neutral_after_rejection and recovered
  # Host recovery never replaces native authorization.
  safety.aol_set_host_request(0)
  neutral_seen = False
  for frame in range(180, 195):
    native.pump(1, mask=0, speed=15.)
    now = (1_000_000 + native.tick * 10_000) * 1000
    packets = adapter.step_lateral(CC, CS, native.packer, joined.host.CI.CC.CAN, frame, now)
    packets += adapter.step_lka(native.packer, joined.host.CI.CC.CAN, now)
    for address, data, bus in packets:
      if address == 0x3D6:
        assert (data[0] >> 4) & 7 == 0
        neutral_seen = True
      assert safety.safety_tx_hook(libsafety_py.make_CANPacket(address, bus, data))
      if address == 0x3CA:
        adapter.observe_can([(now + 1, [(address, bytes(data), bus | 0x80)])], bus)
  assert neutral_seen


@pytest.mark.parametrize('identity', [(CAR.FORD_MUSTANG_MACH_E_MK1, 18), (CAR.FORD_ESCAPE_MK4, 32), (CAR.FORD_F_150_MK14, 66)])
@pytest.mark.parametrize('alpha', [True])
@pytest.mark.parametrize('hands_free', [True])
@pytest.mark.parametrize('topology', ['automatic', 'manual-multi'])
def test_native_first_pedal_preserves_only_granted_lateral(ford_joined, monkeypatch):
  monkeypatch.ford_nonzero = True
  monkeypatch.ford_native_first_pedal = True
  run_actual_producer(ford_joined, monkeypatch, scenario='configuration-parity')


@pytest.mark.parametrize('identity', [(CAR.FORD_MUSTANG_MACH_E_MK1, 18)])
@pytest.mark.parametrize('alpha', [True])
@pytest.mark.parametrize('hands_free', [True])
@pytest.mark.parametrize('topology', ['automatic', 'manual-multi'])
def test_early_pedal_admission_requires_exact_marked_angle_long_profile(ford_joined):
  from opendbc.car import structs
  from openpilot.starpilot.car.ford.aol import early_native_long_withdrawal_supported
  cp = ford_joined.host.CP
  assert early_native_long_withdrawal_supported(cp)
  for field, value in (('alternativeExperience', 0), ('openpilotLongitudinalControl', False),
                       ('passive', True), ('dashcamOnly', True), ('brand', 'hyundai')):
    changed = structs.CarParams(**cp.to_dict())
    setattr(changed, field, value)
    assert not early_native_long_withdrawal_supported(changed)
  for mask in (128, 1, 16):
    changed = structs.CarParams(**cp.to_dict())
    changed.safetyConfigs[-1].safetyParam ^= mask
    assert not early_native_long_withdrawal_supported(changed)


@pytest.mark.parametrize('identity', [(CAR.FORD_MUSTANG_MACH_E_MK1, 18), (CAR.FORD_ESCAPE_MK4, 32), (CAR.FORD_F_150_MK14, 66)])
@pytest.mark.parametrize('alpha', [False, True])
@pytest.mark.parametrize('hands_free', [False, True])
@pytest.mark.parametrize('topology', ['automatic', 'manual-multi'])
def test_temporary_eps_recovery_with_gas_preserves_only_lateral_intent(ford_joined, monkeypatch):
  # Route3b: cruise is off, gas remains pressed through a 150 ms EPS pulse.
  # The actual native hook must still reject active output during that pulse.
  monkeypatch.ford_nonzero = True
  monkeypatch.ford_eps_gas = True
  run_actual_producer(ford_joined, monkeypatch, scenario='configuration-parity')


@pytest.mark.parametrize('identity', [(CAR.FORD_MUSTANG_MACH_E_MK1, 18)])
@pytest.mark.parametrize('alpha', [False])
@pytest.mark.parametrize('hands_free', [True])
@pytest.mark.parametrize('topology', ['automatic'])
@pytest.mark.parametrize('delivery', ['paired', 'axis-first', 'event-first', 'never-paired'])
def test_route45_stock_angle_eps_gas_release_join(ford_joined, monkeypatch, delivery):
  monkeypatch.ford_nonzero = True
  monkeypatch.ford_route45_delivery = delivery
  run_actual_producer(ford_joined, monkeypatch, scenario='route45')


@pytest.mark.parametrize('identity', [(CAR.FORD_MUSTANG_MACH_E_MK1, 18)])
@pytest.mark.parametrize('alpha', [False])
@pytest.mark.parametrize('hands_free', [True])
@pytest.mark.parametrize('topology', ['automatic'])
@pytest.mark.parametrize('refusal', ['permanent-eps', 'main-off', 'cancel'])
def test_route45_eps_join_keeps_physical_refusals(ford_joined, monkeypatch, refusal):
  monkeypatch.ford_nonzero = True
  monkeypatch.ford_route45_delivery = 'axis-first'
  monkeypatch.ford_route45_refusal = refusal
  run_actual_producer(ford_joined, monkeypatch, scenario='route45')


@pytest.mark.parametrize('identity', [(CAR.FORD_MUSTANG_MACH_E_MK1, 18), (CAR.FORD_ESCAPE_MK4, 32), (CAR.FORD_F_150_MK14, 66)])
@pytest.mark.parametrize('alpha', [True])
@pytest.mark.parametrize('hands_free', [False, True])
@pytest.mark.parametrize('topology', ['automatic', 'manual-multi'])
def test_route22_gas_held_first_engagement_keeps_aol_through_braking(ford_joined, monkeypatch):
  from openpilot.starpilot.aol.transport_pause import TransportPauseFeedback
  from opendbc.car import structs

  class Changed:
    def __init__(self, source, **values):
      self.source = source
      self.__dict__.update(values)

    def __getattr__(self, name):
      return getattr(self.source, name)

  checked = []
  original = TransportPauseFeedback._first_ford_gas_lateral_grant

  def check_first_grant(feedback, sm, cp, cs, axis, now_ns, *, latched, producer):
    result = original(feedback, sm, cp, cs, axis, now_ns, latched=latched, producer=producer)
    if result is not None and not checked:
      def refuses(*, state=cs, proof=axis, armed=latched, owner=producer, params=cp):
        assert original(feedback, sm, params, state, proof, now_ns, latched=armed, producer=owner) is None
      for field, value in [('gasPressed', False), ('brakePressed', True), ('regenBraking', True),
                           ('canValid', False), ('canTimeout', True), ('steerFaultTemporary', True),
                           ('steerFaultPermanent', True), ('accFaulted', True), ('doorOpen', True),
                           ('seatbeltUnlatched', True), ('vehicleSensorsInvalid', True),
                           ('steeringDisengage', True), ('gearShifter', structs.CarState.GearShifter.reverse)]:
        refuses(state=Changed(cs, **{field: value}))
      for field, value in [('intentProducerSessionId', 'other'), ('intentIntegrityEpoch', axis.intentIntegrityEpoch + 1),
                           ('sessionId', 'other'), ('nativeAcknowledged', False), ('lateralActive', False),
                           ('desiredLateral', False), ('longitudinalActive', True), ('desiredLongitudinal', False),
                           ('faultReason', 'controlsMismatch'), ('mode', 'off'),
                           ('sourceCarStateMonoTime', now_ns - 30_000_001), ('validUntilMonoTime', now_ns - 1)]:
        refuses(proof=Changed(axis, **{field: value}))
      refuses(armed=False)
      refuses(owner='other')
      refuses(params=Changed(cp, alternativeExperience=0))
      for field, value in [('failed', True), ('paused', True), ('pending_event', True),
                           ('healthy_inventory', ('other', ())), ('lateral_baseline_ns', now_ns)]:
        with monkeypatch.context() as local:
          local.setattr(feedback, field, value)
          refuses()
      checked.append(True)
    return result

  monkeypatch.setattr(TransportPauseFeedback, '_first_ford_gas_lateral_grant', check_first_grant)
  monkeypatch.ford_nonzero = True
  run_actual_producer(ford_joined, monkeypatch, scenario='route22')
  assert checked


@pytest.mark.parametrize('identity', [(CAR.FORD_MUSTANG_MACH_E_MK1, 18)])
@pytest.mark.parametrize('alpha', [True])
@pytest.mark.parametrize('hands_free', [True])
@pytest.mark.parametrize('topology', ['automatic'])
@pytest.mark.parametrize('fault', ['rx-quality', 'source-loss'])
def test_route22_native_fault_still_withdraws_aol(ford_joined, monkeypatch, fault):
  monkeypatch.ford_nonzero = True
  monkeypatch.ford_route22_final_fault = fault
  run_actual_producer(ford_joined, monkeypatch, scenario='route22')


@pytest.mark.parametrize('identity', [(CAR.FORD_F_150_LIGHTNING_MK1, 66), (CAR.FORD_ESCAPE_MK4_5, 66),
                                     (CAR.FORD_EXPEDITION_MK4, 66), (CAR.FORD_F_150_MK14, 66), (CAR.FORD_RANGER_MK2, 66)])
@pytest.mark.parametrize('alpha', [False, True])
@pytest.mark.parametrize('hands_free', [False, True])
@pytest.mark.parametrize('topology', ['automatic'])
def test_lightning_cluster_startup_and_aol_recovery(ford_joined, monkeypatch):
  monkeypatch.ford_nonzero = True
  run_actual_producer(ford_joined, monkeypatch, scenario='configuration-parity')


@pytest.mark.parametrize('identity', [(CAR.FORD_F_150_LIGHTNING_MK1, 66)])
@pytest.mark.parametrize('alpha', [False])
@pytest.mark.parametrize('hands_free', [False, True])
@pytest.mark.parametrize('topology', ['automatic'])
@pytest.mark.parametrize('armed', [False, True])
def test_lightning_unarmed_startup_does_not_show_armed_eps_warning(ford_joined, monkeypatch, armed):
  monkeypatch.ford_startup_armed = armed
  run_actual_producer(ford_joined, monkeypatch, scenario='startup-warning')


@pytest.mark.parametrize('identity', [(CAR.FORD_MUSTANG_MACH_E_MK1, 18), (CAR.FORD_ESCAPE_MK4, 32), (CAR.FORD_F_150_MK14, 66)])
@pytest.mark.parametrize('alpha', [False, True])
@pytest.mark.parametrize('hands_free', [True])
@pytest.mark.parametrize('topology', ['automatic', 'manual-multi'])
@pytest.mark.parametrize('can_clock_offset_ns', [0, 9_000_000_000])
def test_angle_transport_batching_keeps_native_spacing(ford_joined, monkeypatch, can_clock_offset_ns):
  from opendbc.car import structs
  from opendbc.safety.tests.libsafety import libsafety_py
  from openpilot.cereal import messaging

  joined = ford_joined
  native, safety, ci = joined.native, joined.safety, joined.host.CI
  native.arm()
  adapter = ci.CC.bp_lat
  inputs = adapter.host.inputs
  monkeypatch.setattr(inputs, 'update', lambda: None)
  monkeypatch.setattr(inputs, 'lateral_snapshot', lambda speed, *, angle=False: None)
  monkeypatch.setattr(inputs, 'native_permission', lambda cp, max_age_ns: bool(safety.aol_get_permission_mask() & 1))
  control = structs.CarControl(enabled=True, latActive=True)
  control.actuators.curvature = .0001
  state = structs.CarState(canValid=True, vEgoRaw=15., gearShifter=structs.CarState.GearShifter.drive)
  state.cruiseState.available = True
  queue, echoes, rejected = [], [], []
  active_count = 0
  control_address = 0x3D6 if adapter.canfd else 0x3D3
  last_delivery = 0
  for frame in range(300):
    now_us = 1_000_000 + (native.tick + 1) * 10_000
    while queue and queue[0][0] <= now_us:
      delivered, address, data, bus = queue.pop(0)
      safety.set_timer(delivered)
      accepted = safety.safety_tx_hook(libsafety_py.make_CANPacket(address, bus - joined.offset, data))
      if not accepted:
        rejected.append((frame, hex(address), data.hex()))
      elif address == control_address:
        active_count += int(((data[0] >> 4) & 7) == 1) if adapter.canfd else int(bool(data[4] & 4))
      echoes.append((delivered * 1000 + can_clock_offset_ns, [(address, data, bus | (0x80 if accepted else 0xC0))]))
    native.pump(1, mask=1, speed=15.)
    # Exercise the actual interface-to-controller feedback path, including Panda
    # bus offsets. Only echoes produced by real native TX acceptance count.
    ci.update(echoes)
    echoes.clear()
    ci.CS.out = state
    now_ns = now_us * 1000
    panda = messaging.new_message('pandaStates', 1, valid=True, logMonoTime=now_ns)
    panda.pandaStates[0].safetyTxBlocked = len(rejected)
    inputs.sm.update_msgs(now_ns / 1e9, [panda.as_reader()])
    _, packets = ci.CC.update(control.as_reader(), ci.CS, now_ns)
    for address, data, bus in packets:
      if address not in (control_address, 0x3CA):
        continue
      # A delayed FIFO batch followed by an immediate one compresses a nominal
      # 50/30ms send cadence below Panda's unchanged 40/20ms minima.
      delivered = max(last_delivery, now_us + (25_000 if frame % 10 == 5 else 0))
      last_delivery = delivered
      queue.append((delivered, address, data, bus))
  assert not rejected, rejected[:8]
  assert active_count > 25
  safety.aol_set_host_request(0)
  native.pump(10, mask=0, speed=15.)
  ci.CS.out = state
  now_ns = (1_000_000 + native.tick * 10_000) * 1000
  packets = adapter.step_lateral(control, ci.CS, native.packer, ci.CC.CAN, 310, now_ns)
  assert packets and safety.aol_get_permission_mask() == 0
  for address, data, bus in packets:
    assert safety.safety_tx_hook(libsafety_py.make_CANPacket(address, bus - joined.offset, data))


@pytest.mark.parametrize('identity', [(CAR.FORD_MUSTANG_MACH_E_MK1, 18), (CAR.FORD_F_150_MK14, 66)])
@pytest.mark.parametrize('alpha', [False, True])
@pytest.mark.parametrize('hands_free', [True])
@pytest.mark.parametrize('topology', ['automatic', 'manual-multi'])
def test_stock_forwarding_returns_cannot_starve_angle_reengagement(ford_joined, monkeypatch):
  from opendbc.car import structs
  from opendbc.car.ford import fordcan
  from opendbc.safety.tests.libsafety import libsafety_py
  from openpilot.cereal import messaging

  joined = ford_joined
  native, safety, ci = joined.native, joined.safety, joined.host.CI
  native.arm()
  adapter = ci.CC.bp_lat
  inputs = adapter.host.inputs
  monkeypatch.setattr(inputs, 'update', lambda: None)
  monkeypatch.setattr(inputs, 'lateral_snapshot', lambda speed, *, angle=False: None)
  monkeypatch.setattr(inputs, 'native_permission', lambda cp, max_age_ns: bool(safety.aol_get_permission_mask() & 1))
  command = structs.CarControl(enabled=True, latActive=True)
  command.actuators.curvature = .0001
  state = structs.CarState(canValid=True, vEgoRaw=15., gearShifter=structs.CarState.GearShifter.drive)
  state.cruiseState.available = True
  echoes = []
  active = [0, 0]
  forwarded = 0
  neutral_seen = False
  # Genuine camera frames are forwarded only while the real native hook permits
  # it. Those forwarded TX returns share the src|0x80 namespace with host TX.
  for frame in range(300):
    native.pump(1, mask=1, speed=15.)
    now_ns = (1_000_000 + native.tick * 10_000) * 1000
    if neutral_seen and frame % 5 == 1:
      stock = fordcan.create_lat_ctl2_msg(native.packer, ci.CC.CAN, 0, 0., 0., 0., 0., (frame // 5) % 16)
      if safety.safety_fwd_hook(2, stock[0]) == 0:
        echoes.append((now_ns, [(stock[0], stock[1], ci.CC.CAN.main | 0x80)]))
        forwarded += 1
    ci.update(echoes)
    echoes.clear()
    ci.CS.out = state
    # Preserve native permission while exercising one normal host neutral pause.
    # Continued forwarding must not prevent a later real active command.
    command.latActive = not 80 <= frame < 130
    panda = messaging.new_message('pandaStates', 1, valid=True, logMonoTime=now_ns)
    panda.pandaStates[0].safetyTxBlocked = 0
    inputs.sm.update_msgs(now_ns / 1e9, [panda.as_reader()])
    _, packets = ci.CC.update(command.as_reader(), ci.CS, now_ns)
    for address, data, bus in packets:
      assert safety.safety_tx_hook(libsafety_py.make_CANPacket(address, bus - joined.offset, data))
      echoes.append((now_ns + 1, [(address, data, bus | 0x80)]))
      if address == 0x3D6:
        is_active = ((data[0] >> 4) & 7) == 1
        if frame < 80:
          active[0] += int(is_active)
        elif frame < 130:
          neutral_seen |= not is_active
        else:
          active[1] += int(is_active)
  assert forwarded > 2
  assert neutral_seen
  assert active[0] > 3 and active[1] > 10, active
  assert safety.aol_get_permission_mask() == 1


@pytest.mark.parametrize('identity', [(CAR.FORD_MUSTANG_MACH_E_MK1, 18), (CAR.FORD_ESCAPE_MK4, 32)])
@pytest.mark.parametrize('alpha', [False, True])
@pytest.mark.parametrize('hands_free', [True])
@pytest.mark.parametrize('topology', ['automatic', 'manual-multi'])
def test_unrelated_native_rejection_does_not_reset_granted_angle(ford_joined, monkeypatch):
  from types import SimpleNamespace
  from opendbc.car import structs
  from opendbc.car.ford import fordcan
  from opendbc.safety.tests.libsafety import libsafety_py
  from openpilot.cereal import messaging

  joined = ford_joined
  native, safety = joined.native, joined.safety
  native.arm()
  adapter = joined.host.CI.CC.bp_lat
  inputs = adapter.host.inputs
  monkeypatch.setattr(inputs, 'update', lambda: None)
  monkeypatch.setattr(inputs, 'lateral_snapshot', lambda speed, *, angle=False: None)
  monkeypatch.setattr(inputs, 'native_permission', lambda cp, max_age_ns: bool(safety.aol_get_permission_mask() & 1))
  control = structs.CarControl(enabled=True, latActive=True)
  control.actuators.curvature = .0001
  state = structs.CarState(canValid=True, vEgoRaw=15., gearShifter=structs.CarState.GearShifter.drive)
  state.cruiseState.available = True
  source = SimpleNamespace(out=state, lat_ctl_lim_stat=0)
  blocked = active_after = 0
  rejected = False
  for frame in range(180):
    native.pump(1, mask=1, speed=15.)
    now = (1_000_000 + native.tick * 10_000) * 1000
    if frame == 80:
      # LONG is independently denied. Its real rejection must not erase LAT.
      message = fordcan.create_acc_msg(native.packer, joined.host.CI.CC.CAN, True, 1., 1., False, False, v_ego_kph=50.)
      address, data, bus = message
      assert not safety.get_controls_allowed()
      assert not safety.safety_tx_hook(libsafety_py.make_CANPacket(address, bus - joined.offset, data))
      assert safety.aol_get_permission_mask() == 1
      adapter.observe_can([(now, [(address, data, bus | 0xC0)])], bus)
      blocked += 1
      rejected = True
    panda = messaging.new_message('pandaStates', 1, valid=True, logMonoTime=now)
    panda.pandaStates[0].safetyTxBlocked = blocked
    inputs.sm.update_msgs(now / 1e9, [panda.as_reader()])
    packets = adapter.step_lateral(control, source, native.packer, joined.host.CI.CC.CAN, frame, now)
    packets += adapter.step_lka(native.packer, joined.host.CI.CC.CAN, now)
    for address, data, bus in packets:
      assert safety.safety_tx_hook(libsafety_py.make_CANPacket(address, bus - joined.offset, data)), (frame, hex(address), data.hex())
      if address == 0x3CA:
        adapter.observe_can([(now + 1, [(address, data, bus | 0x80)])], joined.host.CI.CC.CAN.main)
      if address in (0x3D3, 0x3D6) and frame >= 80:
        active = ((data[4] >> 2) & 7) if address == 0x3D3 else ((data[0] >> 4) & 7)
        assert active == 1, 'Unrelated LONG rejection reset independently granted steering'
        active_after += 1
  assert rejected and active_after > 10
