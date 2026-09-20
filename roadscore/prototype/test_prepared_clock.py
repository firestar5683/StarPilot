import unittest
import numpy as np
from prepared_clock import PreparedClock,ClockDiscontinuity


class PreparedClockTests(unittest.TestCase):
  @classmethod
  def setUpClass(cls):
    t=np.arange(480000,dtype=np.float32)/48000
    cls.core=np.column_stack((.5*np.sin(t*2100),.4*np.cos(t*1900))).astype(np.float32)
  def test_contiguous_samples_and_small_jitter_are_unchanged(self):
    clock=PreparedClock()
    a,one=clock.render(self.core,0,960)
    b,two=clock.render(self.core,1000,960)
    np.testing.assert_array_equal(a,self.core[:960]);np.testing.assert_array_equal(b,self.core[960:1920])
    self.assertEqual(two['post_error_frames'],40);self.assertEqual(clock.corrections,0)
  def test_measured_1884ms_stall_recovers_without_extra_samples(self):
    clock=PreparedClock();clock.render(self.core,0,960)
    before=self.core.copy();target=960+round(1.884*48000)
    first,info=clock.render(self.core,target,960)
    second,last=clock.render(self.core,target+960,960)
    self.assertEqual(first.shape,(960,2));self.assertEqual(second.shape,(960,2))
    self.assertEqual(info['correction']['delta_frames'],90432)
    self.assertEqual(clock.position,target+1920);self.assertIsNone(clock.fade_from)
    self.assertLess(np.max(abs(first[0]-self.core[960])),.001)
    np.testing.assert_allclose(second[-1],self.core[target+1919],atol=3e-8)
    self.assertEqual(last['post_error_frames'],0)
    self.assertEqual(clock.snapshot()['max_pre_error_seconds'],1.884)
    self.assertEqual(clock.snapshot()['max_post_error_seconds'],0)
    np.testing.assert_array_equal(self.core,before)
  def test_crossfade_independent_of_callback_block_split(self):
    a=PreparedClock();b=PreparedClock();a.render(self.core,0,960);b.render(self.core,0,960)
    whole,_=a.render(self.core,96000,2400)
    parts=[b.render(self.core,96000+i,480)[0] for i in range(0,2400,480)]
    np.testing.assert_array_equal(whole,np.concatenate(parts))
  def test_backward_or_absurd_jump_is_not_silently_accepted(self):
    clock=PreparedClock();clock.render(self.core,48000,960)
    position=clock.position
    for target in (0,position+6*48000):
      with self.assertRaises(ClockDiscontinuity):clock.render(self.core,target,960)
      self.assertEqual(clock.position,position)
  def test_explicit_seek_can_rebase_backwards(self):
    clock=PreparedClock();clock.render(self.core,96000,960)
    _,info=clock.render(self.core,4800,960,explicit_seek=True)
    self.assertEqual(info['correction']['kind'],'explicit-seek');self.assertEqual(clock.position,5760)
    self.assertEqual(clock.explicit_seeks,1);self.assertEqual(clock.corrections,0)
  def test_repeated_clock_instability_during_fade_is_rejected(self):
    clock=PreparedClock();clock.render(self.core,0,960);clock.render(self.core,48000,960)
    with self.assertRaises(ClockDiscontinuity):clock.render(self.core,96000,960)
  def test_original_negative_audio_origin_and_tail_are_zero_padded(self):
    clock=PreparedClock();first,_=clock.render(self.core,-480,960)
    np.testing.assert_array_equal(first[:480],np.zeros((480,2)))
    np.testing.assert_array_equal(first[480:],self.core[:480])
    other=PreparedClock();last,_=other.render(self.core,len(self.core)-480,960)
    np.testing.assert_array_equal(last[:480],self.core[-480:]);np.testing.assert_array_equal(last[480:],np.zeros((480,2)))
  def test_invalid_clock_and_source_are_rejected(self):
    clock=PreparedClock()
    for target in (float('nan'),True,12.5):
      with self.assertRaises(ValueError):clock.render(self.core,target,960)
    with self.assertRaises(ClockDiscontinuity):clock.render(self.core,len(self.core)+48001,960)

if __name__=='__main__':unittest.main()
