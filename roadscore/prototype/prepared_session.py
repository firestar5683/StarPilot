"""Refuse accidental reuse of a different resident composition."""
import json
import os
from pathlib import Path


def verify(metadata,environ):
 if metadata.get('resident_capable') and environ.get('ROADSCORE_RESIDENT')!='1':raise ValueError('Resident service requires an opted-in fresh handoff and playback lease')
 if int(metadata.get('generation_seed',-1))!=int(environ['ROADSCORE_GENERATION_SEED']):raise ValueError('Resident composer belongs to another seed; its owner must finish/release that session')
 if metadata.get('prepared_profile')!=environ.get('ROADSCORE_ACE_PROFILE','prism'):raise ValueError('Resident composer profile differs from this launch')
 if metadata.get('composition_policy','prepared-v1')!=environ.get('ROADSCORE_COMPOSITION_POLICY','prepared-v1'):raise ValueError('Resident composer policy differs from this launch')

if __name__=='__main__':
 generated=Path('/data/roadscore/generated')
 metadata=json.loads((generated/'ace_initial.json').read_text())
 if os.environ.get('ROADSCORE_PREPARE_RESIDENT')=='1':
  if not metadata.get('resident_capable'):raise RuntimeError('Existing worker does not support resident handoff')
  from cached_composition import validate_bank,digest
  from resident_session import request_preparation
  bank=Path(os.environ['ROADSCORE_PLAN_BANK']);profile=os.environ.get('ROADSCORE_ACE_PROFILE','prism')
  validate_bank(bank,profile)
  request_preparation(generated,profile,int(os.environ['ROADSCORE_GENERATION_SEED']),os.environ['ROADSCORE_COMPOSITION_POLICY'],digest(bank/'bank.json'))
  metadata=json.loads((generated/'ace_initial.json').read_text())
 verify(metadata,os.environ)
