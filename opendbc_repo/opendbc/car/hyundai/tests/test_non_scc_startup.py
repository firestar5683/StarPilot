"""Forte receive topology and startup state."""
import itertools
import unittest
from unittest.mock import patch

from opendbc.can import CANPacker
from opendbc.car import Bus, gen_empty_fingerprint, structs
from opendbc.car.hyundai.interface import CarInterface
from opendbc.car.hyundai.non_scc_aol import aol_word, qualified, AOL_EXPERIENCE
from opendbc.car.hyundai.values import CAR, DBC, HyundaiFlags
from opendbc.safety.tests.test_hyundai import checksum


FORTE_IDS = (CAR.KIA_FORTE_2019_NON_SCC, CAR.KIA_FORTE_2021_NON_SCC)
# Fixed classic source set, independent of the production parser's subscriptions.
PT_RATES = {'MDPS12': 50, 'TCS11': 100, 'TCS13': 50, 'TCS15': 10, 'CLU11': 50,
            'CLU15': 5, 'ESP12': 100, 'CGW1': 10, 'CGW2': 5, 'WHL_SPD11': 50,
            'SAS11': 100, 'EMS12': 100, 'EMS16': 100, 'LVR12': 100}


def params(identity, *, source=0x391, alpha=False, aol=False, fca=False, bsm=False):
  fp = gen_empty_fingerprint()
  if source:
    fp[0][source] = 8
  if fca:
    fp[2][0x38d] = 8
  if bsm:
    fp[0][0x58b] = 8
  cp = CarInterface.get_params(identity, fp, [], alpha, False, False)
  if aol:
    cp.safetyConfigs[0].safetyParam = aol_word(cp)
    cp.alternativeExperience = AOL_EXPERIENCE
  return cp


