import json,tempfile,unittest
from pathlib import Path
from demo_engagement import DemoEngagement,presentation_active,presentation_signal,annotate

class Tests(unittest.TestCase):
 def test_modes_are_session_scoped_and_resettable(self):
  with tempfile.TemporaryDirectory() as d:
   c=DemoEngagement(d,'new','replay',clock=lambda:10)
   for mode in ('engaged','disengaged','recorded'):
    c.path.write_text(json.dumps(dict(version=1,session_id='new',mode=mode,created_wall=10)))
    self.assertEqual(c.poll(),mode)
   for patch in ({'session_id':'old'},{'created_wall':9},{'created_wall':11},{'mode':'bad'},{'created_wall':float('nan')}):
    c.path.write_text(json.dumps(dict(version=1,session_id='new',mode='engaged',created_wall=10)|patch))
    self.assertEqual(c.poll(),'recorded')
 def test_live_never_reads_override(self):
  with tempfile.TemporaryDirectory() as d:
   c=DemoEngagement(d,'new','live',clock=lambda:10)
   c.path.write_text(json.dumps(dict(version=1,session_id='new',mode='engaged',created_wall=10)))
   self.assertEqual(c.poll(),'recorded')
 def test_missing_malformed_restore_recorded(self):
  with tempfile.TemporaryDirectory() as d:
   c=DemoEngagement(d,'new','replay',clock=lambda:10)
   for content in ('broken','[]'):
    c.path.write_text(content);self.assertEqual(c.poll(),'recorded')
   c.path.unlink();self.assertEqual(c.poll(),'recorded')
 def test_only_presentation_state_changes(self):
  self.assertTrue(presentation_active('engaged',False))
  self.assertFalse(presentation_active('disengaged',True))
  self.assertTrue(presentation_active('recorded',True))
  original={'engagement_presentation':{'active':True}}
  out=annotate(original,'engaged',False)
  self.assertTrue(out['engagement_presentation']['simulated'])
  self.assertFalse(out['engagement_presentation']['recorded_active'])
  self.assertNotIn('simulated',original['engagement_presentation'])
 def test_combined_selection_is_atomic_and_legacy_resets_signals(self):
  with tempfile.TemporaryDirectory() as d:
   c=DemoEngagement(d,'new','replay',clock=lambda:10)
   value=dict(version=1,session_id='new',mode='disengaged',signal_mode='left',created_wall=10)
   c.path.write_text(json.dumps(value));c.poll()
   self.assertEqual(c.selection,('disengaged','left'))
   value.pop('signal_mode');c.path.write_text(json.dumps(value));c.poll()
   self.assertEqual(c.selection,('disengaged','recorded'))
   value['signal_mode']='both';c.path.write_text(json.dumps(value));c.poll()
   self.assertEqual(c.selection,('recorded','recorded'))
 def test_signal_choice_preserves_recorded_and_suppresses_when_off(self):
  self.assertTrue(presentation_signal('left',False))
  self.assertTrue(presentation_signal('right',False))
  self.assertFalse(presentation_signal('off',True))
  self.assertTrue(presentation_signal('recorded',True))
  self.assertFalse(presentation_signal('recorded',False))

if __name__=='__main__':unittest.main()
