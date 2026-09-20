import ast
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
import numpy as np
import soundfile as sf
from prepared_core import load_archive, initial_frame, PreparedPresentation, archive_tail_proof, RecordedTail
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
    self.assertIsNone(meta['archived_tail'])
  def test_optional_terminal_proof_keeps_original_pcm(self):
    bridge=dict(route='fixture',origin_ns=1000000000,last_t=.7,failure=None,messages=100,
                clock='zero at first model received; source logMonoTime remains unchanged')
    (self.path/'bridge.json').write_text(json.dumps(bridge))
    pcm,rate,meta=load_archive(self.path,'fixture')
    np.testing.assert_array_equal(pcm,self.pcm)
    self.assertEqual(meta['archived_tail']['terminal_model_ns'],1700000000)
    self.assertAlmostEqual(meta['archived_tail']['tail_seconds'],.45)
    (self.path/'bridge.json').write_text('incomplete JSON')
    self.assertIsNone(load_archive(self.path,'fixture')[2]['archived_tail'])
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
  def test_signal_off_overrides_recorded_blinker_through_complete_presentation(self):
    engine=PreparedPresentation(self.path)
    state=dict(active=True,signal_on=True,fresh=True,car_fresh=True,model_fresh=True,speed=10.,
               alert_key='',alert_meaningful=False,curve=dict(kind='curve',phase='neutral',amount=0.,activation=None))
    block=np.zeros((960,2),np.float32)
    engine.process(block,0,state,('engaged','left'))
    count=len(engine.shaker.pulse_frames)
    for frame in range(960,48000,960):
      _,cues=engine.process(block,frame,state,('engaged','off'))
    self.assertEqual(len(engine.shaker.pulse_frames),count)
    self.assertFalse(cues['signal_shaker']['sequence_active'])
    self.assertFalse(cues['signal_shaker']['rendered_active'])
    self.assertEqual(cues['replay_demo']['signal_mode'],'off')
    engine.process(block,48000,state,('engaged','recorded'))
    self.assertGreater(len(engine.shaker.pulse_frames),count)
  def test_staged_cut_stays_clear_with_signal_and_full_presentation_stack(self):
    engine=PreparedPresentation(self.path)
    rate=48000;payoff=2.5
    samples=np.arange(4*rate)/rate
    core=np.repeat((.15*np.sin(2*np.pi*90*samples))[:,None],2,axis=1).astype(np.float32)
    before=core.copy();chunks=[];signal_blocks_during_build=0
    for frame in range(0,len(core),960):
      now=frame/rate
      curve=dict(kind='curve',phase='anticipation' if now<payoff else 'event',
                 amount=min(1.,max(0.,(now-.2)/(payoff-.2))),activation=.2,
                 predicted_peak=payoff,demo_staged_curve=True,demo_build_drop=True)
      if now<.2 or now>=3.5:curve=dict(kind='curve',phase='neutral',amount=0.,activation=None)
      state=dict(active=True,signal_on=True,fresh=True,car_fresh=True,model_fresh=True,
                 speed=10.,alert_key='',alert_meaningful=False,curve=curve,route_t=now)
      wet,cues=engine.process(core[frame:frame+960],frame,state,('engaged','left'))
      if .5<now<2 and cues['signal_shaker']['rendered_active']:
        signal_blocks_during_build+=1
        self.assertEqual(cues['curve_reaction']['build_drop']['rendered_roll_peak'],0.)
      chunks.append(wet)
    result=np.concatenate(chunks)
    self.assertEqual(engine.curve.impact.actual_payoff,round(payoff*rate))
    self.assertGreater(signal_blocks_during_build,5)
    self.assertLess(float(np.max(abs(result[round((payoff-.08)*rate):round((payoff-.02)*rate)]))),1e-6)
    self.assertGreater(float(np.sqrt(np.mean(result[round((payoff+.04)*rate):round((payoff+.12)*rate)]**2))),.09)
    np.testing.assert_array_equal(core,before)
    self.assertEqual(result.shape,core.shape)
    self.assertTrue(np.isfinite(result).all())


