"""Quality evidence follows the same private route ownership as the final score."""
import unittest,tempfile,json,sys
from pathlib import Path
from unittest.mock import patch
R=Path(__file__).resolve().parents[2];sys.path.insert(0,str(R/'prototype'))
import score_archive
class ArchiveTest(unittest.TestCase):
 def test_attempts_move_with_score(self):
  with tempfile.TemporaryDirectory() as folder:
   root=Path(folder);run=root/'results/normal_test';run.mkdir(parents=True)
   (run/'host_heard.flac').write_bytes(b'fixture')
   (run/'host_audio.jsonl').write_text(json.dumps({'audio_s':0,'host_audio_s':0,'route_t':0})+'\n')
   (run/'host_audio_summary.json').write_text(json.dumps({'first_host_dac_wall':0,'portaudio_flags':0}))
   (run/'quality/job').mkdir(parents=True);(run/'quality/job/attempt_0.json').write_text('{"accepted":false}')
   (run/'quality_events.jsonl').write_text('{"quality_rejected":true}\n')
   (run/'runtime_manifest.json').write_text(json.dumps({'composer':'ace','ace_initial_provenance':{'prepared_profile':'aurora'}}))
   with patch.object(score_archive,'ROOT',root):dest=score_archive.archive('0000000000000000/00000000--0000000000',run)
   self.assertTrue((run/'quality').is_symlink());self.assertEqual((run/'quality').resolve(),(dest/'quality').resolve())
   self.assertEqual((dest/'quality/job/attempt_0.json').read_text(),'{"accepted":false}')
   self.assertTrue((dest/'quality_events.jsonl').exists());self.assertEqual(json.loads((dest/'metadata.json').read_text())['profile'],'aurora')
if __name__=='__main__':unittest.main()
