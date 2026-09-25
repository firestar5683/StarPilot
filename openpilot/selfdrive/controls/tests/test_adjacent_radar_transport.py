"""Current radard Track -> qualified custom wire, with no control consumer."""

from collections.abc import Iterator
import unittest
import capnp

from openpilot.cereal import messaging
from openpilot.selfdrive.controls.radard import RadarD


MONO = 100_000_000_000
BOOT = MONO + 2_000_000_000


class Sources(messaging.SubMaster):
  def __init__(self, stamp_ns: int, *, points: tuple[tuple[int, float, float, float], ...] = (), boot_offset_ns: int = BOOT - MONO):
    model_event = messaging.new_message('modelV2', valid=True)
    model_event.logMonoTime = stamp_ns
    model = model_event.modelV2
    model.timestampEof = stamp_ns + boot_offset_ns
    lanes = model.init('laneLines', 4)
    xs = [float(index * 5) for index in range(33)]
    for index, lane in enumerate(lanes):
      lane.x = xs
      lane.y = [(-1.8 if index == 1 else 1.8 if index == 2 else 0.0)] * len(xs)
    model.init('leadsV3', 3)
    model.velocity.x = [15.0] * 33

    car_event = messaging.new_message('carState', valid=True)
    car_event.logMonoTime = stamp_ns
    car_event.carState.vEgo = 15.0

    radar_event = messaging.new_message('radarTracks', valid=True)
    radar_event.logMonoTime = stamp_ns
    radar_points = radar_event.radarTracks.init('points', len(points))
    for wire, (track_id, distance, lateral, relative_speed) in zip(radar_points, points, strict=True):
      wire.trackId = track_id
      wire.dRel = distance
      wire.yRel = lateral
      wire.vRel = relative_speed

    self.data = {'modelV2': model, 'carState': car_event.carState, 'radarTracks': radar_event.radarTracks}
    self.seen = {'modelV2': True}
    self.recv_frame = {'carState': 1}
    self.logMonoTime = dict.fromkeys(self.data, stamp_ns)
    self.recv_time = dict.fromkeys(self.data, stamp_ns / 1e9)
    self.valid = dict.fromkeys(self.data, True)
    self.updated = dict.fromkeys(self.data, True)

  def __getitem__(self, s: str) -> capnp.lib.capnp._DynamicStructReader:
    return self.data[s]

  def all_checks(self, service_list: list[str] | None = None) -> bool:
    return all(self.valid[name] for name in (service_list or self.data))


class Captured(messaging.PubMaster):
  def __init__(self):
    self.messages = {}

  def send(self, s: str, dat: bytes | capnp.lib.capnp._DynamicStructBuilder) -> None:
    self.messages[s] = messaging.log_from_bytes(dat if isinstance(dat, bytes) else dat.to_bytes())


def pairs(*values: int) -> Iterator[tuple[int, int, int]]:
  for now in values:
    yield MONO + now, BOOT + now, 1_000


