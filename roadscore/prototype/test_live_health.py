import copy
import json
from pathlib import Path
import tempfile
import unittest
from live_health import evaluate,LiveHealth,SERVICES,METRICS


def sample(now=100.):
 return {'monotonic':now,'chestnut_present':True,'ages':{k:.05 for k in SERVICES},'valid':{k:True for k in SERVICES},
  'car':{'canValid':True,'canTimeout':False,'vEgo':0.,'standstill':True},
  'device':{'thermalStatus':'ok'},'pandas':[{'faults':[],'safetyRxChecksInvalid':False,'safetyModel':'tesla'}],
  'calibration':'calibrated','processes':{'modeld':{'running':True},'controlsd':{'running':True}},
  'driving_model_local':True,'model_geometry_valid':True,'metrics':{k:10. for k in METRICS},
  'link':{'healthy':True,'monotonic':99.9},'link_owner_verified':True,'car_id':'car','baseline_id':'build','events':[]}


def authorization():
 return {'schema':'roadscore-live-authorization-v1','measured_parked':True,'car_id':'car','baseline_id':'build',
         'user_authorized':True,'coexistence_verified':True,'bounds':{**{k+'_max':20. for k in METRICS},'link_max_age_s':1.}}


class Tests(unittest.TestCase):
 def test_genuine_bounds_and_authorization(self):
  d=sample();o,a=evaluate(d,authorization(),100.)
  self.assertTrue(o.modeld_healthy and o.device_healthy and o.chestnut_healthy and a.user_authorized)
  self.assertTrue(d['diagnostic_healthy'])
 def test_no_authorization_or_bounds_never_production_ready(self):
  d=sample();o,a=evaluate(d,{},100.)
  self.assertFalse(o.modeld_healthy);self.assertFalse(a.user_authorized);self.assertTrue(d['diagnostic_healthy'])
 def test_identity_mismatch(self):
  r=authorization();r['car_id']='another car';o,_=evaluate(sample(),r,100.);self.assertFalse(o.modeld_healthy)
 def test_invalid_stale_future_services(self):
  for service in SERVICES:
   for change in ('stale','future','invalid'):
    d=sample()
    if change=='invalid':d['valid'][service]=False
    else:d['ages'][service]=3. if change=='stale' else -.01
    o,_=evaluate(d,authorization(),100.)
    self.assertFalse(o.modeld_healthy,(service,change));self.assertFalse(d['diagnostic_healthy'])
 def test_faults_calibration_and_model_placement(self):
  for key,value in [('pandas',[{'faults':['relayMalfunction'],'safetyRxChecksInvalid':False,'safetyModel':'tesla'}]),('calibration','uncalibrated'),('driving_model_local',False),('events',[{'immediateDisable':True}]),('model_geometry_valid',False),('chestnut_present',False)]:
   d=sample();d[key]=value;o,_=evaluate(d,authorization(),100.);self.assertFalse(o.modeld_healthy);self.assertFalse(d['diagnostic_healthy'])
 def test_performance_and_link_regression(self):
  for metric in METRICS:
   d=sample();d['metrics'][metric]=21.;o,_=evaluate(d,authorization(),100.);self.assertFalse(o.modeld_healthy)
  for link in ({'healthy':False,'monotonic':99.9},{'healthy':True,'monotonic':90.},{'healthy':True,'monotonic':101.}):
   d=sample();d['link']=link;o,_=evaluate(d,authorization(),100.);self.assertFalse(o.chestnut_healthy)
 def test_moving_cannot_diagnostic_prepare(self):
  d=sample();d['car']['vEgo']=5.;d['car']['standstill']=False;o,_=evaluate(d,authorization(),100.)
  self.assertFalse(o.parked);self.assertFalse(d['diagnostic_healthy'])
 def test_process_cpu_and_pid_identity(self):
  with tempfile.TemporaryDirectory() as folder:
   root=Path(folder);proc=root/'42';proc.mkdir();(proc/'cmdline').write_bytes(b'python\0/selfdrive/modeld/modeld.py\0')
   fields=['0']*22;fields[0]='S';fields[11]='10';fields[12]='5';fields[19]='100'
   (proc/'stat').write_text('42 (modeld) '+' '.join(fields))
   health=LiveHealth(root,proc=root)
   self.assertEqual(health._cpu(42,'modeld',1.),(None,True))
   import os
   fields[11]=str(10+os.sysconf('SC_CLK_TCK'));(proc/'stat').write_text('42 (modeld) '+' '.join(fields))
   self.assertEqual(health._cpu(42,'modeld',2.),(100.,True))
   fields[19]='200';(proc/'stat').write_text('42 (modeld) '+' '.join(fields))
   self.assertEqual(health._cpu(42,'modeld',3.),(None,True))
   self.assertEqual(health._cpu(42,'controlsd',4.),(None,False))
 def test_reader_failure_is_not_healthy(self):
  with tempfile.TemporaryDirectory() as folder:
   def broken(now):raise OSError('no cereal')
   health=LiveHealth(Path(folder),reader=broken,clock=lambda:100.)
   o,a=health.collect();self.assertFalse(o.modeld_healthy);self.assertFalse(o.car_fresh);self.assertFalse(a.user_authorized)

if __name__=='__main__':unittest.main()
