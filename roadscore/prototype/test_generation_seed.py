import os
import unittest
from unittest.mock import patch
from generation_seed import configured_seed, sample_seed

class SeedTests(unittest.TestCase):
 def test_legacy_default(self):
  with patch.dict(os.environ,{},clear=True):self.assertIsNone(configured_seed())
 def test_reproducible_and_separated(self):
  self.assertEqual(sample_seed(42,'prepare',0),sample_seed(42,'prepare',0))
  self.assertEqual(len({sample_seed(base,phase,index) for base in [42,43] for phase in ['prepare','continuation'] for index in range(8)}),32)
 def test_invalid_configuration(self):
  for value in ['-1',str(2**32),'nan']:
   with patch.dict(os.environ,ROADSCORE_GENERATION_SEED=value):
    with self.assertRaises(ValueError):configured_seed()
if __name__=='__main__':unittest.main()
