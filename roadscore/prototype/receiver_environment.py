"""Explicit, quoted environment crossing the normal Mac/receiver boundary."""
import shlex

KEYS = ('ROADSCORE_PRESENTATION_POLICY', 'ROADSCORE_COMPOSITION_POLICY',
        'ROADSCORE_PLANNER_URL', 'ROADSCORE_PLANNER_TOKEN', 'AM_POWER_LIMIT', 'TC_OPT')

def assignments(env):
    return ''.join(key + '=' + shlex.quote(env[key]) + ' ' for key in KEYS if key in env)
