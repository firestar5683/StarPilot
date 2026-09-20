import json
from pathlib import Path
import tempfile
import unittest
from types import SimpleNamespace
from bluetooth_output import prepare_output, real_selection, select_device

class BluetoothOutputTests(unittest.TestCase):
 def test_selected_address_is_process_local_and_stereo(self):
  with tempfile.TemporaryDirectory() as d:
   base=Path(d)/'alsa.conf';base.write_text('system config')
   env={'OPENPILOT_PREFIX':'replay'}
   meta=prepare_output(Path(d)/'run',env=env,reader=lambda _:dict(enabled=True,address='aa:bb:cc:dd:ee:ff'),alsa_base=base,loaded_modules={})
   text=Path(env['ALSA_CONFIG_PATH']).read_text()
   self.assertIn(f'<{base}>',text)
   self.assertIn('pcm.roadscore_bluetooth {',text)
   self.assertIn('device "AA:BB:CC:DD:EE:FF"',text)
   self.assertNotIn('defaults.bluealsa',text)
   self.assertEqual(base.read_text(),'system config')
   self.assertEqual(env['OPENPILOT_PREFIX'],'replay')
   self.assertIsNone(meta['physical_latency_ms'])
   self.assertEqual(select_device([{'name':'default','max_output_channels':2},{'name':'roadscore_bluetooth','max_output_channels':128}],meta),1)
 def test_missing_or_ambiguous_bluetooth_does_not_fallback(self):
  for devices in [[],[{'name':'default','max_output_channels':2}], [{'name':'bluealsa','max_output_channels':128}], [{'name':'roadscore_bluetooth','max_output_channels':1}], [{'name':'roadscore_bluetooth','max_output_channels':2}]*2]:
   with self.assertRaises(RuntimeError):select_device(devices,{'bluetooth_selected':True})
 def test_disabled_does_not_touch_configuration(self):
  env={};self.assertEqual(prepare_output('/unused',env=env,reader=lambda _:dict(enabled=False)),{'bluetooth_selected':False});self.assertEqual(env,{})
 def test_conflicts_and_bad_address_fail_before_changes(self):
  for env,modules,address in [({'ALSA_CONFIG_PATH':'/custom'}, {},'AA:BB:CC:DD:EE:FF'), ({},{'sounddevice':object()},'AA:BB:CC:DD:EE:FF'), ({},{},'bad\naddress')]:
   before=dict(env)
   with self.assertRaises((ValueError,RuntimeError)):
    prepare_output('/unused',env=env,reader=lambda _:dict(enabled=True,address=address),loaded_modules=modules)
   self.assertEqual(env,before)
 def test_reader_ignores_replay_parameter_namespace(self):
  calls=[]
  def run(cmd,**kw):
   calls.append((cmd,kw));return SimpleNamespace(stdout=json.dumps(dict(enabled=True,address='AA:BB:CC:DD:EE:FF')))
  env={'OPENPILOT_PREFIX':'replay','PARAMS_ROOT':'/test','ZMQ':'1','KEEP':'yes'}
  value=real_selection(env,run)
  self.assertTrue(value['enabled']);self.assertEqual(calls[0][1]['env'],{'KEEP':'yes'})
  self.assertEqual(env['OPENPILOT_PREFIX'],'replay')

if __name__=='__main__':unittest.main()
