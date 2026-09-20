"""Prepared ACE PCM with the normal real-time presentation layers; no model imports."""
import json
import math
from pathlib import Path

import numpy as np
import soundfile as sf

from alert_accent import AlertAccent
from curve_reaction import CurveReaction
from demo_engagement import presentation_active, presentation_signal, controls_snapshot, annotate
from engagement_presentation import EngagementPresentation, PresentationConfig
from motion_presentation import MotionPresentation
from presentation_policy import effective_config
from rhythm_timeline import RhythmTimeline
from signal_shaker import SignalShaker, ShakerGrid


def load_archive(path, route):
  path = Path(path)
  launch = json.loads((path/'launch.json').read_text())
  origin = json.loads((path/'replay_origin.json').read_text())
  if launch.get('route') != route or launch.get('render_mode') != 'gold-core':
    raise ValueError('Prepared showcase requires matching route and original ACE core render')
  if launch.get('end_reason') != 'native final segment exhausted':
    raise ValueError('Prepared showcase requires a complete route capture')
  with (path/'audio_blocks.jsonl').open() as timing:
    first = json.loads(next(timing))
  values = [first.get('audio_s'), first.get('callback_wall'), first.get('dac_delay'), origin.get('host_received_wall')]
  if not all(type(x) in (int, float) and math.isfinite(x) for x in values) or first['audio_s'] != 0:
    raise ValueError('Prepared core lacks its original sample/DAC clock')
  if type(origin.get('first_model_ns')) is not int or origin['first_model_ns'] <= 0:
    raise ValueError('Prepared core lacks its original model clock')
  audio, rate = sf.read(path/'dry.wav', dtype='float32', always_2d=True)
  if rate != 48000 or audio.shape[1] != 2 or not len(audio) or not np.isfinite(audio).all():
    raise ValueError('Prepared core must be finite stereo 48 kHz PCM')
  offset = first['callback_wall'] + first['dac_delay'] - origin['host_received_wall']
  if abs(offset) > 2:
    raise ValueError('Unexpected original audio clock offset')
  return audio, rate, {**launch, **origin, 'audio_offset': offset, 'duration': len(audio)/rate}


def initial_frame(meta, mono_ns, dac_since_receipt, rate):
  return round(((mono_ns-meta['first_model_ns'])/1e9+dac_since_receipt-meta['audio_offset'])*rate)


class PreparedPresentation:
  """Identical presentation primitives/order to ACE gold-core playback."""
  def __init__(self, archive, rate=48000, policy='conservative-v4'):
    config = effective_config({}, {'ROADSCORE_PRESENTATION_POLICY': policy})
    self.config = PresentationConfig.read(config['engagement_presentation'])
    self.engagement = EngagementPresentation(rate, cutoff_hz=self.config.cutoff_hz, width=self.config.width, gain=self.config.gain)
    self.motion = MotionPresentation(rate, enabled=config.get('stopped_motion', {}).get('enabled', False))
    self.rhythm = RhythmTimeline(rate, None)
    rows = json.loads((Path(archive)/'rhythm_timeline.json').read_text())
    self.rhythm.entries = tuple((int(row['start_frame']), int(row['end_frame']), ShakerGrid(**row['grid'])) for row in rows)
    grid = self.rhythm.at(0)
    self.shaker = SignalShaker(grid, rate, enabled=True, peak=config['signal_shaker'].get('peak', .018))
    self.curve = CurveReaction(grid, rate, enabled=True, bass_build=config.get('curve_reaction', {}).get('bass_build', False))
    self.alert = AlertAccent(grid, rate, enabled=True)
    self.contained_gain = config['signal_shaker'].get('contained_gain', 1.)

  def process(self, pcm, frame, state, selection):
    mode, signal_mode = selection
    active = presentation_active(mode, state['active'])
    signal_on = presentation_signal(signal_mode, state['signal_on'])
    grid = self.rhythm.at(frame)
    self.shaker.set_grid(grid, frame)
    self.curve.grid = self.alert.grid = grid
    competing = self.shaker.active or abs(self.engagement.mix-float(active)) > .01
    result = self.alert.process(pcm, frame, state['alert_key'], state['alert_meaningful'], state['fresh'], competing)
    result = self.curve.process(result, frame, state['curve'], source_fresh=state['model_fresh'], blocked=self.alert.priority_active or (self.motion.stopped and self.motion.fresh))
    result = self.motion.process(result, speed=state['speed'], source_fresh=state['car_fresh'])
    result = self.engagement.process(result, active, self.config)
    gain = self.contained_gain+(1-self.contained_gain)*min(self.engagement.mix, self.motion.dsp.mix)
    shaken = self.shaker.process(result, frame, signal_on, state['car_fresh'], sequence_key=signal_mode, presentation_gain=gain)
    if not self.alert.priority_active:
      result = shaken
    else:
      self.shaker.rendered_active = False
      self.shaker.rendered_peak = 0.
      self.shaker.suppression_reason = 'meaningful alert priority'
    cues = {**state['curve'], 'section': 'PREPARED PRISM', 'replay_demo': controls_snapshot(mode, signal_mode),
            'signal_shaker': self.shaker.snapshot(), 'alert_accent': self.alert.snapshot(),
            **self.motion.snapshot(), **self.curve.snapshot(),
            **annotate(self.engagement.snapshot(self.config, active, state['fresh']), mode, state['active'])}
    return result, cues
