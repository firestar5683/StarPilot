import io,json,struct,tempfile,unittest
from pathlib import Path
from pcm_transport import read_packet,HEADER
from route_library import local_source,identity
class IntegrationTests(unittest.TestCase):
 def test_pcm_exact_and_eof(self):
  m=json.dumps({'audio_s':0,'callback_wall':123}).encode();raw=struct.pack('<4f',.1,.2,.3,.4)
  stream=io.BytesIO(HEADER.pack(len(m),len(raw))+m+raw)
  meta,pcm=read_packet(stream);self.assertEqual(meta['callback_wall'],123);self.assertEqual(pcm,raw);self.assertIsNone(read_packet(stream))
 def test_pcm_truncation_and_bound(self):
  with self.assertRaises(EOFError):read_packet(io.BytesIO(HEADER.pack(2,4)+b'{}xx'))
  with self.assertRaises(ValueError):read_packet(io.BytesIO(HEADER.pack(100000,4)))
 def test_native_layout_and_unseen_fallback(self):
  route='0123456789abcdef/00000000--abcdefghij'
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);self.assertIsNone(local_source(route,root))
   parent=root/'routes/0123456789abcdef/00000000--abcdefghij';segment=parent/'00000000--abcdefghij--0';segment.mkdir(parents=True);(segment/'rlog.zst').write_bytes(b'x')
   self.assertEqual(local_source(route,root),parent)
 def test_incomplete_download_is_not_selected(self):
  route='0123456789abcdef/00000000--abcdefghij'
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);parent=root/'routes'/route;segment=parent/'00000000--abcdefghij--0';segment.mkdir(parents=True);(segment/'rlog.zst').write_bytes(b'x')
   (parent/'cache_manifest.json').write_text(json.dumps({'files':[{'path':segment.name+'/rlog.zst','bytes':1},{'path':segment.name+'/fcamera.hevc','bytes':2}]}))
   self.assertIsNone(local_source(route,root));(segment/'fcamera.hevc').write_bytes(b'xx');self.assertEqual(local_source(route,root),parent)
 def test_remote_clock_reports_failure_and_stops(self):
  import time
  from render_clock import RenderClock
  def callback(*args):raise ValueError('render failure')
  clock=RenderClock(callback,48000,2,480)
  with clock:time.sleep(.04)
  self.assertIsInstance(clock.error,ValueError);self.assertFalse(clock.thread.is_alive())
 def test_native_eof_requires_final_exhausted_unpaused_segment(self):
  from replay_end import ReplayEnd
  watcher=ReplayEnd();state={'cur_sec':125,'max_sec':180,'paused':False,'speed':1};log='merging segments: 1, 2\nwaiting for events...'
  self.assertFalse(watcher.observe(state,log,0));self.assertTrue(watcher.observe(state,log,2))
  self.assertFalse(watcher.observe(dict(state,paused=True),log,3))
  self.assertFalse(watcher.observe(dict(state,max_sec=240),log,3))
  self.assertFalse(watcher.observe(state,log+'\nmerging segments: 2',3))
 def test_no_path_escape(self):
  for route in ['../somewhere','0123456789abcdef/../../etc','garbage']:
   with self.assertRaises(ValueError):identity(route)
if __name__=='__main__':unittest.main()
