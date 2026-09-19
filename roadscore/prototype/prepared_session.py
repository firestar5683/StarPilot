"""Refuse accidental reuse of a different resident composition."""
import json
import os
from pathlib import Path


def verify(metadata,environ):
 if int(metadata.get('generation_seed',-1))!=int(environ['ROADSCORE_GENERATION_SEED']):raise ValueError('Resident composer belongs to another seed; its owner must finish/release that session')
 if metadata.get('prepared_profile')!=environ.get('ROADSCORE_ACE_PROFILE','prism'):raise ValueError('Resident composer profile differs from this launch')
 if metadata.get('composition_policy','prepared-v1')!=environ.get('ROADSCORE_COMPOSITION_POLICY','prepared-v1'):raise ValueError('Resident composer policy differs from this launch')

if __name__=='__main__':verify(json.loads(Path('/data/roadscore/generated/ace_initial.json').read_text()),os.environ)
