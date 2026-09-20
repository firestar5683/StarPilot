"""Loopback HTTP integration with mocked peer transport; no audio or peer access."""
from concurrent.futures import Future
import contextlib
import copy
import http.client
import io
import json
from pathlib import Path
import tempfile
import threading
import time
import unittest

from mac_showcase import apply_showcase_config, control_server, parser
from paired_demo_controls import GalaxyPeer, PairedDemoControls


class ManualForwarder:
  def __init__(self, out):
    self.out = out
    self.calls = []
    self.closed = False

  def submit(self, action, value):
    # This mock observes the real local Galaxy command file before forwarding.
    command = json.loads((self.out/'demo_engagement.json').read_text())
    field = 'mode' if action == 'demo_engagement' else 'signal_mode'
    if command[field] != value:raise AssertionError('Peer submitted before local write')
    future = Future()
    self.calls.append((action, value, future))
    return future

  def close(self):self.closed = True


class ControlTests(unittest.TestCase):
  def setUp(self):
    self.temp = tempfile.TemporaryDirectory()
    self.addCleanup(self.temp.cleanup)
    self.out = Path(self.temp.name)
    self.project = Path(__file__).resolve().parents[2]
    self.state = dict(input_mode='replay',route='fixture-route',presentation_session_id='mac-session',
                      command_wall=time.monotonic(),engagement_presentation={'enabled':True})
    self.write_state()
    self.server = None
    self.addCleanup(self.stop)

  def write_state(self):
    self.state['command_wall'] = time.monotonic()
    (self.out/'status.json').write_text(json.dumps(self.state))

  def start(self, forwarder=None, follow_peer=False):
    self.server = control_server(self.project,self.out,dict(state='READY',audio_s=1.,muted=True),0,forwarder,follow_peer=follow_peer)
    self.assertEqual(self.server.server_address[0], '127.0.0.1')

  def stop(self):
    if self.server is not None:
      try:self.server.shutdown()
      finally:self.server.server_close();self.server=None

  def request(self, method='GET', path='/status', body=None, headers=None):
    connection = http.client.HTTPConnection('127.0.0.1',self.server.server_port,timeout=1)
    try:
      connection.request(method,path,None if body is None else json.dumps(body),headers=headers or {'Content-Type':'application/json'})
      response = connection.getresponse()
      return response.status,json.loads(response.read())
    finally:connection.close()

  def command(self, value='engaged', field='mode', session='mac-session', headers=None):
    return self.request('POST','/control',{'session_id':session,field:value},headers)

  def test_default_has_no_peer_and_local_ack_is_not_application(self):
    self.start()
    status, result = self.command()
    self.assertEqual(status,200)
    self.assertEqual(result['requested_mode'],'engaged')
    status, result = self.request()
    paired = result['paired_controls']
    self.assertFalse(paired['enabled'])
    self.assertEqual(paired['targets']['comma']['status'],'disabled')
    self.assertTrue(paired['targets']['mac']['acknowledged'])
    self.assertFalse(paired['targets']['mac']['applied'])
    self.state['demo_engagement_mode']='engaged';self.write_state()
    self.assertTrue(self.request()[1]['paired_controls']['targets']['mac']['applied'])

  def test_local_write_then_peer_submission_and_session_rejection(self):
    peer = ManualForwarder(self.out)
    self.start(peer)
    self.assertEqual(self.command(session='old-session')[0],400)
    self.assertEqual(peer.calls,[])
    self.assertEqual(self.command('left','signal_mode')[0],200)
    paired = self.request()[1]['paired_controls']
    self.assertEqual(paired['sequence'],1)
    self.assertEqual(paired['request']['session_id'],'mac-session')
    self.assertEqual(paired['targets']['comma']['status'],'pending')
    self.assertEqual(peer.calls[0][:2],('demo_signal','left'))
    self.assertFalse(paired['music_video_synchronized'])

  def test_older_peer_result_cannot_replace_newer_action(self):
    peer = ManualForwarder(self.out)
    self.start(peer)
    self.assertEqual(self.command('left','signal_mode')[1]['control_sequence'],1)
    self.assertEqual(self.command('right','signal_mode')[1]['control_sequence'],2)
    peer.calls[0][2].set_result({'targets':{'comma':{'status':'applied','value':'left','applied':True}}})
    paired = self.request()[1]['paired_controls']
    self.assertEqual(paired['sequence'],2)
    self.assertEqual(paired['targets']['comma']['status'],'pending')
    self.assertEqual(paired['targets']['comma']['value'],'right')
    peer.calls[1][2].set_result({'targets':{'comma':{'status':'failed','value':'right','error':'peer_not_ready_for_replay'}}})
    status = self.request()[1]
    self.assertTrue(status['demo']['available'])
    self.assertEqual(status['paired_controls']['targets']['comma']['error'],'peer_not_ready_for_replay')

  def test_cross_origin_and_rebinding_host_rejected_before_both_writes(self):
    peer = ManualForwarder(self.out)
    self.start(peer)
    for headers in ({'Origin':'https://other.example','Sec-Fetch-Site':'cross-site'},
                    {'Host':'other.example','Origin':'http://other.example'}):
      self.assertEqual(self.command(headers=headers)[0],403)
    self.assertEqual(peer.calls,[])
    self.assertFalse((self.out/'demo_engagement.json').exists())
    origin = f'http://127.0.0.1:{self.server.server_port}'
    self.assertEqual(self.command(headers={'Origin':origin,'Sec-Fetch-Site':'same-origin'})[0],200)

  def test_peer_future_failure_keeps_local_controls_ready(self):
    peer = ManualForwarder(self.out)
    self.start(peer)
    self.assertEqual(self.command()[0],200)
    peer.calls[0][2].set_exception(RuntimeError('Mock peer error'))
    result = self.request()[1]
    self.assertTrue(result['demo']['available'])
    self.assertEqual(result['paired_controls']['targets']['comma']['error'],'peer_submission_failed')
    self.assertEqual(self.command('disengaged')[0],200)
    self.stop()
    self.assertTrue(peer.closed)

  def test_slow_mock_peer_never_delays_local_http_and_uses_own_session(self):
    entered, release = threading.Event(), threading.Event()
    calls = []
    peer_status = dict(available=True,offroad=True,state='READY',live={'enabled':False},
                       demo=dict(available=True,session_id='comma-session',mode='recorded',signal_mode='recorded'))
    def transport(method, url, payload, headers, timeout):
      calls.append((method,payload))
      if len(calls)==1:entered.set();release.wait(1)
      if method=='GET':return copy.deepcopy(peer_status)
      field = 'signal_mode' if url.endswith('demo_signal') else 'mode'
      peer_status['demo'][field]=payload[field]
      return {'requested_'+field:payload[field],'demo':copy.deepcopy(peer_status['demo'])}
    forwarder = PairedDemoControls(GalaxyPeer('http://192.168.1.50:8082',allow_lan_http=True),enabled=True,transport=transport)
    self.start(forwarder)
    try:
      before = time.monotonic()
      self.assertEqual(self.command('left','signal_mode')[0],200)
      self.assertLess(time.monotonic()-before,.25)
      self.assertTrue(entered.wait(.5))
      self.assertEqual(self.request()[1]['paired_controls']['targets']['comma']['status'],'pending')
    finally:release.set()
    deadline = time.monotonic()+1
    while True:
      result = self.request()[1]['paired_controls']['targets']['comma']
      if result['status']!='pending' or time.monotonic()>deadline:break
      time.sleep(.01)
    self.assertTrue(result['applied'])
    self.assertEqual(calls[1][1],{'session_id':'comma-session','signal_mode':'left'})
    self.assertEqual(json.loads((self.out/'demo_engagement.json').read_text())['session_id'],'mac-session')

  def test_cli_pairing_is_explicit_and_lan_only_without_credentials(self):
    self.assertIsNone(parser().parse_args([]).paired_comma)
    value = 'http://192.168.1.50:8082'
    self.assertEqual(parser().parse_args(['--paired-comma',value]).paired_comma,value)
    for value in ('http://device.local:8082','http://8.8.8.8:8082','http://192.168.1.50:8082/mobile/#/roadscore'):
      with self.subTest(url=value),contextlib.redirect_stderr(io.StringIO()),self.assertRaises(SystemExit):
        parser().parse_args(['--paired-comma',value])

  def test_native_worker_portability_hooks_preserve_mac_defaults(self):
    defaults=parser().parse_args([])
    self.assertFalse(defaults.no_control_server)
    self.assertIsNone(defaults.presentation_root)
    self.assertIsNone(defaults.output_identity)
    native=parser().parse_args(['--audio-worker','--no-control-server','--presentation-root','/fixture/native',
                               '--output-identity','speaker-fixture'])
    self.assertTrue(native.no_control_server)
    self.assertEqual(native.presentation_root,Path('/fixture/native'))
    self.assertEqual(native.output_identity,'speaker-fixture')

  def wait_for(self, predicate):
    deadline=time.monotonic()+1.5
    while not predicate():
      if time.monotonic()>deadline:self.fail('Mock follower did not reach expected state')
      time.sleep(.01)

  def following_peer(self):
    status=dict(available=True,offroad=True,state='READY',live={'enabled':False},
                demo=dict(available=True,session_id='comma-session',mode='recorded',signal_mode='recorded'))
    calls=[]
    def transport(method,*args):
      calls.append(method)
      if method!='GET':raise AssertionError('Follower must never POST to Galaxy')
      return copy.deepcopy(status)
    peer=PairedDemoControls(GalaxyPeer('http://192.168.1.50:8082',allow_lan_http=True),enabled=True,transport=transport)
    self.start(peer,follow_peer=True)
    self.wait_for(lambda:self.request()[1]['paired_controls']['following']['status']=='following')
    return status,calls

  def test_phone_changes_reconcile_locally_without_feedback_posts(self):
    peer,calls=self.following_peer()
    peer['demo'].update(mode='engaged',signal_mode='left')
    path=self.out/'demo_engagement.json'
    self.wait_for(lambda:path.exists() and json.loads(path.read_text()).get('signal_mode')=='left')
    command=json.loads(path.read_text())
    self.assertEqual((command['mode'],command['signal_mode'],command['session_id']),('engaged','left','mac-session'))
    self.state.update(demo_engagement_mode='engaged',demo_signal_mode='left');self.write_state()
    self.wait_for(lambda:self.request()[1]['paired_controls']['following']['status']=='following')
    view=self.request()[1]['paired_controls']['following']
    self.assertEqual(view['snapshot']['session_id'],'comma-session')
    # Galaxy remains authoritative if the Mac later diverges from its state.
    self.state['demo_engagement_mode']='disengaged';self.write_state()
    previous=path.stat().st_mtime_ns
    self.wait_for(lambda:path.stat().st_mtime_ns!=previous)
    self.assertEqual(json.loads(path.read_text())['mode'],'engaged')
    self.assertTrue(calls and all(method=='GET' for method in calls))

  def test_stale_and_reset_peer_pause_without_replacing_local_controls(self):
    peer,calls=self.following_peer()
    peer['demo']['available']=False
    self.wait_for(lambda:self.request()[1]['paired_controls']['following']['error']=='peer_not_ready_for_replay')
    self.assertFalse((self.out/'demo_engagement.json').exists())
    peer['demo'].update(available=True,session_id='new-comma-session',mode='engaged')
    self.wait_for(lambda:self.request()[1]['paired_controls']['following']['error']=='peer_session_changed')
    self.assertIsNone(self.request()[1]['paired_controls']['following']['snapshot'])
    self.assertFalse((self.out/'demo_engagement.json').exists())
    self.assertTrue(all(method=='GET' for method in calls))

  def test_local_session_reset_cannot_receive_old_mirror_commands(self):
    peer,_=self.following_peer()
    self.state['presentation_session_id']='new-mac-session';self.write_state()
    peer['demo']['mode']='engaged'
    self.wait_for(lambda:self.request()[1]['paired_controls']['following']['error']=='local_session_changed')
    self.assertFalse((self.out/'demo_engagement.json').exists())


