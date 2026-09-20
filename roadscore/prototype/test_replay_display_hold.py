import json
from pathlib import Path
import tempfile
import unittest
from replay_display_hold import ReplayDisplayHold

class DisplayHoldTests(unittest.TestCase):
  def setUp(self):
    self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
    self.path=Path(self.tmp.name)/'audio_drained.json';self.now=100.
    self.hold=ReplayDisplayHold(self.path,True,lambda:self.now)
  def marker(self,wall,drained=True):self.path.write_text(json.dumps(dict(wall=wall,drained=drained)))
  def test_actual_onroad_required(self):
    self.assertFalse(self.hold.apply(False));self.assertTrue(self.hold.apply(True))
    self.now+=1;self.assertTrue(self.hold.apply(False))
    self.now+=2;self.marker(self.now);self.assertFalse(self.hold.apply(False))
  def test_stale_marker_ignored_and_timeout_bounded(self):
    self.marker(99);self.hold.apply(True);self.assertTrue(self.hold.apply(False))
    self.now+=20;self.assertFalse(self.hold.apply(False))
  def test_failure_releases_and_cannot_relatch(self):
    self.hold.apply(True);self.marker(100,False)
    self.assertFalse(self.hold.apply(False));self.assertTrue(self.hold.apply(True));self.assertFalse(self.hold.apply(False))
  def test_disabled_never_holds(self):
    hold=ReplayDisplayHold(self.path,False,lambda:self.now)
    self.assertTrue(hold.apply(True));self.assertFalse(hold.apply(False))
  def test_partial_and_future_marker_do_not_release(self):
    self.hold.apply(True);self.path.write_text('{')
    self.assertTrue(self.hold.apply(False));self.marker(200)
    self.assertTrue(self.hold.apply(False))

if __name__=='__main__':unittest.main()
