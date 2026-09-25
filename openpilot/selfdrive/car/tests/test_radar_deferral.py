"""Actual stock Card parsing, control and radar ordering."""
from contextlib import ExitStack
from unittest import mock

import pytest

from opendbc.can import CANPacker
from opendbc.car import Bus
from opendbc.car.hyundai.interface import CarInterface
from opendbc.car.hyundai.radar_interface import RadarInterface
from opendbc.car.hyundai.values import DBC, HyundaiFlags
from openpilot.cereal import messaging, log
from openpilot.common.params import Params
from openpilot.common.prefix import OpenpilotPrefix
from openpilot.selfdrive.car import card as module
from openpilot.selfdrive.car.tests.test_hyundai_aol import candidate


def healthy_stock_card_step(mode="normal"):
  with OpenpilotPrefix(), ExitStack() as stack:
    params = Params()
    params.put_bool('OpenpilotEnabledToggle', True, block=True)
    params.put_bool('AlwaysOnLateral', False, block=True)
    params.put_bool('AlphaLongitudinalEnabled', False, block=True)
    params.put_bool('DisableOpenpilotLongitudinal', True, block=True)
    stock, _ = candidate(False)
    assert not stock.openpilotLongitudinalControl
    assert not stock.flags & HyundaiFlags.CANFD_ENABLE_BLINKERS
    stock.radarUnavailable = False
    ci = CarInterface(stock)
    radar = RadarInterface(stock)
    card = module.Car(CI=ci, RI=radar)
    card.slc_producer_session = 'stock-radar-regression'
    card.wheel_publisher.session = '0123456789abcdef0123456789abcdef'
    assert not card.ioniq6_long_selected and not card.ioniq6_long_prearmed
    assert not card.ci_initialized
    assert radar.msg_count == 32
    packers = {key: CANPacker(parser.dbc.name) for key, parser in ci.can_parsers.items()}
    radar_packer = CANPacker(DBC[stock.carFingerprint][Bus.radar])

    def vehicle_bank():
      frames = []
      for key, parser in ci.can_parsers.items():
        for state in parser.message_states.values():
          values = {}
          if state.name == 'WHEEL_SPEEDS':
            values = dict.fromkeys(('WHL_SpdFLVal', 'WHL_SpdFRVal', 'WHL_SpdRLVal', 'WHL_SpdRRVal'), 72.0)
          if state.name == ci.CS.gear_msg_canfd:
            values['GEAR'] = next((value for value, label in ci.CS.shifter_values.items() if label == 'D'), 0)
          frames.append(packers[key].make_can_msg(state.name, parser.bus, values))
      return frames

    def radar_bank():
      return [radar_packer.make_can_msg(f'RADAR_TRACK_{addr:x}', radar.rcp.bus,
              {'STATE': 3, 'LONG_DIST': float(addr - radar.start_addr + 10), 'LAT_DIST': 0., 'REL_SPEED': -1.})
              for addr in range(radar.start_addr, radar.start_addr + radar.msg_count)]

    for number in range(10):
      cs = ci.update([(9_900_000_000 + number * 10_000_000, vehicle_bank())])
    assert cs.canValid and not cs.canTimeout
    now = 10_000_000_000
    card.CP.passive = mode == 'passive'
    control = messaging.new_message('carControl', valid=mode != 'invalid_control', logMonoTime=now)
    control.carControl.enabled = True
    control.carControl.latActive = True
    control.carControl.longActive = False
    control.carControl.actuators.torque = 0.05
    events = messaging.new_message('onroadEvents', 1 if mode == 'initializing' else 0, valid=True, logMonoTime=now)
    if mode == 'initializing':
      events.onroadEvents[0].name = log.OnroadEvent.EventName.selfdriveInitializing
    device = messaging.new_message('deviceState', valid=True, logMonoTime=now)
    device.deviceState.started = True
    device.deviceState.startedMonoTime = 9_000_000_000
    card.sm.update_msgs(now / 1e9, [control.as_reader(), events.as_reader(), device.as_reader()])
    batch = [(now, vehicle_bank() + radar_bank())]
    trace, messages = [], []
    counts = {'ci': 0, 'ri': 0, 'init': 0, 'apply': 0}
    updates = {'ci': ci.update, 'ri': radar.update}
    calls = {'init': ci.init, 'apply': ci.apply}

    def consume(which, value):
      assert value is batch
      trace.append(which)
      counts[which] += 1
      if which == 'ri' and mode == 'radar_error':
        raise RuntimeError('radar fixture error')
      return updates[which](value)

    def call(which, *args, **kw):
      trace.append(which)
      counts[which] += 1
      return calls[which](*args, **kw)

    def send(service, value):
      trace.append('send:' + service)
      decoded = messaging.log_from_bytes(value) if isinstance(value, bytes) else value
      messages.append((service, decoded.to_dict()))

    new_message = messaging.new_message

    def fixed_message(*args, **kwargs):
      kwargs.setdefault('logMonoTime', now)
      return new_message(*args, **kwargs)

    for target, name, replacement in (
        (module.messaging, 'drain_sock_raw', mock.Mock(return_value=[b'fixture'])),
        (module, 'can_capnp_to_list', mock.Mock(return_value=batch)),
        (module.time, 'monotonic_ns', mock.Mock(return_value=now)),
        (module.time, 'monotonic', mock.Mock(return_value=now / 1e9)),
        (module.messaging, 'new_message', fixed_message),
        (card.sm, 'update', mock.Mock()),
        (card.pm, 'send', send),
        (ci, 'update', lambda value: consume('ci', value)),
        (radar, 'update', lambda value: consume('ri', value)),
        (ci, 'init', lambda *a, **kw: call('init', *a, **kw)),
        (ci, 'apply', lambda *a, **kw: call('apply', *a, **kw))):
      stack.enter_context(mock.patch.object(target, name, replacement))
    stack.enter_context(mock.patch.object(module, 'REPLAY', False))
    if mode == 'direct':
      state, rd = card.state_update()
      assert state.canValid and not state.canTimeout
      assert rd is not None and len(rd.points) == 32
      assert counts == {'ci': 1, 'ri': 1, 'init': 0, 'apply': 0}
      assert trace == ['ci', 'ri']
      assert messages == []
      return {'counts': counts, 'trace': trace}
    if mode == 'radar_error':
      with pytest.raises(RuntimeError, match='^radar fixture error$'):
        card.step()
    else:
      card.step()
    active = mode in ('normal', 'radar_error')
    assert counts == {'ci': 1, 'ri': 1, 'init': int(active), 'apply': int(active)}, counts
    assert card.ci_initialized == active
    assert not card.ioniq6_long_prearmed
    parsed = ci.CS.out
    assert parsed.canValid and not parsed.canTimeout
    by_service = dict(messages)
    if active:
      assert by_service['sendcan']['valid']
      assert by_service['sendcan']['sendcan']
    elif mode == 'invalid_control':
      assert not by_service['sendcan']['valid']
      assert not by_service['sendcan']['sendcan']
    else:
      assert 'sendcan' not in by_service
    if mode == 'radar_error':
      assert 'radarTracks' not in by_service
    else:
      assert by_service['radarTracks']['valid']
      assert len(by_service['radarTracks']['radarTracks']['points']) == 32
    return {'counts': counts, 'trace': trace, 'messages': by_service, 'car_state': parsed.to_dict(),
            'radar_points': [point.to_dict() for point in radar.pts.values()]}


@pytest.mark.parametrize("mode", ("normal", "passive", "initializing", "invalid_control", "radar_error"))
def test_stock_card_publishes_before_radar(mode):
  result = healthy_stock_card_step(mode)
  trace = result['trace']
  assert trace.index('ci') < trace.index('send:carState') < trace.index('ri')
  if mode in ('normal', 'radar_error'):
    assert trace.index('send:carState') < trace.index('init') < trace.index('apply') < trace.index('send:sendcan') < trace.index('ri')
  if mode != 'radar_error':
    assert trace.index('ri') < trace.index('send:radarTracks')


def test_direct_state_update_keeps_eager_radar():
  healthy_stock_card_step("direct")
