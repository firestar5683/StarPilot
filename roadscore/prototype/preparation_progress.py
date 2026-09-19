"""Read preparation progress only from the current launch's worker evidence."""
import json
import math
from pathlib import Path


def current_progress(path, *, seed, profile, launch_wall):
    path=Path(path)
    try:
        if path.stat().st_mtime < launch_wall:return None
        state=json.loads(path.read_text())
    except (OSError,ValueError):return None
    if not isinstance(state,dict) or state.get('generation_seed')!=seed or state.get('profile')!=profile:return None
    phase=str(state.get('phase','')).upper()
    if phase not in ('PREPARING','READY'):return None
    result={'readiness':'PREPARING','preparation_worker_phase':phase,'preparation_worker_pid':state.get('pid')}
    for source,target in [('accepted_buffer_seconds','buffered'),('initial_buffer_seconds','buffered'),
                          ('first_accepted_audio_seconds','first_accepted_audio_seconds'),('elapsed_seconds','preparation_elapsed_seconds')]:
        value=state.get(source)
        if isinstance(value,(int,float)) and not isinstance(value,bool) and math.isfinite(value) and value>=0:result[target]=value
    # Worker READY means audio is prepared; the launcher still must start replay.
    return result
