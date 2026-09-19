"""Conservative pre-commit energy gate. No route reads, device access or playback.
Measure a neutral preview through the existing output gain/DSP, without route events.
"""
from dataclasses import dataclass,asdict
import time,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'prototype'))
from musical import MusicalDSP
import numpy as np

@dataclass(frozen=True)
class QualityPolicy:
 version: str = 'prism-precommit-v2'
 output_gain: float = .65
 energy_domain: str = 'neutral MusicalDSP preview; no gesture or route input'
 window_seconds: float = .1
 quiet_cap: float = .003
 quiet_relative: float = .025
 quiet_floor: float = .0002
 max_quiet_seconds: float = 2.
 collapse_relative: float = .035
 collapse_cap: float = .01
 max_collapse_seconds: float = 4.
 outro_leading_limit_seconds: float = 6.
 max_rerolls: int = 2
 retry_estimate_seconds: float = 30.
 danger_buffer_seconds: float = 10.
 request_buffer_seconds: float = 90.
 initial_buffer_seconds: float = 112.
POLICY=QualityPolicy()

def spans(mask,step):
 result=[];start=None
 for i,value in enumerate(list(mask)+[False]):
  if value and start is None:start=i
  if not value and start is not None:result.append([round(start*step,4),round(i*step,4)]);start=None
 return result

def inspect(wave,rate,prefix_seconds,*,role='verse',policy=POLICY,endpoint_error=None):
 a=np.asarray(wave);start=round(prefix_seconds*rate);new=a[start:];reasons=[]
 result={'policy':asdict(policy),'role':role,'prefix_seconds':prefix_seconds,'committed_seconds':len(a)/rate,'new_seconds':len(new)/rate,'accepted':False,'reasons':reasons}
 if a.ndim!=2 or not len(new) or not np.isfinite(a).all():reasons.append('invalid_or_nonfinite_pcm');return result
 # Include retained context only to initialize the causal filter, then inspect new PCM.
 preview=MusicalDSP(rate).process(a*policy.output_gain,0.)
 new=preview[start:]
 size=round(rate*policy.window_seconds)
 def energy(x):
  if len(x)<size:return np.array([],dtype=float)
  x=np.asarray(x[:len(x)//size*size],dtype=np.float64).reshape(-1,size,a.shape[1]);centered=x-x.mean(axis=1,keepdims=True)
  return np.sqrt(np.mean(centered*centered,axis=(1,2)))
 e=energy(new);source=energy(preview[:start]);current=float(np.quantile(e,.8)) if len(e) else 0.;previous=float(np.quantile(source,.6)) if len(source) else current
 # A uniformly soft musical passage supplies its own scale; a loud source alone
 # cannot classify the entire following sparse section as a dropout.
 reference=min(current,max(previous*1.25,.001)) if len(source) else current
 quiet=max(policy.quiet_floor,min(policy.quiet_cap,reference*policy.quiet_relative));collapse=min(policy.collapse_cap,reference*policy.collapse_relative)
 q=spans(e<quiet,policy.window_seconds);c=spans(e<collapse,policy.window_seconds)
 longest=max([b-a for a,b in q],default=0.);leading=q[0][1] if q and q[0][0]==0 else 0.
 result.update(source_energy_rms=previous,new_energy_rms_p80=current,reference_rms=reference,quiet_threshold=quiet,collapse_threshold=collapse,quiet_spans_new_seconds=q,collapse_spans_new_seconds=c,longest_quiet_seconds=longest,leading_quiet_seconds=leading,energy_windows_rms=e.tolist(),dc_removed_for_energy=True)
 # A quiet interval can straddle a measurement window; reserve one window
 # so a nominal two-second gap does not evade the gate through block alignment.
 result['quiet_span_uncertainty_seconds']=policy.window_seconds
 if role=='outro':
  if leading>=min(policy.outro_leading_limit_seconds,len(new)/rate*.5):reasons.append('outro_silent_before_final_phrase')
 else:
  if longest>0 and longest+policy.window_seconds>=policy.max_quiet_seconds-1e-6:reasons.append('multi_second_near_silence')
  if max([b-a for a,b in c],default=0.)>=policy.max_collapse_seconds-1e-6:reasons.append('severe_energy_collapse')
  if endpoint_error:reasons.append('unusable_terminal_endpoint')
 if not len(e) or float(max(e,default=0))<policy.quiet_floor:reasons.append('no_musical_energy')
 result['accepted']=not reasons
 return result

def reroll_seed(seed,attempt):
 return (int(seed)+0x9E3779B9*attempt)%(2**32)

class QualifiedGenerator:
 """Bounded same-role retries with a monotonic playback deadline supplied by caller."""
 def __init__(self,generate,policy=POLICY,clock=time.monotonic):
  self.generate=generate;self.policy=policy;self.clock=clock;self.estimate=policy.retry_estimate_seconds
 def run(self,role,seed,previous=None,*,deadline=None,record=None):
  attempts=[];started=self.clock();stop_reason='retry_limit'
  for attempt in range(self.policy.max_rerolls+1):
   remaining=None if deadline is None else deadline-self.clock()
   if remaining is not None and remaining<self.estimate+self.policy.danger_buffer_seconds:
    stop_reason='insufficient_playback_buffer';break
   chosen=reroll_seed(seed,attempt);t=self.clock();wave,latent,stats=self.generate(role,chosen,previous)
   elapsed=self.clock()-t
   if not stats.get('cold'):self.estimate=max(self.policy.retry_estimate_seconds,elapsed*1.2)
   quality=inspect(wave,48000,stats['prefix_seconds'],role=role.removeprefix('repaint_'),policy=self.policy,endpoint_error=stats.get('endpoint_error'))
   if not np.isfinite(latent).all():quality['accepted']=False;quality['reasons'].append('nonfinite_latents')
   row={'attempt':attempt,'seed':chosen,'role':role,'wall_seconds':elapsed,'remaining_buffer_before':remaining,'remaining_buffer_after':None if deadline is None else deadline-self.clock(),'quality':quality,'runtime':stats}
   if record:row['artifacts']=record(attempt,wave,latent,row)
   attempts.append(row)
   if quality['accepted']:
    return wave,latent,{**stats,'original_seed':int(seed),'accepted_seed':chosen,'quality_attempts':attempts,'quality_rejections':attempt,'rerolls':attempt,'qualified_wall_seconds':self.clock()-started,'quality_accepted':True}
  return None,None,{'quality_accepted':False,'quality_rejected':True,'original_seed':int(seed),'accepted_seed':None,'quality_attempts':attempts,'quality_rejections':len(attempts),'rerolls':max(0,len(attempts)-1),'qualified_wall_seconds':self.clock()-started,'quality_stop_reason':stop_reason,'safe_action':'retain accepted generated music; no rejected PCM may be committed'}
