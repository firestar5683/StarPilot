#!/usr/bin/env python3
"""Execute actual host shutdown methods with an explicit clock and in-memory Params.
Diagnostic only: no imports of the live application, real Params, or hardware.
Stock timeout, voltage, battery and forced shutdown remain authoritative.
"""
import argparse
import ast
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[3]


def main():
  parser = argparse.ArgumentParser()
  parser.add_argument('--evidence', type=Path, required=True)

  args = parser.parse_args()
  args.evidence.mkdir(parents=True, exist_ok=True)
  path = ROOT/'system/hardware/power_monitoring.py'
  source = path.read_text()
  tree = ast.parse(source)
  cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name=='PowerMonitoring')
  methods = [n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name in ['shutdown_reason','should_shutdown']]
  assert len(methods)==2
  clock = SimpleNamespace(now=0.)
  ns = {'time':SimpleNamespace(monotonic=lambda:clock.now),'SimpleNamespace':SimpleNamespace}
  nodes: list[ast.stmt] = [n for n in tree.body if isinstance(n, ast.Assign)]
  nodes.extend(methods)
  exec(compile(ast.Module(body=nodes,type_ignores=[]),str(path)+':actual-methods','exec'), ns)
  values = {'DisablePowerDown':False,'ForcePowerDown':False}
  pm = SimpleNamespace(low_voltage_start_time=None,car_voltage_mV=14000,car_battery_capacity_uWh=30e6,
      params=SimpleNamespace(get_bool=lambda name:values[name]))
  toggles = SimpleNamespace(device_shutdown_time=3600,low_voltage_shutdown=11.8)
  # Wake is deliberately independent, but not a supported input to this policy.
  pm.wake_on_can = True
  reason = lambda: ns['shutdown_reason'](pm,False,True,1.,False,toggles)
  observed = {}
  for t in range(2,3703):
    clock.now=float(t)
    result = reason()
    if result and 'first_shutdown' not in observed:
      observed['first_shutdown']={'monotonic_s':t,'offroad_s':t-1,'reason':result,'fresh_awake':True}
  assert observed['first_shutdown']=={'monotonic_s':3602,'offroad_s':3601,'reason':'offroad_timeout','fresh_awake':True}
  # The one-hour constant is NOT an unconditional one-hour timeout.
  toggles.device_shutdown_time=0
  assert reason() is None
  observed['no_timeout_healthy_after_hour']=reason()
  # Existing emergency/protective inputs stay intact; never bypass by changing ignition
  # or setting DisablePowerDown to implement stay-awake.
  pm.car_battery_capacity_uWh=0
  assert reason()=='battery_capacity_exhausted'
  observed['exhausted']=reason()
  pm.car_battery_capacity_uWh=30e6; pm.car_voltage_mV=11000
  assert reason() is None
  clock.now+=29; assert reason() is None
  clock.now+=1; assert reason()=='low_voltage'
  observed['low_voltage']=reason()
  values['ForcePowerDown']=True; assert reason()=='forced_power_down'
  observed['forced']=reason()
  values['ForcePowerDown']=False; pm.car_voltage_mV=14000
  toggles.device_shutdown_time=3600
  for awake in [True,False]:
    pm.wake_on_can=awake
    assert reason()=='offroad_timeout' # same answer; no telemetry seam exists yet
  observed['contract']='Wake-only CAN deliberately does not inhibit stock host shutdown.'
  observed['source_sha256']=hashlib.sha256(path.read_bytes()).hexdigest()
  observed['thermal']='Not modeled here; unchanged host thermal protection must be independently preserved in any extension.'
  (args.evidence/'host-policy.json').write_text(json.dumps(observed,indent=2)+'\n')
  print(json.dumps(observed,indent=2))
  print('PASS stock shutdown policy assertions; no live Params or hardware accessed.')


if __name__ == '__main__': main()
