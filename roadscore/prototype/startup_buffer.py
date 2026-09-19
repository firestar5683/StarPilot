"""Explicit measured event-buffer candidate; frozen cohorts keep their own policy."""
import math


def initial_target(environ, composition_policy, default=112.):
    value = environ.get('ROADSCORE_INITIAL_BUFFER_SECONDS')
    if value is None:
        return default
    if composition_policy != 'hook-cache-v1':
        raise ValueError('Initial buffer override is only supported for local cached planning')
    value = float(value)
    if not math.isfinite(value) or not 80 <= value <= default:
        raise ValueError('Validated candidate range is 80 to 112 seconds')
    return value
