import unittest
from song_form import SongForm
class FormTest(unittest.TestCase):
 def test_curve_and_cooldown(self):
  f=SongForm(120);r={'kind':'curve','phase':'anticipation','strength':2,'activation':10,'lead':5}
  f.update(10,r);self.assertEqual(f.next['section'],'chorus');self.assertEqual(f.next['at'],16)
  self.assertIsNone(f.update(15,r));self.assertEqual(f.update(16,r)['section'],'chorus')
  f.update(17,{**r,'activation':17});self.assertIsNone(f.next)
 def test_outro_supersedes(self):
  f=SongForm();f.schedule('bridge',10,16,'predicted curve');f.update(11,{},arrival=True);self.assertEqual(f.next['section'],'outro')
 def test_straight_road_not_fixed_pop_sequence(self):
  f=SongForm()
  for t in range(600):f.update(t,{})
  self.assertEqual(f.section,'verse');self.assertFalse(f.events)
