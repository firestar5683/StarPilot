"""V4 apex timbre; unchanged causal scheduler and V3 turn signals."""
from musical_gestures_v2 import MusicalGestures as V2
from gesture_bank_v4 import GestureBank
class MusicalGestures(V2):
 def __init__(self,source,rate=48000,bpm=128,origin=0.):
  super().__init__(source,rate,bpm,origin)
  self.bank=GestureBank(source,rate,bpm)
  self.phrases={k:self.bank.phrase(k)[0] for k in self.phrases}
