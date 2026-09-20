import importlib.util
import json
from pathlib import Path
import tempfile
import time
import unittest

spec=importlib.util.spec_from_file_location('galaxy_demo_operator',Path(__file__).resolve().parents[1]/'roadscore.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)

class DemoTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
  self.root=Path(self.temp.name);self.run=self.root/'results/current';self.run.mkdir(parents=True)
  self.operator=module.Operator(root=self.root,device=True)
  self.state={'route':'private-route','input_mode':'replay','command_wall':time.monotonic(),'presentation_session_id':'session-a','engagement_presentation':{'enabled':True}}
  self.write()
 def write(self): (self.run/'status.json').write_text(json.dumps(self.state))
 def command(self,mode='engaged',session='session-a',offroad=True):
  return self.operator.operate('demo_engagement',{'mode':mode,'session_id':session},offroad)
 def test_modes_write_only_session_command(self):
  for mode in ('engaged','disengaged','recorded'):
   result=self.command(mode);value=json.loads((self.run/'demo_engagement.json').read_text())
   self.assertEqual(value['version'],1);self.assertEqual(value['mode'],mode);self.assertEqual(value['session_id'],'session-a');self.assertEqual(result['requested_mode'],mode)
   self.assertLessEqual(value['created_wall'],time.monotonic())
  self.assertEqual({p.name for p in self.run.iterdir()},{'status.json','demo_engagement.json'})
 def signal(self,mode='left',session='session-a',offroad=True):
  return self.operator.operate('demo_signal',{'signal_mode':mode,'session_id':session},offroad)
 def test_mixed_commands_preserve_other_unacknowledged_choice(self):
  self.command('disengaged');self.signal('left')
  value=json.loads((self.run/'demo_engagement.json').read_text())
  self.assertEqual((value['mode'],value['signal_mode']),('disengaged','left'))
  self.command('engaged');self.signal('off');self.command('recorded')
  value=json.loads((self.run/'demo_engagement.json').read_text())
  self.assertEqual((value['mode'],value['signal_mode']),('recorded','off'))
  self.signal('recorded');self.assertEqual(json.loads((self.run/'demo_engagement.json').read_text())['signal_mode'],'recorded')
 def test_legacy_command_and_cross_session_file(self):
  path=self.run/'demo_engagement.json'
  path.write_text(json.dumps({'version':1,'session_id':'session-a','mode':'engaged','created_wall':time.monotonic()}))
  self.signal();self.assertEqual(json.loads(path.read_text())['mode'],'engaged')
  path.write_text(json.dumps({'version':1,'session_id':'old','mode':'disengaged','signal_mode':'right','created_wall':time.monotonic()}))
  self.signal();self.assertEqual(json.loads(path.read_text())['mode'],'recorded')
 def test_signal_gates_and_status(self):
  for kwargs in ({'session':'old'},{'offroad':False},{'mode':'hazard'}):
   with self.assertRaises(ValueError):self.signal(**kwargs)
  self.state['demo_signal_mode']='right';self.write();self.assertEqual(self.operator.demo_status()['signal_mode'],'right')
  self.state['command_wall']=time.monotonic()-3;self.write()
  with self.assertRaises(ValueError):self.signal()
  self.state['command_wall']=time.monotonic();self.state['input_mode']='live';self.write()
  with self.assertRaises(ValueError):self.signal()
 def test_live_stale_future_unknown_and_disabled_rejected(self):
  original=dict(self.state)
  for patch in ({'input_mode':'live'},{'route':'live'},{'input_mode':None},{'command_wall':time.monotonic()-3},{'command_wall':time.monotonic()+10},{'command_wall':float('nan')},{'engagement_presentation':{'enabled':False}},{'presentation_session_id':None}):
   self.state={**original,**patch};self.write()
   with self.assertRaises(ValueError):self.command()
  self.assertFalse((self.run/'demo_engagement.json').exists())
 def test_session_onroad_and_invalid_commands_rejected(self):
  for kwargs in ({'session':'old-session'},{'offroad':False},{'mode':'controlsAllowed'}):
   with self.assertRaises(ValueError):self.command(**kwargs)
  for payload in ({'mode':'engaged'}, {'mode':'engaged','session_id':'session-a','pid':1}):
   with self.assertRaises(ValueError):self.operator.operate('demo_engagement',payload,True)
  self.assertFalse((self.run/'demo_engagement.json').exists())
 def test_prepared_demo_readiness_does_not_require_a_warm_worker(self):
  from unittest.mock import patch
  self.state.update(readiness='READY',compute='prepared-core',route_t=12.,elapsed=12.1,source_model_ns=123456789)
  self.write()
  with patch.object(module,'current_worker',return_value={}),patch.object(self.operator,'target',return_value={}),patch.object(self.operator,'live_status',return_value={'enabled':False}):
   state=self.operator.status(True)
  self.assertEqual(state['state'],'READY')
  self.assertEqual(state['backend'],'Prepared local audio')
  self.assertEqual(state['demo']['playhead']['route_t'],12.)
  self.assertGreaterEqual(state['demo']['status_age_seconds'],0.)
 def test_mirror_frame_requires_fresh_owned_session_and_offroad(self):
  from flask import Flask
  from unittest.mock import patch
  import operator_output
  app=Flask(__name__)
  folder=self.run/'mirror';folder.mkdir()
  (folder/'latest.jpg').write_bytes(b'\xff\xd8fixture\xff\xd9')
  frame={'session_id':'ready-session','frame_id':1,'captured_wall':time.monotonic()}
  (folder/'frame.json').write_text(json.dumps(frame))
  with patch.object(module,'Operator') as factory,patch.object(operator_output,'real_offroad',return_value=True) as parked:
   factory.return_value.demo_controller.return_value.status.return_value={'running':True,'request_id':'owned-request','ready_session_id':'ready-session','out':str(self.run)}
   module.register(app,None);client=app.test_client()
   self.assertEqual(client.get('/api/roadscore/demo_frame?request_id=wrong').status_code,409)
   response=client.get('/api/roadscore/demo_frame?request_id=owned-request')
   self.assertEqual(response.status_code,200);self.assertEqual(response.mimetype,'image/jpeg')
   frame['captured_wall']=time.monotonic()-2;(folder/'frame.json').write_text(json.dumps(frame))
   self.assertEqual(client.get('/api/roadscore/demo_frame?request_id=owned-request').status_code,503)
   parked.return_value=False
   self.assertEqual(client.get('/api/roadscore/demo_frame?request_id=owned-request').status_code,409)

if __name__=='__main__':unittest.main()
