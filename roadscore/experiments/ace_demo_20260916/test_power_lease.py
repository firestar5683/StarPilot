import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'prototype'))
from power_lease import maintain
class CpuLeaseTests(unittest.TestCase):
 def test_screen_off_drift_corrected_only_where_needed(self):
  values={'cpu4':'0','cpu5':'1'};writes=[]
  def write(p,v):values[p]=v;writes.append((p,v))
  self.assertEqual(maintain({'cpu4':'1','cpu5':'1'},lambda:True,values.get,write),['cpu4']);self.assertEqual(writes,[('cpu4','1')])
  self.assertEqual(maintain({'cpu4':'1','cpu5':'1'},lambda:True,values.get,write),[])
 def test_onroad_has_no_writes(self):
  writes=[];self.assertIsNone(maintain({'cpu4':'1'},lambda:False,lambda p:'0',lambda *x:writes.append(x)));self.assertEqual(writes,[])
 def test_transition_onroad_stops_before_next_write(self):
  checks=iter([True,True,False]);writes=[]
  self.assertIsNone(maintain({'cpu4':'1','cpu5':'1'},lambda:next(checks),lambda p:'0',lambda *x:writes.append(x)));self.assertEqual(writes,[('cpu4','1')])
if __name__=='__main__':unittest.main()
