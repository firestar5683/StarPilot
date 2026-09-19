"""Clock-only output adapter for remote compute. Never opens an audio device."""
import threading,time
from types import SimpleNamespace
import numpy as np
class RenderClock:
 def __init__(self,callback,samplerate,channels,blocksize):
  self.callback=callback;self.rate=samplerate;self.channels=channels;self.block=blocksize;self.stop=threading.Event();self.error=None;self.thread=None
 def __enter__(self):
  self.thread=threading.Thread(target=self.run,daemon=True);self.thread.start();return self
 def run(self):
  period=self.block/self.rate;deadline=time.monotonic();out=np.zeros((self.block,self.channels),np.float32)
  try:
   while not self.stop.wait(max(0,deadline-time.monotonic())):
    now=time.monotonic()
    if now-deadline>period:raise RuntimeError('Remote render clock missed an entire block')
    self.callback(out,self.block,SimpleNamespace(currentTime=now,outputBufferDacTime=now),'render deadline late' if now-deadline>.05 else '')
    deadline+=period
  except Exception as error:self.error=error;self.stop.set()
 def close(self):
  self.stop.set()
  if self.thread:self.thread.join(timeout=5)
 def __exit__(self,*_):self.close()
