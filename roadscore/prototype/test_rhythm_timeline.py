import unittest
from unittest.mock import patch
import numpy as np
from rhythm_timeline import RhythmTimeline, UNKNOWN
from signal_shaker import ShakerGrid, SignalShaker

GRID=ShakerGrid(128,.2,.8,.9,True,'test')

class RhythmTests(unittest.TestCase):
 def test_lookups_never_analyze_audio_and_expire(self):
  timeline=RhythmTimeline(100,128)
  with patch('rhythm_timeline.assess_grid',return_value=(GRID,{})) as estimate:
   timeline.add(np.zeros((3300,2)),1000)
   calls=estimate.call_count
   self.assertIs(timeline.at(999),UNKNOWN)
   self.assertEqual(timeline.at(2100).beat_phase,20.2)
   self.assertIs(timeline.at(4300),UNKNOWN)
   self.assertEqual(estimate.call_count,calls)
 def test_new_passage_replaces_old_future_grid(self):
  timeline=RhythmTimeline(100,128)
  with patch('rhythm_timeline.assess_grid',return_value=(GRID,{})):
   timeline.add(np.zeros((6000,2)),0)
   timeline.add(np.zeros((2800,2)),3500)
  self.assertEqual(timeline.at(4000).beat_phase,35.2)
  self.assertEqual(timeline.at(5000).beat_phase,45.2)
  self.assertIs(timeline.at(6300),UNKNOWN)
 def test_refresh_does_not_restart_blink_sequence(self):
  shaker=SignalShaker(GRID,rate=8000,enabled=True)
  x=np.zeros((800,2),np.float32)
  for i in range(30):
   if i==10:shaker.set_grid(ShakerGrid(128,.22,.8,.9,True,'refresh'),i*800)
   shaker.process(x,i*800,True,True)
  self.assertEqual(len(shaker.sequence_starts),1)
  self.assertGreater(min(np.diff(shaker.pulse_frames)),800)

if __name__=='__main__':unittest.main()
