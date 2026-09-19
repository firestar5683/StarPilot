"""Read-only audio screening and local listening page for every validation session."""
import argparse
import hashlib
import html
import json
from pathlib import Path

import numpy as np
from scipy.io import wavfile
from scipy.signal import resample_poly, stft


def load(path):
  rate, pcm = wavfile.read(path)
  if np.issubdtype(pcm.dtype, np.integer):
    pcm = pcm.astype(np.float64) / (2 ** (np.iinfo(pcm.dtype).bits - 1))
  return rate, np.asarray(pcm, dtype=np.float64)


def rms(x):
  return float(np.sqrt(np.mean(np.square(x)))) if x.size else 0.


def screen(path):
  rate, pcm = load(path)
  if not np.isfinite(pcm).all():
    return {'file': path.name, 'error': 'Non-finite samples'}
  mono = pcm.mean(axis=1) if pcm.ndim > 1 else pcm
  hop = rate // 10
  levels = np.array([rms(pcm[i:i+hop]) for i in range(0, len(pcm), hop)])
  quiet = levels < 1e-4
  longest = count = 0
  for value in quiet:
    count = count + 1 if value else 0
    longest = max(longest, count)
  fingerprints = {}
  duplicates = []
  for i in range(0, len(pcm) - rate + 1, rate):
    block = pcm[i:i+rate]
    if rms(block) < 1e-4:
      continue
    digest = hashlib.sha256(block.tobytes()).hexdigest()
    if digest in fingerprints:
      duplicates.append([fingerprints[digest], i/rate])
    else:
      fingerprints[digest] = i/rate
  down = resample_poly(mono, 1, 4) if rate == 48000 else mono
  sr = rate // 4 if rate == 48000 else rate
  length = 4 * sr
  phrases = [down[i:i+length] for i in range(0, len(down)-length+1, length)]
  best = None
  for i, left in enumerate(phrases):
    for j in range(i+2, len(phrases)):
      right = phrases[j]
      norm = np.linalg.norm(left) * np.linalg.norm(right)
      score = float(np.dot(left, right) / norm) if norm > 1e-9 else 0.
      if best is None or abs(score) > abs(best['correlation']):
        best = dict(start_seconds=[i*4, j*4], correlation=score)
  frequencies, _, spectrum = stft(down, fs=sr, nperseg=2048, noverlap=1536)
  power = np.abs(spectrum) ** 2
  mean_power = power.mean(axis=1)
  centroid = float(np.dot(frequencies, mean_power) / max(mean_power.sum(), 1e-15))
  return dict(file=path.name, sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
              seconds=len(pcm)/rate, rate=rate, frames=len(pcm), peak=float(np.max(abs(pcm))),
              rms=rms(pcm), samples_at_or_above_full_scale=int(np.count_nonzero(abs(pcm) >= 1)),
              samples_above_0999=int(np.count_nonzero(abs(pcm) >= .999)),
              silence_fraction_100ms=float(quiet.mean()), longest_quiet_seconds=longest*.1,
              exact_repeated_nonsilent_1s_blocks=duplicates,
              strongest_aligned_4s_waveform_match=best, spectral_centroid_hz=centroid)


