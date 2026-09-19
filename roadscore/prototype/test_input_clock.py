import tempfile,unittest
from pathlib import Path
from input_clock import InputClock
class State:
 updated={'modelV2':True};logMonoTime={'modelV2':1000000000}
class Tests(unittest.TestCase):
 def test_live_never_needs_route_clock(self):
  with tempfile.TemporaryDirectory() as path:
   c=InputClock('live',Path(path));s=State();self.assertEqual(c.read(s)['t'],0)
   s.logMonoTime={'modelV2':2500000000};self.assertEqual(c.read(s)['t'],1.5)
 def test_replay_waits_for_its_clock(self):
  with tempfile.TemporaryDirectory() as path:self.assertIsNone(InputClock('replay',Path(path)).read(State()))
if __name__=='__main__':unittest.main()
