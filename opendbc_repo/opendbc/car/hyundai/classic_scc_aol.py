"""Classic stock-SCC AOL identity and transport contract.

Gas, checksum, SCC routing and steering limits remain platform-owned.
Independent lateral authorization is a separate native profile, never LONG.
"""

import time

from opendbc.car import structs
from opendbc.car.hyundai.values import CAR, HyundaiFlags, HyundaiSafetyFlags, is_blended

AOL_MARKER = 0x0400
AOL_EXPERIENCE = 32
_EXCLUDED = int(HyundaiFlags.CANFD | HyundaiFlags.NON_SCC | HyundaiFlags.FCEV)
CLASSIC_SCC_IDS = frozenset(identity for identity in CAR if not int(identity.config.flags) & _EXCLUDED and identity != CAR.HYUNDAI_PALISADE_2023)
_MODELS = (structs.CarParams.SafetyModel.hyundai, structs.CarParams.SafetyModel.hyundaiLegacy)
NORMAL_AOL_WORDS = frozenset(
  AOL_MARKER | gas | limit | camera | lda for gas in (0, 1, 2) for limit in (0, 64, 512) for camera in (0, 8) for lda in (0, 2048)
) | frozenset((0x8408, 0x840A, 0x8C08, 0x8C0A))
LEGACY_AOL_WORDS = frozenset(word for word in NORMAL_AOL_WORDS if not word & (8 | 32768))


def native_profile_supported(model, param):
  return (model == int(_MODELS[0]) and param in NORMAL_AOL_WORDS) or (model == int(_MODELS[1]) and param in LEGACY_AOL_WORDS)


def stock_word(cp):
  word = int(HyundaiSafetyFlags.CAN_REFRESH_MSGS) if cp.carFingerprint in (CAR.HYUNDAI_ELANTRA_2024, CAR.HYUNDAI_ELANTRA_HEV_2024) else 0
  for flag, safety in (
    (HyundaiFlags.EV, HyundaiSafetyFlags.EV_GAS),
    (HyundaiFlags.HYBRID, HyundaiSafetyFlags.HYBRID_GAS),
    (HyundaiFlags.ALT_LIMITS, HyundaiSafetyFlags.ALT_LIMITS),
    (HyundaiFlags.ALT_LIMITS_2, HyundaiSafetyFlags.ALT_LIMITS_2),
    (HyundaiFlags.CAMERA_SCC, HyundaiSafetyFlags.CAMERA_SCC),
  ):
    if int(cp.flags) & int(flag):
      word |= int(safety)
  return word


def aol_word(cp):
  return stock_word(cp) | AOL_MARKER | (int(HyundaiSafetyFlags.HAS_LDA_BUTTON) if int(cp.flags) & int(HyundaiFlags.HAS_LDA_BUTTON) else 0)


def qualified(cp, *, marked_only=False):
  if cp.brand != "hyundai" or cp.carFingerprint not in CLASSIC_SCC_IDS:
    return False
  declared = int(CAR[cp.carFingerprint].config.flags)
  allowed = declared | int(HyundaiFlags.HAS_LDA_BUTTON | HyundaiFlags.USE_FCA | HyundaiFlags.SEND_LFA)
  identity_mask = _EXCLUDED | int(
    HyundaiFlags.EV | HyundaiFlags.HYBRID | HyundaiFlags.ALT_LIMITS | HyundaiFlags.ALT_LIMITS_2 | HyundaiFlags.CAMERA_SCC | HyundaiFlags.LEGACY
  )
  if (
    int(cp.flags) & identity_mask != declared & identity_mask
    or int(cp.flags) & ~allowed
    or is_blended(cp)
    or cp.passive
    or cp.notCar
    or cp.dashcamOnly
    or cp.openpilotLongitudinalControl
    or not cp.pcmCruise
    or cp.alternativeExperience not in (0, AOL_EXPERIENCE)
    or len(cp.safetyConfigs) != 1
  ):
    return False
  safety = cp.safetyConfigs[0]
  model = _MODELS[bool(declared & int(HyundaiFlags.LEGACY))]
  accepted = (aol_word(cp),) if marked_only else (stock_word(cp), aol_word(cp))
  return safety.safetyModel == model and int(safety.safetyParam) in accepted


def native_accepts(cp, model, param):
  return (
    qualified(cp, marked_only=True)
    and cp.alternativeExperience == AOL_EXPERIENCE
    and model == int(cp.safetyConfigs[0].safetyModel.raw)
    and param == aol_word(cp)
  )


