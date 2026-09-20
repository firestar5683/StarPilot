import fcntl
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from demo_catalog import entry
from demo_session import DemoSession, write


class SavedDemoTests(unittest.TestCase):
  def setUp(self):
    self.tmp = tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
    self.root = Path(self.tmp.name)
    for folder in ('assets', 'generated', 'archive'): (self.root/folder).mkdir()
    write(self.root/'assets/demo_catalog.json', {'version':1,'routes':{'route1':{'ready':True,'route':'private/route','archive':'archive'},'route2':{'ready':False}}})
    self.calls=[];self.stops=[];self.running=True;self.offroad=True
    def spawn(command, **kwargs):
      self.calls.append((command,kwargs));return SimpleNamespace(pid=123,poll=lambda:None)
    self.service=DemoSession(self.root,lambda:self.offroad,spawn=spawn,
                             ticks=lambda pid:'birth1' if self.running and pid==123 else None,
                             stop_group=self.stops.append)
    self.request={'alias':'route1','request_id':'test-session-1','muted':True}

  def test_only_registered_ready_route_can_launch(self):
    for alias in ('route2','route3','../route1','route1;other'):
      with self.assertRaises(ValueError):entry(self.root,alias)
    self.assertEqual(entry(self.root,'route1')['archive'],str((self.root/'archive').resolve()))
    self.offroad=False
    with self.assertRaises(ValueError):self.service.start(self.request)
    self.assertEqual(self.calls,[])

  def test_existing_native_replay_blocks_launch(self):
    with (self.root/'generated/native_session.lock').open('a') as lease:
      fcntl.flock(lease,fcntl.LOCK_EX|fcntl.LOCK_NB)
      with self.assertRaises(ValueError):self.service.start(self.request)
    self.assertEqual(self.calls,[])

  def test_launch_is_owned_and_idempotent_without_a_composer(self):
    current=self.service.start(self.request)
    self.assertTrue(current['running']);self.assertFalse(current['generation_invoked'])
    self.assertEqual(self.service.start(self.request)['pid'],123)
    self.assertEqual(len(self.calls),1)
    command,options=self.calls[0]
    self.assertTrue(command[1].endswith('/native_prepared_showcase.py'))
    self.assertIn('--hold-start',command);self.assertIn('--muted',command)
    self.assertNotIn('--screen-mirror',command)
    self.assertFalse(current['screen_mirror'])
    self.assertTrue(options['close_fds']);self.assertTrue(options['start_new_session'])
    with self.assertRaises(ValueError):self.service.start({**self.request,'request_id':'different-request'})
    with self.assertRaises(ValueError):self.service.stop({'request_id':'different-request'})
    self.service.stop({'request_id':self.request['request_id']})
    self.assertEqual(self.stops,[123])

  def test_capture_is_explicit_and_part_of_launch_identity(self):
    with patch.dict('os.environ',{'ROADSCORE_MIRROR_DIR':'/inherited/mirror'}):
      current=self.service.start({**self.request,'screen_mirror':True})
    self.assertTrue(current['screen_mirror'])
    command,options=self.calls[0]
    self.assertIn('--screen-mirror',command)
    self.assertNotIn('ROADSCORE_MIRROR_DIR',options['env'])
    self.assertEqual(self.service.start({**self.request,'screen_mirror':True})['pid'],123)
    with self.assertRaises(ValueError):self.service.start(self.request)
    self.assertEqual(len(self.calls),1)

  def test_optional_capture_defaults_to_false_without_inherited_activation(self):
    with patch.dict('os.environ',{'ROADSCORE_MIRROR_DIR':'/inherited/mirror'}):
      current=self.service.start(self.request)
    self.assertFalse(current['screen_mirror'])
    self.assertEqual(self.service.start({**self.request,'screen_mirror':False})['pid'],123)
    self.assertNotIn('ROADSCORE_MIRROR_DIR',self.calls[0][1]['env'])
    with self.assertRaises(ValueError):self.service.start({**self.request,'screen_mirror':True})

  def test_capture_api_rejects_nonbooleans_and_unknown_fields_before_spawning(self):
    for value in (None,0,1,'true','false',[],{}):
      with self.subTest(value=value),self.assertRaises(ValueError):
        self.service.start({**self.request,'screen_mirror':value})
    with self.assertRaises(ValueError):self.service.start({**self.request,'mirror':True})
    self.assertEqual(self.calls,[])

  def test_matching_ready_session_is_required_for_release(self):
    current=self.service.start(self.request);out=Path(current['out'])
    request={'request_id':self.request['request_id'],'session_id':'prepared-session'}
    with self.assertRaises(ValueError):self.service.release(request)
    write(out/'demo_ready.json',{'ready':True,'session_id':'prepared-session'})
    with self.assertRaises(ValueError):self.service.release({**request,'session_id':'old-session'})
    first=self.service.release(request);again=self.service.release(request)
    self.assertEqual(first['start_at_wall'],again['start_at_wall'])
    self.assertGreater(first['start_at_wall'],first['server_wall'])
    self.assertEqual(json.loads((out/'start.json').read_text())['session_id'],'prepared-session')

  def test_reused_or_exited_pid_is_never_signalled(self):
    self.service.start(self.request);self.running=False
    self.assertFalse(self.service.status()['running'])
    self.service.stop({'request_id':self.request['request_id']})
    self.assertEqual(self.stops,[])
    with self.assertRaises(ValueError):self.service.start(self.request)

  def test_prepared_playback_reserves_output_from_calibration(self):
    from operator_output import playback_process_active
    proc=self.root/'proc';child=proc/'45';child.mkdir(parents=True)
    for command in (b'python\0/data/roadscore/prototype/native_prepared_showcase.py\0--demo',
                    b'python\0/data/roadscore/prototype/mac_showcase.py\0--audio-worker'):
      (child/'cmdline').write_bytes(command)
      self.assertTrue(playback_process_active(proc))
    (child/'cmdline').write_bytes(b'python\0/data/roadscore/prototype/worker_service.py')
    self.assertFalse(playback_process_active(proc))


if __name__=='__main__':unittest.main()
