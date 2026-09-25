from openpilot.system import timed


def test_recorded_clock_pair_is_bound_to_event_timestamp(monkeypatch):
  mono = iter((10_000_000, 10_100_000))
  monkeypatch.setattr(timed.time, 'monotonic_ns', lambda: next(mono))
  monkeypatch.setattr(timed.time, 'clock_gettime_ns', lambda clock: 20_000_000)
  monkeypatch.setattr(timed.time, 'time_ns', lambda: 1_800_000_000_000_000_000)
  monkeypatch.setattr(timed, 'system_time_valid', lambda: True)
  event = timed.clock_message()
  assert event.logMonoTime == event.clocks.deprecated.monotonicNanos == 10_000_000
  assert event.clocks.deprecated.bootTimeNanos == 20_000_000
  assert event.clocks.wallTimeNanos == 1_800_000_000_000_000_000


def test_delayed_clock_sample_does_not_claim_a_precise_pair(monkeypatch):
  mono = iter((10_000_000, 12_000_000))
  monkeypatch.setattr(timed.time, 'monotonic_ns', lambda: next(mono))
  monkeypatch.setattr(timed.time, 'clock_gettime_ns', lambda clock: 20_000_000)
  monkeypatch.setattr(timed, 'system_time_valid', lambda: True)
  event = timed.clock_message()
  assert event.clocks.deprecated.monotonicNanos == event.clocks.deprecated.bootTimeNanos == 0
