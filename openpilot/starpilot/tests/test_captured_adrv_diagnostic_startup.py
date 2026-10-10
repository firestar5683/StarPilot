"""Captured-ADRV startup admits the exact DOS/redPanda ignition projection."""
import gc
import os
import tempfile
import time
from pathlib import Path
from types import SimpleNamespace
from typing import cast
from unittest.mock import patch

import pytest
from opendbc.car import CanData, car_helpers, gen_empty_fingerprint, structs
from opendbc.can.packer import CANPacker
from opendbc.car.hyundai.ecu_startup import Outcome
from opendbc.car.hyundai.hyundaicanfd import hkg_can_fd_checksum
from opendbc.car.hyundai.ioniq6_handoff import TimestampedCanPacket
from opendbc.car.hyundai.interface import CarInterface
from opendbc.car.hyundai.values import CAR
from openpilot.cereal import messaging
from openpilot.common.params import Params
from openpilot.common.prefix import OpenpilotPrefix
from openpilot.selfdrive.car.card import Car
from openpilot.starpilot.vehicle_startup import VehicleStartupOwner

class _CheckedCan:
  def __init__(self, ci):
    self.ci = ci
    ci.update([])
    self.packers = {bus: CANPacker(parser.dbc.name) for bus, parser in ci.can_parsers.items()}
    self.counters = {}
    self.drive = next(value for value, name in ci.CS.shifter_values.items() if name == 'D')
    # Bind every intended field to its actual message; filtering cannot hide a typo.
    required = {
      ci.CS.gear_msg_canfd: {'GEAR'},
      'DOORS_SEATBELTS': {'DRIVER_SEATBELT'},
      'TCS': {'DriverBraking', 'ACCEnable', 'ACC_REQ'},
      'WHEEL_SPEEDS': {'WHL_SpdFLVal', 'WHL_SpdFRVal', 'WHL_SpdRLVal', 'WHL_SpdRRVal'},
      'MDPS': {'MDPS_StrTqSnsrVal', 'MDPS_OutTqVal', 'MDPS_LkaFailSta'},
      'CRUISE_BUTTONS': {'ADAPTIVE_CRUISE_MAIN_BTN', 'LDA_BTN', 'CRUISE_BUTTONS'},
      'CRUISE_BUTTONS_ALT': {'DISTANCE_UNIT'},
      'SCC_CONTROL': {'ACCMode', 'MainMode_ACC', 'VSetDis'},
    }
    subscribed = {parser.dbc.addr_to_msg[address].name
                  for parser in ci.can_parsers.values() for address in parser.addresses}
    dbc = next(iter(ci.can_parsers.values())).dbc
    for name, fields in required.items():
      assert name in dbc.name_to_msg and fields <= dbc.name_to_msg[name].sigs.keys(), (name, fields)
      if name != 'SCC_CONTROL' or not ci.CP.openpilotLongitudinalControl:
        assert name in subscribed, name
    self.intended_signals = set().union(*required.values())

  def message(self, parser, packer, name, values):
    key = (parser.bus, name)
    count = self.counters.get(key, 0)
    self.counters[key] = count + 1
    signals = parser.dbc.name_to_msg[name].sigs
    assert values.keys() <= signals.keys(), (name, values.keys() - signals.keys())
    counter = {'COUNTER': count % (16 if name == 'CRUISE_BUTTONS' else 256)} if 'COUNTER' in signals else {}
    return packer.make_can_msg(name, parser.bus, {**counter, **values})

  def frames(self, samples, *, acc_fault=False, omit=None, cruise=False, main_available=True, acc_req=False, driver_braking=False):
    frames = []
    for bus, parser in self.ci.can_parsers.items():
      for address in sorted(parser.addresses):
        name = parser.dbc.addr_to_msg[address].name
        if name == omit:
          continue
        common = {'GEAR': self.drive, 'DRIVER_SEATBELT': 1, 'DriverBraking': int(driver_braking), 'ACCEnable': int(acc_fault), 'ACC_REQ': int(acc_req),
                  'WHL_SpdFLVal': 45., 'WHL_SpdFRVal': 45., 'WHL_SpdRLVal': 45., 'WHL_SpdRRVal': 45.,
                  'ACCMode': 1 if cruise else 0, 'MainMode_ACC': int(main_available), 'VSetDis': 60, 'DISTANCE_UNIT': 0,
                  'MDPS_StrTqSnsrVal': 0, 'MDPS_OutTqVal': 0, 'MDPS_LkaFailSta': 0}
        assert common.keys() <= self.intended_signals
        common = {field:value for field,value in common.items() if field in parser.dbc.name_to_msg[name].sigs}
        if name == 'CRUISE_BUTTONS':
          for main, lkas, button in samples:
            frames.append(self.message(parser, self.packers[bus], name,
              {**common, 'ADAPTIVE_CRUISE_MAIN_BTN': main, 'LDA_BTN': lkas, 'CRUISE_BUTTONS': button}))
        else:
          frames.append(self.message(parser, self.packers[bus], name, common))
    return frames


