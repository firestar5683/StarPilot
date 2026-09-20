import json
from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest.mock import Mock, patch
from types import SimpleNamespace as NS

from screen_mirror import ScreenMirror, read_ui_rgba


SESSION = 'abcd1234-session'


class ScreenMirrorTests(unittest.TestCase):
  def make(self, folder):
    mirror = ScreenMirror(Path(folder)/'mirror', SESSION)
    self.addCleanup(mirror.close)
    return mirror

  def test_opt_in_requires_isolated_non_frozen_session(self):
    with tempfile.TemporaryDirectory() as folder:
      env = dict(ROADSCORE_MIRROR_DIR=folder, ROADSCORE_SHOWCASE_SESSION=SESSION,
                 ROADSCORE_REPLAY_UI_CONTROLS='1', SIMULATION='1',
                 OPENPILOT_PREFIX='roadscore_replay', ROADSCORE_PRESENTATION_POLICY='conservative-v4')
      mirror = ScreenMirror.from_environ(env)
      self.assertIsNotNone(mirror)
      mirror.close()
      for changed in ({'ROADSCORE_MIRROR_DIR':''}, {'ROADSCORE_SHOWCASE_SESSION':''},
                      {'SIMULATION':'0'}, {'OPENPILOT_PREFIX':'real-car'},
                      {'ROADSCORE_PRESENTATION_POLICY':'frozen'}, {'ROADSCORE_SEED_ORIGIN':'judging-route'}):
        self.assertIsNone(ScreenMirror.from_environ(dict(env, **changed)))
      self.assertFalse((Path(folder)/'latest.jpg').exists())

  def test_directory_and_session_are_explicit(self):
    for directory, session in [('relative/path', SESSION), ('/', SESSION), ('/tmp/../unsafe',SESSION), ('/tmp/safe','')]:
      with self.assertRaises(ValueError):
        ScreenMirror(directory,session)

  def test_offroad_wrong_session_and_closed_never_read_back(self):
    with tempfile.TemporaryDirectory() as folder:
      mirror=self.make(folder);read=Mock()
      self.assertFalse(mirror.capture(read,started=False,session_id=SESSION))
      self.assertFalse(mirror.capture(read,started=True,session_id='old-session'))
      mirror.close()
      self.assertFalse(mirror.capture(read,started=True,session_id=SESSION))
      read.assert_not_called()

  def test_one_slot_drops_busy_and_rate_limited_frames(self):
    with tempfile.TemporaryDirectory() as folder:
      mirror=self.make(folder)
      encoding=threading.Event();release=threading.Event()
      def encode(job):
        encoding.set();release.wait(2)
        return b'jpeg', {'frame_id':job['frame_id']}
      with patch.object(mirror,'_encode',side_effect=encode),patch.object(mirror,'_publish'):
        try:
          read=Mock(return_value=(b'\xff'*16,2,2,False))
          self.assertTrue(mirror.capture(read,started=True,session_id=SESSION,now=1))
          self.assertTrue(encoding.wait(1))
          self.assertFalse(mirror.capture(read,started=True,session_id=SESSION,now=1.01))
          self.assertFalse(mirror.capture(read,started=True,session_id=SESSION,now=2))
          self.assertEqual(read.call_count,1)
          self.assertEqual(mirror._pending.qsize(),0)
        finally:
          mirror.close();release.set();mirror._thread.join(1)

  def test_async_jpeg_atomic_outputs_flip_resize_and_metadata(self):
    from PIL import Image
    with tempfile.TemporaryDirectory() as folder:
      mirror=self.make(folder)
      # Texture readback is upside down; final top must be red.
      original=Image.new('RGBA',(1200,40),'red')
      original.paste('blue',(0,0,1200,20))
      thread_ids=[];done=threading.Event();real=mirror._publish
      def publish(*args):
        thread_ids.append(threading.get_ident());real(*args);done.set()
      with patch.object(mirror,'_publish',side_effect=publish):
        captured=time.monotonic()
        self.assertTrue(mirror.capture(lambda:(original.tobytes(),1200,40,True),started=True,session_id=SESSION,now=captured))
        self.assertTrue(done.wait(2))
      data=json.loads((mirror.directory/'frame.json').read_text())
      self.assertEqual(data['session_id'],SESSION)
      self.assertEqual(data['captured_wall'],captured)
      self.assertGreaterEqual(data['encoded_wall'],captured)
      self.assertGreaterEqual(data['encode_ms'],0)
      self.assertGreaterEqual(data['capture_ms'],0)
      with Image.open(mirror.directory/'latest.jpg') as result:
        self.assertEqual(result.size,(1072,36))
        self.assertGreater(result.getpixel((10,2))[0],200)
        self.assertGreater(result.getpixel((10,33))[2],200)
      self.assertNotEqual(thread_ids[0],threading.get_ident())
      self.assertEqual(sorted(p.name for p in mirror.directory.iterdir()),['frame.json','latest.jpg'])

  def test_readback_error_does_not_break_ui_or_hold_slot(self):
    with tempfile.TemporaryDirectory() as folder:
      mirror=self.make(folder)
      self.assertFalse(mirror.capture(Mock(side_effect=RuntimeError('GPU read failed')),started=True,session_id=SESSION))
      self.assertIn('GPU read failed',mirror.last_error)
      self.assertTrue(mirror._busy.acquire(blocking=False));mirror._busy.release()

  def test_native_texture_orientation_and_release(self):
    image=NS(data=b'abcd',width=1,height=1)
    rl=NS(rl_draw_render_batch_active=Mock(),load_image_from_texture=Mock(return_value=image),
          load_image_from_screen=Mock(return_value=image),unload_image=Mock(),ffi=NS(buffer=lambda data,count:data[:count]))
    self.assertEqual(read_ui_rgba(rl,NS(_render_texture=NS(texture='texture'))),(b'abcd',1,1,True))
    rl.load_image_from_texture.assert_called_once_with('texture')
    rl.unload_image.assert_called_once_with(image)
    self.assertEqual(read_ui_rgba(rl,NS(_render_texture=None)),(b'abcd',1,1,False))


if __name__=='__main__':unittest.main()
