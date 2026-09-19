import unittest
from composition_policy import CompositionPolicy
class CompositionTest(unittest.TestCase):
 def test_outro_needs_delivered_destination_horizon(self):
  p=CompositionPolicy();self.assertEqual(p.choose(0,48000,{},10,30),'base')
  self.assertEqual(p.choose(0,48000,{'valid':True,'remaining':400,'eta':50},10,30),'closing')
 def test_intent_is_not_claimed_heard_before_playback(self):
  p=CompositionPolicy();p.generated({'id':1,'conditioning':'closing'},30)
  p.update(29);self.assertEqual(p.snapshot(29)['outro_heard_seconds'],0)
  p.update(42);self.assertEqual(p.snapshot(42)['outro_heard_seconds'],12)
 def test_nav_transition_requires_generation_lookahead(self):
  p=CompositionPolicy();nav={'valid':True,'remaining':2000,'eta':200,'distance':50}
  self.assertEqual(p.choose(0,48000,nav,10,30),'base')
  self.assertEqual(p.choose(0,48000,{**nav,'distance':500},10,30),'approach')

 def test_route_revision_clears_outro_intent(self):
  p=CompositionPolicy();p.choose(0,48000,{'valid':True,'remaining':100,'eta':30},10,30)
  p.route_change();self.assertFalse(p.outro_intent);self.assertIsNone(p.outro_start)

 def test_navigation_clear_does_not_erase_heard_outro(self):
  p=CompositionPolicy();p.generated({'id':1,'conditioning':'closing'},200);p.update(235);p.route_change()
  self.assertEqual(p.snapshot(239)['outro_heard_seconds'],39)
  self.assertEqual(p.snapshot(239)['outro_job'],1)
  p.generated({'id':2,'conditioning':'base'},250);p.update(251)
  self.assertEqual(p.snapshot(251)['outro_heard_seconds'],0)
