import unittest
from roadscore.prototype.prepare_playback_video import nominal_rate,validate_output

class PlaybackValidationTest(unittest.TestCase):
  def test_nominal_camera_rate(self):
    self.assertEqual(nominal_rate('1000000000/50000001'),20)
  def test_complete_and_partial_segments(self):
    for n in (1200,573):
      source={'r_frame_rate':'20/1','nb_read_frames':str(n),'width':1928,'height':1208}
      out={**source,'codec_name':'h264','avg_frame_rate':'20/1','duration':str(n/20)}
      self.assertEqual(validate_output(source,out,[i/20 for i in range(n)])['output_frames'],n)
      for key,value in [('nb_read_frames',str(n-1)),('width',1280),('avg_frame_rate','40/1'),('duration','1')]:
        with self.assertRaises(ValueError):validate_output(source,{**out,key:value},[i/20 for i in range(n)])
      with self.assertRaises(ValueError):validate_output(source,out,[i/20+.05 for i in range(n)])
      with self.assertRaises(ValueError):validate_output(source,out,list(reversed([i/20 for i in range(n)])))

if __name__=='__main__':unittest.main()