class ForteReceiveStream:
  def __init__(self, cp, *, source=0x391):
    self.ci = CarInterface(cp)
    self.source = source
    self.packer = CANPacker(DBC[cp.carFingerprint][Bus.pt])
    self.tick = 0
    self.now = 1_000_000_000
    self.gear = next(code for code, name in self.ci.CS.shifter_values.items() if name == 'D')

  def step(self, *, missing=None, wrong_bus=None, held=False, fca=True):
    n = self.tick
    self.tick += 1
    self.now += 10_000_000
    values = {'EMS16': {'CRUISE_LAMP_M': 1, 'CRUISE_LAMP_S': 1, 'AliveCounter': n % 4},
              'WHL_SPD11': {'WHL_SPD_FL': 72, 'WHL_SPD_FR': 72, 'WHL_SPD_RL': 72, 'WHL_SPD_RR': 72,
                           'WHL_SPD_AliveCounter_LSB': n % 4, 'WHL_SPD_AliveCounter_MSB': n // 4 % 4},
              'TCS13': {'AliveCounterTCS': n % 8}, 'CLU11': {'CF_Clu_AliveCnt1': n % 16},
              'CGW1': {'CF_Gway_DrvSeatBeltSw': 1}, 'LVR12': {'CF_Lvr_Gear': self.gear}}
    frames = []
    sources = [(name, 0, rate) for name, rate in PT_RATES.items()]
    sources += [('LKAS11', 2, 100)]
    if self.source:
      sources += [('BCM_PO_11' if self.source == 0x391 else 'CLU13', 0, 10)]
    if fca and not self.ci.CP.flags & HyundaiFlags.NON_SCC_NO_FCA:
      sources += [('FCA11', 2, 50)]
    if self.ci.CP.deprecated.enableBsm:
      sources += [('LCA11', 0, 20)]
    for name, bus, rate in sources:
      if name == missing or n and n * rate // 100 == (n - 1) * rate // 100:
        continue
      signal = {'BCM_PO_11': {'LDA_BTN': int(held)}, 'CLU13': {'CF_Clu_LdwsLkasSW': int(held)},
                'LKAS11': {'CF_Lkas_MsgCount': n % 16}}.get(name, values.get(name, {}))
      frame = self.packer.make_can_msg(name, bus, signal)
      if name in ('EMS16', 'WHL_SPD11', 'TCS13'):
        frame = checksum(frame)
      if name == wrong_bus:
        frame = (frame[0], frame[1], 2 if bus == 0 else 0)
      frames.append(frame)
    with patch('opendbc.car.hyundai.non_scc_aol.time.clock_gettime_ns', return_value=self.now):
      return self.ci.update([(self.now, frames)])

  def warm(self, **kwargs):
    for _ in range(220):
      state = self.step(**kwargs)
    return state


class TestNonSccStartup(unittest.TestCase):
  def test_complete_forte_final_profiles_and_lazy_requirements(self):
    for identity, source, alpha, aol, bsm, fca in itertools.product(FORTE_IDS, (0x391, 0x50c),
          (False, True), (False, True), (False, True), (False, True)):
      with self.subTest(identity=identity, source=source, alpha=alpha, aol=aol, bsm=bsm, fca=fca):
        cp = params(identity, source=source, alpha=alpha, aol=aol, bsm=bsm, fca=fca)
        self.assertTrue(qualified(cp))
        self.assertTrue(cp.pcmCruise)
        self.assertFalse(cp.openpilotLongitudinalControl or cp.alphaLongitudinalAvailable)
        stream = ForteReceiveStream(cp, source=source)
        state = stream.warm()
        self.assertTrue(state.canValid)
        self.assertFalse(state.canTimeout)
        self.assertEqual(state.gearShifter, structs.CarState.GearShifter.drive)
        self.assertFalse(state.doorOpen or state.seatbeltUnlatched)
        self.assertTrue(state.cruiseState.available and state.cruiseState.enabled)
        self.assertNotIn('SCC11', stream.ci.can_parsers[Bus.pt].vl)
        self.assertNotIn('SCC12', stream.ci.can_parsers[Bus.pt].vl)
        stream.warm(fca=False)
        self.assertTrue(stream.step(fca=False).canValid)

  def test_all_ten_selected_cruise_sources_require_arrival_and_expire(self):
    from opendbc.car.hyundai.tests.test_non_scc import NON_SCC_CARS
    from opendbc.car.hyundai.carstate import get_non_scc_cruise_signals
    for identity in NON_SCC_CARS:
      cp = params(identity, source=0)
      names = get_non_scc_cruise_signals(cp.flags, cp.carFingerprint)[::2]
      for name in set(names):
        with self.subTest(identity=identity, source=name):
          ci = CarInterface(cp)
          state = ci.update([])
          self.assertFalse(state.canValid, (identity, name, 'empty'))
          parser = ci.can_parsers[Bus.pt]
          message = parser.message_states[parser.dbc.name_to_msg[name].address]
          self.assertFalse(message.ignore_alive, (identity, name))
          self.assertFalse(message.timestamps, (identity, name))
          self.assertFalse(message.valid(1_000_000_000, False), (identity, name, 'never received'))
          packer = CANPacker(DBC[identity][Bus.pt])
          packet = packer.make_can_msg(name, 0, {})
          if name == 'EMS16':
            packet = checksum(packet)
          ci.update([(1_000_000_000, [packet])])
          self.assertTrue(message.timestamps, (identity, name, 'packed arrival'))
          self.assertTrue(message.valid(1_000_000_000, False), (identity, name, 'arrived'))
          expired = 1_000_000_000 + int(message.timeout_threshold) + 1
          self.assertFalse(message.valid(expired, False), (identity, name, 'expired'))
          self.assertFalse(ci.update([(expired, [])]).canValid, (identity, name, 'incomplete stream'))

  def test_required_sources_loss_wrong_bus_and_recovery(self):
    for identity, source, missing, mode in itertools.product(FORTE_IDS, (0x391, 0x50c),
        ('MDPS12', 'WHL_SPD11', 'EMS16', 'TCS13', 'CLU11', 'LKAS11'), ('missing', 'wrong_bus')):
      with self.subTest(identity=identity, source=source, missing=missing, mode=mode):
        stream = ForteReceiveStream(params(identity, source=source, aol=True), source=source)
        case = (identity, source, missing, mode)
        self.assertTrue(stream.warm().canValid, case)
        state = stream.warm(**{mode: missing})
        self.assertFalse(state.canValid, case)
        self.assertTrue(stream.warm().canValid, case)

  def test_alternative_lda_source_expiry_needs_new_neutral_gesture(self):
    for identity, source in itertools.product(FORTE_IDS, (0x391, 0x50c)):
      with self.subTest(identity=identity, source=source):
        stream = ForteReceiveStream(params(identity, source=source, aol=True), source=source)
        self.assertTrue(stream.warm().canValid)
        stream.warm(held=True)
        self.assertTrue(stream.ci.CS.forte_lkas_sources.held)
        name = 'BCM_PO_11' if source == 0x391 else 'CLU13'
        self.assertTrue(stream.warm(missing=name).canValid)
        self.assertFalse(stream.ci.CS.forte_lkas_sources.held)
        for _ in range(220):
          stream.step(held=True)
          self.assertNotIn(True, stream.ci.CS.forte_lkas_sources.edges)
        stream.warm(held=False)
        presses = []
        for _ in range(220):
          stream.step(held=True)
          presses.extend(stream.ci.CS.forte_lkas_sources.edges)
        self.assertIn(True, presses)
        self.assertTrue(stream.ci.CS.forte_lkas_sources.held)
