"""Offline listening experiment: generated-source loops and continuous DSP controls.
No external audio, source separation, event/replay/UI integration, or production service.
"""
import json, time
from pathlib import Path
import numpy as np
import soundfile as sf
from scipy import signal
ROOT=Path('/data/roadscore-feasibility/controllability')
SR=32000
start=time.monotonic()
def load(name):
  x,sr=sf.read(ROOT/f'{name}.wav'); assert sr==SR and x.ndim==1
  return x

def analysis(x):
  f,t,z=signal.stft(x,SR,nperseg=4096,noverlap=3584)
  mag=np.abs(z)
  # Descriptive chroma, not a reliable key detector or a musical-quality metric.
  keep=(f>=65)&(f<2100)
  midi=np.rint(69+12*np.log2(f[keep]/440)).astype(int)
  chroma=np.bincount(midi%12,weights=(mag[keep]**2).mean(axis=1),minlength=12)
  chroma=chroma/(np.linalg.norm(chroma)+1e-12)
  flux=np.maximum(np.diff(np.log1p(mag*100),axis=1),0).mean(axis=0)
  flux=np.maximum(flux-np.median(flux),0)
  rate=SR/512
  corr=signal.correlate(flux,flux,mode='full')[len(flux)-1:]
  candidates=[]
  for k in signal.find_peaks(corr)[0]:
    bpm=60*rate/k
    if 60<=bpm<=160: candidates.append((float(corr[k]/max(corr[0],1e-12)),float(bpm)))
  candidates.sort(reverse=True)
  return {'rms':float(np.sqrt(np.mean(x*x))), 'peak':float(np.max(np.abs(x))),
    'centroid_hz':float((f[:,None]*mag).sum()/max(mag.sum(),1e-12)),
    'high_band_power_fraction':float((mag[f>2000]**2).sum()/max((mag**2).sum(),1e-12)),
    'chroma_unit':chroma.tolist(), 'tempo_candidates':candidates[:5]},flux

def save(name,x):
  assert np.isfinite(x).all()
  # Fixed common gain is used for aligned DSP variants. Any exceptional peak limit is recorded.
  gain=min(1.,.95/max(np.max(np.abs(x)),1e-12))
  sf.write(ROOT/f'{name}.wav',x*gain,SR,subtype='PCM_16')
  return {'seconds':len(x)/SR,'peak_before_limit':float(np.max(np.abs(x))),'file_gain':gain}

metrics={}
for name in ['base','neutral','low','high','release']:
  x=load(name+'_new')
  metrics[name],_=analysis(x)
  target=.10
  matched=x*(target/max(metrics[name]['rms'],1e-12))
  save(name+'_matched',matched)
