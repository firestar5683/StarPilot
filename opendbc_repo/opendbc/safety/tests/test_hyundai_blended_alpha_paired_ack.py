"""Native acknowledgment and caller contract tests with synthetic transport clocks."""
from types import SimpleNamespace
import unittest

from opendbc.car import structs
from opendbc.car.hyundai.blended_longitudinal import BlendedStartup
from opendbc.car.hyundai.interface import CarInterface
from opendbc.car.hyundai.tests.test_palisade_2023 import params
from opendbc.car.hyundai.values import Buttons
from opendbc.safety.tests.libsafety import libsafety_py as lp
from opendbc.safety.tests.test_hyundai import checksum
from openpilot.selfdrive.car.car_events import CarEvents
from openpilot.selfdrive.selfdrived.events import ET
from openpilot.selfdrive.selfdrived.state import StateMachine


class AcknowledgedCancelStream:
  def frames(self, request, button, brake, gas, omit):
    frames = []
    names = set()
    drive = next(key for key, value in self.ci.CS.shifter_values.items() if value in ('D', 'drive'))
    for parser in self.ci.can_parsers.values():
      for address in parser.addresses:
        message = parser.dbc.addr_to_msg[address]
        if message.name in ('SCC11', 'SCC12') or message.name == omit:
          continue
        values = {'COUNTER': self.tick % 16} if 'COUNTER' in message.sigs else {}
        if message.name == 'CGW1':
          values['CF_Gway_DrvSeatBeltSw'] = 1
        elif message.name == 'LVR12':
          values['CF_Lvr_Gear'] = drive
        elif message.name == 'CLU15':
          values['CF_Clu_Gear'] = drive
        elif message.name == 'TCU12':
          values['CUR_GR'] = drive
        elif message.name == 'TCS13':
          values.update(ACCEnable=0, ACC_REQ=int(request), DriverOverride=2 if brake else 0,
                        AliveCounterTCS=self.tick % 8)
        elif message.name == 'CLU11':
          values.update(CF_Clu_CruiseSwState=button, CF_Clu_AliveCnt1=self.tick % 16)
        elif message.name == 'EMS16':
          values.update(CF_Ems_AclAct=int(gas), AliveCounter=self.tick % 4)
        elif message.name == 'WHL_SPD11':
          values.update(WHL_SPD_AliveCounter_LSB=self.tick % 4,
                        WHL_SPD_AliveCounter_MSB=(self.tick % 16) >> 2)
        elif message.name == 'MDPS12':
          values['CR_Mdps_StrColTq'] = 0
        packet = self.packer.make_can_msg(message.name, parser.bus, values)
        if address in (0x260, 0x386, 0x394):
          packet = checksum(packet)
        frames.append(packet)
        names.add((message.name, parser.bus))
    # Exact original HDAI native required LDA alternative, independently of
    # the host parser's lazy address registration.
    if self.pt_bus == 0 and ('BCM_PO_11', 0) not in names:
      frames.append(self.packer.make_can_msg('BCM_PO_11', 0, {}))
    return frames


  def __init__(self, topology, *, request=False):
    from opendbc.can import CANPacker
    from opendbc.car import Bus
    from opendbc.car.hyundai.values import DBC
    stock = params(topology)
    cp = params(topology)
    cp.openpilotLongitudinalControl = True
    cp.pcmCruise = False
    cp.safetyConfigs[0].safetyParam = 0x2014 if topology == 'hdaii' else 0x2004
    self.ci = CarInterface(cp)
    self.pt_bus = int(topology == 'hdaii')
    self.packer = CANPacker(DBC[cp.carFingerprint][Bus.pt])
    self.car_events = CarEvents(cp)
    self.machine = StateMachine()
    self.cc = structs.CarControl()
    self.tick = 0
    self.trace = []
    self.snapshot = None
    self.counters = {}
    self.owner = BlendedStartup(stock, cp, (lambda *args: None, lambda *args: None))
    # Script only the external diagnostic reply; execute the real owner transaction.
    self.owner.owner.exchange = lambda *args, **kwargs: True
    result = self.owner.owner.begin(*self.owner.callbacks, unpublished=True, admission=True)
    assert result.admissible and self.owner.owner.active()
    self.owner.source_floor_ns = 999_999_999  # Explicit synthetic boot epoch.
    self.safety = lp.libsafety
    assert self.safety.set_safety_hooks(cp.safetyConfigs[0].safetyModel.raw, cp.safetyConfigs[0].safetyParam) == 0
    self.safety.init_tests()
    try:
      lp.ffi.cdef('extern bool safety_rx_checks_invalid;')
    except Exception as error:
      if 'multiple declarations' not in str(error):
        raise
    for _ in range(12):
      state = self.step(request=request)
    assert state.canValid and not state.canTimeout
    assert not self.safety.safety_rx_checks_invalid
    assert not self.safety.get_controls_allowed()
    assert not self.trace[-1]['hostEnabled']

  def native_snapshot(self, stamp):
    cp = self.ci.CP
    return (SimpleNamespace(safetyModel=cp.safetyConfigs[0].safetyModel,
                            safetyParam=cp.safetyConfigs[0].safetyParam,
                            alternativeExperience=cp.alternativeExperience,
                            safetyRxChecksInvalid=bool(self.safety.safety_rx_checks_invalid),
                            controlsAllowed=bool(self.safety.get_controls_allowed()),
                            faults=[], ignitionLine=True, ignitionCan=False), stamp, stamp + 1)

  def step(self, *, request=False, button=Buttons.NONE, brake=False, gas=False,
           omit=None, tcs_first=True, evidence='normal', observation=None,
           pulses=(), publish=False):
    frames = self.frames(request, button, brake, gas, omit)
    frames.sort(key=lambda item: (0 if item[0] == (0x394 if tcs_first else 0x4F1)
                                 else 1 if item[0] == (0x4F1 if tcs_first else 0x394) else 2))
    # Optional true→false transitions within one serialized CAN batch.
    for name, values in pulses:
      packet = self.packer.make_can_msg(name, self.pt_bus, values)
      if packet[0] in (0x260, 0x386, 0x394):
        packet = checksum(packet)
      # The pulse arrives before the ordinary final snapshot of this source.
      position = next(i for i, item in enumerate(frames) if item[0] == packet[0])
      frames.insert(position, packet)
    # Counter advances per actual source frame, including multiple samples in
    # one batch. Recompute original RX checksum after changing counter bits.
    counted = []
    for address, data, bus in frames:
      data = bytearray(data)
      key = (address, bus)
      counter = self.counters.get(key, 0)
      if address == 0x260:
        data[7] = (data[7] & 0xC0) | ((counter % 4) << 4)
      elif address == 0x386:
        data[1] = (data[1] & 0x3F) | ((counter % 4) << 6)
        data[3] = (data[3] & 0x3F) | (((counter % 16) >> 2) << 6)
        data[5] &= 0x3F
        data[7] &= 0x3F
      elif address == 0x394:
        data[1] = (data[1] & 0x1F) | ((counter % 8) << 5)
        data[6] &= 0xF0
      elif address == 0x4F1:
        data[3] = (data[3] & 0x0F) | ((counter % 16) << 4)
      else:
        counted.append((address, data, bus))
        continue
      self.counters[key] = counter + 1
      packet = (address, data, bus)
      counted.append(checksum(packet) if address in (0x260, 0x386, 0x394) else packet)
    frames = counted
    can_stamp = 1_000_000_000 + self.tick * 10_000_000
    now = can_stamp + 2000
    self.safety.set_timer(self.tick * 10000)
    rx = [bool(self.safety.safety_rx_hook(lp.make_CANPacket(address, bus, data)))
          for address, data, bus in frames]
    self.safety.safety_tick_current_safety_config()
    previous = self.ci.CS.out
    state = self.ci.update([(can_stamp, frames)])
    # Nominal pandaStates cadence is 10Hz. Its producer timestamp is stamped
    # before reading Panda state; this synthetic sample observes prior CAN RX.
    if self.snapshot is None or self.tick % 10 == 0 or publish:
      self.snapshot = self.native_snapshot(can_stamp + 1000)
    panda, producer, received = observation if observation is not None else self.snapshot
    panda = SimpleNamespace(**vars(panda))
    if evidence == 'wrong_profile':
      panda.safetyParam ^= 0x10
    elif evidence == 'future':
      producer = now + 1
    elif evidence == 'stale':
      producer = received = now - 300_000_001
    matched_clock = 0 < producer <= now and now - producer <= 300_000_000 and 0 < received <= now and now - received <= 300_000_000
    host_enabled = self.trace[-1]['hostEnabled'] if self.trace else False
    self.owner.after_state(ci=self.ci, state=state, now_ns=now,
                           control_enabled=host_enabled, control_current=True,
                           pandas=[panda], panda_log_ns=producer, panda_recv_ns=received,
                           panda_current=matched_clock)
    events = self.car_events.update(state, previous, self.cc)
    enabled, active = self.machine.update(events)
    self.cc.enabled = enabled  # Result of the actual caller, not a seeded intent.
    self.trace.append({'tick': self.tick, 'clockNs': now, 'nativeAllowed': bool(self.safety.get_controls_allowed()),
                      'nativeRxInvalid': bool(self.safety.safety_rx_checks_invalid), 'nativeAllRxAccepted': all(rx),
                      'pandaProducerNs': producer, 'pandaReceiptNs': received, 'pandaAllowed': panda.controlsAllowed,
                      'hostCanValid': bool(state.canValid), 'hostButtonEnable': bool(state.buttonEnable),
                      'hostEnableEvent': events.contains(ET.ENABLE), 'hostNoEntry': events.contains(ET.NO_ENTRY),
                      'hostEnabled': enabled, 'hostActive': active,
                      'hostButtonEvents': [(str(event.type), bool(event.pressed)) for event in state.buttonEvents],
                      'gesture': self.owner.enable_gesture, 'credit': self.owner.enable_credit})
    self.tick += 1
    return state

  def wait_ack(self, *, request=False):
    for _ in range(10):
      state = self.step(request=request)
      if self.trace[-1]['hostEnabled']:
        return state
    raise AssertionError('No acknowledgment within nominal 100ms publication cadence')


