import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from paired_showcase import DemoPeer, control_server, local_start_deadline, mac_command, read_ready, mirror_main, native_pair_main


class NativePairTests(unittest.TestCase):
  def test_release_uses_relative_countdown_across_different_clock_origins(self):
    release={'request_id':'owned','session_id':'peer','server_wall':10000.,'start_at_wall':10001.}
    self.assertAlmostEqual(local_start_deadline(release,'owned','peer',40.,40.1),41.05)

  def test_rejects_foreign_session_stale_release_and_uncertain_rtt(self):
    release={'request_id':'owned','session_id':'peer','server_wall':10000.,'start_at_wall':10001.}
    for changed,sent,received in (({'session_id':'old'},40.,40.1),
                                   ({'request_id':'other'},40.,40.1),
                                   ({'start_at_wall':9999.},40.,40.1),
                                   ({'server_wall':float('nan')},40.,40.1),
                                   ({},40.,41.)):
      with self.assertRaises(ValueError):local_start_deadline({**release,**changed},'owned','peer',sent,received)

  def test_mac_uses_existing_native_command_silently_with_hold_and_follower(self):
    command=mac_command(Path('/project'),'route1',{'archive':'/protected/core','curve_plan':'/protected/curve.json'},
                        'http://192.168.1.2:8082',Path('/owned/mac'),12.)
    self.assertEqual(command[:4],['/project/onroad','--roadscore','route1','--prepared-showcase'])
    for flag in ('--muted','--no-browser','--hold-start','--follow-playhead'):self.assertIn(flag,command)
    self.assertEqual(command[command.index('--port')+1],'0')
    self.assertEqual(command[command.index('--score-archive')+1],'/protected/core')
    self.assertNotIn('--screen-mirror',command)

  def test_local_barrier_requires_matching_prepared_identity(self):
    with tempfile.TemporaryDirectory() as directory:
      path=Path(directory)/'demo_ready.json'
      self.assertIsNone(read_ready(path,'route'))
      path.write_text(json.dumps({'ready':False,'route':'route','session_id':'local'}))
      self.assertIsNone(read_ready(path,'route'))
      path.write_text(json.dumps({'ready':True,'route':'other','session_id':'local'}))
      with self.assertRaises(ValueError):read_ready(path,'route')
      path.write_text(json.dumps({'ready':True,'route':'route','session_id':'local'}))
      self.assertEqual(read_ready(path,'route')['session_id'],'local')

  def test_fullscreen_is_forwarded_only_to_local_native_window(self):
    command=mac_command(Path('/project'),'route1',{'archive':'/protected/core'},
                        'http://192.168.1.2:8082',Path('/owned/mac'),12.,fullscreen=True)
    self.assertIn('--fullscreen',command)

  def test_normal_pair_never_requests_or_inherits_screen_capture(self):
    calls=[]
    def call(action,data=None):
      calls.append((action,data))
      if action=='status':return {'offroad':True}
      if action=='demo_ready':return dict(request_id='paired-test-request',route='private/route',running=True,prepared=True,ready_session_id='native-session')
      if action=='demo_play':return dict(request_id='paired-test-request',session_id='native-session',start_at_wall=101.,server_wall=100.)
      return {}
    peer=SimpleNamespace(call=call,peer=SimpleNamespace(base_url='http://192.168.8.156:8082'))
    process=Mock();process.poll.return_value=None
    def local_ready(path,route):
      path.parent.mkdir(exist_ok=True)
      return {'session_id':'mac-session'}
    with tempfile.TemporaryDirectory() as folder:
      root=Path(folder)/'roadscore';(root/'assets').mkdir(parents=True);(root/'prototype').mkdir()
      (root/'assets/demo_catalog.json').write_text(json.dumps({'paired_comma':peer.peer.base_url}))
      with patch('paired_showcase.HERE',root/'prototype'),patch('paired_showcase.DemoPeer',return_value=peer), \
           patch('paired_showcase.signal.signal'),patch('paired_showcase.subprocess.Popen',return_value=process) as spawn, \
           patch('paired_showcase.stop_mac'),patch('paired_showcase.read_ready',side_effect=local_ready), \
           patch('paired_showcase.uuid.uuid4',return_value=SimpleNamespace(hex='paired-test-request')), \
           patch('demo_catalog.entry',return_value={'route':'private/route','archive':'/protected/core'}), \
           patch('mac_replay_ownership.preflight'),patch.dict('os.environ',{'ROADSCORE_MIRROR_DIR':'/inherited/mirror'}), \
           patch('sys.argv',['paired_showcase','--muted','--duration','0.000000001']):
        native_pair_main()
      self.assertNotIn('ROADSCORE_MIRROR_DIR',spawn.call_args.kwargs['env'])
    payload=next(data for action,data in calls if action=='demo_start')
    self.assertNotIn('screen_mirror',payload)


