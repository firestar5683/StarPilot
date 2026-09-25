import unittest

from opendbc.can import CANPacker
from opendbc.car import Bus, structs
from opendbc.car.hyundai.carstate import CarState
from opendbc.car.hyundai.interface import CarInterface
from opendbc.car.hyundai.tests.test_palisade_2023 import params
from opendbc.car.hyundai.values import Buttons, DBC


def alpha_state(topology):
  cp = params(topology)
  cp.openpilotLongitudinalControl = True
  cp.pcmCruise = False
  cp.safetyConfigs[0].safetyParam |= 4
  state = CarState(cp)
  return state, state.get_can_parsers(cp), CANPacker(DBC[cp.carFingerprint][Bus.pt])


def feed(state, parsers, packer, tick, *, request=0, available=True, button=Buttons.NONE, omit=None):
  frames = []
  for parser in parsers.values():
    for address in parser.addresses:
      message = parser.dbc.addr_to_msg[address]
      if message.name in ('SCC11', 'SCC12') or message.name == omit:
        continue
      values = {'COUNTER': tick % 16} if 'COUNTER' in message.sigs else {}
      if message.name == 'TCS13':
        values.update(ACCEnable=0 if available else 1, ACC_REQ=request)
      elif message.name == 'CLU11':
        values['CF_Clu_CruiseSwState'] = button
      frames.append(packer.make_can_msg(message.name, parser.bus, values))
  for parser in parsers.values():
    parser.update([(1_000_000_000 + tick * 10_000_000, frames)])
  result = state.update(parsers)
  state.out = result
  return result


class TestBlendedCarState(unittest.TestCase):
  def test_alpha_disabled_scc_optional_and_independent_sources_required(self):
    for topology in ('hdai', 'hdaii'):
      state, parsers, packer = alpha_state(topology)
      pt = parsers[Bus.pt]
      self.assertNotIn(0x420, pt.message_states)
      if topology == 'hdaii':
        self.assertTrue(pt.message_states[0x421].ignore_alive)
      else:
        self.assertNotIn(0x421, pt.message_states)
      for tick in range(12):
        result = feed(state, parsers, packer, tick, request=1)
      self.assertTrue(pt.can_valid)
      self.assertTrue(result.cruiseState.available and result.cruiseState.enabled)
      self.assertFalse(result.cruiseState.standstill or result.cruiseState.nonAdaptive)
      for tick in range(12, 75):
        feed(state, parsers, packer, tick, omit='TCS13')
        _ = pt.can_valid  # The interface samples health on every source update.
      self.assertFalse(pt.can_valid)


  def test_stock_parser_and_cancel_behavior_unchanged(self):
    for topology in ('hdai', 'hdaii'):
      cp = params(topology)
      ci = CarInterface(cp)
      for address in (0x420, 0x421):
        self.assertEqual(ci.can_parsers[Bus.pt].message_states[address].frequency, 50)
      ci.CS.out.cruiseState.enabled = False
      events = ci.CS.create_cruise_button_events(Buttons.CANCEL, Buttons.NONE)
      self.assertEqual(events[0].type, structs.CarState.ButtonEvent.Type.cancel)
