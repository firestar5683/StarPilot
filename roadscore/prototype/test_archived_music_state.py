import unittest,json,tempfile
from pathlib import Path
from archived_music_state import ArchivedMusicState
class ArchiveGestureTest(unittest.TestCase):
 def test_never_shows_future_request(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);(p/'gestures.json').write_text(json.dumps({'events':[{'type':'scheduled','id':1,'kind':'curve_apex','requested_frame':100,'scheduled_frame':200}]}))
   a=ArchivedMusicState(p,10);self.assertFalse(a.at(9)['gesture_queued']);self.assertEqual(a.at(15)['gesture_queued'][0]['kind'],'curve_apex')
 def test_ended_signal_tail_disappears(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);(p/'gestures.json').write_text(json.dumps({'events':[{'type':'started','id':1,'kind':'turn_signal','actual_frame':10,'duration_frames':100},{'type':'stop_requested','id':1,'stop_frame':20}]}))
   a=ArchivedMusicState(p,10);self.assertTrue(a.at(1.5)['turn_signal_music']);self.assertFalse(a.at(2.1)['turn_signal_music'])

 def test_road_overlay_exposes_only_already_recorded_decisions(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);(p/'decisions.jsonl').write_text(json.dumps({'elapsed':10,'route_t':110,'phase':'anticipation','kind':'curve','predicted_peak':116})+'\n')
   a=ArchivedMusicState(p)
   self.assertNotIn('lead',a.at(9))
   self.assertEqual(a.at(12)['lead'],4)
