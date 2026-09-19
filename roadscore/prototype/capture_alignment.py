"""Sample-zero timing for fresh or stored normal UI captures."""
import json
from pathlib import Path

def audio_alignment(run, video_origin):
    run = Path(run)
    fresh = run / 'host_audio_summary.json'
    if fresh.exists():
        summary = json.loads(fresh.read_text())
        origin = summary.get('first_host_dac_wall')
        if origin is None or summary.get('errors'):
            raise ValueError('Fresh audio has no valid DAC timeline')
        score = run / 'host_heard.flac'
        start = video_origin - origin
        kind = 'fresh PCM capture DAC origin'
    else:
        summary = json.loads((run / 'stored_summary.json').read_text())
        origin = summary.get('first_dac_wall')
        if origin is None:
            raise ValueError('Stored audio has no DAC timeline')
        score = Path(summary['score']) / 'score.flac'
        start = summary['source_frame_start'] / 48000 + video_origin - origin
        kind = 'stored score DAC origin'
    if not score.is_file():
        raise FileNotFoundError(score)
    return score, start, summary['muted'], kind


def video_frames(run, frames):
    """Trim preparation using the recorded host capture interval, never a manual offset."""
    fresh = Path(run) / 'host_audio_summary.json'
    if not fresh.exists():
        return list(range(len(frames)))
    summary = json.loads(fresh.read_text())
    start = summary['first_host_dac_wall']
    end = start + summary['host_frames'] / 48000
    selected = [i for i, frame in enumerate(frames) if start <= frame['wall'] <= end]
    if len(selected) < 2:
        raise ValueError('Insufficient UI/audio timeline overlap')
    return selected