class ArchivedTailTests(unittest.TestCase):
  def setUp(self):
    self.origin={'first_model_ns':36517892685238}
    self.launch={'route':'fixture','end_reason':'native final segment exhausted'}
    self.bridge=dict(route='fixture',origin_ns=self.origin['first_model_ns'],last_t=300.000663318,
                     failure=None,messages=84032,clock='zero at first model received; source logMonoTime remains unchanged')
  def proof(self,bridge=None,launch=None,duration=306.2):
    return archive_tail_proof(self.bridge if bridge is None else bridge,self.launch if launch is None else launch,
                              self.origin,duration,.173852003)
  def test_measured_terminal_model_and_recorded_tail(self):
    proof=self.proof()
    self.assertEqual(proof['terminal_model_ns'],36817893348556)
    self.assertAlmostEqual(proof['tail_seconds'],6.373188685)
    for delta in (-1,0,1):
      tail=RecordedTail(proof);tail.observe(proof['terminal_model_ns']+delta,300.,100)
      tail.observe(proof['terminal_model_ns']+delta,303.,200)
      self.assertTrue(tail.allows_stale(proof['terminal_model_ns']+delta,303.))
    for delta in (-2,2,-50_000_000):
      self.assertFalse(tail.allows_stale(proof['terminal_model_ns']+delta,303.))
    for age in (-1,float('nan'),proof['tail_seconds']+1.001):
      self.assertFalse(tail.allows_stale(proof['terminal_model_ns'],300.+age))
    self.assertFalse(RecordedTail(None).allows_stale(proof['terminal_model_ns'],303.))
  def test_duplicate_endpoint_cannot_extend_deadline_and_pcm_must_progress(self):
    proof=self.proof();mono=proof['terminal_model_ns'];tail=RecordedTail(proof)
    tail.observe(mono,300.,100)
    tail.observe(mono,301.,200)
    self.assertEqual(tail.terminal_wall,300.)
    self.assertTrue(tail.allows_stale(mono,301.))
    tail.observe(mono,302.1,200)
    self.assertFalse(tail.allows_stale(mono,302.1))
    # A bounded backwards DAC correction cannot masquerade as forward progress.
    tail.observe(mono,302.2,150)
    self.assertFalse(tail.allows_stale(mono,302.2))
    tail.observe(mono,302.3,201)
    self.assertTrue(tail.allows_stale(mono,302.3))
    tail.observe(mono,308.,300)
    self.assertFalse(tail.allows_stale(mono,308.))
  def test_incomplete_foreign_failed_or_excessive_tail_proof_is_rejected(self):
    for patch in ({'route':'other'},{'origin_ns':100},{'failure':'lost pipe'},
                  {'last_t':float('nan')},{'last_t':True},{'last_t':-1},{'messages':0},{'clock':'unknown'}):
      with self.subTest(patch=patch):self.assertIsNone(self.proof({**self.bridge,**patch}))
    self.assertIsNone(self.proof({key:value for key,value in self.bridge.items() if key!='failure'}))
    self.assertIsNone(self.proof(launch={**self.launch,'end_reason':'requested duration'}))
    self.assertIsNone(self.proof(duration=311.))
    self.assertIsNone(self.proof(duration=299.))
  def test_real_worker_stream_loss_gate_accepts_only_bounded_exact_endpoint(self):
    path=Path(__file__).with_name('mac_showcase.py')
    worker=next(node for node in ast.parse(path.read_text()).body if isinstance(node,ast.FunctionDef) and node.name=='audio_worker')
    guard=next(node for node in ast.walk(worker) if isinstance(node,ast.If) and len(node.body)==1
               and isinstance(node.body[0],ast.Raise)
               and 'Replay model stream stopped before prepared audio ended' in ast.unparse(node))
    code=compile(ast.Module(body=[guard],type_ignores=[]),str(path),'exec')
    proof=self.proof()
    tail=RecordedTail(proof);tail.observe(proof['terminal_model_ns'],300.,300*48000)
    tail.observe(proof['terminal_model_ns'],303.,303*48000)
    context=dict(started=1.,now=303.,received={'modelV2':300.},position=303*48000,rate=48000,
                 audio=range(round(306.2*48000)),tail=tail,
                 sm=SimpleNamespace(logMonoTime={'modelV2':proof['terminal_model_ns']}))
    exec(code,context)
    context['sm'].logMonoTime['modelV2']-=50_000_000
    with self.assertRaisesRegex(RuntimeError,'stream stopped'):exec(code,context)
    context['sm'].logMonoTime['modelV2']=proof['terminal_model_ns']
    context['now']=308.
    with self.assertRaisesRegex(RuntimeError,'stream stopped'):exec(code,context)
    context['now']=303.;context['tail']=RecordedTail(None)
    with self.assertRaisesRegex(RuntimeError,'stream stopped'):exec(code,context)
    # A stuck callback cannot hide forever inside the old final-two-second grace.
    context.update(now=305.,position=305*48000,tail=tail)
    with self.assertRaisesRegex(RuntimeError,'stream stopped'):exec(code,context)

if __name__=='__main__':unittest.main()
