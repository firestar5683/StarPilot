"""Validate imported PCM extent without loading a composer or contacting a device."""
import json
import math
from pathlib import Path


def replay_archive(score, route, explicit_start=None):
    import soundfile as sf
    score = Path(score)
    meta = json.loads((score / 'metadata.json').read_text())
    if meta.get('route') != route:
        raise ValueError('Stored score belongs to a different route')
    if meta.get('first_model_ns') is None:
        raise ValueError('Stored score lacks its measured route clock')
    offset = meta.get('audio_file_start_relative_first_model')
    if not isinstance(offset, (int, float)) or not math.isfinite(offset):
        raise ValueError('Stored score lacks its measured audio clock')
    info = sf.info(score / 'score.flac')
    if info.frames <= 0:
        raise ValueError('Stored score is empty')
    start = meta.get('replay_start_seconds', 0) if explicit_start is None else explicit_start
    if not isinstance(start, int) or start < 0:
        raise ValueError('Stored replay start must be a nonnegative integer')
    # Allow replay startup plus the entire captured tail, including positive DAC delay.
    return start, info.duration + abs(offset) + max(0, meta.get('replay_start_seconds',0) - start) + 90
