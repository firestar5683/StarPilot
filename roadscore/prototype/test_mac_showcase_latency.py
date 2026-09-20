import argparse
import unittest

from mac_showcase import native_bluetooth_latency, output_latency_seconds, parser


class NativeBluetoothLatencyTests(unittest.TestCase):
  def setUp(self):
    self.env={'OPENPILOT_PREFIX':'roadscore_replay','ROADSCORE_PREPARED_SHOWCASE':'1'}
    self.args=parser().parse_args(['--audio-worker','--no-control-server',
                                  '--audio-device','roadscore_bluetooth',
                                  '--output-identity','bluealsa:AA:BB:CC:DD:EE:FF',
                                  '--output-latency','0.25'])

  def test_default_leaves_host_latency_unchanged(self):
    args=parser().parse_args([])
    self.assertIsNone(args.output_latency)
    self.assertIsNone(native_bluetooth_latency(args,{}))
    self.args.output_latency=None
    self.assertIsNone(native_bluetooth_latency(self.args,self.env))

  def test_native_selected_bluetooth_accepts_bounded_numeric_latency(self):
    self.assertEqual(native_bluetooth_latency(self.args,self.env),.25)
    for value in ('.02','.25','.5'):
      self.assertEqual(output_latency_seconds(value),float(value))

  def test_invalid_latency_is_rejected_before_any_audio_opens(self):
    for value in ('nan','inf','-inf','0','-1','.019','.501','text',True,None):
      with self.subTest(value=value),self.assertRaises(argparse.ArgumentTypeError):
        output_latency_seconds(value)

  def test_override_cannot_change_mac_system_or_unowned_output(self):
    for field,value in [('audio_worker',False),('no_control_server',False),
                        ('audio_device',None),('audio_device','default'),
                        ('output_identity','system'),('output_identity','bluealsa:invalid')]:
      old=getattr(self.args,field);setattr(self.args,field,value)
      with self.subTest(field=field,value=value),self.assertRaises(ValueError):
        native_bluetooth_latency(self.args,self.env)
      setattr(self.args,field,old)
    for env in ({},{**self.env,'OPENPILOT_PREFIX':'roadscore-showcase-mac'},
                {**self.env,'ROADSCORE_PREPARED_SHOWCASE':'0'}):
      with self.subTest(env=env),self.assertRaises(ValueError):
        native_bluetooth_latency(self.args,env)


if __name__=='__main__':unittest.main()
