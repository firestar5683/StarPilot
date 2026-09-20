import tempfile,unittest
from pathlib import Path
from input_clock import InputClock
class State:
 def __init__(self,stamp=1_000_000_000):
  self.updated={'modelV2':True}
  self.logMonoTime={k:stamp for k in ('modelV2','carState','selfdriveState')}
  self.valid={k:True for k in self.logMonoTime}
class Tests(unittest.TestCase):
 def test_live_never_needs_route_clock(self):
  with tempfile.TemporaryDirectory() as path:
   now=[1_000_000_000]
   c=InputClock('live',Path(path),source_clock=lambda:now[0]);s=State()
   self.assertEqual(c.read(s)['t'],0)
   now[0]=2_500_000_000;s=State(now[0])
   self.assertEqual(c.read(s)['t'],1.5)
 def test_replay_waits_for_its_clock(self):
  with tempfile.TemporaryDirectory() as path:self.assertIsNone(InputClock('replay',Path(path)).read(State()))
 def test_live_waits_for_all_valid_inputs_before_start(self):
  for topic in ('modelV2','carState','selfdriveState'):
   c=InputClock('live',Path('/unused'),source_clock=lambda:1_000_000_000)
   s=State();s.valid[topic]=False
   self.assertIsNone(c.read(s));self.assertIsNone(c.origin)
 def test_live_stale_future_and_rollback_stop_after_start(self):
  for stamp in (1,2_000_000_000,999_999_999):
   c=InputClock('live',Path('/unused'),source_clock=lambda:1_000_000_000)
   c.read(State());s=State();s.logMonoTime['carState']=stamp
   with self.assertRaises(RuntimeError):c.read(s)
 def test_boot_clock_independent_of_wall_clock(self):
  c=InputClock('live',Path('/unused'),source_clock=lambda:1_000_000_000,wall_clock=lambda:100)
  self.assertEqual(c.read(State())['origin_wall'],100)
if __name__=='__main__':unittest.main()