class TestBlendedPairedAcknowledgment(unittest.TestCase):
  def setUp(self):
    self.streams = []

  def stream(self, topology, **kwargs):
    stream = AcknowledgedCancelStream(topology, **kwargs)
    self.streams.append(stream)
    return stream


  def assert_host_off(self, stream, state):
    self.assertFalse(state.buttonEnable)
    self.assertFalse(stream.trace[-1]['hostEnabled'])

  def test_delayed_native_ack_and_second_cancel_before_tcs_ack(self):
    for topology in ('hdai', 'hdaii'):
      stream = self.stream(topology)
      stream.step(button=Buttons.CANCEL)
      stream.step(button=Buttons.CANCEL)
      self.assert_host_off(stream, stream.step())
      self.assertTrue(stream.safety.get_controls_allowed())
      self.assertTrue(stream.wait_ack().buttonEnable)
      self.assertFalse(stream.trace[-1]['hostNoEntry'])
      self.assert_host_off(stream, stream.step(button=Buttons.CANCEL))
      self.assertFalse(stream.safety.get_controls_allowed())
      self.assert_host_off(stream, stream.step())
      for _ in range(10):
        self.assert_host_off(stream, stream.step())

  def test_native_rejected_first_pair_then_later_physical_cycles(self):
    for topology in ('hdai', 'hdaii'):
      stream = self.stream(topology)
      for _ in range(11):
        stream.step(omit='TCS13')
      stream.step(button=Buttons.CANCEL, omit='TCS13')
      self.assert_host_off(stream, stream.step(omit='TCS13'))
      self.assertFalse(stream.safety.get_controls_allowed())
      for _ in range(10):
        self.assert_host_off(stream, stream.step())
      stream.step(button=Buttons.CANCEL)
      self.assert_host_off(stream, stream.step())
      self.assertTrue(stream.wait_ack().buttonEnable)
      self.assert_host_off(stream, stream.step(button=Buttons.CANCEL))
      self.assert_host_off(stream, stream.step())
      self.assertFalse(stream.safety.get_controls_allowed())

  def test_wrong_profile_stale_and_future_ack_cannot_enable(self):
    for topology in ('hdai', 'hdaii'):
      for evidence in ('wrong_profile', 'stale', 'future'):
        stream = self.stream(topology)
        stream.step(button=Buttons.CANCEL)
        self.assert_host_off(stream, stream.step())
        self.assertTrue(stream.safety.get_controls_allowed())
        self.assert_host_off(stream, stream.step(evidence=evidence, publish=True))
        for _ in range(10):
          self.assert_host_off(stream, stream.step())

  def test_native_on_cached_before_release_is_not_new_ack(self):
    for topology in ('hdai', 'hdaii'):
      stream = self.stream(topology)
      stream.step(button=Buttons.CANCEL)
      stream.step()
      stream.wait_ack()
      cached_on = stream.snapshot
      stream.step(button=Buttons.CANCEL)
      stream.step()
      stream.step(publish=True)  # Fresh real native OFF witness.
      stream.step(button=Buttons.CANCEL)
      self.assert_host_off(stream, stream.step(observation=cached_on))
      self.assertTrue(stream.safety.get_controls_allowed())
      self.assert_host_off(stream, stream.step(observation=cached_on))
      self.assertTrue(stream.wait_ack().buttonEnable)

  def test_pending_rejected_credit_expires_after_500ms(self):
    for topology in ('hdai', 'hdaii'):
      stream = self.stream(topology)
      for _ in range(11):
        stream.step(omit='TCS13')
      stream.step(button=Buttons.CANCEL, omit='TCS13')
      self.assert_host_off(stream, stream.step(omit='TCS13'))
      credit = stream.owner.enable_credit
      self.assertIsNotNone(credit)
      for _ in range(50):
        self.assert_host_off(stream, stream.step())
      self.assertIsNotNone(stream.owner.enable_credit)
      self.assert_host_off(stream, stream.step())
      self.assertIsNone(stream.owner.enable_credit)
      self.assertFalse(stream.safety.get_controls_allowed())

  def test_set_and_resume_use_fresh_postrelease_native_ack(self):
    for topology in ('hdai', 'hdaii'):
      for button in (Buttons.SET_DECEL, Buttons.RES_ACCEL):
        stream = self.stream(topology, request=True)
        stream.step(request=True, button=button)
        self.assert_host_off(stream, stream.step(request=True))
        self.assertTrue(stream.safety.get_controls_allowed())
        self.assertTrue(stream.wait_ack(request=True).buttonEnable)

  def test_tcs_pedal_and_same_batch_pulses_invalidate_cancel(self):
    for topology in ('hdai', 'hdaii'):
      for inhibit in ('tcs', 'brake', 'gas', 'batch_tcs', 'batch_brake', 'batch_gas'):
        stream = self.stream(topology)
        stream.step(button=Buttons.CANCEL)
        if inhibit.startswith('batch_'):
          signal = inhibit[6:]
          if signal == 'gas':
            pulse = ('EMS16', {'CF_Ems_AclAct': 1, 'AliveCounter': stream.tick % 4})
          else:
            pulse = ('TCS13', {'ACC_REQ': int(signal == 'tcs'),
                              'DriverOverride': 2 if signal == 'brake' else 0,
                              'AliveCounterTCS': stream.tick % 8})
          stream.step(button=Buttons.CANCEL, pulses=(pulse,))
        else:
          stream.step(button=Buttons.CANCEL, request=inhibit == 'tcs', brake=inhibit == 'brake', gas=inhibit == 'gas')
        stream.step(button=Buttons.CANCEL)
        self.assert_host_off(stream, stream.step())
        for _ in range(10):
          self.assert_host_off(stream, stream.step())
        self.assertFalse(stream.safety.get_controls_allowed())

  def test_active_host_same_batch_cancel_press_release_stops_both(self):
    for topology in ('hdai', 'hdaii'):
      stream = self.stream(topology)
      stream.step(button=Buttons.CANCEL)
      stream.step()
      stream.wait_ack()
      self.assertTrue(stream.trace[-1]['hostEnabled'])
      pulse = ('CLU11', {'CF_Clu_CruiseSwState': Buttons.CANCEL})
      self.assert_host_off(stream, stream.step(pulses=(pulse,)))
      self.assertFalse(stream.safety.get_controls_allowed())
      self.assertEqual(len(stream.trace[-1]['hostButtonEvents']), 2)

  def test_source_loss_recovery_and_owner_init_require_a_new_pair(self):
    for topology in ('hdai', 'hdaii'):
      stream = self.stream(topology)
      stream.step(button=Buttons.CANCEL)
      for _ in range(115):
        stream.step(button=Buttons.CANCEL, omit='TCS13')
      self.assertTrue(stream.trace[-1]['nativeRxInvalid'])
      self.assertTrue(any(not sample['hostCanValid'] for sample in stream.trace))
      stream.step(button=Buttons.CANCEL)
      self.assert_host_off(stream, stream.step())
      self.assertFalse(stream.safety.get_controls_allowed())
      for _ in range(10):
        self.assert_host_off(stream, stream.step())
      stream.step(button=Buttons.CANCEL)
      stream.step()
      self.assertIsNotNone(stream.owner.enable_credit)
      replacement = self.stream(topology)
      self.assertIsNone(replacement.owner.enable_credit)
      self.assertIsNone(replacement.owner.enable_gesture)
      self.assert_host_off(replacement, replacement.step())
      self.assertFalse(replacement.safety.get_controls_allowed())
