import unittest

from opendbc.car.structs import CarParams
from opendbc.safety.tests.test_hyundai_classic_scc_aol import TestHyundaiClassicSccAol as Shared


class TestNexoStockAol(unittest.TestCase):
  setUp = Shared.setUp
  tearDown = Shared.tearDown
  reset = Shared.reset
  rx = Shared.rx
  request = Shared.request

  def feed(self, word, *, gas=0, gas_bus=0, omit=False, pressed=False):
    Shared.feed(self, word, main=True, source='BCM_PO_11', pressed=pressed)
    if not omit:
      self.rx('FCEV_ACCELERATOR', {'ACCELERATOR_PEDAL': gas}, bus=gas_bus)

  def test_checked_fcev_pedal_cannot_be_overwritten_by_ice(self):
    for word in (0x0500, 0x0D00):
      self.reset(word)
      for _ in range(8):
        self.feed(word)
      self.feed(word, pressed=True)
      self.assertEqual(self.request(1), 1)
      self.feed(word, gas=1)
      self.assertTrue(self.safety.get_gas_pressed_prev())
      self.rx('EMS16', {'AliveCounter': self.counter % 4}, integrity=True)
      self.assertTrue(self.safety.get_gas_pressed_prev())
      self.feed(word, gas=0)
      self.assertFalse(self.safety.get_gas_pressed_prev())
      self.assertEqual(self.request(2), 0)
      self.assertFalse(self.safety.get_controls_allowed())

  def test_pedal_missing_or_wrong_bus_revokes_and_requires_new_gesture(self):
    for wrong_bus in (False, True):
      self.reset(0x0D00)
      for _ in range(8):
        self.feed(0x0D00)
      self.feed(0x0D00, pressed=True)
      self.assertEqual(self.request(1), 1)
      for _ in range(120):
        self.feed(0x0D00, gas_bus=1 if wrong_bus else 0, omit=not wrong_bus)
        self.request(1)
      self.assertEqual(self.request(1), 0)
      for _ in range(8):
        self.feed(0x0D00)
      self.assertEqual(self.request(1), 0)
      self.request(0)
      self.feed(0x0D00, pressed=True)
      self.assertEqual(self.request(1), 1)

  def test_legacy_and_long_namespace_remain_denied(self):
    for word, mode in ((0x0500, CarParams.SafetyModel.hyundaiLegacy),
                       (0x0D00, CarParams.SafetyModel.hyundaiLegacy),
                       (0x0504, CarParams.SafetyModel.hyundai),
                       (0x0D04, CarParams.SafetyModel.hyundai)):
      self.reset(word, mode=mode)
      for _ in range(8):
        self.feed(word, pressed=True)
      self.assertEqual(self.request(1), 0)

  def test_real_ci_and_native_agree_on_checked_pedal_and_ice_injection(self):
    import time

    from opendbc.car import gen_empty_fingerprint
    from opendbc.car.hyundai.interface import CarInterface
    from opendbc.car.hyundai.values import CAR
    from opendbc.safety.tests.libsafety.libsafety_py import make_CANPacket
    from opendbc.safety.tests.test_hyundai import checksum

    cp = CarInterface.get_params(CAR.HYUNDAI_NEXO_1ST_GEN, gen_empty_fingerprint(), [], False, False, False)
    assert cp.safetyConfigs[0].safetyParam == 0x0100
    cp.safetyConfigs[0].safetyParam = 0x0500
    cp.alternativeExperience = 32
    ci = CarInterface(cp)
    ci.update([])
    self.reset(0x0500)
    for tick in range(24):
      self.safety.set_timer(self.now)
      gas = 1 if 8 <= tick < 16 else 0
      packets = []
      sources = ((0, 'CGW1'), (0, 'CGW2'), (0, 'WHL_SPD11'), (0, 'CLU15'),
                 (0, 'SAS11'), (0, 'MDPS12'), (0, 'CLU11'), (0, 'TCS13'),
                 (0, 'TCS15'), (0, 'TCS11'), (0, 'FCEV_ACCELERATOR'), (0, 'EMS20'),
                 (0, 'SCC11'), (0, 'SCC12'), (0, 'EMS16'), (2, 'LKAS11'))
      for bus, name in sources:
        values = {}
        if name == 'FCEV_ACCELERATOR':
          values['ACCELERATOR_PEDAL'] = gas
        elif name == 'EMS16':
          values['AliveCounter'] = tick % 4
        elif name == 'WHL_SPD11':
          values.update(WHL_SPD_AliveCounter_LSB=tick % 4, WHL_SPD_AliveCounter_MSB=(tick // 4) % 4)
        elif name == 'TCS13':
          values['AliveCounterTCS'] = tick % 8
        elif name == 'CLU11':
          values['CF_Clu_AliveCnt1'] = tick % 16
        elif name == 'SCC12':
          values['CR_VSM_Alive'] = tick % 16
        elif name == 'SCC11':
          values['MainMode_ACC'] = 1
        assert set(values) <= set(self.packer.dbc.name_to_msg[name].sigs)
        msg = self.packer.make_can_msg(name, bus, values)
        if name in ('EMS16', 'WHL_SPD11', 'TCS13', 'SCC12'):
          msg = checksum(msg)
        packets.append(msg)
        self.safety.safety_rx_hook(make_CANPacket(msg[0], msg[2], msg[1]))
      state = ci.update([(time.clock_gettime_ns(time.CLOCK_BOOTTIME), packets)])
      assert state.gasPressed == bool(gas)
      assert bool(self.safety.get_gas_pressed_prev()) == bool(gas)
      ice = checksum(self.packer.make_can_msg('EMS16', 0, {'AliveCounter': tick % 4}))
      assert ice[0] == 0x260 and ice[1][7] >> 6 == 0
      self.safety.safety_rx_hook(make_CANPacket(ice[0], ice[2], ice[1]))
      assert bool(self.safety.get_gas_pressed_prev()) == bool(gas)
      self.now += 10_000
