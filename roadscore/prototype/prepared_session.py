"""Refuse accidental reuse of a different resident composition."""
import json
import os
from pathlib import Path
from startup_buffer import initial_target,require_session_protocol,SESSION_PROTOCOL


def verify(metadata,environ):
 if 'ROADSCORE_INITIAL_BUFFER_SECONDS' in environ:
  target=initial_target(environ,environ.get('ROADSCORE_COMPOSITION_POLICY','prepared-v1'))
  if metadata.get('initial_buffer_target_seconds')!=target:raise ValueError('Prepared audio buffer target differs from requested session')
 if metadata.get('resident_capable') and environ.get('ROADSCORE_RESIDENT')!='1':raise ValueError('Resident service requires an opted-in fresh handoff and playback lease')
 if int(metadata.get('generation_seed',-1))!=int(environ['ROADSCORE_GENERATION_SEED']):raise ValueError('Resident composer belongs to another seed; its owner must finish/release that session')
 if metadata.get('prepared_profile')!=environ.get('ROADSCORE_ACE_PROFILE','prism'):raise ValueError('Resident composer profile differs from this launch')
 if metadata.get('composition_policy','prepared-v1')!=environ.get('ROADSCORE_COMPOSITION_POLICY','prepared-v1'):raise ValueError('Resident composer policy differs from this launch')


def requested_buffer(metadata,environ):
 if 'ROADSCORE_INITIAL_BUFFER_SECONDS' not in environ:return None
 target=initial_target(environ,environ['ROADSCORE_COMPOSITION_POLICY'])
 if metadata.get('resident_session_protocol',0)>=SESSION_PROTOCOL:return target
 if metadata.get('initial_buffer_target_seconds')==target:return None
 require_session_protocol(metadata)
 return target

if __name__=='__main__':
 generated=Path('/data/roadscore/generated')
 metadata=json.loads((generated/'ace_initial.json').read_text())
 if os.environ.get('ROADSCORE_PREPARE_RESIDENT')=='1':
  if not metadata.get('resident_capable'):raise RuntimeError('Existing worker does not support resident handoff')
  from cached_composition import validate_bank,digest
  from resident_session import request_preparation
  bank=Path(os.environ['ROADSCORE_PLAN_BANK']);profile=os.environ.get('ROADSCORE_ACE_PROFILE','prism')
  validate_bank(bank,profile)
  request_preparation(generated,profile,int(os.environ['ROADSCORE_GENERATION_SEED']),os.environ['ROADSCORE_COMPOSITION_POLICY'],digest(bank/'bank.json'),initial_buffer_seconds=requested_buffer(metadata,os.environ),short_startup_test=os.environ.get('ROADSCORE_TEST_SHORT_STARTUP')=='1')
  metadata=json.loads((generated/'ace_initial.json').read_text())
 verify(metadata,os.environ)
