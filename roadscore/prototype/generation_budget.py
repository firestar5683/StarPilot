"""Track measured generation cost separately from musical rejection."""
class GenerationBudget:
 def __init__(self):self.required_seconds=40.
 def observe(self,result):
  explicit=result.get('minimum_start_buffer_seconds')
  if isinstance(explicit,(int,float)):self.required_seconds=max(40.,float(explicit))
  for attempt in result.get('quality_attempts',[]):
   if not attempt.get('runtime',{}).get('cold',False):
    policy=attempt.get('quality',{}).get('policy',{})
    self.required_seconds=max(float(policy.get('retry_estimate_seconds',30.)),float(attempt['wall_seconds'])*1.2)+float(policy.get('danger_buffer_seconds',10.))
  return bool(result.get('quality_rejected') and result.get('quality_stop_reason')=='insufficient_playback_buffer' and not result.get('quality_attempts'))
