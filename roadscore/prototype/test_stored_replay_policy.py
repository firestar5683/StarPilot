import json
import tempfile
import unittest
from pathlib import Path
from stored_replay_policy import replay_archive
from score_archive import recording_complete, prefer_new_score
from capture_alignment import video_frames

class StoredReplayTests(unittest.TestCase):
 def test_archive_offset_and_explicit_seek(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)
   meta={'route':'route','first_model_ns':123,'audio_file_start_relative_first_model':.25,'replay_start_seconds':149}
   (p/'metadata.json').write_text(json.dumps(meta))
   header=bytearray(b'fLaC'+bytes([128,0,0,34])+bytes(34))
   header[18:26]=((48000<<44)|14400000).to_bytes(8,'big')
   (p/'score.flac').write_bytes(header)
   self.assertEqual(replay_archive(p,'route'),(149,390.25))
   self.assertEqual(replay_archive(p,'route',160),(160,390.25))
   self.assertEqual(replay_archive(p,'route',0),(0,539.25))
   with self.assertRaisesRegex(ValueError,'different route'):replay_archive(p,'other')
   meta['audio_file_start_relative_first_model']=None
   (p/'metadata.json').write_text(json.dumps(meta))
   with self.assertRaisesRegex(ValueError,'audio clock'):replay_archive(p,'route')
 def test_partial_does_not_replace_complete_excerpt(self):
  self.assertFalse(prefer_new_score({'complete':False,'audio_seconds':400},{'complete':True,'replay_start_seconds':149,'audio_seconds':300}))
 def test_partial_audio_is_not_complete(self):
  eof={'end_reason':'native final segment exhausted'}
  self.assertTrue(recording_complete([{}],eof,{}))
  self.assertFalse(recording_complete([],eof,{}))
  self.assertFalse(recording_complete([{}],{'end_reason':'requested duration'},{}))
  self.assertFalse(recording_complete([{}],eof,{'failure':'clock lost'}))
 def test_stored_video_trims_startup_and_preserves_tail(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)
   (p/'stored_summary.json').write_text(json.dumps({'first_dac_wall':200,'source_frame_start':44100,'source_frame_end':132300,'sample_rate':44100}))
   self.assertEqual(video_frames(p,[{'wall':w} for w in [10,199,200,201,202,203]]),[2,3,4])
   with self.assertRaises(ValueError):video_frames(p,[{'wall':10}])
if __name__=='__main__':unittest.main()
