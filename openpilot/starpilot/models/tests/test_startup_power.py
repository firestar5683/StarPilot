from types import SimpleNamespace

import pytest

from opendbc.car.hyundai.hyundaicanfd import CanBus
from opendbc.car.hyundai.model_startup import model_power_ready, model_power_ready_bus
from opendbc.car.hyundai.values import CAR, HyundaiFlags
from opendbc.car.structs import CarParams
from openpilot.starpilot.models.startup import POWER_STABLE_NS, PowerReadiness, wait_for_chestnut_power


NS = 1_000_000_000


def test_readiness_requires_ready_and_three_seconds_of_current_voltage():
  state = PowerReadiness()
  for step in range(200):
    now = NS + step * NS // 10
    assert state.update(now, now, 12_000, step >= 170) is False
  now += NS // 10
  assert state.update(now, now, 13_200, True)


@pytest.mark.parametrize("bad", ["low", "missing", "stale", "future", "not-ready", "clock", "gap"])
def test_bad_evidence_restarts_stability(bad):
  state = PowerReadiness()
  for step in range(29):
    now = NS + step * NS // 10
    assert not state.update(now, now, 12_000, True)
  now += NS // 10
  sample, voltage, ready = now, 12_000, True
  if bad == "low":
    voltage = 9_999
  elif bad == "missing":
    sample = 0
  elif bad == "stale":
    sample -= NS
  elif bad == "future":
    sample += 1
  elif bad == "not-ready":
    ready = False
  elif bad == "clock":
    now -= 2 * NS
    sample = now
  elif bad == "gap":
    now += NS
    sample = now
  assert not state.update(now, sample, voltage, ready)
  for step in range(1, 30):
    stamp = now + step * NS // 10
    assert not state.update(stamp, stamp, 12_000, True)
  stamp = now + POWER_STABLE_NS + NS // 10
  assert state.update(stamp, stamp, 12_000, True)


@pytest.mark.parametrize("lka,offset", [(False, 0), (True, 0), (False, 4), (True, 4)])
def test_vehicle_ready_uses_exact_vehicle_bus_and_payload(lka, offset):
  cp = CarParams(carFingerprint=CAR.HYUNDAI_IONIQ_6, brand="hyundai", flags=int(HyundaiFlags.CANFD_LKA_STEER_MSG) if lka else 0)
  # Bus offset is derived from the installed safety configuration.
  cp.init("safetyConfigs", 2 if offset else 1)
  bus = model_power_ready_bus(cp)
  assert bus is not None
  assert bus == CanBus(cp).ECAN
  data = bytearray(32)
  data[3] = 0x40
  def message(address=0x35, src=bus, dat=data):
    return SimpleNamespace(address=address, src=src, dat=bytes(dat))
  assert model_power_ready([message()], bus) is True
  assert model_power_ready([message(dat=bytes(32))], bus) is False
  assert model_power_ready([message(src=bus + 1), message(address=0x36), message(dat=data[:4])], bus) is None
  assert model_power_ready([message(), message(dat=bytes(32))], bus) is False
  cp.carFingerprint = CAR.KIA_EV6
  assert model_power_ready_bus(cp) is None


def test_wait_is_bounded_and_never_opens_gpu_without_power(monkeypatch):
  from openpilot.starpilot.models import startup
  clock = SimpleNamespace(now=0.)
  class Messages:
    def __init__(self, services):
      self.data = {"pandaStates": [], "deviceState": SimpleNamespace(started=True)}
      self.seen = dict.fromkeys(services, False)
      self.valid = dict.fromkeys(services, False)
      self.updated = dict.fromkeys(services, False)
      self.logMonoTime = dict.fromkeys(services, 0)
    def __getitem__(self, key): return self.data[key]
    def update(self, timeout): clock.now += .1
  monkeypatch.setattr(startup.messaging, "SubMaster", Messages)
  monkeypatch.setattr(startup.HARDWARE, "get_device_type", lambda: "mici")
  monkeypatch.setattr(startup.time, "monotonic", lambda: clock.now)
  monkeypatch.setattr(startup.time, "monotonic_ns", lambda: int(clock.now * NS))
  with pytest.raises(TimeoutError, match="did not stabilize"):
    wait_for_chestnut_power(SimpleNamespace(brand="mock"), timeout=1.)
  assert clock.now < 1.2


def test_current_drive_requires_positive_monotonic_evidence():
  from openpilot.starpilot.models.startup import current_drive
  class SM(dict):
    seen = {'deviceState': False}
    valid = {'deviceState': True}
    logMonoTime = {'deviceState': 20 * NS}
  sm = SM(deviceState=SimpleNamespace(started=True, startedMonoTime=10 * NS))
  assert not current_drive(sm, 20 * NS)
  sm.seen['deviceState'] = True
  assert current_drive(sm, 20 * NS)
  assert not current_drive(sm, 23 * NS)
  assert not current_drive(sm, 19 * NS)
  sm['deviceState'].startedMonoTime = 0
  assert not current_drive(sm, 20 * NS)


def test_suspend_gap_requires_new_power_stability():
  from openpilot.starpilot.models.startup import supply_voltage
  state = PowerReadiness()
  # Native Panda/CAN stamps use BOOTTIME, which advances while MONOTONIC is suspended.
  for tick in range(31):
    stamp = (20 * NS) + tick * NS // 10
    ready = state.update(stamp, stamp, 12_000, True)
  assert ready
  assert not state.update(stamp + 60 * NS, stamp, 12_000, True)
  assert not state.update(stamp + 60 * NS + NS // 10, stamp + 60 * NS + NS // 10, 12_000, True)
  low = SimpleNamespace(pandaType='tres', voltage=3_900)
  high = SimpleNamespace(pandaType='tres', voltage=12_000)
  assert supply_voltage([low]) == 3_900
  assert supply_voltage([low, high]) == 0


def test_paired_clocks_preserve_distinct_domains(monkeypatch):
  from openpilot.starpilot.models import startup
  monkeypatch.setattr(startup.time, 'CLOCK_BOOTTIME', 7, raising=False)
  monkeypatch.setattr(startup.time, 'monotonic_ns', lambda: 20 * NS)
  monkeypatch.setattr(startup.time, 'clock_gettime_ns', lambda clock: 80 * NS)
  assert startup.paired_clocks_ns() == (20 * NS, 80 * NS)