save('model_variants_comparison',np.concatenate([
  load('neutral_matched'),np.zeros(SR//2),load('low_matched'),np.zeros(SR//2),load('high_matched')]))
base=load('base_full')
base_stats,flux=analysis(base)
# Autocorrelation is ambiguous on short music. Choose strongest candidate only as a loop hypothesis.
tempo_candidates=base_stats['tempo_candidates']
strongest_bpm=tempo_candidates[0][1] if tempo_candidates else 100.
# Use the requested tempo only to choose among strong measured candidates; not as ground truth.
near_requested=[(strength,bpm) for strength,bpm in tempo_candidates
  if abs(bpm-100)<5 and strength>=.8*tempo_candidates[0][0]]
bpm=near_requested[0][1] if near_requested else strongest_bpm
fade=round(.12*SR)
peaks=signal.find_peaks(flux,distance=round(.25*SR/512))[0]*512
def make_loop(tempo):
  length=round(8*60/tempo*SR)
  candidates=[int(p) for p in peaks if p>SR and p+length+fade<len(base)]
  if not candidates: candidates=[SR]
  def seam_cost(p):
    a=base[p:p+fade];b=base[p+length:p+length+fade]
    return float(np.mean((a-b)**2)/(np.mean(a*a+b*b)+1e-12))
  p=min(candidates,key=seam_cost)
  x=base[p:p+length+fade]
  w=.5-.5*np.cos(np.linspace(0,np.pi,fade))
  loop=np.concatenate([x[:fade]*w+x[length:length+fade]*(1-w),x[fade:length]])
  return loop,p,length,seam_cost(p)
loop,p,length,seam_score=make_loop(bpm)
alternative,alternative_start,alternative_length,alternative_cost=make_loop(strongest_bpm)
save('loop_alternative_tempo',np.tile(.78*alternative,4))
# Circular filtering preserves the same source phase and periodic boundary.
def filt(x,cutoff,kind):
  sos=signal.butter(2,cutoff,btype=kind,fs=SR,output='sos')
  return signal.sosfiltfilt(sos,np.tile(x,3))[len(x):2*len(x)]
soft=filt(loop,1500,'lowpass')
bright=filt(loop,2200,'highpass')
low=.52*soft
neutral=.78*loop
high=.95*loop+.22*bright
common_gain=min(1.,.85/max(np.max(np.abs(y)) for y in [low,neutral,high]))
low*=common_gain;neutral*=common_gain;high*=common_gain
files={}
for name,y in [('loop_low',low),('loop_neutral',neutral),('loop_high',high)]:
  files[name]=save(name,np.tile(y,4))
  metrics[name],_=analysis(y)
# One shared phase across 8 repeated phrases; intensity rises and falls continuously.
N=len(loop)*8
t=np.arange(N)/SR
phrase=len(loop)/SR
control=np.interp(t,np.array([0,2,4,5,7,8])*phrase,[0,0,1,1,0,0])
control=control*control*(3-2*control)
l=np.tile(low,8);h=np.tile(high,8)
adaptive=l*(1-control)+h*control
# Add a pitched-source-derived reverse swell before peak; no synth, sample library, or new notes.
swell_len=min(round(1.2*SR),len(loop))
swell=loop[-swell_len:][::-1]*np.linspace(0,1,swell_len)**2*.14*common_gain
peak_sample=4*len(loop)
adaptive[peak_sample-swell_len:peak_sample]+=swell
# Presentation fade at file boundaries only; loop seams remain exposed internally.
adaptive[:1600]*=np.linspace(0,1,1600);adaptive[-1600:]*=np.linspace(1,0,1600)
files['hybrid_tension_release']=save('hybrid_tension_release',adaptive)
# Same passage A/Bs, with common generated prefix retained. Model branches are not crossfade-aligned stems.
for name in ['neutral','low','high']:
  full=load(name+'_full')
  files[name+'_context']=save(name+'_context',full)
# Continuation chain: base (12s), high new (8s), release new (8s).
# Use 120ms aligned overlap in already-shared prefix, preserve timeline duration.
def append_continuation(previous,full,prefix_seconds=8):
  ov=round(.12*SR); boundary=round(prefix_seconds*SR)
  w=.5-.5*np.cos(np.linspace(0,np.pi,ov))
  result=previous.copy()
  result[-ov:]=result[-ov:]*(1-w)+full[boundary-ov:boundary]*w
  return np.concatenate([result,full[boundary:]])
chain=append_continuation(base,load('high_full'))
chain=append_continuation(chain,load('release_full'))
files['model_tension_release_chain']=save('model_tension_release_chain',chain)
for name in ['neutral','low','high']:
  metrics[name]['chroma_cosine_to_base']=float(np.dot(metrics[name]['chroma_unit'],metrics['base']['chroma_unit']))
metrics['release']['chroma_cosine_to_high']=float(np.dot(metrics['release']['chroma_unit'],metrics['high']['chroma_unit']))
result={'analysis_warning':'Short-clip tempo/chroma are descriptive hypotheses, not verified BPM/key or listening quality.',
  'metrics':metrics,'loop':{'bpm_hypothesis':bpm,'beats_assumed':8,'requested_bpm_prior':100,'strongest_autocorrelation_bpm':strongest_bpm,'alternative_period_seconds':alternative_length/SR,'start_seconds':p/SR,'period_seconds':length/SR,
    'overlap_seconds':fade/SR,'seam_cost':seam_score,'common_gain':common_gain,
    'seam_sample_jump':float(abs(loop[-1]-loop[0])),'max_interior_sample_jump':float(np.max(np.abs(np.diff(loop))))},
  'files':files,'elapsed_seconds':time.monotonic()-start}
(ROOT/'arrangement.json').write_text(json.dumps(result,indent=2))
print(json.dumps(result,indent=2))
