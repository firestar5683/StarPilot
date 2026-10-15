"""Actual RadarD lead selection without changing radar health or input data."""

from types import SimpleNamespace
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from openpilot.selfdrive.controls import radard
from openpilot.selfdrive.controls.radard import RadarD
from openpilot.selfdrive.controls.tests.test_adjacent_radar_transport import Captured, MONO, Sources
from openpilot.starpilot.longitudinal.voacc import selected


class VoaccTest(unittest.TestCase):
  def source(self, *, vision=True):
    source = Sources(MONO, points=((17, 5., 0., 0.),))
    source.data['radarTracks'].init('errors')
    source.data['carState'].vEgo = 0.
    for lead in source.data['modelV2'].leadsV3:
      lead.prob = .99 if vision else 0.
      lead.x, lead.y, lead.v, lead.a = [20.], [0.], [15.], [0.]
      lead.xStd, lead.yStd, lead.vStd = [1.], [1.], [1.]
    return source

  def test_vision_only_both_leads_ignore_low_speed_radar_override(self):
    source = self.source()
    raw = {name: value.to_dict() for name, value in source.data.items()}
    normal, vision = RadarD(), RadarD(use_voacc=True)
    normal.update(source, source['radarTracks'])
    vision.update(source, source['radarTracks'])
    self.assertTrue(normal.radar_state.leadOne.radar)
    self.assertEqual(normal.radar_state.leadOne.dRel, 5.)
    for lead in (vision.radar_state.leadOne, vision.radar_state.leadTwo):
      self.assertTrue(lead.present)
      self.assertFalse(lead.radar)
      self.assertEqual(lead.radarTrackId, -1)
      self.assertAlmostEqual(lead.dRel, 18.48, delta=1e-6)
    self.assertEqual(vision.tracks[17].dRel, 5.)
    self.assertEqual(raw, {name: value.to_dict() for name, value in source.data.items()})

  def test_no_vision_lead_does_not_use_radar_only_lead(self):
    source = self.source(vision=False)
    radar = RadarD(use_voacc=True)
    radar.update(source, source['radarTracks'])
    self.assertFalse(radar.radar_state.leadOne.present)
    self.assertFalse(radar.radar_state.leadTwo.present)

  def test_radar_errors_and_message_validity_are_preserved(self):
    for field in ('canError', 'radarFault', 'wrongConfig', 'radarUnavailableTemporary'):
      with self.subTest(field=field):
        source = self.source()
        setattr(source.data['radarTracks'].errors, field, True)
        source.valid['radarTracks'] = False
        radar = RadarD(use_voacc=True)
        radar.update(source, source['radarTracks'])
        publisher = Captured()
        radar.publish(publisher)
        result = publisher.messages['radarState']
        self.assertFalse(result.valid)
        self.assertTrue(getattr(result.radarState.radarErrors, field))

  def test_specialized_honda_radar_leads_are_bypassed_but_tracks_still_update(self):
    source = self.source()
    radar = RadarD(honda_bosch_a_radar=True, use_voacc=True)
    policy = SimpleNamespace(update_tracks=Mock(), leads=Mock(side_effect=AssertionError("radar lead path")))
    radar.honda_bosch_a = policy
    radar.update(source, source['radarTracks'])
    policy.update_tracks.assert_called_once_with(source, source['radarTracks'], radar)
    policy.leads.assert_not_called()
    self.assertFalse(radar.radar_state.leadOne.radar)

  def test_default_off_keeps_normal_output(self):
    source = self.source()
    default, disabled = RadarD(), RadarD(use_voacc=False)
    default.update(source, source['radarTracks'])
    disabled.update(source, source['radarTracks'])
    self.assertEqual(default.radar_state.to_dict(), disabled.radar_state.to_dict())

  def test_main_latches_setting_until_next_drive(self):
    with tempfile.TemporaryDirectory() as directory:
      path = Path(directory) / 'UseVOACC'
      path.write_bytes(b'1')
      params = SimpleNamespace(get=lambda *args, **kwargs: b'cp', get_param_path=lambda key: str(path))
      cp = SimpleNamespace(brand='toyota', carFingerprint='test', radarDelay=0., radarUnavailable=False,
                           openpilotLongitudinalControl=True, notCar=False, dashcamOnly=False, passive=False)
      source = self.source()
      source.update = Mock(side_effect=(None, StopIteration))
      instances = []

      def create(*args, **kwargs):
        result = RadarD(*args, **kwargs)
        instances.append(result)
        path.write_bytes(b'0')
        return result

      with patch.object(radard, 'Params', return_value=params), \
           patch.object(radard, 'config_realtime_process'), patch.object(radard, 'set_core_affinity'), \
           patch.object(radard, 'feature_enabled', return_value=False), \
           patch.object(radard.messaging, 'log_from_bytes', return_value=cp), \
           patch.object(radard.messaging, 'SubMaster', return_value=source), \
           patch.object(radard.messaging, 'PubMaster', return_value=Captured()), \
           patch.object(radard, 'voacc_selected', wraps=selected) as read, \
           patch.object(radard, 'RadarD', side_effect=create):
        with self.assertRaises(StopIteration):
          radard.main()
      read.assert_called_once_with(params, cp)
      self.assertTrue(instances[0].use_voacc)
      self.assertFalse(instances[0].radar_state.leadOne.radar)
      self.assertFalse(selected(params, cp), 'Next drive reads the newly saved Off')
