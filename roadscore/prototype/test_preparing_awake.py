import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock
from preparing_awake import PreparationWake

class WakeTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
  self.path=Path(self.tmp.name)/'status.json';self.device=Mock();self.ui=SimpleNamespace(started=False)
  self.wake=PreparationWake(self.path,True)
 def state(self,**values):self.path.write_text(json.dumps(values))
 def test_long_cold_preparation_remains_visible_then_stops_on_ready(self):
  self.state(readiness='Preparing')
  for second in range(0,901):self.assertTrue(self.wake.update(self.ui,self.device,second))
  self.assertEqual(self.device.reset_interactive_timeout.call_count,901)
  self.state(readiness='READY');self.assertFalse(self.wake.update(self.ui,self.device,901))
  self.assertEqual(self.device.reset_interactive_timeout.call_count,901)
 def test_no_other_ui_or_playback_is_kept_awake(self):
  self.state(readiness='PREPARING')
  self.ui.started=True;self.assertFalse(self.wake.update(self.ui,self.device,0))
  self.ui.started=False
  self.assertFalse(PreparationWake(self.path,False).update(self.ui,self.device,0))
  self.assertFalse(PreparationWake(None,True).update(self.ui,self.device,0))
  self.device.reset_interactive_timeout.assert_not_called()
 def test_failure_missing_and_invalid_status_stop_refresh(self):
  for second,value in enumerate([{'readiness':'DEGRADED'},{'readiness':'Preparing','worker_failed':True},{'readiness':'Preparing','failure_kind':'connection_lost'},[]]):
   self.path.write_text(json.dumps(value));self.assertFalse(self.wake.update(self.ui,self.device,second))
  self.path.unlink();self.assertFalse(self.wake.update(self.ui,self.device,4))
  self.path.write_text('{');self.assertFalse(self.wake.update(self.ui,self.device,5))
  self.device.reset_interactive_timeout.assert_not_called()
 def test_bounded_polling(self):
  self.state(readiness='PREPARING')
  self.assertTrue(self.wake.update(self.ui,self.device,0))
  self.assertFalse(self.wake.update(self.ui,self.device,.1))
  self.assertTrue(self.wake.update(self.ui,self.device,1))

if __name__=='__main__':unittest.main()