class ClassicSccLkasSources:
  """Original per-frame button selection over current-session raw observations.

  The Sonata hybrid's SWL status can affect host intent, but cannot by itself
  authorize native steering. Native authorization still observes physical
  BCM/CLU button bits. Expiry and held-at-start protection remain fail closed.
  """

  def __init__(self, identity):
    self.identity = identity
    self.sources = {}
    self.selected = None
    self.previous = {"bcm": 0, "clu13": 0, "swl_stat": 0}
    self.held = False
    self.neutral_seen = False
    self.edges = []
    self.neutral_sources = set()
    self.blocked_sources = set()

  def update(self, can_packets):
    self.edges = []
    try:
      now = time.clock_gettime_ns(time.CLOCK_BOOTTIME)
    except (AttributeError, OSError):
      self.sources.clear()
      self.neutral_sources.clear()
      self.blocked_sources.clear()
      self.neutral_seen = False
      self.held = False
      self.previous = dict.fromkeys(self.previous, 0)
      self.selected = None
      return
    age = 300_000_000
    current = {address: value for address, value in self.sources.items() if 0 <= now - value[0] <= age}
    if len(current) != len(self.sources):
      for address, (_, data) in self.sources.items():
        held_source = (
          bool(data[0] & 0x10) if address == 0x391 else bool(data[7] & 1 or (self.identity == CAR.HYUNDAI_SONATA_HYBRID and ((data[4] >> 4) & 7) == 4))
        )
        if address not in current:
          self.neutral_sources.discard(address)
          if held_source and (self.identity != CAR.HYUNDAI_SONATA or address == 0x391):
            self.blocked_sources.add(address)
      self.neutral_seen = False
    self.sources = current
    samples = []
    accepted = set()
    for stamp, packets in can_packets:
      if type(stamp) is not int or not 0 < stamp <= now or now - stamp > age:
        continue
      for address, data, bus in packets:
        if bus != 0 or address not in (0x391, 0x50C) or len(data) != 8:
          continue
        previous = self.sources.get(address)
        if previous is not None and stamp <= previous[0]:
          continue
        self.sources[address] = (stamp, bytes(data))
        accepted.add(address)
        source_held = (
          bool(data[0] & 0x10) if address == 0x391 else bool(data[7] & 1 or (self.identity == CAR.HYUNDAI_SONATA_HYBRID and ((data[4] >> 4) & 7) == 4))
        )
        if self.identity == CAR.HYUNDAI_SONATA and address != 0x391:
          continue
        if source_held:
          if address not in self.neutral_sources:
            self.blocked_sources.add(address)
        else:
          self.neutral_sources.add(address)
          self.blocked_sources.discard(address)
        samples.append(bool(data[0] & 0x10) if address == 0x391 else bool(data[7] & 1))
    bcm = self.sources.get(0x391)
    clu = self.sources.get(0x50C)
    states = {"bcm": int(bool(bcm and bcm[1][0] & 0x10)), "clu13": int(bool(clu and clu[1][7] & 1)), "swl_stat": int(bool(clu and ((clu[1][4] >> 4) & 7) == 4))}
    if self.identity == CAR.HYUNDAI_SONATA:
      held = bool(states["bcm"])
    elif self.identity == CAR.HYUNDAI_SONATA_HYBRID:
      changed = [source for source, state in states.items() if state != self.previous[source]]
      active = [source for source, state in states.items() if state]
      if self.selected in changed:
        selected = self.selected
      elif active:
        selected = active[0]
      elif changed:
        selected = changed[0]
      else:
        selected = self.selected
      self.previous = states
      if selected is not None:
        self.selected = selected
      held = bool(states[selected]) if selected is not None else False
    elif self.identity == CAR.HYUNDAI_ELANTRA_HEV_2024:
      held = any(samples) if samples else bool(states["bcm"] or states["clu13"])
    else:
      held = bool(states["bcm"] or states["clu13"])
    fresh_neutral = bool(accepted) and not self.blocked_sources and not held and (self.identity != CAR.HYUNDAI_SONATA or 0x391 in accepted)
    if fresh_neutral:
      if not self.neutral_seen and not self.held:
        self.edges.append(False)
      self.neutral_seen = True
    if held != self.held and self.neutral_seen and not self.blocked_sources and (held or fresh_neutral):
      self.edges.append(held)
    self.held = held
