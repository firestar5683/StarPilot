import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'prototype'))
from demo_status import summarize
class ReadinessTests(unittest.TestCase):
 def test_stale_other_worker_link_is_not_ready(self):
  service={'running':True,'phase':'READY','profile':'prism','started_wall':10};worker={'pid':21,'phase':'READY','profile':'prism'};initial={'prepared_profile':'prism','duration':112,'created_wall':11}
  self.assertFalse(summarize(service,worker,initial,{'owner_pid':20,'healthy':True},True,True)['ready_for_replay'])
  self.assertTrue(summarize(service,worker,initial,{'owner_pid':21,'healthy':True},True,True)['ready_for_replay'])
  initial['created_wall']=9
  self.assertFalse(summarize(service,worker,initial,{'owner_pid':21,'healthy':True},True,True)['ready_for_replay'])
 def test_old_initial_buffer_cannot_certify_preparation(self):
  result=summarize({'running':True,'phase':'Preparing','profile':'aurora'},{'pid':21,'phase':'preparing','profile':'aurora'},{'prepared_profile':'prism','duration':112,'created_wall':11},{'owner_pid':21,'healthy':True},False,True)
  self.assertFalse(result['ready_for_replay']);self.assertIsNone(result['accepted_initial_seconds'])
if __name__=='__main__':unittest.main()