class MirrorControlTests(unittest.TestCase):
  def setUp(self):
    self.calls=[]
    def call(action,data=None):
      self.calls.append((action,data));return {'demo':{'available':True,'session_id':'device-session'}}
    self.peer=SimpleNamespace(peer=SimpleNamespace(base_url='http://192.168.8.156:8082'),call=call,
                              frame=lambda request:(b'\xff\xd8image\xff\xd9',{'X-RoadScore-Age-Ms':'12'}))
    self.server=control_server(self.peer,'owned-request',0,{'phase':'Playing saved replay','muted':True})
    self.url='http://127.0.0.1:'+str(self.server.server_port)
    self.addCleanup(self.server.server_close);self.addCleanup(self.server.shutdown)
  def post(self,data,origin=None):
    return urlopen(Request(self.url+'/control',data=json.dumps(data).encode(),headers={'Content-Type':'application/json','Origin':origin or self.url}),timeout=2)
  def test_controls_change_one_authoritative_peer(self):
    with self.post({'session_id':'device-session','field':'mode','value':'disengaged'}) as response:
      self.assertEqual(response.status,200)
    self.assertEqual(self.calls,[('demo_engagement',{'session_id':'device-session','mode':'disengaged'})])
  def test_cross_origin_and_arbitrary_action_rejected(self):
    with self.assertRaises(HTTPError) as error:self.post({'session_id':'s','field':'mode','value':'engaged'},'http://elsewhere.invalid')
    self.assertEqual(error.exception.code,403)
    with self.assertRaises(HTTPError):self.post({'session_id':'s','field':'launch','value':'shell'})
    self.assertEqual(self.calls,[])
  def test_frame_is_native_image_with_age(self):
    with urlopen(self.url+'/frame?n=1',timeout=2) as response:
      self.assertEqual(response.headers.get_content_type(),'image/jpeg')
      self.assertEqual(response.headers['X-RoadScore-Age-Ms'],'12')
      self.assertEqual(response.read(),b'\xff\xd8image\xff\xd9')
  def test_peer_stays_explicit_and_operations_are_bounded(self):
    calls=[]
    peer=DemoPeer('http://192.168.8.156:8082',transport=lambda *args:calls.append(args) or {'ok':True})
    self.assertEqual(calls,[])
    peer.call('demo_start',{'alias':'route1'})
    self.assertEqual(calls[0][0],'POST');self.assertEqual(calls[0][-1],4.)
    with self.assertRaises(ValueError):DemoPeer('http://unrelated.example:8082')


class LegacyMirrorLaunchTests(unittest.TestCase):
  def test_legacy_viewer_explicitly_requests_native_capture(self):
    calls=[]
    def call(action,data=None):
      calls.append((action,data))
      if action=='status':return {'offroad':True}
      if action=='demo_ready':return {'request_id':'mirror-test-request','running':True,'prepared':True,'ready_session_id':'native-session'}
      return {}
    peer=SimpleNamespace(call=call)
    server=Mock(server_port=56976)
    with tempfile.TemporaryDirectory() as folder:
      root=Path(folder);(root/'assets').mkdir();(root/'prototype').mkdir()
      (root/'assets/demo_catalog.json').write_text(json.dumps({'paired_comma':'http://192.168.8.156:8082'}))
      with patch('paired_showcase.HERE',root/'prototype'),patch('paired_showcase.DemoPeer',return_value=peer), \
           patch('paired_showcase.control_server',return_value=server),patch('paired_showcase.signal.signal'), \
           patch('paired_showcase.uuid.uuid4',return_value=SimpleNamespace(hex='mirror-test-request')), \
           patch('demo_catalog.entry',return_value={'route':'private/route'}), \
           patch('sys.argv',['paired_showcase','--screen-mirror','--no-browser','--muted','--duration','0']):
        mirror_main()
    payload=next(data for action,data in calls if action=='demo_start')
    self.assertEqual(payload,{'alias':'route1','request_id':'mirror-test-request','muted':True,'screen_mirror':True})
    self.assertIn(('demo_stop',{'request_id':'mirror-test-request'}),calls)
    server.shutdown.assert_called_once();server.server_close.assert_called_once()


if __name__=='__main__':unittest.main()
