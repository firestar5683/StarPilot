import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
import soundfile as sf

from prepared_core import load_archive, initial_frame
from staged_music import digest


class StagedMusicTests(unittest.TestCase):
  def setUp(self):
    temporary = tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup)
    self.root = Path(temporary.name);self.reference = self.root/'reference';self.staged = self.root/'staged'
    self.reference.mkdir();self.staged.mkdir()
    self.launch = dict(route='fixture',render_mode='gold-core',end_reason='native final segment exhausted',
                       native_replay_args=['fixture','--start','149','--data_dir','cache'])
    def save(name, value): (self.reference/name).write_text(json.dumps(value))
    save('launch.json',self.launch)
    save('replay_origin.json',dict(first_model_ns=1000000000,host_received_wall=10.))
    save('audio_blocks.jsonl',dict(audio_s=0.,callback_wall=10.05,dac_delay=.1))
    save('bridge.json',dict(route='fixture',origin_ns=1000000000,last_t=.7,failure=None,messages=10,
                           clock='zero at first model received; source logMonoTime remains unchanged'))
    sf.write(self.reference/'dry.wav',np.ones((48000,2),np.float32)*.1,48000,subtype='FLOAT')
    sf.write(self.staged/'dry.wav',np.ones((48000,2),np.float32)*.2,48000,subtype='FLOAT')
    (self.staged/'launch.json').write_text(json.dumps({**self.launch,'render_mode':'staged-demo-music',
      'mode':'staged-demo','generation_invoked':False,'end_reason':'planned playback against verified route recording'}))
    (self.staged/'rhythm_timeline.json').write_text('[]')
    (self.staged/'provenance.json').write_text(json.dumps(dict(source='standalone recording',seed=33602)))
    self.manifest = dict(version=1,kind='standalone-music-over-replay',route='fixture',reference_alias='route1',
      reference_hashes={name:digest(self.reference/name) for name in ('launch.json','replay_origin.json','audio_blocks.jsonl','bridge.json','dry.wav')})
    self.save_manifest()
    self.catalog = patch('staged_music.entry',return_value=dict(archive=str(self.reference)))
    self.catalog.start();self.addCleanup(self.catalog.stop)

  def save_manifest(self):
    self.manifest['asset_hashes']={name:digest(self.staged/name) for name in ('dry.wav','rhythm_timeline.json','provenance.json')}
    (self.staged/'staged_music.json').write_text(json.dumps(self.manifest))

  def test_independent_music_keeps_verified_route_clock_and_tail(self):
    original = load_archive(self.reference,'fixture')
    audio,rate,meta = load_archive(self.staged,'fixture')
    np.testing.assert_array_equal(audio,np.ones((48000,2),np.float32)*.2)
    self.assertEqual(meta['render_mode'],'staged-demo-music')
    self.assertEqual(meta['archived_tail'],original[2]['archived_tail'])
    self.assertEqual(initial_frame(meta,1000000000,.15,rate),0)
    self.assertFalse(meta['generation_invoked'])
    np.testing.assert_array_equal(load_archive(self.reference,'fixture')[0],original[0])

  def test_wrong_route_and_altered_source_are_rejected(self):
    with self.assertRaises(ValueError):load_archive(self.staged,'other')
    (self.reference/'bridge.json').write_text('{}')
    with self.assertRaisesRegex(ValueError,'reference changed'):load_archive(self.staged,'fixture')

  def test_changed_music_or_provenance_is_rejected(self):
    (self.staged/'provenance.json').write_text('{}')
    with self.assertRaisesRegex(ValueError,'asset changed'):load_archive(self.staged,'fixture')

  def test_different_duration_or_clipping_cannot_bypass_hash_check(self):
    for audio in (np.zeros((24000,2),np.float32),np.ones((48000,2),np.float32)*1.1):
      sf.write(self.staged/'dry.wav',audio,48000,subtype='FLOAT');self.save_manifest()
      with self.assertRaisesRegex(ValueError,'complete replay duration'):load_archive(self.staged,'fixture')

  def test_timing_reference_cannot_be_another_staged_asset(self):
    with patch('staged_music.entry',return_value=dict(archive=str(self.staged))):
      with self.assertRaisesRegex(ValueError,'original route recording'):load_archive(self.staged,'fixture')

  def test_staged_launch_cannot_override_verified_clock(self):
    launch=json.loads((self.staged/'launch.json').read_text())
    launch.update(first_model_ns=99,audio_offset=100,duration=999,host_received_wall=0,archived_tail=None)
    (self.staged/'launch.json').write_text(json.dumps(launch))
    meta=load_archive(self.staged,'fixture')[2]
    original=load_archive(self.reference,'fixture')[2]
    for key in ('first_model_ns','audio_offset','duration','host_received_wall','archived_tail'):
      self.assertEqual(meta[key],original[key])


if __name__=='__main__':unittest.main()
