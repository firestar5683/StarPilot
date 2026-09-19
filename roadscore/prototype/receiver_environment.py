"""Explicit, quoted environment crossing the normal Mac/receiver boundary."""
import shlex

KEYS = ('ROADSCORE_PRESENTATION_POLICY', 'ROADSCORE_COMPOSITION_POLICY',
        'ROADSCORE_PLANNER_URL', 'ROADSCORE_PLANNER_TOKEN', 'AM_POWER_LIMIT', 'TC_OPT')

def assignments(env):
    return ''.join(key + '=' + shlex.quote(env[key]) + ' ' for key in KEYS if key in env)

def resolve_compute(env, *, composer, replay=False, judging=False, transport_only=False):
    """Normal event defaults; frozen cohorts and explicit mitigation settings stay intact."""
    normal = composer == 'ace' and not (replay or judging or transport_only)
    if normal:
        env.setdefault('AM_POWER_LIMIT', '100')
        env.setdefault('TC_OPT', '2')
    return {'policy': 'normal-event-100w-v1' if normal else 'preserved-environment',
            'requested_power_limit_watts': env.get('AM_POWER_LIMIT'),
            'tc_opt': env.get('TC_OPT'),
            'actual_power_limit_watts': None}
