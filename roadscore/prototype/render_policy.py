"""Explicit output-only policy; generated ACE PCM already includes its 0.65 gain."""
import os
MODES = ('current', 'gold-core')
def selected(environ=None):
 mode = (os.environ if environ is None else environ).get('ROADSCORE_RENDER_MODE', 'current')
 if mode not in MODES: raise ValueError('Unknown RoadScore rendering mode: ' + mode)
 return mode

def validate(mode, composer, section_bank=False):
 if mode not in MODES: raise ValueError('Unknown RoadScore rendering mode')
 if mode == 'gold-core' and (composer != 'ace' or section_bank):
  raise ValueError('Gold core requires ACE generated audio without the experimental section bank')

def ring_only(mode, musical_mode, ending_start, frames, rate):
 return mode == 'current' and musical_mode and ending_start is not None and frames-ending_start >= rate*.3

def render(mode, chunk, dsp, amount, ending, gestures, cadence, cadence_args):
 if mode == 'gold-core':
  # Unity bypass: do not attenuate the already-scaled source a second time.
  return chunk
 if mode != 'current': raise ValueError('Unknown RoadScore rendering mode')
 rendered = dsp.process(chunk, amount, ending)
 if gestures is not None: rendered = gestures.render(rendered)
 if cadence_args is not None: rendered = cadence(rendered, *cadence_args)
 return rendered
