import unittest
from jitter import overdue_frames
class JitterTest(unittest.TestCase):
 def test_no_drift_concealment(self):
  self.assertEqual(overdue_frames(10,10.005,48000,4800),0)
  self.assertEqual(overdue_frames(10,10.25,48000,4800),4800)
  self.assertEqual(overdue_frames(10.2,10.25,48000,4800),2400)
  self.assertEqual(overdue_frames(10.3,10.25,48000,4800),0)
