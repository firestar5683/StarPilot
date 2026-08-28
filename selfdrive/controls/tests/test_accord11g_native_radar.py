from types import SimpleNamespace

import pytest
from opendbc.car.honda.values import CAR as HONDA_CAR
from openpilot.selfdrive.controls.radard import (
  HONDA_ACCORD_11G_LEAD_ACCEL_TAU,
  KalmanParams,
  RadarD,
  Track,
  get_honda_accord_11g_lead,
  get_honda_accord_11g_radar_state_from_vision,
  is_honda_accord_11g_radar_car,
  match_honda_accord_11g_vision_to_track,
  update_honda_accord_11g_accel_tau,
)


class FakeTrack:
  def __init__(self, identifier, d_rel, y_rel, v_rel, *, low_speed=False):
    self.identifier = identifier
    self.dRel = d_rel
    self.yRel = y_rel
    self.vRel = v_rel
    self.vLead = v_rel + 10.0
    self.vLeadK = self.vLead
    self.aLeadK = 0.0
    self.aLeadTau = SimpleNamespace(x=HONDA_ACCORD_11G_LEAD_ACCEL_TAU)
    self.low_speed = low_speed
    self.leadTrackID = 0

  def get_RadarState(self, model_prob=0.0):
    return {
      "status": True,
      "dRel": self.dRel,
      "yRel": self.yRel,
      "vRel": self.vRel,
      "vLead": self.vLead,
      "vLeadK": self.vLeadK,
      "aLeadK": self.aLeadK,
      "aLeadTau": self.aLeadTau.x,
      "modelProb": model_prob,
      "radar": True,
      "radarTrackId": self.identifier,
    }

  def potential_low_speed_lead(self, _v_ego):
    return self.low_speed


class FakeFilter:
  def __init__(self, value):
    self.x = value

  def update(self, value):
    self.x = value


def make_lead(*, x=31.52, y=0.0, v=10.0, a=-0.4):
  return SimpleNamespace(
    x=[x], y=[y], v=[v], a=[a],
    xStd=[1.0], yStd=[1.0], vStd=[1.0],
  )


@pytest.mark.parametrize("brand,fingerprint,expected", [
  ("honda", HONDA_CAR.HONDA_ACCORD_11G, True),
  ("honda", HONDA_CAR.HONDA_CIVIC_BOSCH, False),
  ("toyota", HONDA_CAR.HONDA_ACCORD_11G, False),
])
def test_accord11g_native_radar_scope_is_exact(brand, fingerprint, expected):
  CP = SimpleNamespace(brand=brand, carFingerprint=fingerprint)
  assert is_honda_accord_11g_radar_car(CP) is expected


def test_accord11g_native_radar_track_tau_policy_is_isolated():
  accord_track = Track(1, 10.0, KalmanParams(0.05), honda_accord_11g_radar=True)
  generic_track = Track(2, 10.0, KalmanParams(0.05))
  assert accord_track.aLeadTau.x == pytest.approx(HONDA_ACCORD_11G_LEAD_ACCEL_TAU)
  assert generic_track.aLeadTau.x != pytest.approx(HONDA_ACCORD_11G_LEAD_ACCEL_TAU)

  fake_filter = FakeFilter(0.1)
  update_honda_accord_11g_accel_tau(fake_filter, 0.1)
  assert fake_filter.x == pytest.approx(HONDA_ACCORD_11G_LEAD_ACCEL_TAU)
  update_honda_accord_11g_accel_tau(fake_filter, 0.8)
  assert fake_filter.x == pytest.approx(0.0)


def test_accord11g_native_radar_matches_validated_track_without_preference():
  lead = make_lead()
  tracks = {
    1: FakeTrack(1, 30.0, 0.0, 0.0),
    2: FakeTrack(2, 45.0, 2.0, 8.0),
  }
  assert match_honda_accord_11g_vision_to_track(10.0, lead, tracks) is tracks[1]


def test_accord11g_native_radar_vision_fallback_matches_validated_values():
  lead = make_lead(x=41.52, y=1.5, v=8.0, a=-0.6)
  result = get_honda_accord_11g_radar_state_from_vision(lead, 10.0, 9.0, 0.8)
  assert result == {
    "dRel": 40.0,
    "yRel": -1.5,
    "vRel": -1.0,
    "vLead": 9.0,
    "vLeadK": 9.0,
    "aLeadK": -0.6,
    "aLeadTau": 0.3,
    "fcw": False,
    "modelProb": 0.8,
    "status": True,
    "radar": False,
    "radarTrackId": -1,
  }


def test_accord11g_native_radar_probability_and_low_speed_policy():
  lead = make_lead()
  model_track = FakeTrack(1, 30.0, 0.0, 0.0)
  close_track = FakeTrack(2, 8.0, 0.0, -8.0, low_speed=True)
  tracks = {1: model_track, 2: close_track}

  assert not get_honda_accord_11g_lead(
    10.0, True, tracks, lead, 10.0, 0.5, low_speed_override=False,
  )["status"]

  result = get_honda_accord_11g_lead(2.0, True, tracks, lead, 10.0, 0.8)
  assert result["radarTrackId"] == close_track.identifier
  assert all(track.leadTrackID == close_track.identifier for track in tracks.values())

  second = get_honda_accord_11g_lead(2.0, True, tracks, lead, 10.0, 0.8, low_speed_override=False)
  assert second["radarTrackId"] == model_track.identifier


def test_non_accord_radard_keeps_native_dom_mode():
  generic = RadarD(radar_ts=0.05)
  accord = RadarD(radar_ts=0.05, honda_accord_11g_radar=True)
  assert not generic.honda_accord_11g_radar
  assert accord.honda_accord_11g_radar
