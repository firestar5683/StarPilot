"""Allocation high-water instrumentation for isolated experiments only."""
from tinygrad.device import Buffer
from tinygrad.helpers import GlobalCounters
peak=0
original=Buffer.allocate
def allocate(self,*args,**kwargs):
 global peak
 result=original(self,*args,**kwargs);peak=max(peak,GlobalCounters.mem_used);return result
Buffer.allocate=allocate
