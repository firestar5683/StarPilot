"""The runtime's bounded fenced decoder, with submission/readback trace enabled."""
from chunk_decode import FencedChunkDecoder

class ChunkDecoder(FencedChunkDecoder):
 def __init__(self,vae,window=375,core=250):
  def trace(stage,start,n,timeline):
   print('VAE_FENCE',stage,start,'of',n,'timeline',timeline,flush=True)
  super().__init__(vae,window,core,trace=trace)
