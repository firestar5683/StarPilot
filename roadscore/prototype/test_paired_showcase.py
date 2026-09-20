import json
from types import SimpleNamespace
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from paired_showcase import DemoPeer, control_server


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


if __name__=='__main__':unittest.main()
