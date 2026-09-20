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

  def test_measured_65ms_bluetooth_delay_correction_crossfades(self):
    # Saved0217 failed with next8757465 vs expected8754316: 3149 frames,
    # or65.60ms backwards in the estimated DAC clock, not in model messages.
    clock=PreparedClock();clock.render(self.core,96000,960)
    previous=clock.position;target=previous-3149
    first,info=clock.render(self.core,target,960)
    second,last=clock.render(self.core,target+960,960)
    self.assertEqual(info['correction']['kind'],'backward-dac-recovery')
    self.assertEqual(info['correction']['delta_frames'],-3149)
    self.assertEqual(first.shape,(960,2));self.assertEqual(second.shape,(960,2))
    self.assertLess(np.max(abs(first[0]-self.core[previous])),.001)
    np.testing.assert_allclose(second[-1],self.core[target+1919],atol=3e-8)
    self.assertEqual(last['post_error_frames'],0)
    self.assertEqual(clock.explicit_seeks,0);self.assertEqual(clock.corrections,1)
    self.assertIsNone(clock.fade_from)

  def test_reverse_clock_recovery_has_a_separate_small_bound(self):
    clock=PreparedClock();clock.render(self.core,96000,960)
    before=clock.position
    with self.assertRaises(ClockDiscontinuity):clock.render(self.core,before-12001,960)
    self.assertEqual(clock.position,before)
    with self.assertRaises(ValueError):PreparedClock(maximum_backward_seconds=1.)
  def test_explicit_seek_can_rebase_backwards(self):
    clock=PreparedClock();clock.render(self.core,96000,960)
    _,info=clock.render(self.core,4800,960,explicit_seek=True)
    self.assertEqual(info['correction']['kind'],'explicit-seek');self.assertEqual(clock.position,5760)
    self.assertEqual(clock.explicit_seeks,1);self.assertEqual(clock.corrections,0)
  def test_bounded_dac_bounce_finishes_blend_before_latest_correction(self):
    before=self.core.copy()
    for delta in (-3149,3149):
      with self.subTest(delta=delta):
        clock=PreparedClock();reference=PreparedClock()
        for item in (clock,reference):item.render(self.core,96000,960)
        previous=clock.position;target=previous+delta
        first,_=clock.render(self.core,target,960)
        reference.render(self.core,target,960)
        # DAC estimate returns to its old trajectory midway through the fade.
        second,deferred=clock.render(self.core,previous+960,960)
        uninterrupted,_=reference.render(self.core,target+960,960)
        np.testing.assert_array_equal(second,uninterrupted)
        self.assertTrue(deferred['correction_deferred']);self.assertIsNone(deferred['correction'])
        self.assertEqual(deferred['post_error_frames'],-delta)
        self.assertEqual(clock.corrections,1);self.assertIsNone(clock.fade_from)
        # Use the newest estimate, rather than the older deferred target.
        latest=previous+1920+137
        third,resumed=clock.render(self.core,latest,960)
        fourth,last=clock.render(self.core,latest+960,960)
        self.assertEqual(resumed['correction']['to_frame'],latest)
        self.assertFalse(resumed['correction_deferred'])
        self.assertLess(np.max(abs(third[0]-self.core[target+1920])),.001)
        np.testing.assert_allclose(fourth[-1],self.core[latest+1919],atol=3e-8)
        self.assertEqual(np.concatenate((first,second,third,fourth)).shape,(3840,2))
        self.assertEqual(clock.position,latest+1920);self.assertEqual(clock.corrections,2)
        self.assertEqual(last['post_error_frames'],0);self.assertEqual(clock.explicit_seeks,0)
    np.testing.assert_array_equal(self.core,before)

  def test_transient_deferred_estimate_is_not_applied_later(self):
    clock=PreparedClock();clock.render(self.core,96000,960)
    target=clock.position-3149
    clock.render(self.core,target,960)
    _,deferred=clock.render(self.core,target+960+3149,960)
    self.assertTrue(deferred['correction_deferred'])
    pcm,settled=clock.render(self.core,target+1920,960)
    self.assertIsNone(settled['correction']);self.assertEqual(clock.corrections,1)
    np.testing.assert_array_equal(pcm,self.core[target+1920:target+2880])

  def test_out_of_bound_clock_change_during_fade_is_still_rejected(self):
    clock=PreparedClock();clock.render(self.core,96000,960);clock.render(self.core,100800,960)
    position=clock.position;fade=(clock.fade_from,clock.fade_done)
    for target in (position-12001,position+5*48000+1):
      with self.assertRaises(ClockDiscontinuity):clock.render(self.core,target,960)
      self.assertEqual(clock.position,position);self.assertEqual((clock.fade_from,clock.fade_done),fade)

  def test_explicit_seek_during_fade_is_not_deferred(self):
    clock=PreparedClock();clock.render(self.core,96000,960);clock.render(self.core,100800,960)
    _,info=clock.render(self.core,4800,960,explicit_seek=True)
    self.assertEqual(info['correction']['kind'],'explicit-seek');self.assertFalse(info['correction_deferred'])
    self.assertEqual(clock.position,5760);self.assertEqual(clock.explicit_seeks,1)
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
