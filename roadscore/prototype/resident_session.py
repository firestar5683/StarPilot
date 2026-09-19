"""Idle-only resident handoff bound to an exact fresh session and conditioning bank."""
from contextlib import contextmanager
import fcntl
import json
import math
from pathlib import Path
import re
import time
import uuid


@contextmanager
def session_lease(generated):
    with (Path(generated) / 'session.lock').open('a') as handle:
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            yield
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


def session_active(generated):
    try:
        with session_lease(generated):
            return False
    except BlockingIOError:
        return True


def validate_session(request):
    profile = request.get('profile')
    seed = request.get('generation_seed')
    policy = request.get('composition_policy')
    bank = request.get('bank_sha256')
    if profile not in ('prism', 'aurora'):
        raise ValueError('Unsupported resident profile')
    if type(seed) is not int or not 0 <= seed < 2**32:
        raise ValueError('Fresh session seed must be an unsigned 32-bit integer')
    if policy != 'hook-cache-v1':
        raise ValueError('Resident handoff requires hook-cache-v1')
    if not isinstance(bank, str) or re.fullmatch('[0-9a-f]{64}', bank) is None:
        raise ValueError('Resident handoff requires the conditioning bank SHA-256')
    return profile, seed, policy, bank


def request_preparation(generated, profile, seed, composition_policy, bank_sha256, timeout=1560):
    generated = Path(generated)
    selection = {'profile': profile, 'generation_seed': seed,
                 'composition_policy': composition_policy, 'bank_sha256': bank_sha256}
    validate_session(selection)
    if not math.isfinite(timeout) or timeout <= 0:
        raise ValueError('Preparation timeout must be finite and positive')
    with (generated / 'session_command.lock').open('a') as handle:
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        request = generated / 'session_request.json'
        if request.exists():
            raise RuntimeError('An unacknowledged preparation exists; inspect it before retrying')
        if session_active(generated):
            raise RuntimeError('Playback or preparation owns the resident session')
        token = uuid.uuid4().hex
        payload = {'id': token, **selection}
        temporary = request.with_suffix('.tmp')
        temporary.write_text(json.dumps(payload))
        temporary.replace(request)
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            try:
                result = json.loads((generated / 'session_result.json').read_text())
            except (OSError, ValueError):
                result = {}
            if isinstance(result, dict) and result.get('id') == token:
                if result.get('error'):
                    raise RuntimeError(str(result['error']))
                if validate_session(result) != validate_session(selection):
                    raise RuntimeError('Resident acknowledgment belongs to a different session')
                if result.get('phase') != 'READY' or not result.get('preparation_id'):
                    raise RuntimeError('Resident preparation did not report READY with provenance')
                return result
            time.sleep(min(.2, max(0, deadline - time.monotonic())))
        raise TimeoutError('Preparation still pending; do not silently retry or restart')
