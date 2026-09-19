import unittest
from overlay_view import gesture_view, EventPresentation, overlay_view

class RenderedCueTests(unittest.TestCase):
 def test_enabled_is_not_audible(self):
  self.assertEqual(gesture_view({'signal_shaker':{'enabled':True,'sequence_active':True,'rendered_active':False}}),('','',None))
 def test_actual_rendered_cues(self):
  for field,kind in [('signal_shaker','turn_signal'),('core_apex','curve_apex'),('alert_accent','native_alert')]:
   self.assertEqual(gesture_view({field:{'enabled':True,'rendered_active':True}})[2],kind)
 def test_engagement_transition_then_recent(self):
  presentation=EventPresentation()
  state={'readiness':'READY','engagement_presentation':{'enabled':True,'input_fresh':True,'rendered_state':'transition','active':True}}
  self.assertEqual(presentation.update(overlay_view(state),1)['event_state'],'active')
  state['engagement_presentation']['rendered_state']='open'
  self.assertEqual(presentation.update(overlay_view(state),2)['event'],'Recent: Engaged')
  self.assertEqual(presentation.update(overlay_view(state),4)['event'],'')

if __name__=='__main__':unittest.main()
