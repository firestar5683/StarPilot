import json,tempfile,time,unittest
from pathlib import Path
from cue_timing import audible_state,REFERENCE
from status_relay import StatusRelay

class CueTests(unittest.TestCase):
 def test_dac_plus_residual_and_live_health(self):
  state={'presentation_timing_reference':REFERENCE,'phase':'wrong-early','buffered':44,'route_t':10,'readiness':'DEGRADED','presentation_timeline':[{'audible_wall':10.323,'sequence':1,'cues':{'phase':'stopped','buffered':0}},{'audible_wall':10.45,'sequence':2,'cues':{'phase':'moving'}}]}
  self.assertNotIn('phase',audible_state(state,10.322))
  shown=audible_state(state,10.324);self.assertEqual(shown['phase'],'stopped');self.assertEqual(shown['buffered'],44);self.assertEqual(shown['readiness'],'DEGRADED')
  self.assertEqual(audible_state(state,10.451)['phase'],'moving')
  self.assertEqual(state['phase'],'wrong-early')
 def test_new_session_does_not_retain_previous_cue(self):
  for session in ('old','new'):
   state={'presentation_session_id':session,'presentation_timing_reference':REFERENCE,'presentation_timeline':[]}
   self.assertNotIn('phase',audible_state(state,100))
 def test_legacy_and_invalid_entries(self):
  self.assertEqual(audible_state({'phase':'legacy'},3),{'phase':'legacy'})
  state={'presentation_timing_reference':REFERENCE,'presentation_timeline':[None,{'audible_wall':float('nan'),'cues':{}},{'audible_wall':5,'cues':{}}]}
  self.assertNotIn('phase',audible_state(state,3))
 def test_relay_is_atomic_and_keeps_last_valid_status(self):
  with tempfile.TemporaryDirectory() as folder:
   folder=Path(folder);source=folder/'in.json';target=folder/'out.json';source.write_text('{"phase":"ready"}')
   relay=StatusRelay(source,target,interval=.005);relay.start()
   try:
    deadline=time.monotonic()+1
    while not target.exists() and time.monotonic()<deadline:time.sleep(.005)
    self.assertEqual(json.loads(target.read_text())['phase'],'ready')
    source.write_text('{broken');time.sleep(.03)
    self.assertEqual(json.loads(target.read_text())['phase'],'ready')
   finally:relay.close()
   self.assertFalse(relay.thread.is_alive())
if __name__=='__main__':unittest.main()