class _StartupTraffic:
  def __init__(self, offset):
    self.offset = offset
    self.counter = 0
    self.stream = None

  def recv(self, wait_for_one=False):
    if self.stream is not None:
      frames = [CanData(*frame) for frame in self.stream.frames([(0, 0, 0)])]
      return [TimestampedCanPacket(frames, time.clock_gettime_ns(time.CLOCK_BOOTTIME))]
    self.counter += 1
    data = bytearray(32)
    data[2], data[4] = self.counter % 256, 7
    data[0:2] = hkg_can_fd_checksum(0x51, None, data).to_bytes(2, 'little')
    return [TimestampedCanPacket([CanData(0x51, bytes(data), self.offset)], time.clock_gettime_ns(time.CLOCK_BOOTTIME))]


class _DiagnosticQuery:
  calls = []
  bus: int = 0

  def __init__(self, send, recv, bus, addresses, requests, responses, **kwargs):
    assert bus == self.bus and addresses == [(0x730, None)]
    command = requests[0]
    assert command in (b'\x10\x03', b'\x28\x83\x01', b'\x28\x00\x01')
    assert responses == [{b'\x10\x03': b'\x50\x03', b'\x28\x83\x01': b'', b'\x28\x00\x01': b'\x68\x00'}[command]]
    self.calls.append((bus, addresses, requests, responses))
    self.send, self.command = send, command

  def get_data(self, timeout):
    self.send([CanData(0x730, bytes((len(self.command),)) + self.command + bytes(7-len(self.command)), self.bus)])
    return {(0x730, None): b''}


CARS = (CAR.KIA_EV6, CAR.GENESIS_GV70_ELECTRIFIED_1ST_GEN)


@pytest.fixture(autouse=True)
def boot_clock():
  with patch.object(time, 'CLOCK_BOOTTIME', getattr(time, 'CLOCK_BOOTTIME', time.CLOCK_MONOTONIC), create=True):
    yield


def factory(car, offset=4):
  fp = gen_empty_fingerprint()
  fp[offset + 2][0x50], fp[offset + 1][0x1cf] = 16, 8
  fw = [structs.CarParams.CarFw(ecu=structs.CarParams.Ecu.adas)]
  cp = CarInterface.get_params(car, fp, fw, True, False, False)
  assert [int(c.safetyParam) for c in cp.safetyConfigs] == ([0, 0x15] if offset else [0x15])
  return cp, fp, fw


def diagnostic_states(types=('dos', 'redPanda'), dos_can=False, external=True):
  msg = messaging.new_message('pandaStates', len(types), valid=True)
  for i, ps in enumerate(msg.pandaStates):
    ps.pandaType, ps.safetyModel, ps.safetyParam = types[i], 'elm327', 1
    ps.ignitionLine = external if i else False
    ps.ignitionCan = dos_can if i == 0 else False
    ps.controlsAllowed = ps.safetyRxChecksInvalid = False
  return msg


@pytest.mark.parametrize('car', CARS)
@pytest.mark.parametrize('case', ('dos_no_can', 'dos_can', 'external_off', 'not_dos', 'not_red',
                                 'wrong_order', 'stale_source', 'future_source', 'stale_receipt',
                                 'invalid', 'not_alive', 'not_seen', 'rx_invalid', 'controls',
                                 'wrong_mode', 'wrong_param', 'offroad', 'controls_ready', 'cp1',
                                 'borrowed_cp', 'wrong_count', 'future_receipt', 'owner_rx_invalid', 'dos_can_external_off'))
