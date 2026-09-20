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

if __name__=='__main__':unittest.main()
