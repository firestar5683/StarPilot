import unittest,json
from pathlib import Path
from presentation_policy import select_launch,effective_config,CONSERVATIVE

class PolicyTests(unittest.TestCase):
 def test_inspectable_fragment_matches_runtime_defaults(self):
  fragment=Path(__file__).resolve().parents[1]/'tools/presentation_conservative_v1.json'
  self.assertEqual(json.loads(fragment.read_text()),CONSERVATIVE)
 def test_normal_prism_gets_integrated_policy_without_extra_flags(self):
  self.assertEqual(select_launch('ace','prism'),{'render_mode':'gold-core','policy':'conservative-v2'})
 def test_explicit_optouts(self):
  self.assertEqual(select_launch('ace','prism',policy='off'),{'render_mode':'gold-core','policy':'off'})
  self.assertEqual(select_launch('ace','prism',render_mode='current'),{'render_mode':'current','policy':'off'})
 def test_stored_and_judging_do_not_inherit_demo_defaults(self):
  self.assertEqual(select_launch('ace','prism',replay=True),{'render_mode':'current','policy':'off'})
  self.assertEqual(select_launch('ace','prism',judging=True),{'render_mode':'current','policy':'frozen'})
  with self.assertRaises(ValueError):select_launch('ace','prism',judging=True,policy='conservative-v1')
  with self.assertRaises(ValueError):select_launch('ace','prism',replay=True,render_mode='gold-core')
 def test_effective_config_does_not_change_generation_or_input(self):
  original={'composition_control':True,'rolling':True,'identity':'kpop_control','custom':{'seed':123}}
  out=effective_config(original,{'ROADSCORE_PRESENTATION_POLICY':'conservative-v1'})
  for key,value in original.items():self.assertEqual(out[key],value)
  self.assertTrue(out['engagement_presentation']['enabled']);self.assertNotIn('signal_shaker',original)
  out['custom']['seed']=9;self.assertEqual(original['custom']['seed'],123)
 def test_frozen_missing_env_and_off_explicit(self):
  original={'signal_shaker':{'enabled':True},'engagement_presentation':{'enabled':True,'version':2}}
  self.assertEqual(effective_config(original,{}),original)
  off=effective_config(original,{'ROADSCORE_PRESENTATION_POLICY':'off'})
  self.assertFalse(off['signal_shaker']['enabled']);self.assertFalse(off['engagement_presentation']['enabled'])
 def test_v2_keeps_frozen_and_legacy_alerts_off(self):
  config={'alert_accent':{'enabled':True}}
  for policy in ('off','conservative-v1'):
   self.assertFalse(effective_config(config,{'ROADSCORE_PRESENTATION_POLICY':policy})['alert_accent']['enabled'])
  latest=effective_config({}, {'ROADSCORE_PRESENTATION_POLICY':'conservative-v2'})
  self.assertTrue(latest['alert_accent']['enabled'])
  self.assertEqual(latest['core_apex']['dip_db'],-3.)
 def test_other_backend_and_legacy_incompatibility(self):
  self.assertEqual(select_launch('sa3','prism'),{'render_mode':'current','policy':'off'})
  with self.assertRaises(ValueError):select_launch('ace','prism',render_mode='current',policy='conservative-v1')
  with self.assertRaises(ValueError):effective_config({}, {'ROADSCORE_PRESENTATION_POLICY':'typo'})
if __name__=='__main__':unittest.main()
