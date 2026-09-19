import sys,unittest
from pathlib import Path
import numpy as np
P=Path(__file__).resolve().parent;R=P.parents[1]
sys.path.insert(0,str(R/'prototype'));sys.path.insert(0,str(R/'experiments/gestures_v2_20260916'))
from test_v2 import GesturesV2Test
sys.path.insert(0,str(P))
from musical_gestures_v3 import MusicalGestures
from gesture_bank_v2 import GestureBank as V2
class V3Test(GesturesV2Test):
 def make(self):return MusicalGestures(np.random.default_rng(1).normal(0,.03,(96000,2)).astype(np.float32),48000,120)
 def test_impact_energy_increases_without_clipping(self):
  g=self.make();old=V2(np.random.default_rng(1).normal(0,.03,(96000,2)).astype(np.float32),48000,120).phrase('curve_apex')[0];new=g.phrases['curve_apex']
  self.assertGreater(np.sum(new[:24000]**2),np.sum(old[:24000]**2)*2)
  self.assertLess(abs(new).max(),.98)
 def test_bright_activation_is_distinct_from_sustain(self):
  g=self.make();a=g.phrases['turn_signal'];b=g.phrases['turn_signal_sustain'];self.assertFalse(np.array_equal(a,b[:len(a)]));self.assertGreater(abs(a).max(),abs(b).max())
if __name__=='__main__':unittest.main()
