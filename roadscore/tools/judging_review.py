"""Post-capture anonymous listening artifacts; never imported by runtime."""
import argparse
import html
import json
from pathlib import Path
import shutil
import soundfile as sf

DIMENSIONS = ['Musical quality', 'Development', 'Road responsiveness', 'Continuity', 'Event payoff', 'Arrival', 'Wow factor']


def build(root):
    review = root / 'review'
    review.mkdir(exist_ok=True, mode=0o700)
    sections = []
    for label in 'ABCDEFGHIJK':
        ledger = root / f'official_{label}.json'
        record = json.loads(ledger.read_text()) if ledger.exists() else {'phase': 'not started'}
        run_paths = record.get('run_paths', [])
        run = Path(run_paths[0]) if len(run_paths) == 1 else None
        figures = []
        technical = ""
        if run is not None and (run / "event_replay_audit.json").exists():
            audit = json.loads((run / "event_replay_audit.json").read_text())
            safe = {key: audit.get(key) for key in ("checks", "audio_seconds", "accepted_jobs", "accepted_music_holds", "navigation_present", "curve_activations", "input_time_violations")}
            technical = "<details><summary>Technical results · separate from ratings</summary><pre>"+html.escape(json.dumps(safe, indent=2))+"</pre></details>"
        if run is not None and (run / 'host_heard.flac').exists():
            target = review / label
            target.mkdir(exist_ok=True, mode=0o700)
            full = target / 'full.flac'
            if not full.exists():
                shutil.copy2(run / 'host_heard.flac', full)
            info = sf.info(full)
            duration = info.duration
            traces = [json.loads(s) for s in (run / 'trace.jsonl').read_text().splitlines()]
            cuts = [('representative', 0, min(120, duration))]
            curves = [t for t in traces if t.get('kind') == 'curve' and t.get('activation') is not None]
            if curves:
                peak = max(curves, key=lambda t: t.get('strength', 0))
                at = peak.get('elapsed', 0)
                cuts.append(('curve', max(0, at-20), min(duration, at+30)))
            nav = next((t for t in traces if t.get('nav', {}).get('valid')), None)
            if nav:
                at = nav.get('elapsed', 0)
                cuts.append(('navigation', max(0, at-15), min(duration, at+25)))
            if (run / 'ending.json').exists():
                cuts.append(('arrival', max(0, duration-45), duration))
            metadata = []
            for name, start, end in cuts:
                with sf.SoundFile(full) as source:
                    source.seek(round(start * source.samplerate))
                    audio = source.read(round((end-start)*source.samplerate), dtype='int16')
                    sf.write(target / f'{name}.flac', audio, source.samplerate, subtype='PCM_16')
                metadata.append({'name': name, 'start_seconds': start, 'end_seconds': end})
            (target / 'cuts.json').write_text(json.dumps(metadata, indent=2))
            for name in ['full'] + [c[0] for c in cuts]:
                figures.append(f'<p>{html.escape(name.title())}</p><audio controls preload="none" src="{label}/{name}.flac"></audio>')
        fields = ''.join(f'<label>{dimension}<input type="number" min="1" max="10" step="1" data-key="{label}:{dimension}"></label>' for dimension in DIMENSIONS)
        sections.append(f'<section><h2>Submission {label}</h2><p>{html.escape(record["phase"])}</p>'+''.join(figures)+technical+fields+f'<label>Notes<textarea data-key="{label}:notes"></textarea></label></section>')
    page = '''<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>RoadScore private listening review</title>
<style>body{font:17px system-ui;max-width:960px;margin:32px auto;padding:0 20px;background:#111827;color:#e5e7eb}section{background:#1f2937;border-radius:16px;padding:24px;margin:24px 0}audio{width:100%}label{display:inline-flex;flex-direction:column;margin:10px;gap:8px}input{width:80px}textarea{width:280px;height:70px}button,input,textarea{font:inherit;padding:8px}</style>
<h1>RoadScore · private listening review</h1><p>Anonymous submissions. No autoplay. Rate each dimension from 1–10. No winner is calculated. Technical reliability and musical preference remain separate. Excerpts follow fixed time/event rules, without musical cherry-picking.</p><button id="export">Save ratings locally</button>'''+''.join(sections)+'''
<script>
const key='roadscore-event-judging-v1';let scores={};try{scores=JSON.parse(localStorage.getItem(key)||'{}')}catch(e){}
for(const el of document.querySelectorAll('[data-key]')){el.value=scores[el.dataset.key]||'';el.addEventListener('input',()=>{scores[el.dataset.key]=el.value;try{localStorage.setItem(key,JSON.stringify(scores))}catch(e){}})}
document.querySelector('#export').onclick=()=>{const url=URL.createObjectURL(new Blob([JSON.stringify(scores,null,2)],{type:'application/json'}));const a=document.createElement('a');a.href=url;a.download='roadscore-private-ratings.json';a.click();URL.revokeObjectURL(url)};
</script>'''
    (review / 'index.html').write_text(page)
    return review / 'index.html'


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('root', type=Path)
    print(build(parser.parse_args().root))
