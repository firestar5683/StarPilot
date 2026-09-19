"""Optional reproducible sampling, independent of wall time and job filenames."""
import hashlib
import os


def configured_seed(required=False):
    value = os.environ.get('ROADSCORE_GENERATION_SEED')
    if value is None:
        if required:
            raise ValueError("ACE requires a session seed; launch through ./onroad --roadscore or provide an explicit seed")
        return None
    seed = int(value)
    if not 0 <= seed < 2**32:
        raise ValueError('ROADSCORE_GENERATION_SEED must be an unsigned 32-bit integer')
    return seed


def sample_seed(base, phase, index):
    if phase not in ('prepare', 'continuation') or index < 0:
        raise ValueError('Invalid generation seed phase/index')
    key = f'roadscore-sample-v1:{base}:{phase}:{index}'
    return int.from_bytes(hashlib.sha256(key.encode()).digest()[:4], 'big')
