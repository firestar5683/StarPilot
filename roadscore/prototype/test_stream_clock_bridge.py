import unittest

from stream_clock_bridge import StreamClockBridge


class StreamClockBridgeTests(unittest.TestCase):
  def test_uses_narrowest_bracket_and_supports_distinct_clock_origins(self):
    walls=iter([100.,100.02,101.,101.002,102.,102.01])
    source=iter([500.01,501.001,502.005])
    bridge=StreamClockBridge.measure(lambda:next(source),clock=lambda:next(walls),samples=3)
    self.assertAlmostEqual(bridge.offset,-400.)
    self.assertAlmostEqual(bridge.uncertainty,.001)
    self.assertAlmostEqual(bridge.dac_wall(505.02),105.02)

  def test_delayed_callback_then_burst_cannot_shift_stream_clock_mapping(self):
    # The old conversion added callback-entry delay to the DAC timestamp.
    # A delayed callback followed by prompt callbacks looked like a seek back.
    bridge=StreamClockBridge(-400.,.0001)
    driver_current=[500.,500.02,500.04,500.06]
    entered=[100.,100.08,100.04,100.06]
    dac=[stamp+.056 for stamp in driver_current]
    old=[now+d-current for now,d,current in zip(entered,dac,driver_current)]
    self.assertLess(old[2],old[1])
    mapped=[bridge.dac_wall(stamp) for stamp in dac]
    for a,b in zip(mapped,mapped[1:]):self.assertAlmostEqual(b-a,.02)

  def test_invalid_samples_and_uncertain_bracket_fail_closed(self):
    for source in (0.,float('nan'),float('inf')):
      with self.assertRaises(ValueError):StreamClockBridge.measure(lambda:source,clock=lambda:1.,samples=1)
    walls=iter([1.,1.1])
    with self.assertRaises(ValueError):StreamClockBridge.measure(lambda:10.,clock=lambda:next(walls),samples=1)
    with self.assertRaises(ValueError):StreamClockBridge.measure(lambda:10.,samples=0)

  def test_invalid_dac_timestamp_is_rejected(self):
    with self.assertRaises(ValueError):StreamClockBridge(0.,0.).dac_wall(float('nan'))

  def test_silent_callbacks_calibrate_once_without_get_stream_time(self):
    delays=[.002,.008,.003,.0003,.004,.006,.001,.002]
    observations=[(100.+i*.02+delay,500.+i*.02,500.+i*.02+.04) for i,delay in enumerate(delays)]
    bridge=StreamClockBridge.from_callbacks(observations)
    self.assertAlmostEqual(bridge.offset,-399.9997)
    self.assertAlmostEqual(bridge.dac_wall(501.04),101.0403)
    self.assertAlmostEqual(bridge.offset_spread,.0077)
    self.assertIsNone(bridge.uncertainty)

  def test_uninitialized_or_nonadvancing_callback_clock_is_not_used(self):
    for samples in ([(1.,0.,0.)]*8,[(1.+i*.02,500.,500.04) for i in range(8)],[]):
      with self.assertRaises(ValueError):StreamClockBridge.from_callbacks(samples)

  def test_coreaudio_batch_may_repeat_current_time_while_dac_advances(self):
    samples=[(100.+i*.02,500.+(i//2)*.04,500.1+i*.02) for i in range(8)]
    bridge=StreamClockBridge.from_callbacks(samples)
    self.assertAlmostEqual(bridge.offset,-400.)
    self.assertAlmostEqual(bridge.dac_wall(501.),101.)

  def test_bluetooth_dac_estimate_can_adjust_during_silent_priming(self):
    samples=[(100.+i*.015,500.+i*.015,500.+i*.015+.06) for i in range(8)]
    samples[4]=(samples[4][0],samples[4][1],samples[3][2]-.002235)
    bridge=StreamClockBridge.from_callbacks(samples)
    self.assertAlmostEqual(bridge.offset,-400.)


if __name__=='__main__':unittest.main()
