import json, os, tempfile, unittest
from pathlib import Path
from unittest.mock import patch, Mock
import composer_choice as c

class ResidentHandoffTest(unittest.TestCase):
 def check(self, optin, capable, judging=False):
  with tempfile.TemporaryDirectory() as folder:
   root=Path(folder); (root/'generated').mkdir()
   (root/'generated/ace_worker_state.json').write_text(json.dumps({'profile':'prism','generation_seed':1}))
   (root/'generated/ace_initial.json').write_text(json.dumps({'resident_capable':capable}))
   command=Mock(); command.read_bytes.return_value=b'python /worker.py\0'
   env={'ROADSCORE_COMPOSER':'ace','ROADSCORE_RESIDENT':optin,'ROADSCORE_SEED_ORIGIN':'judging-route' if judging else 'fresh-session'}
   with patch.object(c,'ROOT',root),patch.object(c,'worker_path',return_value=Path('/worker.py')),patch.object(Path,'glob',return_value=[command]),patch.dict(os.environ,env),patch('generation_seed.configured_seed',return_value=2),patch('ace_profiles.selected',return_value='prism'):
    c.check_available()
 def test_opted_capable_reaches_authenticated_handoff(self):self.check('1',True)
 def test_no_optin_rejects(self):
  with self.assertRaises(SystemExit):self.check('0',True)
 def test_nonresident_rejects(self):
  with self.assertRaises(SystemExit):self.check('1',False)
 def test_judging_rejects(self):
  with self.assertRaises(SystemExit):self.check('1',True,True)
if __name__=='__main__':unittest.main()
