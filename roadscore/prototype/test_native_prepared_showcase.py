import fcntl
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from native_prepared_showcase import native_session, install_current, start_deadline, native_environment, worker_arguments, replay_arguments


class NativePreparedTests(unittest.TestCase):
  def setUp(self):
    self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
    self.root=Path(self.tmp.name)/'roadscore';(self.root/'results').mkdir(parents=True)
    self.out=self.root/'results/new';self.out.mkdir()
  def test_same_lock_and_children_do_not_inherit(self):
    with native_session(self.root):
      with self.assertRaises(RuntimeError):
        with native_session(self.root):pass
      child=subprocess.Popen([sys.executable,'-c','import time;time.sleep(2)'],close_fds=True)
    try:
      with native_session(self.root):pass
    finally:child.terminate();child.wait()
  def test_previous_directory_and_symlink_are_preserved(self):
    current=self.root/'results/current';current.mkdir();(current/'dry.wav').write_bytes(b'protected')
    previous=install_current(self.root,self.out,'one')
    self.assertEqual((previous/'dry.wav').read_bytes(),b'protected')
    self.assertEqual(current.resolve(),self.out.resolve())
    second=self.root/'results/second';second.mkdir()
    old_link=install_current(self.root,second,'two')
    self.assertTrue(old_link.is_symlink());self.assertEqual(old_link.resolve(),self.out.resolve())
    self.assertEqual(current.resolve(),second.resolve())
  def test_current_rejects_nonowned_output(self):
    with self.assertRaises(ValueError):install_current(self.root,Path(self.tmp.name)/'other','one')
  def test_barrier_binds_session_and_clock_window(self):
    path=self.out/'start.json'
    self.assertIsNone(start_deadline(path,'s',100.))
    def request(**kw):
      path.write_text(json.dumps(dict(session_id='s',play=True,**kw)))
      return start_deadline(path,'s',100.)
    self.assertEqual(request(start_at_wall=101.),101.)
    self.assertEqual(request(start_at_wall=99.5),100.)
    self.assertEqual(request(),100.)
    self.assertIsNone(request(start_at_wall=98.))
    self.assertIsNone(request(start_at_wall=106.))
    self.assertIsNone(request(start_at_wall=float('nan')))
    path.write_text(json.dumps(dict(session_id='other',play=True)))
    self.assertIsNone(start_deadline(path,'s',100.))
  def test_native_environment_cannot_inherit_remote_generation(self):
    env=native_environment(Path(self.tmp.name),self.root,self.out,'session',{'ZMQ':'1','PARAMS_ROOT':'bad','OPENPILOT_ZMQ_NAMESPACE':'bad','ROADSCORE_PCM_RETURN':'1','ROADSCORE_GENERATION_SEED':'42'})
    self.assertEqual(env['OPENPILOT_PREFIX'],'roadscore_replay')
    self.assertEqual(env['ROADSCORE_STATUS_FILE'],str(self.out/'status.json'))
    for key in ('ZMQ','PARAMS_ROOT','OPENPILOT_ZMQ_NAMESPACE','ROADSCORE_PCM_RETURN','ROADSCORE_GENERATION_SEED'):self.assertNotIn(key,env)
  def test_saved_playback_primes_camera_and_cache_before_source_clock_starts(self):
    for inherited in ({}, {'ROADSCORE_REPLAY_PRIME':'0'}):
      with self.subTest(inherited=inherited):
        env=native_environment(Path(self.tmp.name),self.root,self.out,'session',inherited)
        self.assertEqual(env['ROADSCORE_REPLAY_PRIME'],'1')
  def test_worker_reuses_existing_pcm_dsp_and_output_identity(self):
    args=worker_arguments(Path(self.tmp.name),self.root,self.out,Path('/archive'),'fixture',False,output={'bluetooth_selected':True,'pcm_name':'roadscore_bluetooth','output_identity':'bluealsa:AA:BB'})
    self.assertIn('--audio-worker',args);self.assertIn('--no-control-server',args)
    self.assertIn('--presentation-root',args);self.assertIn('bluealsa:AA:BB',args)
    self.assertEqual(args[args.index('--output-latency')+1],'0.25')
    self.assertTrue(args[1].endswith('/mac_showcase.py'))
    self.assertFalse(any('ace_worker' in item or 'power_worker' in item for item in args))
  def test_system_output_keeps_its_existing_latency_default(self):
    for output in (None, {'bluetooth_selected':False}):
      args=worker_arguments(Path(self.tmp.name),self.root,self.out,Path('/archive'),'fixture',False,output=output)
      self.assertNotIn('--output-latency',args)
      self.assertNotIn('--output-identity',args)
  def test_continuous_capture_is_absent_even_with_inherited_mirror_directory(self):
    from screen_mirror import ScreenMirror
    inherited={'ROADSCORE_MIRROR_DIR':'/old/session/mirror'}
    for choice in ({}, {'screen_mirror':False}):
      env=native_environment(Path(self.tmp.name),self.root,self.out,'session-123',inherited,**choice)
      self.assertNotIn('ROADSCORE_MIRROR_DIR',env)
      self.assertIsNone(ScreenMirror.from_environ(env))
    self.assertEqual(inherited['ROADSCORE_MIRROR_DIR'],'/old/session/mirror')
  def test_explicit_legacy_mirror_uses_only_this_owned_output(self):
    env=native_environment(Path(self.tmp.name),self.root,self.out,'session-123',
                           {'ROADSCORE_MIRROR_DIR':'/old/session/mirror'},screen_mirror=True)
    self.assertEqual(env['ROADSCORE_MIRROR_DIR'],str(self.out/'mirror'))
    self.assertEqual(env['ROADSCORE_REPLAY_PRIME'],'1')
  def test_native_replay_uses_only_given_local_cache(self):
    meta={'native_replay_args':['fixture','--data_dir','old','--start','149']}
    args=replay_arguments(meta,Path('/local/playback'))
    self.assertEqual(args[args.index('--data_dir')+1],'/local/playback')
    self.assertIn('--no-hw-decoder',args);self.assertIn('--no-loop',args);self.assertIn('--headless',args)
    self.assertEqual(meta['native_replay_args'][2],'old')

if __name__=='__main__':unittest.main()
