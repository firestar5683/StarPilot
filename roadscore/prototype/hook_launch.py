"""Automatic Mac planner lifecycle for ordinary remote native sessions."""
import json
import os
from pathlib import Path
import secrets
import subprocess
import time


def enabled(session, replay, composer):
 return bool(session and not replay and composer=='ace' and session['seed_origin']!='judging-route')


def start_planner(launch, env, out, roadscore, bench, native=False):
 if native:
  if not env.get('ROADSCORE_PLANNER_URL') or not env.get('ROADSCORE_PLANNER_TOKEN'):
   raise RuntimeError('Hook composition needs a connected host semantic planner; launch on the Mac or configure its authenticated loopback tunnel')
  return
 assets=Path(env.get('ROADSCORE_ASSETS_ROOT',str(Path.home()/'Desktop/RoadScore')))
 python=Path(env.get('ROADSCORE_PLANNER_PYTHON',str(assets/'experiments/composition_20260916/venv/bin/python')))
 if not python.is_file():raise RuntimeError('Existing Mac ACE preparation environment missing: '+str(python))
 env['ROADSCORE_PLANNER_TOKEN']=secrets.token_urlsafe(32)
 ready=out/'planner_ready.json'
 planner=launch([str(python),str(roadscore/'prototype/hook_service.py'),'--assets-root',str(assets),'--cache',str(assets/'cache/hook-plans-v2'),'--ready',str(ready)],'semantic_planner')
 deadline=time.monotonic()+300
 while not ready.exists():
  if planner.poll() is not None or time.monotonic()>deadline:raise RuntimeError('Host semantic planner failed; see semantic_planner.log')
  time.sleep(.1)
 port=int(json.loads(ready.read_text())['port']);remote_port=int(env.get('ROADSCORE_PLANNER_REMOTE_PORT','8767'))
 tunnel=launch(['ssh','-T','-o','ExitOnForwardFailure=yes','-o','ServerAliveInterval=15','-R',f'127.0.0.1:{remote_port}:127.0.0.1:{port}',bench,'printf "PLANNER_TUNNEL_READY\\n"; cat'],'semantic_tunnel',stdin=subprocess.PIPE)
 deadline=time.monotonic()+30
 while b'PLANNER_TUNNEL_READY' not in (out/'semantic_tunnel.log').read_bytes():
  if tunnel.poll() is not None or time.monotonic()>deadline:raise RuntimeError('Exclusive planner tunnel unavailable; see semantic_tunnel.log')
  time.sleep(.1)
 env['ROADSCORE_PLANNER_URL']=f'http://127.0.0.1:{remote_port}'