def test_actual_card_admission_matrix(car, case):
  cp, _, _ = factory(car, offset=0 if case == 'cp1' else 4)
  owner = CarInterface.startup_owner(cp, (list, lambda frames: None), requested=True)
  holder = VehicleStartupOwner(owner)
  if case == 'borrowed_cp':
    owner.cp.carFingerprint = CAR.HYUNDAI_IONIQ_5
  types = ('dos',) if case == 'cp1' else ('uno', 'redPanda') if case == 'not_dos' else \
          ('dos', 'uno') if case == 'not_red' else ('redPanda', 'dos') if case == 'wrong_order' else ('dos', 'redPanda')
  if case == 'wrong_count':
    types = ('dos', 'redPanda', 'redPanda')
  msg = diagnostic_states(types, case in ('dos_can', 'dos_can_external_off'), case not in ('external_off', 'dos_can_external_off'))
  if case in ('rx_invalid', 'owner_rx_invalid', 'controls', 'wrong_mode', 'wrong_param'):
    ps = msg.pandaStates[1 if case == 'owner_rx_invalid' else 0]
    if case in ('rx_invalid', 'owner_rx_invalid'):
      ps.safetyRxChecksInvalid = True
    elif case == 'controls':
      ps.controlsAllowed = True
    elif case == 'wrong_mode':
      ps.safetyModel = 'noOutput'
    else:
      ps.safetyParam = 0
  sm = SimpleNamespace(update=lambda timeout: None,
                       logMonoTime={'pandaStates': 110_000_000_000 +
                                    (1 if case == 'future_source' else -300_000_001 if case == 'stale_source' else -100_000_000)},
                       recv_time={'pandaStates': 10.000000001 if case == 'future_receipt' else 9.699999999 if case == 'stale_receipt' else 9.9},
                       seen={'pandaStates': case != 'not_seen'}, valid={'pandaStates': case != 'invalid'},
                       alive={'pandaStates': case != 'not_alive'})
  class StateInput:
    def __getattr__(self, name):
      return getattr(sm, name)
    def __getitem__(self, name):
      assert name == 'pandaStates'
      return msg.pandaStates
  host = Car.__new__(Car)
  host.sm, host.vehicle_startup = cast(messaging.SubMaster, StateInput()), holder
  host.params = cast(Params, SimpleNamespace(get_bool=lambda name: (case == 'offroad' and name == 'IsOffroad') or
                                             (case == 'controls_ready' and name == 'ControlsReady')))
  with patch.object(time, 'CLOCK_BOOTTIME', getattr(time, 'CLOCK_BOOTTIME', time.CLOCK_MONOTONIC), create=True), \
       patch.object(time, 'monotonic_ns', return_value=10_000_000_000), \
       patch.object(time, 'clock_gettime_ns', return_value=110_000_000_000):
    assert host.startup_diagnostic_admission() is (case in ('dos_no_can', 'dos_can'))


def construct(car, *, dos_can=False, types=('dos', 'redPanda'), external=True, mode='sent', missing_stock=False):
  cp, fp, fw = factory(car)
  traffic = _StartupTraffic(4)
  trace = []
  _DiagnosticQuery.calls, _DiagnosticQuery.bus = [], 5
  real_get_car = car_helpers.get_car
  def receive(wait_for_one=False):
    packets = traffic.recv(wait_for_one)
    if missing_stock and traffic.stream is not None:
      address = traffic.stream.ci.can_parsers[next(b for b, p in traffic.stream.ci.can_parsers.items() if p.bus == 5)].dbc.name_to_msg['SCC_CONTROL'].address
      return [TimestampedCanPacket([f for f in packet if f.address != address], packet.log_mono_time_ns) for packet in packets]
    return packets
  def get_car(*args, **kwargs):
    ci = real_get_car(*args, **kwargs)
    trace.append(('ci_constructed', ci.CP.openpilotLongitudinalControl))
    traffic.stream = _CheckedCan(ci)
    return ci
  def send(frames):
    for f in frames:
      trace.append(('send', f.address, bytes(f.dat).hex(), f.src))
  def diagnostic(sm, timeout=0):
    msg = diagnostic_states(types, dos_can, external)
    trace.append(('diagnostic', int(msg.logMonoTime), tuple((str(p.pandaType), p.ignitionLine, p.ignitionCan) for p in msg.pandaStates)))
    sm.update_msgs(time.monotonic(), [msg.as_reader()])
  class Query(_DiagnosticQuery):
    def get_data(self, timeout):
      value = super().get_data(timeout)
      if self.command == b'\x28\x83\x01' and mode == 'restored':
        raise OSError('declared partial ECU-disable transport failure')
      return value
  host = Car.__new__(Car)
  try:
    with patch.object(car_helpers, 'fingerprint', return_value=(car, fp, '0' * 17, fw, cp.fingerprintSource, True)), \
         patch('openpilot.selfdrive.car.card.get_car', side_effect=get_car), \
         patch('openpilot.selfdrive.car.card.messaging.recv_one_retry', return_value=SimpleNamespace(can=[1])), \
         patch('openpilot.selfdrive.car.card.can_comm_callbacks', return_value=(receive, send)), \
         patch('openpilot.cereal.messaging.SubMaster.update', diagnostic), \
         patch('opendbc.car.hyundai.ecu_startup.IsoTpParallelQuery', Query), \
         patch('opendbc.car.disable_ecu.IsoTpParallelQuery', Query):
      Car.__init__(host)
    return host, trace
  except BaseException:
    if getattr(host, 'vehicle_startup', None) is not None:
      host.vehicle_startup.close()
    raise


