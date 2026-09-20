import ast
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from cereal import log, car, custom
from cue_timing import REFERENCE
from replay_ui_controls import ReplayUIControls, ReplayStateView, isolated_replay, apply_turn_intent, replay_turn_alert, restore_recorded_turn_icon


class Subscriber:
  def __init__(self):
    self.builders = {
      'selfdriveState': log.SelfdriveState.new_message(enabled=True, active=True, state='enabled', alertText1='Recorded alert'),
      'starpilotSelfdriveState': custom.StarPilotSelfdriveState.new_message(),
      'starpilotCarState': custom.StarPilotCarState.new_message(alwaysOnLateralEnabled=False, pauseLateral=True),
      'carState': car.CarState.new_message(leftBlinker=False, rightBlinker=True, vEgo=12),
      'modelV2': log.ModelDataV2.new_message(),
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
  def test_recorded_icon_direction_uses_original_fresh_model_and_blinkers(self):
    self.state('recorded','left');self.view.update()
    self.assertTrue(self.view['carState'].leftBlinker)
    self.assertEqual(self.view.recorded_turn_side(),'right')
    model=self.sm.builders['modelV2'].meta
    model.laneChangeState='laneChangeStarting';model.laneChangeDirection='left'
    self.assertEqual(self.view.recorded_turn_side(),'left')
    self.sm.alive['modelV2']=False
    self.assertEqual(self.view.recorded_turn_side(),'right')
    self.sm.builders['carState'].leftBlinker=True
    self.assertIsNone(self.view.recorded_turn_side())  # Both blinkers are ambiguous.
    self.sm.builders['carState'].leftBlinker=False;self.sm.valid['carState']=False
    self.assertIsNone(self.view.recorded_turn_side())
  def test_recorded_icon_cache_survives_manual_off_and_unknown_direction(self):
    widget=SimpleNamespace(_last_icon_side='right')
    restore_recorded_turn_icon(widget,'left','right')
    widget._last_icon_side='left'  # Native renderer draws the simulated prompt.
    restore_recorded_turn_icon(widget,'off',None)
    self.assertEqual(widget._last_icon_side,'left')  # Do not alter its normal fade.
    restore_recorded_turn_icon(widget,'recorded',None)
    self.assertEqual(widget._last_icon_side,'right')
    widget=SimpleNamespace(_last_icon_side=None)
    restore_recorded_turn_icon(widget,'left',None);widget._last_icon_side='left'
    restore_recorded_turn_icon(widget,'recorded',None)
    self.assertIsNone(widget._last_icon_side)  # Never promote a manual side to recorded.
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

  def test_signal_off_fades_correct_side_and_recorded_clears_simulation(self):
    class Filter:
      x=1
      def update(self,target):self.x=(self.x+target)/2
    widget=SimpleNamespace(_pre=False,_turn_intent_direction=0,FADE_IN_ANGLE=30,
                           _turn_intent_alpha_filter=Filter(),_turn_intent_rotation_filter=Filter())
    apply_turn_intent(widget,'right');apply_turn_intent(widget,'off')
    self.assertEqual(widget._turn_intent_direction,1)
    self.assertGreater(widget._turn_intent_alpha_filter.x,.01)
    self.assertFalse(apply_turn_intent(widget,'recorded'))
    self.assertEqual(widget._turn_intent_alpha_filter.x,0)
    self.assertEqual(widget._turn_intent_direction,0)

  def test_native_steer_prompt_labels_directions_and_independent_reset(self):
    widget=SimpleNamespace(_prev_alert=None,_alpha_filter=SimpleNamespace(x=0))
    for mode,signal in [('recorded','left'),('engaged','right'),('disengaged','left')]:
      self.state(mode,signal);self.view.update()
      before=self.view['selfdriveState'].to_dict()
      prompt=replay_turn_alert(widget,self.view.signal_mode,None,SimpleNamespace)
      self.assertEqual(prompt.text1,'Steer '+signal.title())
      self.assertEqual(prompt.text2,'Confirm Lane Change')
      self.assertEqual(prompt.alert_type,'preLaneChange'+signal.title()+'/warning')
      self.assertIs(widget._prev_alert,prompt)
      self.assertEqual(self.view['selfdriveState'].to_dict(),before)
    for reset in ('off','recorded'):
      replay_turn_alert(widget,'right',None,SimpleNamespace)
      self.state('engaged',reset);self.view.update()
      self.assertTrue(self.view['selfdriveState'].enabled)
      self.assertIsNone(replay_turn_alert(widget,self.view.signal_mode,None,SimpleNamespace))
      self.assertIsNone(widget._prev_alert)

  def test_manual_signals_replace_recorded_blinkers_and_routine_alerts_only(self):
    for service in ('selfdriveState','starpilotSelfdriveState'):
      source=self.sm.builders[service]
      source.alertType='preLaneChangeRight/warning';source.alertSize='mid';source.alertStatus='normal'
      source.alertText1='Steer Right';source.alertText2='Confirm Lane Change'
    before={key:value.to_dict() for key,value in self.sm.builders.items()}
    for selection,blinkers in [('left',(True,False)),('right',(False,True)),('off',(False,False))]:
      self.state('recorded',selection);self.view.update()
      self.assertEqual((self.view['carState'].leftBlinker,self.view['carState'].rightBlinker),blinkers)
      self.assertTrue(self.view['selfdriveState'].enabled)
      for service in ('selfdriveState','starpilotSelfdriveState'):
        self.assertEqual(str(self.view[service].alertSize),'none')
        self.assertEqual(self.view[service].alertType,'')
      for key,value in self.sm.builders.items():self.assertEqual(value.to_dict(),before[key])
    self.state('recorded','recorded');self.view.update()
    self.assertTrue(self.view['carState'].rightBlinker)
    for service in ('selfdriveState','starpilotSelfdriveState'):
      self.assertEqual(self.view[service].alertType,'preLaneChangeRight/warning')
    for kind,status in [('laneChangeBlocked/warning','normal'),('steerUnavailable/immediateDisable','critical'),
                        ('preLaneChangeRight/warning','critical')]:
      for service in ('selfdriveState','starpilotSelfdriveState'):
        self.sm.builders[service].alertType=kind;self.sm.builders[service].alertStatus=status
      self.state('recorded','off');self.view.update()
      for service in ('selfdriveState','starpilotSelfdriveState'):self.assertEqual(self.view[service].alertType,kind)

  def test_manual_prompt_replaces_recorded_turn_and_its_cached_fade(self):
    for kind in ('preLaneChangeLeft/warning','preLaneChangeRight/warning','laneChange/warning'):
      for selection in ('left','right','off'):
        recorded=SimpleNamespace(text1='Recorded turn',alert_type=kind,status=0)
        widget=SimpleNamespace(_prev_alert=recorded,_alpha_filter=SimpleNamespace(x=1))
        result=replay_turn_alert(widget,selection,recorded,SimpleNamespace)
        if selection=='off':
          self.assertIsNone(result);self.assertIsNone(widget._prev_alert);self.assertEqual(widget._alpha_filter.x,0)
        else:self.assertEqual(result.text1,'Steer '+selection.title())
        self.assertIs(replay_turn_alert(widget,'recorded',recorded,SimpleNamespace),recorded)

  def test_manual_arrow_hook_never_falls_back_to_recorded_onroad_events(self):
    class Filter:
      x=1.
      def update(self,target):self.x=target
    widget=SimpleNamespace(_pre=True,_turn_intent_direction=1,FADE_IN_ANGLE=30,
                           _turn_intent_alpha_filter=Filter(),_turn_intent_rotation_filter=Filter())
    calls=[]
    namespace=dict(ui_state=SimpleNamespace(started=True,sm=self.view),ReplayStateView=ReplayStateView,
                   apply_turn_intent=apply_turn_intent,replay_arrow_mode='recorded',
                   original_turn_intent=lambda widget:calls.append('recorded events'))
    source=Path(__file__).with_name('normal_ui_audit.py')
    node=next(node for node in ast.walk(ast.parse(source.read_text())) if isinstance(node,ast.FunctionDef) and node.name=='replay_turn_intent')
    exec(compile(ast.Module(body=[node],type_ignores=[]),str(source),'exec'),namespace)
    self.state('recorded','off');self.view.update();namespace['replay_turn_intent'](widget)
    self.assertEqual(widget._turn_intent_direction,0);self.assertEqual(widget._turn_intent_alpha_filter.x,0)
    for direction,expected in [('left',-1),('right',1)]:
      self.state('recorded',direction);self.view.update();namespace['replay_arrow_mode']=direction
      namespace['replay_turn_intent'](widget);self.assertEqual(widget._turn_intent_direction,expected)
    self.assertEqual(calls,[])
    namespace['replay_arrow_mode']='off'  # An unrelated native alert owns the display.
    namespace['replay_turn_intent'](widget);self.assertEqual(calls,[])
    self.state('recorded','recorded');self.view.update();namespace['replay_turn_intent'](widget)
    self.assertEqual(calls,['recorded events'])

  def test_filtered_turn_still_exposes_important_secondary_native_alert(self):
    source=Path(__file__).resolve().parents[2]/'selfdrive/ui/mici/onroad/alert_renderer.py'
    node=next(node for node in ast.walk(ast.parse(source.read_text())) if isinstance(node,ast.FunctionDef) and node.name=='get_alert')
    node.returns=None
    for arg in node.args.args:arg.annotation=None
    namespace=dict(Alert=SimpleNamespace,AlertSize=log.SelfdriveState.AlertSize,custom=custom)
    exec(compile(ast.Module(body=[node],type_ignores=[]),str(source),'exec'),namespace)
    self.sm.updated['selfdriveState']=True
    ss=self.sm.builders['selfdriveState'];ss.alertType='preLaneChangeRight/warning';ss.alertSize='mid'
    critical=self.sm.builders['starpilotSelfdriveState'];critical.alertType='steerUnavailable/immediateDisable'
    critical.alertSize='full';critical.alertStatus='critical';critical.alertText1='Take control'
    self.state('recorded','off');self.view.update()
    result=namespace['get_alert'](SimpleNamespace(_prev_alert=None),self.view)
    self.assertEqual(result.text1,'Take control');self.assertEqual(result.alert_type,critical.alertType)

  def test_native_alert_and_fade_preempt_simulated_prompt(self):
    native=SimpleNamespace(text1='Recorded alert',alert_type='laneChangeBlocked/warning')
    widget=SimpleNamespace(_prev_alert=None,_alpha_filter=SimpleNamespace(x=1))
    replay_turn_alert(widget,'left',None,SimpleNamespace)
    widget._prev_alert=native  # Native get_alert caches its own alert before the adapter.
    self.assertIs(replay_turn_alert(widget,'right',native,SimpleNamespace),native)
    self.assertIs(widget._prev_alert,native)
    self.assertIsNone(replay_turn_alert(widget,'right',None,SimpleNamespace))
    self.assertIs(widget._prev_alert,native)
    self.assertIsNone(replay_turn_alert(widget,'off',None,SimpleNamespace))
    self.assertIs(widget._prev_alert,native)
    widget._alpha_filter.x=.005
    prompt=replay_turn_alert(widget,'right',None,SimpleNamespace)
    self.assertEqual(prompt.text1,'Steer Right')

  def test_stale_or_unhealthy_replay_clears_only_simulated_prompt(self):
    widget=SimpleNamespace(_prev_alert=None,_alpha_filter=SimpleNamespace(x=1))
    self.state();self.view.update()
    replay_turn_alert(widget,self.view.signal_mode,None,SimpleNamespace)
    self.state(command_wall=90);self.view.update()
    self.assertIsNone(replay_turn_alert(widget,self.view.signal_mode,None,SimpleNamespace))
    self.assertIsNone(widget._prev_alert)
    self.state();self.view.update()
    replay_turn_alert(widget,self.view.signal_mode,None,SimpleNamespace)
    self.sm.alive['carState']=False;self.view.update()
    self.assertIsNone(replay_turn_alert(widget,self.view.signal_mode,None,SimpleNamespace))
    self.assertIsNone(widget._prev_alert)

  def test_renderer_hook_drives_native_side_icon_and_yields_to_alerts(self):
    # Execute the real hook and native icon layout without importing Linux messaging or opening a window.
    root=Path(__file__).resolve().parents[2]
    ui=SimpleNamespace(started=True)
    rectangle=lambda *values:SimpleNamespace(x=values[0],y=values[1],width=values[2],height=values[3])
    namespace=dict(ReplayStateView=ReplayStateView,replay_turn_alert=replay_turn_alert,
                   restore_recorded_turn_icon=restore_recorded_turn_icon,ui_state=ui,
                   original_get_alert=lambda widget,sm:getattr(widget,'native_alert',None),
                   Alert=lambda **fields:SimpleNamespace(**fields),AlertSize=SimpleNamespace(mid=2),
                   AlertStatus=SimpleNamespace(normal=0),replay_arrow_mode='recorded',
                   rl=SimpleNamespace(Rectangle=rectangle),IconSide=SimpleNamespace(left='left',right='right'),
                   IconLayout=lambda texture,side,*margins:SimpleNamespace(texture=texture,side=side),
                   AlertLayout=lambda text_rect,icon:SimpleNamespace(text_rect=text_rect,icon=icon))
    for source,name in [(Path(__file__).with_name('normal_ui_audit.py'),'replay_get_alert'),
                        (root/'selfdrive/ui/mici/onroad/alert_renderer.py','_icon_helper')]:
      node=next(node for node in ast.walk(ast.parse(source.read_text())) if isinstance(node,ast.FunctionDef) and node.name==name)
      node.returns=None
      for arg in node.args.args:arg.annotation=None
      exec(compile(ast.Module(body=[node],type_ignores=[]),str(source),'exec'),namespace)
    widget=SimpleNamespace(_prev_alert=None,_alpha_filter=SimpleNamespace(x=0),_alert_y_filter=SimpleNamespace(x=0),
                           _rect=rectangle(0,0,500,240),_txt_turn_signal_left=SimpleNamespace(width=104),
                           _txt_turn_signal_right=SimpleNamespace(width=104),_last_icon_side=None)
    namespace['ALERT_MARGIN']=18
    for side in ('left','right'):
      self.state('recorded',side);self.view.update()
      prompt=namespace['replay_get_alert'](widget,self.view)
      self.assertEqual(prompt.text1,'Steer '+side.title())
      icon=namespace['_icon_helper'](widget,prompt).icon
      self.assertEqual(icon.side,side)
      self.assertIs(icon.texture,getattr(widget,'_txt_turn_signal_'+side))
      self.assertTrue(ui.roadscore_replay_prompt_active)
      self.assertEqual(namespace['replay_arrow_mode'],side)
    # Route2 at64.4s: manual Left has populated the native cache, while the
    # recording is already changing lanes right with a directionless alert.
    self.state('recorded','left');self.view.update()
    prompt=namespace['replay_get_alert'](widget,self.view)
    namespace['_icon_helper'](widget,prompt)
    self.assertEqual(widget._last_icon_side,'left')
    model=self.sm.builders['modelV2'].meta
    model.laneChangeState='laneChangeStarting';model.laneChangeDirection='right'
    self.state('recorded','recorded');self.view.update()
    native=SimpleNamespace(text1='Changing Lanes',alert_type='laneChange/warning',status=0)
    widget.native_alert=widget._prev_alert=native
    restored=namespace['replay_get_alert'](widget,self.view)
    self.assertIs(restored,native)
    icon=namespace['_icon_helper'](widget,restored).icon
    self.assertEqual(icon.side,'right');self.assertIs(icon.texture,widget._txt_turn_signal_right)
    self.assertFalse(ui.roadscore_replay_prompt_active)
    self.assertEqual(namespace['replay_arrow_mode'],'recorded')
    # Important native alerts continue to preempt manual simulated arrows.
    self.state('recorded','left');self.view.update()
    native=SimpleNamespace(text1='Recorded critical alert')
    widget.native_alert=widget._prev_alert=native
    self.assertIs(namespace['replay_get_alert'](widget,self.view),native)
    self.assertFalse(ui.roadscore_replay_prompt_active)
    self.assertEqual(namespace['replay_arrow_mode'],'off')
    widget.native_alert=None;widget._alpha_filter.x=1
    self.assertIsNone(namespace['replay_get_alert'](widget,self.view))
    self.assertEqual(namespace['replay_arrow_mode'],'off')
    widget._prev_alert=None;ui.started=False
    self.assertIsNone(namespace['replay_get_alert'](widget,self.view))
    self.assertFalse(ui.roadscore_replay_prompt_active)

if __name__=='__main__':unittest.main()
