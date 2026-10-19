"""Actual global capture predicate + real typed collector, not fit/native authority.

Synthetic typed endpoints isolate capture admission; no model/profile is made.
"""
from dataclasses import replace
from types import SimpleNamespace

import pytest

from openpilot.starpilot.flm.canonical_surface_adapter import GROUPS
from openpilot.starpilot.flm.event_collection import EventCollectionAdapter, event_keys
from openpilot.starpilot.flm.fullrate_collector import FullrateCollector
from openpilot.starpilot.flm.tests.test_fullrate_pipeline import BASE, IDENTITY, snapshots


class RawEventFixture:
  raw_collection = True
  command_domain = 'torque'
  model = None
  envelope = object()
  identity = IDENTITY
  source_epoch = '2' * 64
  physical_observable = EventCollectionAdapter.physical_observable
  cohort = EventCollectionAdapter.cohort
  raw_maneuver_complete = EventCollectionAdapter.raw_maneuver_complete

  def __init__(self, group):
    self.key = ('event', group)


def feed(collector, tick, *, speed=2., fault=False, native=True, override=False, valid=True, expected_inputs=True):
  stamp = BASE + tick * 50_000_000
  control, output, response = snapshots(stamp)
  response = replace(response, speed_mps=speed, fault=fault, native_allowed=native, override=override, valid=valid)
  assert collector.control(control, stamp + 1_000_000) is expected_inputs
  assert collector.output(output, stamp + 1_000_000) is expected_inputs
  return collector.physical(response, stamp + 1_000_000)


def test_registry_is_all_twelve_canonical_groups():
  assert len(GROUPS) == 12
  assert set(event_keys(None)) == {('event', group) for group in GROUPS}


@pytest.mark.parametrize('group', GROUPS)
def test_every_registered_group_captures_same_existing_low_speed_inventory(group):
  adapter = RawEventFixture(group)
  collector = FullrateCollector(adapter)
  for tick in range(46):
    accepted = feed(collector, tick)
  assert accepted and collector.raw_points
  assert all(point.physical['speed_mps'] == 2. for point in collector.raw_points)
  assert collector.points == [] and collector.result is None
  assert collector.fit_result is None and collector.last_validation is None and adapter.model is None
  assert adapter.physical_observable(SimpleNamespace(speed_mps=5.3, roll_rad=0.))
  assert adapter.physical_observable(SimpleNamespace(speed_mps=30., roll_rad=0.))


@pytest.mark.parametrize('group', GROUPS)
@pytest.mark.parametrize('speed', [0., 1.999999, float('nan'), float('inf')])
def test_below_existing_low_floor_or_nonfinite_never_captures(group, speed):
  collector = FullrateCollector(RawEventFixture(group))
  for tick in range(46):
    feed(collector, tick)
  assert collector.raw_points
  assert not feed(collector, 46, speed=speed)
  assert not collector.raw_points and collector.last_qualified_response == 0


@pytest.mark.parametrize('group', GROUPS)
@pytest.mark.parametrize('bad', [{'fault': True}, {'native': False}, {'override': True}, {'valid': False}])
def test_fault_or_native_withdrawal_still_clears_and_requires_fresh_warmup(group, bad):
  collector = FullrateCollector(RawEventFixture(group))
  for tick in range(46):
    feed(collector, tick)
  assert collector.raw_points
  assert not feed(collector, 46, **bad)
  assert not collector.raw_points and collector.last_qualified_response == 0
  assert not feed(collector, 47, expected_inputs=not bad.get('override', False))
  assert not collector.raw_points
  assert collector.fit_result is None and collector.last_validation is None


@pytest.mark.parametrize('group', GROUPS)
def test_original_roll_veto_remains(group):
  predicate = RawEventFixture(group).physical_observable
  assert not predicate(SimpleNamespace(speed_mps=2., roll_rad=.3))
  assert not predicate(SimpleNamespace(speed_mps=30., roll_rad=-.3))
