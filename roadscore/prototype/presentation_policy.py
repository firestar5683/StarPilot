"""Generic launch presentation policy; never changes composer, seeds or route data."""
import copy
import os

POLICIES = ('conservative-v1', 'off', 'frozen')
CONSERVATIVE = {
 'presentation_policy_version': 'conservative-v1',
 'signal_shaker': {'enabled': True},
 'core_apex': {'enabled': True},
 'engagement_presentation': {'version': 2, 'enabled': True, 'attack_ms': 220, 'release_ms': 650},
}

def select_launch(composer, profile, replay=False, judging=False, render_mode=None, policy=None):
 if policy is not None and policy not in POLICIES:raise ValueError('Unknown presentation policy')
 if render_mode is not None and render_mode not in ('current','gold-core'):raise ValueError('Unknown rendering mode')
 if replay:
  if render_mode not in (None,'current') or policy not in (None,'off'):
   raise ValueError('Stored playback retains recorded presentation; it cannot be remixed by launch flags')
  return {'render_mode':'current','policy':'off'}
 if judging:
  # Existing official cohorts retain the actual frozen files/configuration. A new
  # cohort needs explicit runner/schema binding before adopting a new policy.
  if policy not in (None,'frozen') or render_mode not in (None,'current'):
   raise ValueError('Judging presentation must remain bound to its frozen configuration')
  return {'render_mode':'current','policy':'frozen'}
 normal_prism=composer=='ace' and profile=='prism'
 mode=render_mode or ('gold-core' if normal_prism else 'current')
 chosen=policy or ('conservative-v1' if normal_prism and mode=='gold-core' else 'off')
 if chosen=='conservative-v1' and (composer!='ace' or mode!='gold-core'):
  raise ValueError('Conservative presentation requires ACE gold-core rendering')
 return {'render_mode':mode,'policy':chosen}

def selected(environ=None):
 value=(os.environ if environ is None else environ).get('ROADSCORE_PRESENTATION_POLICY','frozen')
 if value not in POLICIES:raise ValueError('Unknown presentation policy: '+value)
 return value

def effective_config(config,environ=None):
 """Return a copy; never mutate the global runtime file or an archived policy."""
 result=copy.deepcopy(config);policy=selected(environ)
 if policy=='frozen':return result
 if policy=='conservative-v1':result.update(copy.deepcopy(CONSERVATIVE))
 else:
  result.update(presentation_policy_version='off',signal_shaker={'enabled':False},core_apex={'enabled':False},engagement_presentation={'version':2,'enabled':False})
 return result