class AdjacentRadarTransportTest(unittest.TestCase):
  def test_real_track_selection_and_qualified_wire_without_historical_lead_claim(self):
    samples = pairs(10_000_000, 30_000_000)
    radar = RadarD(adjacent_enabled=True, radar_available=True, clock_pair_fn=lambda: next(samples))
    first = Sources(MONO + 8_000_000, points=((17, 25.0, 3.0, -7.0),))
    radar.update(first, first['radarTracks'])
    self.assertIsNone(radar.adjacent_observation.ambiguous)  # startup evidence barrier

    fresh = Sources(MONO + 25_000_000, points=((17, 25.0, 3.0, -7.0),))
    radar.update(fresh, fresh['radarTracks'])
    publisher = Captured()
    radar.publish(publisher)
    ordinary = publisher.messages['radarState']
    event = publisher.messages['starpilotRadarState']
    wire = event.starpilotRadarState.qualifiedAdjacent
    self.assertTrue(ordinary.valid)
    self.assertTrue(event.valid)
    self.assertEqual(wire.status, 'ambiguous')
    self.assertEqual((wire.radarTracksMonoTime, wire.modelMonoTime, wire.carStateMonoTime), (MONO + 25_000_000,) * 3)
    self.assertEqual(wire.cameraEofBootTime, BOOT + 25_000_000)
    self.assertEqual(wire.observedMonoTime, MONO + 25_000_000)
    self.assertEqual(wire.left.trackId, 17)
    self.assertTrue(wire.left.present)
    self.assertFalse(wire.right.present)
    self.assertFalse(event.starpilotRadarState.leadLeft.status)
    self.assertFalse(event.starpilotRadarState.leadRight.status)
    self.assertLess(wire.observedMonoTime, wire.validUntilMonoTime)

  def test_known_clear_requires_current_valid_scan(self):
    samples = pairs(10_000_000, 30_000_000, 50_000_000, 70_000_000)
    radar = RadarD(adjacent_enabled=True, radar_available=True, clock_pair_fn=lambda: next(samples))
    for stamp in (8_000_000, 25_000_000):
      source = Sources(MONO + stamp)
      radar.update(source, source['radarTracks'])
    publisher = Captured()
    radar.publish(publisher)
    self.assertTrue(publisher.messages['starpilotRadarState'].valid)
    self.assertEqual(publisher.messages['starpilotRadarState'].starpilotRadarState.qualifiedAdjacent.status, 'clear')

    stale_scan = Sources(MONO + 45_000_000)
    stale_scan.updated['radarTracks'] = False
    radar.update(stale_scan, stale_scan['radarTracks'])
    radar.publish(publisher)
    self.assertFalse(publisher.messages['starpilotRadarState'].valid)
    self.assertEqual(publisher.messages['starpilotRadarState'].starpilotRadarState.qualifiedAdjacent.status, 'unknown')

    invalid = Sources(MONO + 65_000_000)
    invalid.valid['radarTracks'] = False
    radar.update(invalid, invalid['radarTracks'])
    radar.publish(publisher)
    self.assertFalse(publisher.messages['starpilotRadarState'].valid)

  def test_clock_offset_change_rearms_and_requires_post_resume_sources(self):
    new_boot = BOOT + 100_000_000
    samples = iter(
      (
        (MONO + 10_000_000, BOOT + 10_000_000, 1_000),
        (MONO + 30_000_000, BOOT + 30_000_000, 1_000),
        (MONO + 80_000_000, new_boot + 80_000_000, 1_000),
        (MONO + 100_000_000, new_boot + 100_000_000, 1_000),
      )
    )
    radar = RadarD(adjacent_enabled=True, radar_available=True, clock_pair_fn=lambda: next(samples))
    for stamp in (8_000_000, 25_000_000):
      source = Sources(MONO + stamp)
      radar.update(source, source['radarTracks'])
    self.assertFalse(radar.adjacent_observation.ambiguous)

    cached = Sources(MONO + 75_000_000, boot_offset_ns=new_boot - MONO)
    radar.update(cached, cached['radarTracks'])
    self.assertIsNone(radar.adjacent_observation.ambiguous)
    fresh = Sources(MONO + 95_000_000, boot_offset_ns=new_boot - MONO)
    radar.update(fresh, fresh['radarTracks'])
    self.assertFalse(radar.adjacent_observation.ambiguous)

  def test_clock_regression_with_same_offset_does_not_reuse_old_source(self):
    samples = iter(
      (
        (MONO + 10_000_000, BOOT + 10_000_000, 1_000),
        (MONO + 30_000_000, BOOT + 30_000_000, 1_000),
        (MONO + 20_000_000, BOOT + 20_000_000, 1_000),
        (MONO + 40_000_000, BOOT + 40_000_000, 1_000),
      )
    )
    radar = RadarD(adjacent_enabled=True, radar_available=True, clock_pair_fn=lambda: next(samples))
    for stamp in (8_000_000, 25_000_000):
      source = Sources(MONO + stamp)
      radar.update(source, source['radarTracks'])
    self.assertFalse(radar.adjacent_observation.ambiguous)

    old = Sources(MONO + 18_000_000)
    radar.update(old, old['radarTracks'])
    self.assertIsNone(radar.adjacent_observation.ambiguous)
    # Still in the prior stamp era: old data remains before the new barrier.
    reused = Sources(MONO + 25_000_000)
    radar.update(reused, reused['radarTracks'])
    self.assertIsNone(radar.adjacent_observation.ambiguous)

  def test_no_radar_capability_never_reports_clear(self):
    samples = pairs(10_000_000, 30_000_000)
    radar = RadarD(adjacent_enabled=True, radar_available=False, clock_pair_fn=lambda: next(samples))
    for stamp in (8_000_000, 25_000_000):
      source = Sources(MONO + stamp)
      radar.update(source, source['radarTracks'])
    publisher = Captured()
    radar.publish(publisher)
    self.assertFalse(publisher.messages['starpilotRadarState'].valid)
    self.assertEqual(publisher.messages['starpilotRadarState'].starpilotRadarState.qualifiedAdjacent.status, 'unknown')

  def test_default_off_keeps_only_original_radar_output_and_never_samples_clocks(self):
    def forbidden_clock():
      raise AssertionError('adjacent clocks must not be sampled when feature is off')

    radar = RadarD(radar_available=True, clock_pair_fn=forbidden_clock)
    source = Sources(MONO + 25_000_000, points=((17, 25.0, 3.0, -7.0),))
    radar.update(source, source['radarTracks'])
    publisher = Captured()
    radar.publish(publisher)
    self.assertEqual(set(publisher.messages), {'radarState'})
    self.assertTrue(publisher.messages['radarState'].valid)


if __name__ == '__main__':
  unittest.main()