def main():
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument('directory', type=Path)
  args = parser.parse_args()
  root = args.directory
  validation = json.loads((root / 'validation.json').read_text())
  report = {'scope': 'All sessions retained, original samples/gain unchanged; no listening judgment.',
            'limits': 'Silence is channel-combined RMS below -80 dBFS in 100ms blocks. Repetition compares exact non-silent 1s blocks and zero-lag 4s waveform blocks; it does not measure memorable melody, shifted phrases, or musical quality. RMS/centroid section contrast can reflect level/timbre alone.',
            'sessions': []}
  cards = []
  for number, seed in enumerate(validation['sessions'], 1):
    folder = root / f'session_{number}'
    core = folder / 'core.wav'
    windows = sorted(folder.glob('[0-9][0-9]_*.wav'))
    entry = {'session': number, 'seed': seed['generation_seed'], 'complete_core_available': core.exists(),
             'windows': [screen(p) for p in windows]}
    entry['section_contrast'] = [dict(from_file=a['file'], to_file=b['file'],
      rms_change_db=float(20*np.log10(max(b['rms'], 1e-12)/max(a['rms'], 1e-12))),
      centroid_change_hz=b['spectral_centroid_hz']-a['spectral_centroid_hz'])
      for a, b in zip(entry['windows'], entry['windows'][1:]) if 'error' not in a and 'error' not in b]
    if core.exists():
      entry['core'] = screen(core)
      rate, pcm = load(core)
      parts = [load(p) for p in windows]
      entry['core_matches_ordered_windows_exactly'] = bool(parts and all(r == rate for r, _ in parts)
          and np.array_equal(pcm, np.concatenate([wave for _, wave in parts])))
      seams = np.cumsum([len(wave) for _, wave in parts])[:-1]
      entry['seams'] = [dict(seconds=float(i/rate), sample_step=float(np.max(abs(pcm[i]-pcm[i-1])))) for i in seams]
    report['sessions'].append(entry)
    title = f'Session {number}'
    choices = ([core] if core.exists() else []) + windows
    options = ''.join(f'<option value="session_{number}/{html.escape(p.name)}">{html.escape("Full session" if p == core else p.stem.replace("_", " "))}</option>' for p in choices)
    player = (f'<select aria-label="Session {number} section">{options}</select><audio controls preload="metadata" src="session_{number}/{html.escape(choices[0].name)}"></audio>'
              if choices else '<p class="pending">Session audio is not available yet.</p>')
    metrics = entry.get('core', {})
    summary = (f'{metrics["seconds"]:.1f}s · peak {metrics["peak"]:.3f} · {metrics["samples_at_or_above_full_scale"]} full-scale samples'
               if metrics and 'error' not in metrics else 'Screening pending')
    cards.append(f'<section><h2>{title}</h2><p class="seed">Seed {seed["generation_seed"]}</p>{player}<p>{summary}</p></section>')
  (root / 'audio_screening.json').write_text(json.dumps(report, indent=2))
  page = '''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>RoadScore · Fresh hook review</title><style>
  :root{color-scheme:dark;font:16px system-ui;background:#101417;color:#eef2f4}body{max-width:980px;margin:40px auto;padding:0 24px}h1{font-size:32px;margin-bottom:12px}p{line-height:1.55;color:#c1cbd1}section{padding:24px;border:1px solid #344149;border-radius:16px;margin:20px 0}h2{margin:0}audio{width:100%;margin:12px 0}.seed{font:13px ui-monospace;color:#9cabb5}a{color:#91d7c5}select{padding:8px;margin-top:16px;background:#26383e;color:white;border:1px solid #61767f;border-radius:8px}li{padding:6px}button{background:#26383e;color:white;border:1px solid #61767f;border-radius:8px;padding:10px 16px;cursor:pointer}
  </style><h1>Fresh hook review</h1><p>Three fresh sessions, one policy. Listen for a recognizable hook, meaningful development, and a convincing return. All outputs stay here; no seed was selected for sounding best.</p><p>Mac MLX audition — native runtime equivalence is unverified. Audio is unchanged and never starts automatically. One player runs at a time.</p><button id="stop">Pause all</button>'''+''.join(cards)+'''<p><a href="audio_screening.json">Objective screening</a> · <a href="validation.json">Generation record</a></p><p>Clipping, silence, repeated-block and section-contrast checks flag technical properties. They do not establish musical quality or a memorable melody.</p><script>
  const players=[...document.querySelectorAll('audio')];
  for(const player of players)player.addEventListener('play',()=>{for(const other of players)if(other!==player)other.pause()});
  for(const select of document.querySelectorAll('select'))select.addEventListener('change',()=>{const player=select.parentElement.querySelector('audio');player.pause();player.src=select.value;player.load()});
  document.querySelector('#stop').addEventListener('click',()=>players.forEach(player=>player.pause()));
  </script></html>'''
  (root / 'listen.html').write_text(page)
  print(json.dumps([{'session': e['session'], 'windows': len(e['windows']), 'core': e['complete_core_available']} for e in report['sessions']]))


if __name__ == '__main__':
  main()
