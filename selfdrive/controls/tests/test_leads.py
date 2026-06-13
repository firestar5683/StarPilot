from types import SimpleNamespace

import cereal.messaging as messaging

from opendbc.car.toyota.values import CAR as TOYOTA
from openpilot.selfdrive.test.process_replay import replay_process_with_name
from openpilot.selfdrive.controls.radard import g90_low_speed_radar_lead_sane, g90_radar_lead_lateral_sane


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
