import json,tempfile,unittest
from pathlib import Path
from capture_alignment import audio_alignment,video_frames

class AlignmentTests(unittest.TestCase):
 def test_fresh_preparation_and_leading_silence_share_actual_capture_origin(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);(p/'host_heard.flac').touch()
   (p/'host_audio_summary.json').write_text(json.dumps({'first_host_dac_wall':200.,'muted':True,'errors':[]}))
   self.assertEqual(audio_alignment(p,100.)[1],-100.)
   self.assertEqual(audio_alignment(p,203.25)[1],3.25)
 def test_stored_partial_route_offset_is_preserved(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);(p/'score.flac').touch()
   (p/'stored_summary.json').write_text(json.dumps({'first_dac_wall':200.,'source_frame_start':480000,'score':d,'muted':True}))
   self.assertEqual(audio_alignment(p,202.)[1],12.)
 def test_fresh_video_omits_preparation_from_measured_interval(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);(p/'host_audio_summary.json').write_text(json.dumps({'first_host_dac_wall':200.,'host_frames':96000}))
   self.assertEqual(video_frames(p,[{'wall':x} for x in [100.,199.,200.,201.,202.,203.]]),[2,3,4])
 def test_invalid_fresh_capture_does_not_fall_back(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);(p/'host_audio_summary.json').write_text(json.dumps({'first_host_dac_wall':200.,'errors':['lost PCM']}))
   with self.assertRaises(ValueError):audio_alignment(p,202.)
if __name__=='__main__':unittest.main()
