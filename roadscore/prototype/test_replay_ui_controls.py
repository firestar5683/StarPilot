import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from cereal import log, car, custom
from cue_timing import REFERENCE
from replay_ui_controls import ReplayUIControls, ReplayStateView, isolated_replay, apply_turn_intent


class Subscriber:
  def __init__(self):
    self.builders = {
      'selfdriveState': log.SelfdriveState.new_message(enabled=True, active=True, state='enabled', alertText1='Recorded alert'),
      'starpilotCarState': custom.StarPilotCarState.new_message(alwaysOnLateralEnabled=False, pauseLateral=True),
      'carState': car.CarState.new_message(leftBlinker=False, rightBlinker=True, vEgo=12),
    }
    self.updated = {key: False for key in self.builders}
    self.valid = {key: True for key in self.builders}
    self.alive = dict(self.valid)
    self.logMonoTime = {key: 123 for key in self.builders}
  def __getitem__(self, key):return self.builders[key].as_reader()
  def update(self, *args, **kwargs):return 17


class Tests(unittest.TestCase):
  def setUp(self):
    self.tmp = tempfile.TemporaryDirectory()
    self.addCleanup(self.tmp.cleanup)
    self.path = Path(self.tmp.name)/'status.json'
    self.controls = ReplayUIControls(self.path, enabled=True, clock=lambda: 100)
    self.sm = Subscriber()
    self.view = ReplayStateView(self.sm, self.controls)
  def state(self, mode='disengaged', signal='left', **patch):
    state = dict(command_wall=99.5, input_mode='replay', presentation_session_id='session',
                 replay_demo=dict(mode=mode, signal_mode=signal),presentation_timing_reference=REFERENCE,
                 presentation_timeline=[dict(audible_wall=99.8,cues=dict(replay_demo=dict(mode=mode,signal_mode=signal)))])
    state.update(patch)
    self.path.write_text(json.dumps(state))
  def test_full_native_state_without_mutating_recording(self):
    before = {key:value.to_bytes() for key,value in self.sm.builders.items()}
    for value in self.sm.builders.values():value.clear_write_flag()
    self.state();self.assertEqual(self.view.update(0),17)
    ss = self.view['selfdriveState']
    self.assertFalse(ss.enabled);self.assertFalse(ss.active);self.assertEqual(str(ss.state),'disabled')
    self.assertEqual(ss.alertText1,'Recorded alert')
    self.assertTrue(self.view['starpilotCarState'].alwaysOnLateralEnabled)
    self.assertFalse(self.view['starpilotCarState'].pauseLateral)
    self.assertTrue(self.view['carState'].leftBlinker);self.assertFalse(self.view['carState'].rightBlinker)
    self.assertEqual(self.view['carState'].vEgo,12)
    self.assertTrue(self.view.updated['selfdriveState']);self.assertFalse(self.sm.updated['selfdriveState'])
    self.assertIs(self.view.valid,self.sm.valid);self.assertIs(self.view.logMonoTime,self.sm.logMonoTime)
    for key,value in self.sm.builders.items():self.assertEqual(before[key],value.to_bytes())
    ui = SimpleNamespace(started=True, always_on_lateral_active=False, switchback_mode_enabled=True)
    self.view.apply_native_mode(ui);self.assertTrue(ui.always_on_lateral_active);self.assertFalse(ui.switchback_mode_enabled)
  def test_reset_restores_latest_source_and_signal_independence(self):
    self.state();self.view.update()
    self.state('engaged','right');self.view.update()
    self.assertTrue(self.view['selfdriveState'].enabled);self.assertFalse(self.view['starpilotCarState'].alwaysOnLateralEnabled)
    self.assertFalse(self.view['carState'].leftBlinker);self.assertTrue(self.view['carState'].rightBlinker)
    self.state('recorded','off');self.view.update()
    self.assertFalse(self.view['carState'].leftBlinker);self.assertFalse(self.view['carState'].rightBlinker)
    self.sm.builders['selfdriveState'].enabled=False
    self.state('recorded','recorded');self.view.update()
    self.assertFalse(self.view['selfdriveState'].enabled);self.assertTrue(self.view['carState'].rightBlinker)
  def test_no_override_without_fresh_same_replay_session(self):
    self.state();self.view.update()
    for patch in ({'command_wall':97},{'command_wall':101},{'command_wall':float('nan')},
                  {'presentation_session_id':'different'}, {'input_mode':'live'}, {'compute':'none'}):
      self.state(**patch);self.view.update()
      self.assertEqual((self.view.mode,self.view.signal_mode),('recorded','recorded'))
    self.state();self.sm.alive['carState']=False;self.view.update()
    self.assertEqual(self.view.mode,'recorded')
  def test_waits_for_audible_timeline(self):
    self.state(presentation_timing_reference=REFERENCE,presentation_timeline=[
      dict(audible_wall=101,cues=dict(replay_demo=dict(mode='disengaged',signal_mode='left'))) ])
    self.view.update();self.assertEqual(self.view.mode,'recorded')
    self.state(presentation_timing_reference=REFERENCE,presentation_timeline=[
      dict(audible_wall=99.9,cues=dict(replay_demo=dict(mode='disengaged',signal_mode='right'))) ])
    self.view.update();self.assertEqual((self.view.mode,self.view.signal_mode),('disengaged','right'))
  def test_transport_gate_and_disabled_reader(self):
    env=dict(ROADSCORE_REPLAY_UI_CONTROLS='1',SIMULATION='1',OPENPILOT_PREFIX='roadscore_replay')
    self.assertTrue(isolated_replay(env))
    for patch in ({'ZMQ':'1'}, {'OPENPILOT_PREFIX':''}, {'SIMULATION':'0'}, {'ROADSCORE_REPLAY_UI_CONTROLS':'0'}):
      self.assertFalse(isolated_replay(env|patch))
    self.state();self.controls.enabled=False;self.view.update();self.assertEqual(self.view.mode,'recorded')
  def test_unverified_or_stale_audio_never_binds_or_overrides(self):
    self.state(presentation_timing_reference='unknown');self.view.update()
    self.assertIsNone(self.controls.session);self.assertEqual(self.view.mode,'recorded')
    self.state(presentation_timeline=[]);self.view.update();self.assertIsNone(self.controls.session)
    self.state(presentation_timeline=[dict(audible_wall=90,cues=dict(replay_demo=dict(mode='disengaged',signal_mode='left')))])
    self.view.update();self.assertIsNone(self.controls.session);self.assertEqual(self.view.mode,'recorded')
  def test_malformed_and_missing_status_revert(self):
    self.state();self.view.update()
    for text in ('[]','broken','null'):
      self.path.write_text(text);self.view.update();self.assertEqual(self.view.mode,'recorded')
    self.path.unlink();self.view.update();self.assertEqual(self.view.mode,'recorded')
  def test_callback_controls_survive_output_delay_and_status_serialization(self):
    from operator_output import PresentationDelay
    delay=PresentationDelay(Path(self.tmp.name),output_provider=lambda:None,clock=lambda:100)
    snapshot=dict(command_wall=100,input_mode='replay',presentation_session_id='new')
    cues=dict(replay_demo=dict(mode='disengaged',signal_mode='right'))
    state=delay.apply(snapshot,dict(sequence=1,callback_wall=99.5,dac_wall=99.8,cues=cues))
    self.path.write_text(json.dumps(state));self.view.update()
    self.assertEqual((self.view.mode,self.view.signal_mode),('disengaged','right'))
  def test_native_turn_arrow_direction_and_recorded_fallback(self):
    class Filter:
      x=0
      def update(self,target):self.target=target
    widget=SimpleNamespace(_pre=False,_turn_intent_direction=0,FADE_IN_ANGLE=30,
                           _turn_intent_alpha_filter=Filter(),_turn_intent_rotation_filter=Filter())
    self.assertTrue(apply_turn_intent(widget,'left'))
    self.assertEqual(widget._turn_intent_direction,-1);self.assertEqual(widget._turn_intent_alpha_filter.target,1)
    self.assertTrue(apply_turn_intent(widget,'right'));self.assertEqual(widget._turn_intent_direction,1)
    self.assertTrue(apply_turn_intent(widget,'off'));self.assertEqual(widget._turn_intent_direction,0)
    self.assertEqual(widget._turn_intent_alpha_filter.target,0)
    self.assertFalse(apply_turn_intent(widget,'recorded'))

if __name__=='__main__':unittest.main()
