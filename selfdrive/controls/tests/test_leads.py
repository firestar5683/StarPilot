from types import SimpleNamespace

import cereal.messaging as messaging

from opendbc.car.toyota.values import CAR as TOYOTA
from openpilot.selfdrive.test.process_replay import replay_process_with_name
from openpilot.selfdrive.controls.radard import g90_low_speed_radar_lead_sane, g90_radar_lead_lateral_sane, leads_are_duplicate


class TestLeads:
  def test_g90_radar_filters_side_tracks(self):
    side_track = SimpleNamespace(dRel=13.0, yRel=-10.38, cnt=10)
    centered_track = SimpleNamespace(dRel=10.8, yRel=-0.21, cnt=5)
    close_side_ghost = SimpleNamespace(dRel=2.2, yRel=2.41, cnt=10)
    close_centered_track = SimpleNamespace(dRel=2.2, yRel=1.2, cnt=10)
    far_low_speed_track = SimpleNamespace(dRel=15.5, yRel=0.58, cnt=5)

    assert not g90_radar_lead_lateral_sane(side_track)
    assert g90_radar_lead_lateral_sane(centered_track)
    assert not g90_radar_lead_lateral_sane(close_side_ghost)
    assert g90_radar_lead_lateral_sane(close_centered_track)
    assert g90_low_speed_radar_lead_sane(centered_track, 2.0)
    assert not g90_low_speed_radar_lead_sane(far_low_speed_track, 3.5)

  def test_duplicate_radar_leads_share_track(self):
    lead_one = {
      "status": True,
      "radar": True,
      "radarTrackId": 20293,
    }
    lead_two = {
      "status": True,
      "radar": True,
      "radarTrackId": 20293,
    }
    different_track = {
      "status": True,
      "radar": True,
      "radarTrackId": 20326,
    }
    vision_only = {
      "status": True,
      "radar": False,
      "radarTrackId": -1,
    }

    assert leads_are_duplicate(lead_one, lead_two)
    assert not leads_are_duplicate(lead_one, different_track)
    assert not leads_are_duplicate(lead_one, vision_only)

  def test_vision_leads_are_not_force_deduped(self):
    lead_one = {
      "status": True,
      "radar": False,
      "radarTrackId": -1,
      "dRel": 48.3,
      "vLead": 18.9,
      "yRel": 0.14,
      "modelProb": 0.99,
    }
    lead_two = {
      "status": True,
      "radar": False,
      "radarTrackId": -1,
      "dRel": 48.4,
      "vLead": 19.0,
      "yRel": 0.14,
      "modelProb": 1.00,
    }
    distinct_lead = {
      "status": True,
      "radar": False,
      "radarTrackId": -1,
      "dRel": 48.3,
      "vLead": 18.9,
      "yRel": 1.10,
      "modelProb": 0.99,
    }

    assert not leads_are_duplicate(lead_one, lead_two)
    assert not leads_are_duplicate(lead_one, distinct_lead)

  def test_duplicate_lead_helper_supports_attribute_objects(self):
    lead_one = SimpleNamespace(
      status=True,
      radar=True,
      radarTrackId=1234,
    )
    lead_two = SimpleNamespace(
      status=True,
      radar=True,
      radarTrackId=1234,
    )

    assert leads_are_duplicate(lead_one, lead_two)

  def test_radar_fault(self):
    # if there's no radar-related can traffic, radard should either not respond or respond with an error
    # this is tightly coupled with underlying car radar_interface implementation, but it's a good sanity check
    def single_iter_pkg():
      # single iter package, with meaningless cans and empty carState/modelV2
      msgs = []
      for _ in range(500):
        can = messaging.new_message("can", 1)
        cs = messaging.new_message("carState")
        cp = messaging.new_message("carParams")
        msgs.append(can.as_reader())
        msgs.append(cs.as_reader())
        msgs.append(cp.as_reader())
      model = messaging.new_message("modelV2")
      msgs.append(model.as_reader())

      return msgs

    msgs = [m for _ in range(3) for m in single_iter_pkg()]
    out = replay_process_with_name("card", msgs, fingerprint=TOYOTA.TOYOTA_COROLLA_TSS2)
    states = [m for m in out if m.which() == "liveTracks"]
    failures = [not state.valid for state in states]

    assert len(states) == 0 or all(failures)
