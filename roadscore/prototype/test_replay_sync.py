import copy
import ast
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from mac_showcase import cleanup_children, parser
from replay_sync import ReplayFollower, start_deadline, validate_follow_options


class ReplaySyncTests(unittest.TestCase):
  def setUp(self):
    self.sync = ReplayFollower('route', 100_000_000_000, duration=300)
    # Peer uptime intentionally differs from Mac uptime by nearly a million
    # seconds. Only peer age and local RTT/receipt durations may be combined.
    self.snapshot = dict(session_id='peer',route='route',request_started_wall=9.8,received_wall=10.,
                         peer_status={'demo':dict(available=True,readiness='READY',route='route',session_id='peer',
                           playhead=dict(source_model_ns=110_000_000_000,route_t=10.,sampled_wall=999999.,server_wall=999999.1))})
    self.replay = dict(cur_sec=158.,min_sec=120.,max_sec=480.,paused=False,speed=1.)
  def evaluate(self, **changes):
    data=dict(snapshot=self.snapshot,local_model_ns=108_000_000_000,local_received=10.,
              replay=self.replay,now=10.,replay_age=0.)
    data.update(changes)
    return self.sync.evaluate(**data)

  def test_independent_clocks_and_absolute_seek(self):
    result=self.evaluate()
    self.assertAlmostEqual(result['skew_seconds'],2.2)
    self.assertAlmostEqual(result['command']['seek'],160.2)
    self.assertAlmostEqual(result['rtt_seconds'],.2)

  def test_deadband_bounded_seek_and_no_command_feedback(self):
    self.assertEqual(self.evaluate(local_model_ns=110_000_000_000)['status'],'tracking')
    result=self.evaluate(local_model_ns=102_000_000_000)
    self.assertEqual(result['command'],{'seek':161.})
    self.sync.issued(result,10.,0.)
    self.assertEqual(self.evaluate(now=10.1)['reason'],'correction_cooldown')
    self.assertIsNone(self.evaluate(now=10.1)['command'])

  def test_seek_reanchor_requires_written_matching_bounded_correction(self):
    self.assertFalse(self.sync.consume_reanchor(2.2,10.))
    result=self.evaluate();self.sync.issued(result,10.,.1)
    self.assertFalse(self.sync.consume_reanchor(.1,10.2))
    self.assertFalse(self.sync.consume_reanchor(-2.,10.3))
    self.assertFalse(self.sync.consume_reanchor(9.,10.4))
    self.assertTrue(self.sync.consume_reanchor(2.3,10.5))
    self.assertFalse(self.sync.consume_reanchor(2.3,10.6))
    self.sync.issued(result,11.,0.)
    self.assertFalse(self.sync.consume_reanchor(2.2,16.1))

  def test_stale_timing_rejects_correction(self):
    for value in (None,[],{},'invalid'):
      snapshot=copy.deepcopy(self.snapshot);snapshot['peer_status']['demo']['playhead']=value
      self.assertEqual(self.evaluate(snapshot=snapshot)['reason'],'invalid_peer_playhead')
    for field,value in [('request_started_wall',9.),('received_wall',11.)]:
      snapshot=copy.deepcopy(self.snapshot);snapshot[field]=value
      self.assertIsNone(self.evaluate(snapshot=snapshot)['command'])
    self.assertEqual(self.evaluate(now=12.)['reason'],'peer_stale')
    self.assertEqual(self.evaluate(local_received=9.)['reason'],'local_model_stale')
    self.assertEqual(self.evaluate(replay_age=1.)['reason'],'local_replay_unready')
    self.assertEqual(self.evaluate(replay=None)['reason'],'local_replay_unready')

  def test_peer_identity_readiness_and_archive_checks(self):
    self.evaluate()
    for patch,reason in [({'route':'other'},'peer_route_mismatch'),({'session_id':'new'},'peer_session_changed')]:
      snapshot=copy.deepcopy(self.snapshot);snapshot.update(patch);snapshot['peer_status']['demo'].update(patch)
      self.assertEqual(self.evaluate(snapshot=snapshot)['reason'],reason)
    snapshot=copy.deepcopy(self.snapshot);snapshot['peer_status']['demo']['readiness']='PREPARING'
    self.assertEqual(self.evaluate(snapshot=snapshot)['reason'],'peer_unready')
    snapshot=copy.deepcopy(self.snapshot);snapshot['peer_status']['demo']['playhead']['route_t']=11.
    self.assertEqual(self.evaluate(snapshot=snapshot)['reason'],'peer_archive_clock_mismatch')

  def test_stationary_peer_model_cannot_be_extrapolated_forever(self):
    self.evaluate()
    snapshot=copy.deepcopy(self.snapshot);snapshot.update(request_started_wall=10.7,received_wall=10.9)
    self.assertEqual(self.evaluate(snapshot=snapshot,now=10.9,local_received=10.9)['reason'],'peer_model_stopped')
    snapshot['peer_status']['demo']['playhead'].update(source_model_ns=111_000_000_000,route_t=11.)
    self.assertEqual(self.evaluate(snapshot=snapshot,now=10.9,local_received=10.9)['status'],'correcting')

  def test_pauses_and_actual_archive_bounds_freeze_correction(self):
    self.assertEqual(self.evaluate(replay=dict(self.replay,paused=True))['reason'],'local_replay_unready')
    self.assertEqual(self.evaluate(replay=dict(self.replay,speed=2))['reason'],'local_replay_unready')
    self.assertEqual(self.evaluate(replay=dict(self.replay,cur_sec=479))['reason'],'seek_outside_route')
    self.sync.duration=9
    self.assertEqual(self.evaluate()['reason'],'seek_outside_archive')

  def test_start_barrier_exact_session_and_short_local_deadline(self):
    value=dict(session_id='mac',play=True,start_at_wall=101.)
    self.assertEqual(start_deadline(value,'mac',100.),101.)
    self.assertEqual(start_deadline(dict(value,start_at_wall=99.5),'mac',100.),100.)
    for patch in ({'session_id':'other'},{'play':False},{'start_at_wall':98.},{'start_at_wall':106.},
                  {'start_at_wall':float('nan')},{'extra':True}):
      self.assertIsNone(start_deadline(value|patch,'mac',100.))

  def test_follow_mode_is_explicit_muted_and_hidden(self):
    normal=parser().parse_args([]);validate_follow_options(normal)
    self.assertFalse(normal.follow_playhead);self.assertFalse(normal.hold_start)
    for flags in (['--follow-playhead'],['--follow-playhead','--muted'],
                  ['--follow-playhead','--paired-comma','http://192.168.8.156:8082'],
                  ['--follow-playhead','--muted','--paired-comma','http://192.168.8.156:8082','--no-control-server']):
      with self.assertRaises(ValueError):validate_follow_options(parser().parse_args(flags))
    args=parser().parse_args(['--follow-playhead','--muted','--paired-comma','http://192.168.8.156:8082','--port','56976'])
    validate_follow_options(args)
    self.assertEqual(args.port,0);self.assertTrue(args.no_browser)

  def test_real_callback_uses_stable_stream_clock_and_records_failures(self):
    import numpy as np
    from prepared_clock import PreparedClock
    from stream_clock_bridge import StreamClockBridge
    # Execute the real callback without constructing messaging, audio or UI.
    path=Path(__file__).with_name('mac_showcase.py')
    worker=next(node for node in ast.parse(path.read_text()).body if isinstance(node,ast.FunctionDef) and node.name=='audio_worker')
    callback=next(node for node in worker.body if isinstance(node,ast.FunctionDef) and node.name=='callback')
    callback.body=[ast.copy_location(ast.Global(names=node.names),node) if isinstance(node,ast.Nonlocal) else node for node in callback.body]
    context=dict(position=None,rendered=None,done=False,flags=0,max_drift=0.,first_frame=None,callback_revision=0,
                 anchor=(100_000_000_000,100.,0),bridge=StreamClockBridge(-400.,.0001),
                 time=SimpleNamespace(monotonic=lambda:100.08),meta={},rate=48000,
                 initial_frame=lambda meta,mono,elapsed,rate:round(elapsed*rate),sync=None,
                 playback_clock=PreparedClock(),audio=np.zeros((480000,2),np.float32),
                 processor=SimpleNamespace(process=lambda chunk,*args:(chunk,{})),state={},
                 controls=SimpleNamespace(selection=('recorded','recorded')),a=SimpleNamespace(muted=True),
                 errors=[],clock_errors=[],clock_observations=[])
    exec(compile(ast.Module(body=[callback],type_ignores=[]),str(path),'exec'),context)
    out=np.ones((960,2),np.float32)
    # Startup gathers only a bounded set of silent observations. No stream.time
    # getter, model anchor, source-frame processing or output is required.
    saved_bridge=context['bridge'];context['bridge']=None
    for i in range(30):
      context['time'].monotonic=lambda i=i:99.+i*.02
      context['callback'](out,960,SimpleNamespace(currentTime=499.+i*.02,outputBufferDacTime=499.04+i*.02),False)
      self.assertFalse(out.any())
    self.assertEqual(len(context['clock_observations']),24)
    self.assertIsNone(context['position'])
    calibrated=StreamClockBridge.from_callbacks(context['clock_observations'][:20])
    self.assertAlmostEqual(calibrated.offset,-400.)
    context['bridge']=saved_bridge;context['time'].monotonic=lambda:100.08
    context['callback'](out,960,SimpleNamespace(currentTime=500.,outputBufferDacTime=500.056),False)
    context['time'].monotonic=lambda:100.04
    context['callback'](out,960,SimpleNamespace(currentTime=500.02,outputBufferDacTime=500.076),False)
    self.assertEqual(context['errors'],[])
    self.assertEqual(context['playback_clock'].corrections,0)
    self.assertAlmostEqual(context['rendered']['dac_wall'],100.076)
    self.assertFalse(out.any())
    context['callback'](out,960,SimpleNamespace(currentTime=500.04,outputBufferDacTime=float('nan')),False)
    self.assertTrue(context['done']);self.assertEqual(len(context['clock_errors']),1)
    self.assertEqual(context['clock_errors'][0]['portaudio_current_time'],500.04)
    self.assertIn('next_source_frame',context['clock_errors'][0])

  def test_cleanup_stops_all_groups_before_reaping_and_survives_race(self):
    import signal
    events=[]
    def kill(pid,sig):
      events.append(('kill',pid,sig))
      if pid==2:raise ProcessLookupError()
    children=[SimpleNamespace(pid=pid,poll=lambda:None,wait=lambda timeout,pid=pid:events.append(('wait',pid,timeout))) for pid in (1,2,3)]
    logs=[SimpleNamespace(close=lambda:events.append(('close',)))]
    with patch('mac_showcase.signal.signal') as ignored,patch('mac_showcase.os.killpg',side_effect=kill):
      cleanup_children(children,logs)
    self.assertEqual([event[0] for event in events],['kill']*3+['wait']*3+['close'])
    self.assertEqual(ignored.call_count,2)
    self.assertEqual(events[0][2],signal.SIGTERM)


if __name__=='__main__':unittest.main()
