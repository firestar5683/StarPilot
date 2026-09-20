import json
from pathlib import Path
import tempfile
import unittest
import numpy as np
import soundfile as sf
from prepared_core import load_archive, initial_frame, PreparedPresentation
from replay_ui_controls import isolated_replay


class PreparedTests(unittest.TestCase):
  def setUp(self):
    self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
    self.path=Path(self.tmp.name)
    (self.path/'launch.json').write_text(json.dumps(dict(route='fixture',render_mode='gold-core',end_reason='native final segment exhausted')))
    (self.path/'replay_origin.json').write_text(json.dumps(dict(first_model_ns=1000000000,host_received_wall=10.)))
    (self.path/'audio_blocks.jsonl').write_text(json.dumps(dict(audio_s=0.,callback_wall=10.05,dac_delay=.1))+'\n')
    self.pcm=np.ones((48000,2),np.float32)*.1
    sf.write(self.path/'dry.wav',self.pcm,48000,subtype='FLOAT')
    (self.path/'rhythm_timeline.json').write_text(json.dumps([dict(start_frame=0,end_frame=480000,grid=dict(bpm=120.,beat_phase=0.,tempo_confidence=1.,phase_confidence=1.,coherent=True,reason='fixture'))]))
  def test_original_clock_and_pcm_preserved(self):
    pcm,rate,meta=load_archive(self.path,'fixture')
    np.testing.assert_array_equal(pcm,self.pcm)
    self.assertEqual(initial_frame(meta,1000000000,.15,rate),0)
    self.assertEqual(initial_frame(meta,1500000000,.15,rate),24000)
  def test_wrong_route_and_final_pcm_rejected(self):
    with self.assertRaises(ValueError):load_archive(self.path,'other')
    (self.path/'launch.json').write_text(json.dumps(dict(route='fixture',render_mode='current',end_reason='native final segment exhausted')))
    with self.assertRaises(ValueError):load_archive(self.path,'fixture')
  def test_reaction_changes_without_changing_source(self):
    engine=PreparedPresentation(self.path)
    state=dict(active=True,signal_on=False,fresh=True,car_fresh=True,model_fresh=True,speed=10.,alert_key='',alert_meaningful=False,curve=dict(kind='curve',phase='neutral',amount=0.,activation=None))
    before=self.pcm.copy()
    chunks=[];cues={}
    for frame in range(0,48000,960):
      wet,cues=engine.process(self.pcm[frame:frame+960],frame,state,('disengaged','left'));chunks.append(wet)
    result=np.concatenate(chunks)
    self.assertLess(engine.engagement.mix,.01)
    self.assertGreater(len(engine.shaker.pulse_frames),0)
    self.assertTrue(cues['replay_demo']['simulated'])
    np.testing.assert_array_equal(self.pcm,before)
    self.assertEqual(result.shape,before.shape)
  def test_mac_isolation_requires_explicit_matching_namespace(self):
    env=dict(ROADSCORE_REPLAY_UI_CONTROLS='1',SIMULATION='1',ZMQ='1',ROADSCORE_PREPARED_SHOWCASE='1',ROADSCORE_SHOWCASE_SESSION='abcdefgh',OPENPILOT_ZMQ_NAMESPACE='roadscore-showcase-abcdefgh')
    self.assertTrue(isolated_replay(env))
    for key in ('ROADSCORE_PREPARED_SHOWCASE','ROADSCORE_SHOWCASE_SESSION','SIMULATION'):
      self.assertFalse(isolated_replay({**env,key:''}))
    self.assertFalse(isolated_replay({**env,'OPENPILOT_ZMQ_NAMESPACE':'roadscore-native-abc'}))

if __name__=='__main__':unittest.main()
