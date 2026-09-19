"""Prepared ACE with a fixed lookahead guard and exact committed-tail continuation.
No route data or future driving inputs enter this policy. The uncommitted model
ending is excluded before choosing the next source prefix, not crossfaded away.
"""
import json
import numpy as np
from ace_runtime import Composer as LegacyComposer
from chunk_decode import FencedChunkDecoder
from window_policy import retained_end
class Composer(LegacyComposer):
 def __init__(self,root,profile='prism'):
  super().__init__(root);self.profile=profile;self.decoder=FencedChunkDecoder(self.vae)
  self.policy=json.loads((self.root/'profiles'/profile/'profile.json').read_text())
 def generate(self,case,seed,previous=None):
  if case not in self.policy['roles']:raise ValueError('Unknown prepared ACE role: '+case)
  wave,latent,stats=super().generate('profiles/'+self.profile+'/'+case,seed,previous)
  seconds=self.policy['roles'][case]['commit_seconds']
  try:frames,endpoint=retained_end(wave,48000,stats['prefix_seconds'],seconds,allow_fade=case=='outro')
  except ValueError as e:
   frames=round(seconds*25);endpoint={'rejected':str(e)};stats['endpoint_error']=str(e)
  seconds=frames/25
  committed=wave[:frames*1920];z=latent[:,:frames]
  prefix=stats['prefix_seconds'];new=seconds-prefix
  if new<=0 or not np.isfinite(committed).all():raise ValueError('Invalid committed ACE window')
  model_seconds=stats['duration'];stats.update(endpoint=endpoint,case=case,prepared_profile=self.profile,model_duration=model_seconds,duration=seconds,discarded_lookahead_seconds=model_seconds-seconds,new_seconds=new,warm_rtf_new_audio=(stats['generation_seconds']+stats['decode_seconds'])/new,continuation_policy='fixed lookahead; next prefix comes from committed latent tail')
  return committed,z,stats
