from dataclasses import replace
import json
import math

import pytest

from openpilot.starpilot.common.model_stats import Reducer, Sample, parse_identity, rates, RELEASE_SECONDS

OWNER = json.dumps({'version': 1, 'roles': [{'modelId': 'rdf43', 'artifact': 'unverified-load:test', 'backend': 'comma'}]})
OTHER = OWNER.replace('rdf43', 'gpu')


def sample(t, **kwargs):
  return replace(Sample(t, OWNER, 10, enabled=True, lat=True, long=True), **kwargs)


def feed(reducer, start, stop, **kwargs):
  for i in range(start, stop):
    reducer.update(sample(i / 100, **kwargs))


def totals(reducer):
  return {key: sum(row[key] for row in reducer.metrics.values())
          for key in ('assistedMeters', 'interventionMeters', 'disengagementMeters', 'interventions', 'disengagements', 'steering', 'brake', 'gas')}


def test_manual_not_included_and_zero_event_rates():
  r = Reducer()
  feed(r, 0, 101, enabled=False, lat=False, long=False)
  assert totals(r)['assistedMeters'] == 0
  assert rates(totals(r))['milesPerIntervention'] is None
  feed(r, 101, 202)
  assert totals(r)['assistedMeters'] == pytest.approx(10)
  assert totals(r)['interventions'] == 0


@pytest.mark.parametrize('kind', ['steering', 'brake', 'gas'])
def test_held_input_counts_once_and_rearms(kind):
  r = Reducer()
  feed(r, 0, 10)
  feed(r, 10, 1010, **{kind: True})
  assert totals(r)['interventions'] == 1
  assert totals(r)[kind] == 1
  assert totals(r)['assistedMeters'] > totals(r)['interventionMeters']
  released = 1010 + int(RELEASE_SECONDS * 100) + 2
  feed(r, 1010, released)
  feed(r, released, released + 10, **{kind: True})
  assert totals(r)['interventions'] == 2


def test_overlap_chatter_counts_one_with_three_types():
  r = Reducer()
  feed(r, 0, 10)
  feed(r, 10, 20, steering=True)
  feed(r, 20, 30, steering=True, brake=True)
  feed(r, 30, 40, gas=True)
  feed(r, 40, 50)
  feed(r, 50, 60, gas=True)
  assert {k: totals(r)[k] for k in ('interventions', 'steering', 'brake', 'gas')} == dict(interventions=1, steering=1, brake=1, gas=1)


def test_brake_disable_counts_both_and_stationary_counts():
  r = Reducer()
  feed(r, 0, 10, speed=0)
  feed(r, 10, 20, speed=0, brake=True, enabled=False, lat=False, long=False)
  assert totals(r)['interventions'] == totals(r)['disengagements'] == 1
  assert totals(r)['assistedMeters'] == 0


@pytest.mark.parametrize('initial_manual', [False, True])
def test_initially_held_and_manual_input_do_not_create_engagement_edge(initial_manual):
  r = Reducer()
  feed(r, 0, 10, gas=True, enabled=not initial_manual)
  feed(r, 10, 30, gas=True)
  assert totals(r)['interventions'] == 0
  released = 30 + int(RELEASE_SECONDS * 100) + 2
  feed(r, 30, released)
  feed(r, released, released + 10, gas=True)
  assert totals(r)['interventions'] == 1


def test_manual_rising_edge_stays_blocked_at_engagement():
  r = Reducer()
  feed(r, 0, 10, enabled=False)
  feed(r, 10, 20, enabled=False, brake=True)
  feed(r, 20, 40, brake=True)
  assert totals(r)['interventions'] == 0


def test_override_not_disengagement_and_aol_separate():
  r = Reducer()
  feed(r, 0, 10)
  feed(r, 10, 20, lat=False, long=False)
  assert totals(r)['disengagements'] == 0
  feed(r, 20, 30, enabled=False, aol=True, long=False)
  feed(r, 30, 40, enabled=False, aol=False, lat=False, long=False)
  assert r.row(OWNER, 'full')['disengagements'] == 1
  assert r.row(OWNER, 'aol')['disengagements'] == 1
  assert r.row(OWNER, 'aol')['assistedMeters'] > 0


@pytest.mark.parametrize('bad', [dict(valid=False), dict(reverse=True), dict(onroad=False), dict(owner=None),
                               dict(speed=math.nan), dict(speed=math.inf), dict(speed=-1), dict(speed=101)])
def test_invalid_sample_breaks_edges_and_distance(bad):
  r = Reducer()
  r.update(sample(0))
  r.update(sample(.1, **bad))
  r.update(sample(.2, enabled=False, brake=True))
  assert totals(r)['assistedMeters'] == 0
  assert totals(r)['interventions'] == totals(r)['disengagements'] == 0
  assert r.gaps == 1


def test_gap_duplicate_and_out_of_order():
  r = Reducer()
  r.update(sample(0))
  r.update(sample(.1))
  r.update(sample(.1, brake=True, enabled=False))
  r.update(sample(.05, brake=True, enabled=False))
  r.update(sample(1, enabled=False, brake=True))
  assert totals(r)['assistedMeters'] == pytest.approx(1)
  assert totals(r)['interventions'] == totals(r)['disengagements'] == 0
  assert r.gaps == 1


def test_switch_does_not_charge_ambiguous_takeover_to_fallback():
  r = Reducer()
  feed(r, 0, 10)
  r.update(sample(.1, owner=OTHER, enabled=False, brake=True))
  assert totals(r)['disengagements'] == totals(r)['interventions'] == 0
  assert r.gaps == 1
  assert r.row(OTHER, 'full')['assistedMeters'] == 0


@pytest.mark.parametrize('bad', ['', '{}', '{', 'null', '[]', '{"version":1,"roles":[]}', '{"version":1,"roles":[null]}'])
def test_unknown_identity_rejected(bad):
  assert parse_identity(bad) is None


def test_valid_pair_identity_preserved():
  identity = json.loads(OWNER)
  identity['roles'].append(json.loads(OTHER)['roles'][0])
  assert len(json.loads(parse_identity(json.dumps(identity)))['roles']) == 2


def test_two_second_grouping_merges_quick_corrections_and_restarts_timer():
  r = Reducer()
  feed(r,0,10)
  feed(r,10,20,steering=True)
  feed(r,20,170)  # 1.5 seconds fully released
  feed(r,170,180,gas=True)
  assert totals(r)['interventions'] == 1
  assert totals(r)['steering'] == totals(r)['gas'] == 1
  feed(r,180,330)  # another 1.5 seconds; timer starts from the latest release
  feed(r,330,340,brake=True)
  assert totals(r)['interventions'] == 1
  feed(r,340,542)  # more than two seconds continuously clear
  feed(r,542,550,steering=True)
  assert totals(r)['interventions'] == 2
  assert r.snapshot()['interventionReleaseSeconds'] == 2.0
  assert r.snapshot()['definitionVersion'] == 2
