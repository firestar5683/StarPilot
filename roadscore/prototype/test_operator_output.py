import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('operator_output', Path(__file__).with_name('operator_output.py'))
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)

class Clock:
  value = 100.
  def __call__(self): return self.value

class Sink:
  failed = False
  def __init__(self, callback, count): self.callback, self.count, self.closed = callback, count, False
  def start(self): pass
  def close(self): self.closed = True

class OutputTests(unittest.TestCase):
  def setUp(self):
    self.temp = tempfile.TemporaryDirectory(); self.root = Path(self.temp.name); self.clock = Clock()
    self.output = dict(id='speaker-a', name='Speaker', connected=True, muted=False)
    self.parked = True
    self.scan=patch.object(m,'playback_process_active',return_value=False);self.scan.start();self.addCleanup(self.scan.stop)
    self.owner = m.OutputOwner(self.root, lambda:self.parked, Sink, lambda:self.output, self.clock)
  def tearDown(self):
    self.owner._close(); self.temp.cleanup()

  def test_start_requires_attendance_and_locks_session(self):
    with self.assertRaises(ValueError): self.owner.dispatch('calibration_start')
    result = self.owner.dispatch('calibration_start', attended=True)
    self.assertTrue(result['session'])
    self.assertTrue(m.busy(self.root/'generated/session.lock'))
    self.assertTrue(m.busy(self.root/'generated/operator.lock'))
    self.owner.dispatch('calibration_cancel', session=result['session'])
    self.assertFalse(m.busy(self.root/'generated/session.lock'))

  def test_busy_muted_and_onroad_reject_before_sink(self):
    self.root.joinpath('generated').mkdir()
    with m.lease(self.root/'generated/session.lock'):
      with self.assertRaises(ValueError): self.owner.dispatch('calibration_start', attended=True)
    self.root.joinpath('.session-muted').touch()
    with self.assertRaises(ValueError): self.owner.dispatch('calibration_start', attended=True)
    self.root.joinpath('.session-muted').unlink(); self.parked=False
    with self.assertRaises(ValueError): self.owner.dispatch('set_latency', latency_ms=100)

  def test_paired_beats_outliers_duplicate_and_save(self):
    token=self.owner.dispatch('calibration_start', attended=True)['session']
    for i in range(8):self.owner.session['sink'].callback(i,100000+i*600)
    with self.assertRaises(ValueError):self.owner.dispatch('calibration_tap',session=token,server_ms=100200,uncertainty_ms=3)
    offsets=[200,201,198,202,199,203,197,200,201,199,400,205,200,201,199,200]
    for index, offset in enumerate(offsets):
      i=index+8;click=100000+i*600;self.clock.value=(click+offset)/1000
      self.owner.session['sink'].callback(i,click)
      self.owner.dispatch('calibration_tap', session=token, server_ms=click+offset, uncertainty_ms=3)
      with self.assertRaises(ValueError):self.owner.dispatch('calibration_tap',session=token,server_ms=click+offset+5,uncertainty_ms=3)
    result=self.owner.dispatch('calibration_result',session=token)
    self.assertEqual(result['latency_ms'],200);self.assertEqual(result['rejected_taps'],1)
    self.assertEqual(result['count_in_beats'],8);self.assertTrue(result['whole_beat_ambiguity_possible'])
    self.assertFalse((self.root/'generated/output_timing.json').exists())
    self.owner.dispatch('set_latency',latency_ms=result['latency_ms'])
    self.assertEqual(self.owner.status()['latency_ms'],200)
    self.output={**self.output,'id':'speaker-b'}
    self.assertEqual(self.owner.status()['latency_ms'],0)

  def test_uncertain_clock_stale_token_and_judging_lock(self):
    token=self.owner.dispatch('calibration_start',attended=True)['session']
    self.owner.session['sink'].callback(0,100000)
    with self.assertRaises(ValueError):self.owner.dispatch('calibration_tap',session=token,server_ms=100200,uncertainty_ms=26)
    self.owner.dispatch('calibration_cancel',session=token)
    with self.assertRaises(ValueError):self.owner.dispatch('calibration_tap',session=token,server_ms=100200,uncertainty_ms=1)
    with m.lease(self.root/'generated/operator.lock'):
      self.assertTrue(self.owner.status()['judging_locked'])
      with self.assertRaises(BlockingIOError):self.owner.dispatch('set_latency',latency_ms=200)

  def test_presentation_delays_only_observed_cues(self):
    self.owner.dispatch('set_latency',latency_ms=200)
    delay=m.PresentationDelay(self.root,lambda:self.output,self.clock)
    original={'phase':'curve','buffered':90,'route_t':100,'readiness':'READY'}
    shown=delay.apply(original)
    self.assertNotIn('phase',shown);self.assertEqual(shown['route_t'],100)
    self.clock.value+=.21
    next_snapshot={'phase':'apex','buffered':80,'route_t':101,'readiness':'DEGRADED'}
    shown=delay.apply(next_snapshot)
    self.assertEqual(shown['phase'],'curve');self.assertEqual(shown['readiness'],'DEGRADED')
    self.assertEqual(shown['buffered'],80);self.assertEqual(next_snapshot['phase'],'apex')

  def test_rendered_cues_delay_without_touching_raw_audio_clock_or_core(self):
    import copy
    self.owner.dispatch('set_latency',latency_ms=250)
    delay=m.PresentationDelay(self.root,lambda:self.output,self.clock)
    raw=dict(signal_shaker={'rendered_active':True},core_apex={'rendered_active':True},alert_accent={'rendered_active':False},engagement_presentation={'active':True},elapsed=50,route_t=10,source_cutoff_ns=123,buffered=80,readiness='READY')
    original=copy.deepcopy(raw)
    first=delay.apply(raw)
    self.assertNotIn('signal_shaker',first)
    self.assertEqual(first['elapsed'],50);self.assertEqual(first['source_cutoff_ns'],123)
    self.clock.value+=.26
    current={**raw,'signal_shaker':{'rendered_active':False},'route_t':11,'elapsed':50.26,'readiness':'DEGRADED'}
    shown=delay.apply(current)
    self.assertTrue(shown['signal_shaker']['rendered_active'])
    self.assertEqual(shown['readiness'],'DEGRADED');self.assertEqual(shown['route_t'],11)
    self.assertEqual(raw,original);self.assertFalse(current['signal_shaker']['rendered_active'])
    self.output=None;self.clock.value+=3
    bypass=delay.apply(current)
    self.assertEqual(bypass['presentation_latency_ms'],0);self.assertFalse(bypass['signal_shaker']['rendered_active'])

  def test_watchdog_cancels_own_audio_and_releases_leases(self):
    token=self.owner.dispatch('calibration_start',attended=True)['session']
    sink=self.owner.session['sink']
    self.output={**self.output, 'id':'changed-output'}
    self.assertFalse(self.owner._check_session(token))
    self.assertTrue(sink.closed)
    self.assertFalse(m.busy(self.root/'generated/session.lock'))
    token=self.owner.dispatch('calibration_start',attended=True)['session']
    self.clock.value+=8
    self.assertFalse(self.owner._check_session(token))
    self.assertFalse(m.busy(self.root/'generated/operator.lock'))

  def test_child_failure_survives_watchdog_and_reaches_poll_status(self):
    token=self.owner.dispatch('calibration_start',attended=True)['session']
    self.owner.session['sink'].failed=True
    self.owner.session['sink'].error='PortAudioError: selected BlueALSA PCM could not open'
    self.assertFalse(self.owner._check_session(token))
    self.assertIn('BlueALSA',self.owner.status()['error'])
    with self.assertRaisesRegex(ValueError,'BlueALSA'):
      self.owner.dispatch('calibration_poll',session=token)
    failure=json.loads((self.root/'generated/calibration_failure.json').read_text())
    self.assertIn('PortAudioError',failure['error'])

  def test_real_params_reads_ignore_replay_namespace_and_fail_closed(self):
    import os
    params=self.root/'real';params.mkdir()
    with patch.dict(os.environ,{'OPENPILOT_PREFIX':'replay','PARAMS_ROOT':'/not-real'}),patch.object(m.subprocess,'check_output',side_effect=AssertionError('No subprocess')):
      self.assertFalse(m.real_offroad(params))
      (params/'IsOffroad').write_bytes(b'1');(params/'IsOnroad').write_bytes(b'0')
      self.assertTrue(m.real_offroad(params))
      (params/'IsOnroad').write_bytes(b'1');self.assertFalse(m.real_offroad(params))
      (params/'BluetoothEnabled').write_bytes(b'1');(params/'BluetoothAudioAddress').write_text('AA:BB:CC:DD:EE:FF')
      self.assertEqual(m.real_bluetooth_selection(params)['address'],'AA:BB:CC:DD:EE:FF')

  def test_slow_watchdog_output_lookup_does_not_block_taps(self):
    import threading,time
    token=self.owner.dispatch('calibration_start',attended=True)['session']
    for i in range(9):self.owner.session['sink'].callback(i,100000+i*600)
    self.clock.value=105.
    entered=threading.Event();release=threading.Event()
    def slow():entered.set();release.wait(2);return self.output
    self.owner.output_provider=slow
    thread=threading.Thread(target=self.owner._check_session,args=(token,));thread.start();self.assertTrue(entered.wait(1))
    start=time.perf_counter()
    self.owner.dispatch('calibration_poll',session=token)
    self.owner.dispatch('calibration_tap',session=token,server_ms=105000,uncertainty_ms=3)
    elapsed=time.perf_counter()-start
    release.set();thread.join(2)
    self.assertLess(elapsed,.1)

  def test_selected_speaker_identity_never_falls_back(self):
    selected=dict(enabled=True,address='AA:BB:CC:DD:EE:FF')
    status=dict(enabled=True,powered=True,devices=[dict(address='11:22:33:44:55:66',name='Other',connected=True,audio=True)])
    result=m.describe_output(selected,status)
    self.assertEqual(result['id'],'bluealsa:AA:BB:CC:DD:EE:FF');self.assertFalse(result['connected'])
    status['devices'].append(dict(address=selected['address'],name='Selected',connected=True,audio=True))
    result=m.describe_output(selected,status);self.assertEqual(result['name'],'Selected');self.assertTrue(result['connected'])
    self.assertIsNone(result['physical_latency_ms'])

  def test_process_guard_blocks_nonresident_playback(self):
    with patch.object(m,'playback_process_active',return_value=True):
      with self.assertRaises(ValueError):self.owner.dispatch('calibration_start',attended=True)

  def test_deterministic_pcm_and_measured_dac_timestamp_no_real_audio(self):
    import numpy as np
    class Stream:
      def __init__(self,**kwargs):self.kwargs=kwargs
      def start(self):pass
      def stop(self):pass
      def close(self):pass
    fake=types.SimpleNamespace(OutputStream=Stream,query_devices=lambda:[dict(name='pulse',max_output_channels=2)])
    stamps=[]
    with patch.dict(sys.modules,{'sounddevice':fake}):
      from operator_click_process import ClickSequence
      sink=ClickSequence(lambda i,at:stamps.append((i,at)),0,count=4)
      second=ClickSequence(lambda *_:None,0,count=4)
    self.assertTrue(np.array_equal(sink.pcm,second.pcm))
    self.assertLessEqual(abs(sink.pcm).max(),.071)
    self.assertEqual(sink.beats[1]-sink.beats[0],28800)
    self.assertGreater(abs(sink.pcm[sink.beats[0]:sink.beats[0]+1000]).max(),abs(sink.pcm[sink.beats[1]:sink.beats[1]+1000]).max())
    sink.index=sink.beats[0]
    with patch('operator_click_process.time.monotonic',return_value=50):
      out=np.zeros((480,2),dtype=np.float32)
      sink.callback(out,480,types.SimpleNamespace(outputBufferDacTime=8.02,currentTime=8),False)
    self.assertAlmostEqual(stamps[0][1],50020)
    self.assertTrue(np.any(out))

if __name__=='__main__':unittest.main()
