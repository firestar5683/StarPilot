"""Same-cycle native source readings and UI-only drawer intent boundaries."""
from dataclasses import replace
from types import SimpleNamespace
import unittest
from unittest.mock import patch,Mock
import pyray as rl
from openpilot.cereal import log, messaging
from openpilot.starpilot.speed_limits.runtime import Runtime
from openpilot.starpilot.speed_limits.runtime_settings import parse
from openpilot.starpilot.ui.tests.test_slc_ui_runtime import START,replay_inputs
from openpilot.starpilot.ui.onroad_state import OnroadState,OnroadInput,SpeedLimitObservation,ObservationKind,speed_limit_from_message
from openpilot.starpilot.ui.presentation import Profile,FontRole
from openpilot.starpilot.ui.onroad_large_widgets import UnifiedSpeedWidget
from openpilot.starpilot.ui.runtime_snapshot import display_message
from openpilot.starpilot.ui.onroad_customization import default_document,validate_document,set_speed_sources
from openpilot.starpilot.ui import clip

class DrawerNativeTest(unittest.TestCase):
  def test_qualified_source_rows_roundtrip_and_do_not_change_selection(self):
    sm,cp=replay_inputs();runtime=Runtime(parse({'SpeedLimitController':True}),session_id='drawer-native')
    out=runtime.step(sm,cp,now_ns=START).message
    with log.Event.from_bytes(out.to_bytes()) as decoded:
      obs=speed_limit_from_message(decoded.slcState)
      rows={row.source:row for row in obs.source_readings}
      self.assertEqual(rows['dashboard'].kind,'valid');self.assertAlmostEqual(rows['dashboard'].speed_mps,25)
      self.assertTrue(rows['dashboard'].enabled);self.assertTrue(rows['map'].enabled)
      self.assertEqual(rows['map'].kind,'unknown');self.assertIsNone(rows['map'].speed_mps)
      self.assertFalse(rows['online'].enabled);self.assertEqual(obs.source,'dashboard')
      self.assertEqual(decoded.slcState.sourceReadings[0].source,'dashboard')
    self.assertEqual(speed_limit_from_message(None).source_readings,())
    empty=messaging.new_message('slcState');self.assertEqual(len(empty.slcState.sourceReadings),0)

  def test_drawer_tap_is_preference_only_and_never_accepts_pending(self):
    obs=SpeedLimitObservation(ObservationKind.VALID,'dashboard',25,session_id='drawer',presentation_id=1)
    state=OnroadState(False,False,20,100,obs);doc=default_document();doc['speedSources']=True
    state=replace(state,customization=doc);emitted=[];touch=OnroadInput(emitted.append,Profile.LARGE)
    touch.drawer_bounds=lambda:rl.Rectangle(264,271,248,215)
    touch.press(400,320,state);touch.release(400,320,state)
    self.assertEqual([(r.kind,r.value) for r in emitted],[('set_speed_sources',False)])
    touch.press(400,150,state);self.assertFalse(touch.claimed)
    pending=replace(state,speed_limit=replace(obs,pending_speed_limit_mps=30,decision_id=2))
    touch.press(400,320,pending);touch.release(400,320,pending);self.assertEqual(len(emitted),1)
    touch.press(400,320,state);touch.release(400,320,replace(state,speed_limit=SpeedLimitObservation()))
    self.assertEqual(len(emitted),1)

  def test_nested_drawer_clip_restores_parent_after_exception(self):
    calls=[]
    with patch.object(rl,'rl_draw_render_batch_active'),patch.object(rl,'begin_scissor_mode',side_effect=lambda *v:calls.append(v)):
      with self.assertRaises(ValueError):
        with clip.clipped(rl.Rectangle(264,271,248,215),rl.Rectangle(30,30,1800,1020)):
          raise ValueError('render failed')
    self.assertEqual(calls,[(264,271,248,215),(30,30,1800,1020)])

  def test_saved_document_flag_is_optional_strict_and_preserved(self):
    doc=default_document();self.assertNotIn('speedSources',validate_document(doc))
    doc['speedSources']=True;self.assertIs(validate_document(doc)['speedSources'],True)
    doc['speedSources']=1
    with self.assertRaises(ValueError):validate_document(doc)

  def test_invalid_saved_layout_is_preserved_without_write(self):
    params=SimpleNamespace(put=lambda *args: self.fail('invalid saved layout overwritten'))
    with patch('openpilot.starpilot.ui.onroad_customization.read_saved',return_value=(b'{broken',True)):
      with self.assertRaises(ValueError):set_speed_sources(params,True)
    with patch('openpilot.starpilot.ui.onroad_customization.read_saved',return_value=(None,False)):
      with self.assertRaises(ValueError):set_speed_sources(params,True)

  def test_expired_producer_and_old_drive_transport_cannot_supply_readings(self):
    sm,cp=replay_inputs();runtime=Runtime(parse({'SpeedLimitController':True}),session_id='drawer-expiry')
    runtime.step(sm,cp,now_ns=START)
    expired=runtime.step(sm,cp,now_ns=START+6_000_000_000).message.slcState
    rows={str(row.source):row for row in expired.sourceReadings}
    self.assertNotEqual(str(rows['dashboard'].observationKind),'valid')
    fresh=SimpleNamespace(logMonoTime={'slcState':START},alive={'slcState':True},valid={'slcState':True},recv_frame={'slcState':2})
    # A dict-backed transport exposes the same freshness fields as SubMaster.
    class Transport(dict):pass
    transport=Transport(slcState=expired)
    for key in ('logMonoTime','alive','valid','recv_frame'):setattr(transport,key,getattr(fresh,key))
    self.assertIsNone(display_message(transport,'slcState',START+200_000_001))
    self.assertIsNone(display_message(transport,'slcState',START,after_frame=2))
    self.assertEqual(speed_limit_from_message(None).source_readings,())

  def test_disabled_and_invalid_rows_have_no_value_or_ui_authority(self):
    sm,cp=replay_inputs();runtime=Runtime(parse({}),session_id='drawer-disabled')
    message=runtime.step(sm,cp,now_ns=START).message.slcState
    self.assertFalse(message.enabled);self.assertTrue(all(not row.enabled for row in message.sourceReadings))
    message.observationKind='valid';message.speedLimit=25;message.sessionId='diagnostic'
    row=message.sourceReadings[0];row.observationKind='valid';row.speedLimit=float('nan')
    rows=speed_limit_from_message(message).source_readings
    self.assertEqual(rows[0].kind,'unknown');self.assertIsNone(rows[0].speed_mps)
    row.observationKind='unknown';row.speedLimit=99
    self.assertIsNone(speed_limit_from_message(message).source_readings[0].speed_mps)

  def test_accepted_source_is_highlighted_instead_of_selected_equal_value_source(self):
    from openpilot.starpilot.ui.onroad_state import SourceReading
    obs=SpeedLimitObservation(ObservationKind.VALID,'vision',25,accepted_source='dashboard',
      source_readings=(SourceReading('dashboard',True,'valid',25),SourceReading('vision',True,'valid',25)))
    state=OnroadState(False,False,20,100,obs)
    drawn=[];fonts=SimpleNamespace(measure=lambda *args:SimpleNamespace(width=20,height=20),
      draw=lambda text,role,*args:drawn.append((text,role)))
    widget=UnifiedSpeedWidget(fonts);widget._draw_source_contents(rl.Rectangle(264,271,248,215),state)
    self.assertIn(('Dashboard',FontRole.BOLD),drawn);self.assertIn(('Vision',FontRole.SEMI_BOLD),drawn)

  def test_actual_custom_right_edge_exposes_no_outside_drawer_touch(self):
    obs=SpeedLimitObservation(ObservationKind.VALID,'dashboard',25,session_id='edge')
    doc=default_document();doc['speedSources']=True;doc['layouts']['large']['cruise_limits']['x']=1654
    state=OnroadState(False,False,20,100,obs,customization=validate_document(doc))
    fonts=SimpleNamespace(measure=lambda *args:SimpleNamespace(width=20,height=20),draw=Mock(),
      vertical_ink=lambda text,role,size:(size*.2,size*.8))
    widget=UnifiedSpeedWidget(fonts);widget._source_session='edge'
    widget._source_drawer.update(True,0);widget._source_drawer.update(True,1)
    with patch.object(widget._source_drawer,'draw_frame'),patch.object(widget._source_drawer,'draw_contents'):
      widget.render(rl.Rectangle(30,30,1800,1020),state)
    bounds=widget.source_bounds();self.assertEqual(bounds.width,0);self.assertEqual(bounds.x,1830)
    emitted=[];touch=OnroadInput(emitted.append,Profile.LARGE);touch.drawer_bounds=widget.source_bounds
    touch.press(1850,320,state);touch.release(1850,320,state);self.assertEqual(emitted,[])