class RememberedConfigTests(unittest.TestCase):
  def setUp(self):
    self.config = dict(route='route1',archive='/fixture/archive',paired_comma='http://192.168.1.50:8082',controls_port=56976)

  def resolve(self, flags=(), config=None):
    return apply_showcase_config(parser().parse_args(list(flags)),self.config if config is None else config)

  def test_saved_pair_and_stable_port_without_recurring_flags(self):
    value = self.resolve()
    self.assertEqual(value.paired_comma,self.config['paired_comma'])
    self.assertEqual(value.port,56976)
    self.assertEqual(value.score_archive,Path('/fixture/archive'))

  def test_absent_optional_choices_remain_unpaired_and_ephemeral(self):
    value = self.resolve(config={'route':'route1','archive':'/fixture/archive'})
    self.assertIsNone(value.paired_comma)
    self.assertEqual(value.port,0)
    value = self.resolve(['--score-archive','/explicit/archive'],config={})
    self.assertIsNone(value.paired_comma)
    self.assertEqual(value.port,0)

  def test_cli_pair_and_zero_port_override_saved_values(self):
    url = 'http://192.168.1.51:8082'
    value = self.resolve(['--paired-comma',url,'--port','0','--score-archive','/explicit/archive'])
    self.assertEqual(value.paired_comma,url)
    self.assertEqual(value.port,0)
    self.assertEqual(value.score_archive,Path('/explicit/archive'))

  def test_unpaired_overrides_remembered_target_for_one_launch(self):
    value = self.resolve(['--unpaired'])
    self.assertIsNone(value.paired_comma)
    self.assertEqual(value.port,56976)
    self.assertEqual(self.config['paired_comma'],'http://192.168.1.50:8082')
    with contextlib.redirect_stderr(io.StringIO()),self.assertRaises(SystemExit):
      parser().parse_args(['--unpaired','--paired-comma',self.config['paired_comma']])

  def test_saved_peer_cannot_leak_to_different_explicit_route(self):
    value = self.resolve(['different-route','--score-archive','/explicit/archive'])
    self.assertIsNone(value.paired_comma)
    self.assertEqual(value.port,0)
    with self.assertRaises(ValueError):self.resolve(['different-route'])

  def test_invalid_saved_choices_fail_without_peer_contact(self):
    for value in (-1,65536,True,'56976',None):
      with self.subTest(port=value),self.assertRaises(ValueError):
        self.resolve(config={**self.config,'controls_port':value})
    for value in ('http://remote.example:8082','http://8.8.8.8:8082','',False):
      with self.subTest(peer=value),self.assertRaises(ValueError):
        self.resolve(config={**self.config,'paired_comma':value})
    value = self.resolve(config={**self.config,'paired_comma':None})
    self.assertIsNone(value.paired_comma)


if __name__=='__main__':unittest.main()
