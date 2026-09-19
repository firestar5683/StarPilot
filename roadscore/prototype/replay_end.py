"""Detect native replay's exhausted final segment, never infer a musical ending.
Native --no-loop waits rather than exiting. Only this presentation supervisor sees
segment bounds; RoadScore continues to receive causal cereal and then plain EOF.
"""
class ReplayEnd:
 def __init__(self):self.position=None;self.changed=None
 def observe(self,state,log_text,wall):
  position=state.get('cur_sec')
  if position is None:return False
  if position!=self.position:self.position=position;self.changed=wall
  waiting=log_text.rfind('waiting for events...')
  return (not state.get('paused',True) and state.get('speed')==1 and position>0
          and position>=state.get('max_sec',float('inf'))-60
          and waiting>=0 and waiting>log_text.rfind('merging segments:')
          and self.changed is not None and wall-self.changed>=1.)
