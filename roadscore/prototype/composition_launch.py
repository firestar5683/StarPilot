"""Choose explicit native cached planning without substituting legacy conditioning."""
from pathlib import Path
from hook_launch import enabled


def configure(session, replay, composer, *, native, transport_only, environ, root):
    if transport_only or not enabled(session, replay, composer):
        return 'prepared-v1'
    if not native:
        return 'hook-v2'
    bank = Path(environ.get('ROADSCORE_PLAN_BANK', '/data/roadscore-event-assets/conditioning/current'))
    from cached_composition import validate_bank
    validate_bank(bank, profile=environ.get('ROADSCORE_ACE_PROFILE', 'prism'))
    environ['ROADSCORE_PLAN_BANK'] = str(bank.resolve())
    environ.pop('ROADSCORE_PLANNER_URL', None)
    environ.pop('ROADSCORE_PLANNER_TOKEN', None)
    return 'hook-cache-v1'
