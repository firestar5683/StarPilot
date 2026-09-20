import json
from http.client import IncompleteRead
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
from urllib.error import HTTPError, URLError

from paired_showcase import native_pair_main, retryable_status_error


class AudioFirstPairTests(unittest.TestCase):
  def run_pair(self, playback, *, mac_code=1, preparation_code=None,
               preparation_error=None, expected_stop=True, interrupt_sleep=False):
    calls=[];clock=[1000.];seen=[];ready_calls=0
    events=iter(playback)
    owned=dict(request_id='audio-first-test',route='private/route',running=True,
               prepared=True,ready_session_id='native-session')
    def call(action,data=None):
      nonlocal ready_calls
      calls.append((action,data,clock[0]))
      if action=='status':return {'offroad':True}
      if action=='demo_ready':
        ready_calls+=1
        if ready_calls==1:
          if preparation_error:raise preparation_error
          return owned
        event=next(events)
        if isinstance(event,BaseException):raise event
        seen.append(event)
        return {**owned,**event}
      if action=='demo_play':
        return dict(request_id='audio-first-test',session_id='native-session',
                    start_at_wall=101.,server_wall=100.)
      return {}
    def local_ready(path,route):
      path.parent.mkdir(exist_ok=True)
      return {'session_id':'mac-session'}
    def sleep(seconds):
      if interrupt_sleep:raise KeyboardInterrupt()
      clock[0]+=seconds
    peer=SimpleNamespace(call=call,peer=SimpleNamespace(base_url='http://192.168.8.156:8082'))
    process=Mock();process.poll.side_effect=[preparation_code,mac_code]
    failure=None;report=None;monitor=None
    with tempfile.TemporaryDirectory() as folder:
      root=Path(folder)/'roadscore';(root/'assets').mkdir(parents=True);(root/'prototype').mkdir()
      (root/'assets/demo_catalog.json').write_text(json.dumps({'paired_comma':peer.peer.base_url}))
      with patch('paired_showcase.HERE',root/'prototype'),patch('paired_showcase.DemoPeer',return_value=peer), \
           patch('paired_showcase.signal.signal'),patch('paired_showcase.subprocess.Popen',return_value=process), \
           patch('paired_showcase.stop_mac') as stop_mac,patch('paired_showcase.read_ready',side_effect=local_ready), \
           patch('paired_showcase.uuid.uuid4',return_value=SimpleNamespace(hex='audio-first-test')), \
           patch('paired_showcase.time.monotonic',side_effect=lambda:clock[0]), \
           patch('paired_showcase.time.sleep',side_effect=sleep),patch('builtins.print') as output, \
           patch('demo_catalog.entry',return_value={'route':'private/route','archive':'/protected/core'}), \
           patch('mac_replay_ownership.preflight'),patch('sys.argv',['paired_showcase']):
        try:native_pair_main()
        except BaseException as error:failure=error
      path=root/'results/paired_showcase_audio-first-test/mac_display.json'
      if path.exists():report=json.loads(path.read_text())
      path=path.with_name('peer_monitor.json')
      if path.exists():monitor=json.loads(path.read_text())
    stop_mac.assert_called_once_with(process)
    stops=[(action,data) for action,data,_ in calls if action=='demo_stop']
    self.assertEqual(stops,[('demo_stop',{'request_id':'audio-first-test'})] if expected_stop else [])
    return SimpleNamespace(failure=failure,report=report,calls=calls,seen=seen,
                           elapsed=clock[0]-1000.,output=output,monitor=monitor)

  def test_failed_mac_does_not_stop_healthy_native_audio_before_its_eof(self):
    result=self.run_pair([{}]*20+[{'running':False,'complete':True}])
    self.assertIsNone(result.failure)
    self.assertEqual(len(result.seen),21)
    self.assertEqual(result.elapsed,10.)
    self.assertEqual(result.report['state'],'DEGRADED')
    self.assertEqual(result.report['returncode'],1)
    self.assertEqual(result.report['native_audio'],'continuing')
    self.assertEqual(sum('comma audio continues' in str(c) for c in result.output.call_args_list),1)

  def test_clean_mac_eof_does_not_impose_five_second_native_tail_limit(self):
    result=self.run_pair([{}]*16+[{'running':False,'complete':True}],mac_code=0)
    self.assertIsNone(result.failure)
    self.assertEqual(result.elapsed,8.)
    self.assertEqual(result.report['returncode'],0)

  def test_mac_preparation_failure_still_stops_owned_native_session(self):
    result=self.run_pair([],preparation_code=1)
    self.assertIsInstance(result.failure,RuntimeError)
    self.assertIn('failed to prepare',str(result.failure))
    self.assertFalse(any(action=='demo_play' for action,_,_ in result.calls))
    self.assertIsNone(result.report)

  def test_native_failure_and_ownership_change_still_stop_pair(self):
    for event,reason in [({'failure':'native decoder failed'},'native decoder failed'),
                         ({'request_id':'replacement-owner'},'ownership changed'),
                         ({'running':False,'complete':False},'stopped before completion')]:
      with self.subTest(event=event):
        result=self.run_pair([{},event])
        self.assertIsInstance(result.failure,RuntimeError)
        self.assertIn(reason,str(result.failure))

  def test_ctrl_c_still_cleans_up_after_mac_has_failed(self):
    result=self.run_pair([{},KeyboardInterrupt()])
    self.assertIsInstance(result.failure,KeyboardInterrupt)
    self.assertEqual(result.report['native_audio'],'continuing')

  def test_status_timeout_recovers_without_restart_or_early_stop(self):
    result=self.run_pair([URLError(TimeoutError('timed out')),{},
                          {'running':False,'complete':True}])
    self.assertIsNone(result.failure)
    self.assertEqual(result.monitor['state'],'CONNECTED')
    self.assertEqual(result.monitor['total_failures'],1)
    self.assertEqual(result.calls[-1][0],'demo_stop')
    for action in ('demo_start','demo_play'):
      self.assertEqual(sum(c[0]==action for c in result.calls),1)
    self.assertTrue(result.seen[-1]['complete'])

  def test_recovery_resets_consecutive_failures(self):
    result=self.run_pair([TimeoutError()]*3+[{}]+[URLError('connection reset')]*3+
                         [{'running':False,'complete':True}])
    self.assertIsNone(result.failure)
    self.assertEqual(result.monitor['state'],'CONNECTED')
    self.assertEqual(result.monitor['total_failures'],6)
    self.assertEqual(result.monitor['consecutive_failures'],0)

  def test_persistent_monitor_failure_leaves_native_playback_running(self):
    result=self.run_pair([URLError('timed out')]*4,expected_stop=False)
    self.assertIsNone(result.failure)
    self.assertEqual(result.monitor['state'],'UNREACHABLE')
    self.assertEqual(result.monitor['consecutive_failures'],4)
    self.assertFalse(result.monitor['native_stop_requested'])
    self.assertEqual(result.elapsed,3.5)
    self.assertTrue(any('status is unknown' in str(c) for c in result.output.call_args_list))

  def test_ctrl_c_during_network_retry_still_attempts_owned_stop(self):
    result=self.run_pair([TimeoutError()],interrupt_sleep=True)
    self.assertIsInstance(result.failure,KeyboardInterrupt)

  def test_verified_failure_after_timeout_is_not_hidden(self):
    for event,reason in [({'failure':'audio failed'},'audio failed'),
                         ({'request_id':'replacement-owner'},'ownership changed')]:
      with self.subTest(event=event):
        result=self.run_pair([TimeoutError(),event])
        self.assertIsInstance(result.failure,RuntimeError)
        self.assertIn(reason,str(result.failure))

  def test_protocol_and_permission_errors_do_not_retry(self):
    for error in (ValueError('not JSON'),HTTPError('http://peer',403,'Forbidden',{},None)):
      with self.subTest(error=error):
        result=self.run_pair([error])
        self.assertIs(result.failure,error)
        self.assertIsNone(result.monitor)

  def test_preparation_network_failure_still_cleans_up_without_release(self):
    error=URLError('timed out')
    result=self.run_pair([],preparation_error=error)
    self.assertIs(result.failure,error)
    self.assertFalse(any(c[0]=='demo_play' for c in result.calls))

  def test_transient_http_and_connection_errors_are_retryable(self):
    for error in (HTTPError('http://peer',503,'Unavailable',{},None),
                  IncompleteRead(b'partial'),ConnectionResetError(),TimeoutError(),
                  URLError('timed out')):
      with self.subTest(error=error):self.assertTrue(retryable_status_error(error))


if __name__=='__main__':unittest.main()
