"""One persisted seed decision per normal launch; official judging stays explicit."""
import secrets

MAX_SEED = 2**32


def seed_argument(value):
    try:
        seed = int(value)
    except (TypeError, ValueError) as error:
        raise ValueError('RoadScore seed must be an unsigned 32-bit integer') from error
    if isinstance(value, bool) or str(seed) != str(value) or not 0 <= seed < MAX_SEED:
        raise ValueError('RoadScore seed must be an unsigned 32-bit integer')
    return seed


def select_session(explicit=None, *, judging_seed=None, random_bits=None):
    if judging_seed is not None:
        expected = seed_argument(judging_seed)
        if explicit is None or seed_argument(explicit) != expected:
            raise ValueError('Official judging requires its unchanged route-derived CLI seed')
        seed, origin = expected, 'judging-route'
    elif explicit is not None:
        seed, origin = seed_argument(explicit), 'explicit'
    else:
        seed, origin = (random_bits or secrets.randbits)(32), 'fresh-session'
        seed = seed_argument(seed)
    return {'generation_seed': seed, 'seed_origin': origin,
            'sample_seed_policy': 'roadscore-sample-v1',
            'reproduce_cli': ['--roadscore-seed', str(seed)]}


def seed_environment(session):
    return {'ROADSCORE_GENERATION_SEED': str(session['generation_seed']),
            'ROADSCORE_SEED_ORIGIN': session['seed_origin']}


def remote_assignments(session):
    # Values are constrained to uint32 and the closed origin set above.
    return ' '.join(key + '=' + value for key, value in seed_environment(session).items()) + ' '