def _exercise_factory_transaction(car, case):
  params = Params()
  for name, value in (('OpenpilotEnabledToggle', True), ('SafeMode', False), ('AlwaysOnLateral', False),
                      ('IsReleaseBranch', False), ('AlphaLongitudinalEnabled', True), ('IsOffroad', False)):
    params.put_bool(name, value, block=True)
  params.put('MainCruiseButtonControl', 0, block=True)
  params.put('LKASButtonControl', 0, block=True)
  started = time.monotonic()
  if case == 'missing_stock':
    with pytest.raises(RuntimeError, match='stock CANFD sources did not become fresh'):
      construct(car, external=False, missing_stock=True)
    assert time.monotonic() - started < 5.0, 'existing three-second stock warmup remains bounded'
    assert not params.get('CarParams'), 'failed warmup cannot publish'
    return
  host, trace = construct(car, dos_can=case == 'dos_can', external=case != 'external_off',
                          types=('uno', 'redPanda') if case == 'not_dos' else ('dos', 'redPanda'),
                          mode='restored' if case == 'restored' else 'sent')
  try:
    owner = host.vehicle_startup.owner
    sends = [(i, row) for i, row in enumerate(trace) if row[0] == 'send']
    disables = [(i, row) for i, row in sends if row[2].startswith('03288301')]
    restores = [(i, row) for i, row in sends if row[2].startswith('03280001')]
    assert owner.ready and owner.published
    assert owner.bus == 5 and owner.template_bus == 4 and owner.camera_bus == 6
    assert host.CP.carFingerprint == car
    assert [int(c.safetyParam) for c in host.CP.safetyConfigs] == ([0, 0x15] if case in ('dos_no_can', 'dos_can') else [0, 0x11])
    if case in ('dos_no_can', 'dos_can'):
      assert owner.outcome is Outcome.SENT_UNCONFIRMED and host.CP.openpilotLongitudinalControl
      assert disables and all(row[1] == 0x730 and row[3] == 5 for _, row in disables)
      assert all(any(t[0] == 'diagnostic' for t in trace[:i]) for i, _ in disables)
      assert not restores
    else:
      assert not host.CP.openpilotLongitudinalControl and host.CP.pcmCruise
      assert owner.outcome is (Outcome.STOCK_RESTORED if case == 'restored' else Outcome.STOCK_UNTOUCHED)
      assert bool(disables) is (case == 'restored') and bool(restores) is (case == 'restored')
      if restores:
        assert disables[0][0] < restores[0][0]
      parser = next(p for p in host.CI.can_parsers.values() if p.bus == 5)
      source = parser.message_states[parser.dbc.name_to_msg['SCC_CONTROL'].address]
      assert source.timestamps[-1] > owner.floor_ns
      assert owner._sources(host.CI, time.clock_gettime_ns(time.CLOCK_BOOTTIME), floor=owner.floor_ns)
    raw = params.get('CarParams')
    assert Path(params.get_param_path('CarParams')).read_bytes() == raw
    with structs.CarParams.from_bytes(raw) as stored:
      assert stored.to_dict() == host.CP.as_reader().to_dict()
  finally:
    host.vehicle_startup.close()


@pytest.mark.parametrize('car', CARS)
@pytest.mark.parametrize('case', ('dos_no_can', 'dos_can', 'external_off', 'not_dos', 'restored', 'missing_stock'))
def test_actual_card_factory_transaction_and_stock_warmup(car, case):
  with tempfile.TemporaryDirectory(prefix='hkg-dos-startup-') as temporary, \
       patch.dict(os.environ, {'PARAMS_ROOT': temporary}), OpenpilotPrefix():
    try:
      _exercise_factory_transaction(car, case)
    finally:
      gc.collect()
