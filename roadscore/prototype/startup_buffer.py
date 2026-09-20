"""Explicit measured event-buffer candidate; frozen cohorts keep their own policy."""
import math


def initial_target(environ, composition_policy, default=112.):
    value = environ.get('ROADSCORE_INITIAL_BUFFER_SECONDS')
    if value is None:
        return default
    if composition_policy != 'hook-cache-v1':
        raise ValueError('Initial buffer override is only supported for local cached planning')
    value = float(value)
    minimum = 35. if environ.get('ROADSCORE_TEST_SHORT_STARTUP') == '1' else 80.
    if not math.isfinite(value) or not minimum <= value <= default:
        raise ValueError('Startup reserve outside supported range (35–112 only for explicit short-startup test; otherwise 80–112)')
    return value


SESSION_PROTOCOL = 2


def session_target(request, composition_policy, fallback=112.):
    """Bound a requested reserve without changing generation/quality policy."""
    if 'initial_buffer_target_seconds' not in request:
        return fallback
    if request.get('session_protocol') != SESSION_PROTOCOL:
        raise ValueError('Per-session buffer target requires resident protocol 2')
    value = request['initial_buffer_target_seconds']
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError('Session buffer target must be numeric seconds')
    return initial_target({'ROADSCORE_INITIAL_BUFFER_SECONDS': value, 'ROADSCORE_TEST_SHORT_STARTUP': '1' if request.get('startup_policy') == 'short-startup-test-v1' else '0'}, composition_policy)


def require_session_protocol(metadata):
    if metadata.get('resident_session_protocol', 0) < SESSION_PROTOCOL:
        raise RuntimeError('Existing worker cannot change its buffer per session; its owner must restart it once with the new code after playback finishes')
