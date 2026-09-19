"""Optional beat-locked signal-sequence shaker. No per-blink/sample randomization."""
from dataclasses import dataclass, asdict
import math,re
import numpy as np
from bar_grid import grid as estimate_grid

@dataclass(frozen=True)
class ShakerGrid:
 bpm: float
 beat_phase: float
 tempo_confidence: float
 phase_confidence: float
 coherent: bool
 reason: str
 confirmed: bool = False
 @property
 def usable(self):
  return (math.isfinite(self.bpm) and 60 <= self.bpm <= 200 and math.isfinite(self.beat_phase)
          and (self.confirmed or (self.coherent and self.tempo_confidence >= .3 and self.phase_confidence >= .35)))

def profile_tempo_prior(manifest):
 match=re.search(r"(?<![0-9.])([0-9]+(?:\.[0-9]+)?)\s*BPM",str(manifest.get("style","")),re.IGNORECASE)
 value=float(match.group(1)) if match else None
 return value if value is not None and 60<=value<=200 else None

def assess_grid(wave, rate, bpm_prior=None):
 """Assess once outside callback. Conflicting acoustic tempo wins a veto, not a guessed beat."""
 if len(wave)<30*rate:return ShakerGrid(128.,0.,0.,0.,False,'insufficient audio for grid'),{}
 g=estimate_grid(wave[:30*rate],rate,bpm_prior)
 best=max(x['autocorrelation'] for x in g['tempo_candidates'])
 agreement=g['pulse_confidence']/max(best,1e-9)
 # Bar accent confidence is not beat-phase confidence. Compare phase of two halves.
 a=estimate_grid(wave[:15*rate],rate,g['bpm']);b=estimate_grid(wave[15*rate:30*rate],rate,g['bpm'])
 period=60/g['bpm'];drift=abs(((b['beat_phase']+15-a['beat_phase']+period/2)%period)-period/2)
 phase=max(0.,1.-drift/(period*.25))
 coherent=bpm_prior is not None and agreement>=.85 and abs(g['bpm']/bpm_prior-1)<.08 and abs(a['bpm']/b['bpm']-1)<.03
 reason='coherent estimated pulse; downbeat unverified' if coherent else 'tempo/phase ambiguity; rhythmic additions bypassed'
 return ShakerGrid(g['bpm'],g['beat_phase'],g['pulse_confidence'],phase,coherent,reason),{**g,'acoustic_agreement':agreement,'phase_drift_seconds':drift,'phase_confidence':phase}

class SignalShaker:
 def __init__(self,grid,rate=48000,enabled=False,peak=.012,debounce_seconds=1.2):
  self.grid=grid;self.rate=rate;self.enabled=enabled;self.peak=min(.02,max(0.,float(peak)))
  self.debounce=round(debounce_seconds*rate);self.release=round(.16*rate)
  self.last_on=None;self.active=False;self.next_tick=None;self.stop_frame=None;self.tail=np.zeros((0,2),np.float32)
  self.sequence_pulses=0;self.sequence_start=0
  self.rendered_active=False;self.rendered_peak=0.;self.rendered_start=0;self.rendered_end=0
  self.sequence_starts=[];self.pulse_frames=[];self.events=[]
  # Fixed filtered grains, prepared before audio. No callback RNG or file/FFT operations.
  n=round(.085*rate);t=np.arange(n)/rate;rng=np.random.default_rng(1701)
  noise=rng.standard_normal(n);freq=np.fft.rfftfreq(n,1/rate);spectrum=np.fft.rfft(noise)
  spectrum*=np.clip((freq-2300)/1000,0,1)*np.clip((11500-freq)/3000,0,1)
  grain=np.fft.irfft(spectrum,n);env=(1-np.exp(-t/.004))*np.exp(-t/.022)
  grain=grain*env;grain/=max(abs(grain).max(),1e-9)
  self.grain=np.column_stack((grain,grain)).astype(np.float32)*self.peak
  self.step=rate*60/grid.bpm/2 if grid.usable else 1.;self.origin=grid.beat_phase*rate
 def process(self,pcm,start_frame,signal_on,signal_fresh):
  self.rendered_active=False;self.rendered_peak=0.;self.rendered_start=start_frame;self.rendered_end=start_frame+len(pcm)
  if not self.enabled or not self.grid.usable:return pcm
  end=start_frame+len(pcm)
  if signal_fresh and signal_on:
   self.last_on=start_frame
   if not self.active:
    self.active=True;self.stop_frame=None;self.sequence_pulses=0;self.sequence_start=start_frame
    tick=math.ceil((start_frame-self.origin)/self.step-1e-10);self.next_tick=tick
    self.sequence_starts.append(start_frame);self.events.append({'kind':'sequence_start','frame':start_frame,'next_pulse_frame':round(self.origin+tick*self.step)})
  if self.active and (not signal_fresh or (self.last_on is not None and start_frame-self.last_on>self.debounce)):
   self.active=False;self.stop_frame=start_frame;self.events.append({'kind':'release','frame':start_frame})
  overlay=np.zeros((len(pcm),2),np.float32)
  take=min(len(pcm),len(self.tail));overlay[:take]+=self.tail[:take];self.tail=self.tail[take:].copy()
  while self.active and self.sequence_pulses<32 and round(self.origin+self.next_tick*self.step)<end:
   frame=round(self.origin+self.next_tick*self.step);self.next_tick+=1
   if frame<start_frame:continue
   gain=1. if self.next_tick%2 else .65;grain=self.grain*gain;offset=frame-start_frame;count=min(len(grain),len(pcm)-offset)
   overlay[offset:offset+count]+=grain[:count]
   if count<len(grain):
    rest=grain[count:];new=np.zeros((max(len(rest),len(self.tail)),2),np.float32);new[:len(self.tail)]+=self.tail;new[:len(rest)]+=rest;self.tail=new
   self.pulse_frames.append(frame);self.sequence_pulses+=1
  if self.stop_frame is not None:
   envelope=np.clip(1-(np.arange(start_frame,end)-self.stop_frame)/self.release,0,1).astype(np.float32)
   overlay*=envelope[:,None]
  self.rendered_peak=float(np.max(np.abs(overlay),initial=0));self.rendered_active=self.rendered_peak>0
  if not self.rendered_active:return pcm
  return pcm+overlay
 def snapshot(self):
  return {'rendered_active':self.rendered_active,'rendered_peak':self.rendered_peak,'rendered_block_start_seconds':self.rendered_start/self.rate,'rendered_block_end_seconds':self.rendered_end/self.rate,'enabled':self.enabled,'grid':asdict(self.grid),'rhythm_enabled':self.enabled and self.grid.usable,'uncertain_policy':'no added pulses','sequence_active':self.active,'peak_limit':self.peak,'subdivision':'eighth notes','debounce_seconds':self.debounce/self.rate,'maximum_pulses_per_sequence':32}
