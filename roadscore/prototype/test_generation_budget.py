import unittest
from generation_budget import GenerationBudget

class GenerationBudgetTest(unittest.TestCase):
 def test_slow_rejection_then_deadline_deferral_is_not_two_bad_generations(self):
  budget=GenerationBudget()
  rejected={'quality_rejected':True,'quality_stop_reason':'insufficient_playback_buffer','quality_attempts':[{'wall_seconds':44.,'runtime':{'cold':False}}]}
  self.assertFalse(budget.observe(rejected))
  self.assertGreater(budget.required_seconds,44.)
  reserve=budget.required_seconds
  self.assertTrue(budget.observe({'quality_rejected':True,'quality_stop_reason':'insufficient_playback_buffer','quality_attempts':[]}))
  self.assertEqual(budget.required_seconds,reserve)
  # One normal 24s accepted-material hold supplies enough time for another attempt.
  self.assertGreater(44.+24.,reserve)
 def test_cold_compile_does_not_make_every_future_request_impossible(self):
  budget=GenerationBudget()
  budget.observe({'quality_attempts':[{'wall_seconds':309.,'runtime':{'cold':True}}]})
  self.assertLess(budget.required_seconds,90.)
 def test_actual_rejection_is_still_a_quality_failure(self):
  self.assertFalse(GenerationBudget().observe({'quality_rejected':True,'quality_stop_reason':'retry_limit','quality_attempts':[{'wall_seconds':25.,'runtime':{'cold':False}}]}))

if __name__=='__main__':unittest.main()
